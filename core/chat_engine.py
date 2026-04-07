# -*- coding: utf-8 -*-
"""
聊天引擎核心模块
================

编排消息处理和流式输出的主逻辑。

核心架构：
- 主管 Agent（default）：负责理解用户意图、分发任务、汇总汇报
- 员工 Agent（用户创建的）：各司其职，绑定不同模型和技能
- @指派：用户通过 @员工名 直接指派任务
- FC（Function Calling）：主管通过 FC 调度员工和工具
- 关键词匹配：FC 不可用时的降级方案
"""

import os
import sys
import logging
import re
import json
import asyncio
from typing import List, Optional, AsyncGenerator

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 保持后台任务引用，防止被 GC 回收导致 "Task was destroyed" 警告
_background_tasks: set = set()

from core.security import sanitize_file_id, is_sensitive_request, get_reject_message
from core.model_router import build_llm_for_agent
from core.prompt_builder import build_system_prompt, build_title_prompt
from core.errors import friendly_error_message
from core.memory import get_memory_manager
from core.agents import get_agent_manager
from core.search import get_search_api_key, do_search
from core.llm_stream import (
    stream_llm_real as _stream_llm_real,
    aggregate_tool_calls as _aggregate_tool_calls,
    get_agent_api_key as _get_agent_api_key,
)
from core.chat_helpers import (
    parse_thinking as _parse_thinking,
    parse_mentions as _parse_mentions,
    build_history_text as _build_history_text,
    build_file_content as _build_file_content,
    build_chat_messages as _build_chat_messages,
)
from core.worker_executor import (
    stream_worker_content as _stream_worker_content,
    stream_worker_task as _stream_worker_task,
    _resolve_thinking_agent,
)
from core.fc_dispatcher import stream_with_fc as _stream_with_fc
from core.skill_executor import stream_skill_match as _stream_skill_match

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(project_root, "data")
_skills_loaded = False
_skills_lock = __import__("threading").Lock()


def _get_memory():
    return get_memory_manager(_DATA_DIR)


def _get_agent_manager():
    return get_agent_manager(_DATA_DIR)


def _ensure_skills():
    global _skills_loaded
    if _skills_loaded:
        return
    with _skills_lock:
        if _skills_loaded:
            return
        from skills import set_data_dir, load_builtin_skills, load_custom_skills, load_disabled, load_skill_configs
        set_data_dir(_DATA_DIR)
        load_builtin_skills()
        load_custom_skills()
        load_disabled()
        load_skill_configs()
        _skills_loaded = True


from core.model_info import (
    get_model_capabilities as _get_model_capabilities,
    model_supports_thinking as _model_supports_thinking,
    find_thinking_model as _find_thinking_model,
    find_model_with_capabilities as _find_model_with_capabilities,
)


def _model_supports_tool_use(model_id: str) -> bool:
    return "tool_use" in _get_model_capabilities(model_id)


async def _background_summary(memory, session_id: str):
    """后台异步生成摘要，不阻塞响应流"""
    try:
        await asyncio.to_thread(memory.generate_summary, session_id)
    except Exception as e:
        logger.warning(f"后台自动摘要失败: {e}")


def _schedule_background_task(coro):
    """调度后台任务并保持引用，防止 GC 回收"""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _generate_title(agent_config, user_input: str, ai_response: str, lang: str = "zh") -> Optional[str]:
    try:
        title_prompt = build_title_prompt(user_input, ai_response, lang)
        title_llm = build_llm_for_agent(agent_config)
        title_resp = await asyncio.to_thread(title_llm.call, messages=title_prompt)
        generated_title = str(title_resp).strip().strip('"').strip("'")
        if generated_title and len(generated_title) <= 30:
            return generated_title
    except Exception as e:
        logger.warning(f"生成标题失败: {e}")
    return None


