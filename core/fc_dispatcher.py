# -*- coding: utf-8 -*-
"""
FC 调度模块
===========

主管 Agent 通过 Function Calling 调度员工和工具的逻辑。

从 chat_engine.py 拆分而来，保持原有逻辑不变。
"""

import os
import re
import json
import asyncio
import logging
from typing import AsyncGenerator

from core.llm_stream import (
    stream_llm_real as _stream_llm_real,
    aggregate_tool_calls as _aggregate_tool_calls,
)
from core.chat_helpers import (
    parse_thinking as _parse_thinking,
    build_history_text as _build_history_text,
    build_file_content as _build_file_content,
    build_chat_messages as _build_chat_messages,
)
from core.errors import friendly_error_message
from core.worker_executor import stream_worker_content, _resolve_thinking_agent

logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_manager_system_prompt(agent_config, get_agent_manager_fn, ensure_skills_fn, lang: str = "zh") -> str:
    """构建主管 Agent 的 system prompt，包含团队成员信息和工具使用规则"""
    manager = get_agent_manager_fn()
    workers = manager.list_workers()

    base_prompt = (
        f"你是 {agent_config.name}，一个团队的「主管」。\n"
        f"你的职责是理解用户的需求，决定是自己回答还是分配给团队成员。\n\n"
    )

    if workers:
        base_prompt += "## 你的团队成员\n\n"
        for w in workers:
            role_desc = w.role or w.description or "通用助手"
            info = f"- **{w.name}**（模型: {w.model_id}）：{role_desc}"
            if w.skills:
                ensure_skills_fn()
                from skills import get_skills_for_agent
                agent_skills = get_skills_for_agent(w.skills)
                if agent_skills:
                    info += "，技能：" + "、".join(s["name"] for s in agent_skills)
            base_prompt += info + "\n"
        base_prompt += "\n当需要用到团队成员的能力时，使用对应的 assign_to 工具来分配任务。\n"

    base_prompt += (
        "\n## 工具使用规则（必须严格遵守）\n"
        "1. 当用户请求可以通过工具完成时，调用对应的工具\n"
        "2. **严禁同时调用多个工具** — 每次请求只能调用一个工具\n"
        "3. 精准匹配用户意图，不要添加用户没有要求的功能\n"
        "4. **文档分析优先**：当用户上传了文件并要求分析/总结/理解时，使用 summarize_document 工具\n"
        "5. **翻译仅限明确请求**：只有用户明确说「翻译」「translate」时才调用翻译工具\n"
        "\n## 示例\n"
        "- 用户上传文件说「分析这个文档」→ 调用 summarize_document\n"
        "- 用户上传文件说「帮我总结」→ 调用 summarize_document\n"
        "- 用户说「翻译这段话」→ 调用 translate_text\n"
        "- 用户说「画一只狗」→ 调用 generate_image\n"
        "- 用户说「朗读这段话」→ 调用 text_to_speech\n"
    )

    if lang == "zh":
        base_prompt += "\n请用中文回复。"
    else:
        base_prompt += "\nPlease respond in English."

    return base_prompt