async def _stream_normal_chat(agent_config, clean_input: str, original_input: str, session_id: str, memory, files, file_infos, enable_thinking=False, enable_search=False, lang="zh", tools=None) -> AsyncGenerator[str, None]:
    import time as _time
    _t0 = _time.monotonic()
    _original_model = agent_config.model_id
    if enable_thinking:
        agent_config = _resolve_thinking_agent(agent_config)
        if agent_config.model_id != _original_model:
            logger.warning(f"[normal_chat] 思考模式模型切换: {_original_model} → {agent_config.model_id} (原模型不支持thinking)")
    system_prompt = build_system_prompt(agent_config.name, lang=lang, enable_thinking=enable_thinking)
    if tools:
        system_prompt += (
            "\n\n## 可用工具\n"
            "你可以使用以下工具来完成用户的请求。当用户的需求可以通过工具完成时（如画图、生成图片、网页抓取、文字转语音等），**必须调用对应的工具**，不要用文字说你做不到：\n"
        )
        for t in tools:
            fname = t.get("function", {}).get("name", "")
            fdesc = t.get("function", {}).get("description", "")
            if fname:
                system_prompt += f"- {fname}: {fdesc}\n"
        system_prompt += (
            "\n**严格规则：每次只能调用一个工具**\n"
            "- 精准匹配用户意图，不要添加用户没有要求的功能\n"
            "- 用户说「画一只狗」→ 只调用 generate_image，绝不调用 text_to_speech\n"
        )
    context_messages = memory.get_context_messages(session_id)
    upload_dir = os.path.join(project_root, "data", "uploads")
    user_content = await _build_file_content(files, clean_input, upload_dir)
    messages = _build_chat_messages(system_prompt, context_messages, user_content)
    logger.info(f"[normal_chat] prompt构建耗时: {(_time.monotonic()-_t0)*1000:.0f}ms, history_msgs={len(context_messages)}")

    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    tool_call_chunks = []

    # [优化] 将用户消息保存与 LLM 调用并行执行，减少首字节延迟
    _t1 = _time.monotonic()
    _save_user_msg_task = asyncio.create_task(
        asyncio.to_thread(memory.add_message, "user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
    )

    try:
        _t2 = _time.monotonic()
        logger.info(f"[normal_chat] LLM请求发起 (add_message已异步, 准备耗时: {(_t2-_t0)*1000:.0f}ms)")
        _first_chunk_logged = False
        async for chunk in _stream_llm_real(messages, agent_config, tools=tools, enable_search=enable_search, enable_thinking=enable_thinking):
            if not _first_chunk_logged:
                logger.info(f"[normal_chat] 首个chunk耗时: {(_time.monotonic()-_t2)*1000:.0f}ms (从LLM请求发起到首个响应)")
                _first_chunk_logged = True
            chunk_type = chunk.get("type", "")
            chunk_content = chunk.get("content", "")

            if chunk_type == "thinking":
                full_thinking_parts.append(chunk_content)
                yield json.dumps({"type": "thinking", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "content":
                full_response_parts.append(chunk_content)
                yield json.dumps({"type": "content", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "tool_calls":
                tool_call_chunks.append(chunk["tool_calls"])

        if tool_call_chunks:
            _ensure_skills()
            from skills import execute_tool_by_name
            aggregated = _aggregate_tool_calls(tool_call_chunks)
            
            # 限制：只执行第一个工具调用，避免LLM过度调用多个不相关的工具
            if len(aggregated) > 1:
                logger.warning(f"[normal_chat] LLM返回了{len(aggregated)}个工具调用，只执行第一个: {[tc.get('function', {}).get('name', '') for tc in aggregated]}")
                aggregated = aggregated[:1]
            
            for tc in aggregated:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")
                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                yield json.dumps({"type": "tool_start", "tool_name": func_name}, ensure_ascii=False) + "\n"
                tool_result = await asyncio.to_thread(execute_tool_by_name, func_name, func_args)
                result_msg = tool_result.get("message", "")
                _t, _c = _parse_thinking(result_msg)
                if _t and enable_thinking:
                    yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                if _c:
                    yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                    full_response_parts.append(_c)

        full_response = "".join(full_response_parts)
        full_thinking = "".join(full_thinking_parts)

        # [优化] 确保用户消息已保存完成，再保存助手消息（防止并发写入丢失）
        await _save_user_msg_task
        logger.info(f"[normal_chat] add_message(user)异步完成, 耗时: {(_time.monotonic()-_t1)*1000:.0f}ms")

        ai_meta = {}
        if full_thinking:
            ai_meta["thinking"] = full_thinking
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        msg_count = len(memory.get_messages(session_id))
        if msg_count > 0 and msg_count % memory.SUMMARY_THRESHOLD == 0:
            _schedule_background_task(_background_summary(memory, session_id))

        done_event = {"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id}
        yield json.dumps(done_event, ensure_ascii=False) + "\n"

        if msg_count <= 2:
            title = await _generate_title(agent_config, original_input, full_response, lang)
            if title:
                yield json.dumps({"type": "title", "title": title}, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"流式对话失败: {e}")
        # 确保异步保存任务完成，避免孤立任务
        try:
            await _save_user_msg_task
        except Exception:
            pass
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"


def get_welcome_message(agent_name: str = "GymClaw") -> str:
    return (
        f"你好！我是 {agent_name}，你的 AI 助手。\n\n"
        "我可以帮你：\n"
        "- 💬 聊天对话、翻译、文档总结\n"
        "- 🖼️ 生成图片、数据分析图表\n"
        "- 🔊 文字转语音、音视频转写\n"
        "- 🌐 网页抓取、联网搜索报告\n"
        "- 📧 发送邮件、任务管理、定时提醒\n"
        "- 📚 知识库问答、代码执行\n\n"
        "有什么可以帮你的吗？"
    )


async def process_message(
    user_input: str,
    session_id: str = "default",
    agent_id: str = "default",
    files: List[str] = None,
    enable_thinking: bool = False,
    enable_search: bool = False,
    lang: str = "zh",
) -> dict:
    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    async for chunk in stream_message(
        user_input=user_input,
        session_id=session_id,
        agent_id=agent_id,
        files=files,
        enable_thinking=enable_thinking,
        enable_search=enable_search,
        lang=lang,
    ):
        try:
            data = json.loads(chunk)
            if data.get("type") == "content":
                full_response_parts.append(data.get("content", ""))
            elif data.get("type") == "thinking":
                full_thinking_parts.append(data.get("content", ""))
        except Exception:
            pass
    full_response = "".join(full_response_parts)
    full_thinking = "".join(full_thinking_parts)
    result = {"response": full_response}
    if full_thinking:
        result["thinking"] = full_thinking
    return result


async def stream_message(
    user_input: str,
    session_id: str = "default",
    agent_id: str = "default",
    files: List[str] = None,
    enable_thinking: bool = False,
    enable_search: bool = False,
    lang: str = "zh",
) -> AsyncGenerator[str, None]:
    """
    核心消息处理入口

    执行路径（优先级从高到低）：
    1. @指派：用户消息包含 @员工名 → 直接指派给员工
    2. 安全检查：敏感内容拒绝
    3. 联网搜索：enable_search 时注入搜索结果
    4. FC 调度：主管模型支持 tool_use 且有员工 → FC 调度员工和工具
    5. 关键词匹配：匹配内置技能
    6. 普通对话
    """
    import time as _time
    _t0 = _time.monotonic()
    memory = _get_memory()
    manager = _get_agent_manager()
    agent = manager.get_agent(agent_id)
    if not agent:
        agent = manager.get_agent("default")

    if enable_thinking:
        from dataclasses import asdict
        from core.agents import AgentConfig
        override = asdict(agent)
        override["enable_thinking"] = True
        agent = AgentConfig(**override)

    file_infos = []
    if files:
        upload_dir = os.path.join(project_root, "data", "uploads")
        for f in files:
            file_id = sanitize_file_id(f)
            file_infos.append({
                "file_id": file_id,
                "filename": os.path.basename(f),
                "url": f"/api/files/{file_id}",
            })

    clean_input, mentions = _parse_mentions(user_input)
    logger.info(f"[stream_message] 初始化耗时: {(_time.monotonic()-_t0)*1000:.0f}ms, agent={agent.name}, model={agent.model_id}, thinking={enable_thinking}")

    search_via_tool = False
    if enable_search:
        search_key = get_search_api_key()
        agent_key = _get_agent_api_key(agent)
        if search_key and agent_key and search_key == agent_key:
            search_via_tool = True
        else:
            search_results = await do_search(clean_input)
            if search_results:
                clean_input = clean_input + "\n\n---\n以下是与用户问题相关的联网搜索结果，请基于这些信息回答：\n\n" + search_results + "\n---\n"
            else:
                logger.warning("Path B 联网搜索未返回结果，降级为无搜索对话")

    # 路径 1：@指派
    if mentions:
        for mention_name in mentions:
            worker = manager.get_agent_by_name(mention_name)
            if worker:
                yield json.dumps({"type": "worker", "worker_name": worker.name, "worker_model": worker.model_id}, ensure_ascii=False) + "\n"
                async for chunk in _stream_worker_task(worker, clean_input, user_input, session_id, memory, lang, enable_thinking=enable_thinking, file_infos=file_infos, generate_title_fn=_generate_title):
                    yield chunk
                return

    # 路径 2：安全检查
    if is_sensitive_request(clean_input):
        yield json.dumps({"type": "content", "content": get_reject_message(lang)}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "done", "agent_name": agent.name, "model_id": agent.model_id}, ensure_ascii=False) + "\n"
        return

    # 路径 3：FC 调度
    if _model_supports_tool_use(agent.model_id):
        workers = manager.list_workers()
        if workers:
            logger.info(f"[路径3-FC] 检测到 {len(workers)} 个员工，走 FC 调度, 路由耗时: {(_time.monotonic()-_t0)*1000:.0f}ms")
            async for chunk in _stream_with_fc(
                agent, clean_input, user_input, session_id, memory, files, file_infos,
                get_agent_manager_fn=_get_agent_manager, ensure_skills_fn=_ensure_skills,
                generate_title_fn=_generate_title, schedule_bg_task_fn=lambda m, sid: _schedule_background_task(_background_summary(m, sid)),
                enable_search=search_via_tool, enable_thinking=enable_thinking, lang=lang,
            ):
                yield chunk
            return
        else:
            # 无员工但模型支持 tool_use → 轻量 FC：普通对话 + 技能工具
            _ts = _time.monotonic()
            _ensure_skills()
            _skill_load_ms = (_time.monotonic() - _ts) * 1000
            from skills import get_all_tool_schemas
            skill_tools = get_all_tool_schemas()
            if skill_tools:
                logger.info(f"[路径3-FC轻量] 无员工，注入 {len(skill_tools)} 个技能工具, 技能加载耗时: {_skill_load_ms:.0f}ms, 总路由耗时: {(_time.monotonic()-_t0)*1000:.0f}ms")
                async for chunk in _stream_normal_chat(agent, clean_input, user_input, session_id, memory, files, file_infos, enable_thinking=enable_thinking, enable_search=search_via_tool, lang=lang, tools=skill_tools):
                    yield chunk
                return
            logger.debug("[路径3-FC] 无员工且无技能工具，走普通对话")

    # 路径 4：关键词匹配
    _ensure_skills()
    from skills import match_skill, match_skill_for_agent
    matched = None
    if agent.skills:
        matched = match_skill_for_agent(clean_input, agent.skills)
    if not matched:
        matched = match_skill(clean_input)
    if matched:
        async for chunk in _stream_skill_match(agent, matched, clean_input, user_input, session_id, memory, files, file_infos, generate_title_fn=_generate_title, enable_thinking=enable_thinking, lang=lang):
            yield chunk
        return

    # 路径 5：普通对话
    async for chunk in _stream_normal_chat(agent, clean_input, user_input, session_id, memory, files, file_infos, enable_thinking=enable_thinking, enable_search=search_via_tool, lang=lang):
        yield chunk