async def stream_with_fc(
    agent_config, clean_input: str, original_input: str, session_id: str,
    memory, files, file_infos,
    get_agent_manager_fn, ensure_skills_fn, generate_title_fn,
    schedule_bg_task_fn,
    enable_search=False, enable_thinking=False, lang="zh",
) -> AsyncGenerator[str, None]:
    """主管 FC 模式 — 通过 Function Calling 调度员工和工具"""
    import time as _time
    _t0 = _time.monotonic()
    logger.info(f"[FC调度] 开始执行, agent={agent_config.name}, enable_thinking={enable_thinking}, clean_input={clean_input[:50]}")
    _original_model = agent_config.model_id
    if enable_thinking:
        agent_config = _resolve_thinking_agent(agent_config)
        if agent_config.model_id != _original_model:
            logger.warning(f"[FC调度] 思考模式模型切换: {_original_model} → {agent_config.model_id}")
    from skills import get_unassigned_tool_schemas, get_tool_schemas_by_skill_ids, execute_tool_by_name, get_skills_for_agent

    ensure_skills_fn()

    system_prompt = build_manager_system_prompt(agent_config, get_agent_manager_fn, ensure_skills_fn, lang)
    context_messages = memory.get_context_messages(session_id)
    upload_dir = os.path.join(project_root, "data", "uploads")
    user_content = await _build_file_content(files, clean_input, upload_dir)
    messages = _build_chat_messages(system_prompt, context_messages, user_content)

    # [优化] 将用户消息保存与后续处理并行执行
    _save_user_msg_task = asyncio.create_task(
        asyncio.to_thread(memory.add_message, "user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
    )

    manager = get_agent_manager_fn()
    workers = manager.list_workers()
    worker_map = {}
    worker_skills_map: dict = {}
    agents_involved = [{"name": agent_config.name, "model_id": agent_config.model_id, "role": "manager"}]

    assigned_skill_ids: set = set()
    worker_tool_definitions = []
    for idx, w in enumerate(workers):
        if w.skills:
            for sid in w.skills:
                assigned_skill_ids.add(sid)
            worker_skills_map[w.name] = w.skills

        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', w.name).lower()
        if not safe_name:
            safe_name = f"worker_{idx + 1}"
        existing_names = {d["function"]["name"] for d in worker_tool_definitions}
        candidate = f"assign_to_{safe_name}"
        if candidate in existing_names:
            candidate = f"assign_to_{safe_name}_{idx + 1}"
        role_desc = w.role or w.description or "通用助手"
        desc = f"将任务分配给员工「{w.name}」处理。{w.name}的职责：{role_desc}。使用的模型：{w.model_id}。"
        
        # 构建技能枚举和描述
        skill_enum = []
        skill_desc_parts = []
        if w.skills:
            agent_skills = get_skills_for_agent(w.skills)
            if agent_skills:
                for sk in agent_skills:
                    skill_enum.append(sk["id"])
                    skill_desc_parts.append(f"{sk['id']}({sk['name']})")
                desc += "擅长技能：" + "、".join(s["name"] for s in agent_skills) + "。"
        
        # 构建工具参数
        tool_params = {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": f"要交给{w.name}处理的任务描述",
                },
            },
            "required": ["task"],
        }
        
        # 如果员工有多个技能，添加 skill 参数让主管指定
        if len(skill_enum) > 1:
            tool_params["properties"]["skill"] = {
                "type": "string",
                "description": f"指定{w.name}使用的技能：" + "、".join(skill_desc_parts),
                "enum": skill_enum,
            }
        
        worker_tool_definitions.append({
            "type": "function",
            "function": {
                "name": candidate,
                "description": desc,
                "parameters": tool_params,
            },
        })
        worker_map[candidate] = w

    tools = get_unassigned_tool_schemas(assigned_skill_ids) + worker_tool_definitions
    logger.info(f"[FC调度] 工具列表: {[t.get('function', {}).get('name', 'unknown') for t in tools]}")

    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    tool_call_chunks = []

    try:
        logger.info(f"[FC调度] 调用LLM, model={agent_config.model_id}, 准备耗时: {(_time.monotonic()-_t0)*1000:.0f}ms")
        async for chunk in _stream_llm_real(messages, agent_config, tools=tools if tools else None, enable_search=enable_search, enable_thinking=enable_thinking):
            chunk_type = chunk.get("type", "")
            chunk_content = chunk.get("content", "")

            if chunk_type == "thinking":
                full_thinking_parts.append(chunk_content)
                yield json.dumps({"type": "thinking", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "content":
                full_response_parts.append(chunk_content)
                yield json.dumps({"type": "content", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "tool_calls":
                logger.info(f"[FC调度] 收到tool_calls: {chunk['tool_calls']}")
                tool_call_chunks.append(chunk["tool_calls"])

        full_response = "".join(full_response_parts)
        full_thinking = "".join(full_thinking_parts)

        if tool_call_chunks:
            aggregated = _aggregate_tool_calls(tool_call_chunks)
            
            # 限制：只执行第一个工具调用，避免LLM过度调用多个不相关的工具
            if len(aggregated) > 1:
                logger.warning(f"[FC调度] LLM返回了{len(aggregated)}个工具调用，只执行第一个: {[tc.get('function', {}).get('name', '') for tc in aggregated]}")
                aggregated = aggregated[:1]

            for tc in aggregated:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")

                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                if func_name.startswith("assign_to_") and func_name in worker_map:
                    worker = worker_map[func_name]
                    task_desc = func_args.get("task", clean_input)
                    specified_skill = func_args.get("skill")  # 主管指定的技能
                    yield json.dumps({"type": "worker", "worker_name": worker.name, "worker_model": worker.model_id}, ensure_ascii=False) + "\n"

                    agents_involved.append({"name": worker.name, "model_id": worker.model_id, "role": "worker"})

                    w_result = {}
                    async for chunk in stream_worker_content(worker, task_desc, enable_thinking=enable_thinking, enable_search=enable_search, lang=lang, result=w_result, specified_skill=specified_skill, files=files):
                        yield chunk
                    full_response += w_result.get("response", "")
                    full_thinking += w_result.get("thinking", "")

                else:
                    yield json.dumps({"type": "tool_start", "tool_name": func_name}, ensure_ascii=False) + "\n"
                    from skills import get_skill_by_tool_name
                    import inspect as _inspect
                    skill = get_skill_by_tool_name(func_name)
                    if skill and skill.get("handler"):
                        user_input_for_skill = func_args.get("prompt") or func_args.get("text") or func_args.get("url") or str(func_args)
                        if _inspect.isasyncgenfunction(skill["handler"]):
                            context_for_skill = {"files": files, "agent_config": agent_config, "tool_args": func_args, "enable_thinking": enable_thinking}
                            content = ""
                            async for _chunk in skill["handler"](user_input_for_skill, context_for_skill):
                                if _chunk:
                                    yield json.dumps({"type": "content", "content": _chunk}, ensure_ascii=False) + "\n"
                                    content += _chunk
                            tool_result = None
                        else:
                            context_for_skill = {"files": files, "agent_config": agent_config, "tool_args": func_args}
                            tool_result = await asyncio.to_thread(skill["handler"], user_input_for_skill, context_for_skill)
                    else:
                        tool_result = await asyncio.to_thread(execute_tool_by_name, func_name, func_args, files)
                    if tool_result is not None:
                        result_msg = tool_result.get("message", "")
                        thinking, content = _parse_thinking(result_msg)
                        if thinking and enable_thinking:
                            yield json.dumps({"type": "thinking", "content": thinking}, ensure_ascii=False) + "\n"
                        if content:
                            yield json.dumps({"type": "content", "content": content}, ensure_ascii=False) + "\n"
                            full_response += content

        ai_meta = {}
        if full_thinking:
            ai_meta["thinking"] = full_thinking
        if len(agents_involved) > 1:
            ai_meta["agents"] = agents_involved
        # [优化] 确保用户消息已保存完成
        await _save_user_msg_task
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        msg_count = len(memory.get_messages(session_id))
        if msg_count > 0 and msg_count % memory.SUMMARY_THRESHOLD == 0:
            from core.memory import get_memory_manager
            schedule_bg_task_fn(memory, session_id)

        done_event = {"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id}
        if len(agents_involved) > 1:
            done_event["agents"] = agents_involved
        yield json.dumps(done_event, ensure_ascii=False) + "\n"

        if msg_count <= 2:
            title = await generate_title_fn(agent_config, original_input, full_response, lang)
            if title:
                yield json.dumps({"type": "title", "title": title}, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"FC 流式对话失败: {e}")
        try:
            await _save_user_msg_task
        except Exception:
            pass
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"
