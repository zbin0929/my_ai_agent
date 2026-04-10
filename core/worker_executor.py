# -*- coding: utf-8 -*-
"""
员工执行模块
============

处理员工（Worker Agent）的任务执行逻辑，包含：
- Runner 型员工：直接执行绑定的技能工具
- Smart/Agent 型员工：通过 LLM 思考后执行
- 流式内容生成和工具调用处理

从 chat_engine.py 拆分而来，保持原有逻辑不变。
"""

import json
import asyncio
import logging
from typing import AsyncGenerator, Optional

from core.llm_stream import (
    stream_llm_real as _stream_llm_real,
    aggregate_tool_calls as _aggregate_tool_calls,
)
from core.chat_helpers import parse_thinking as _parse_thinking
from core.errors import friendly_error_message

logger = logging.getLogger(__name__)


def _resolve_thinking_agent(agent_config):
    """如果启用了思考模式，自动切换到支持思考的模型"""
    from core.model_info import model_supports_thinking, find_thinking_model
    if not getattr(agent_config, 'enable_thinking', False):
        return agent_config
    if model_supports_thinking(agent_config.model_id):
        return agent_config
    thinking_model_id = find_thinking_model()
    if thinking_model_id:
        from dataclasses import asdict
        from core.agents import AgentConfig
        override = asdict(agent_config)
        override["model_id"] = thinking_model_id
        return AgentConfig(**override)
    return agent_config


async def stream_worker_content(worker_agent, task_input: str, enable_thinking: bool = False, enable_search: bool = False, lang: str = "zh", result: dict = None, specified_skill: str = None, files: list = None) -> AsyncGenerator[str, None]:
    """执行员工内容生成（runner 或 LLM），yield SSE 事件字符串。累计文本存入 result dict。
    
    Args:
        specified_skill: 主管指定的技能 ID，如果提供则优先使用该技能
        files: 上传的文件 ID 列表
    """
    from skills import get_tool_schemas_by_skill_ids, get_skills_for_agent, execute_tool_by_name

    full_response = ""
    full_thinking = ""
    worker_type = worker_agent.get_agent_type()

    if worker_type == "runner":
        worker_skill_ids = worker_agent.skills or []
        if worker_skill_ids:
            from skills import match_skill_for_agent
            matched_skill = None
            
            # 优先使用主管指定的技能
            if specified_skill and specified_skill in worker_skill_ids:
                agent_skills = get_skills_for_agent(worker_skill_ids)
                for sk in agent_skills:
                    if sk.get("id") == specified_skill:
                        matched_skill = sk
                        logger.info(f"[worker] 使用主管指定的技能: {specified_skill}")
                        break
            
            # 如果没有指定或指定的技能不存在，使用关键词匹配
            if not matched_skill:
                matched_skill = match_skill_for_agent(task_input, worker_skill_ids)
            
            # 如果还是没有匹配到，尝试智能推断
            if not matched_skill:
                agent_skills = get_skills_for_agent(worker_skill_ids)
                doc_keywords = ["分析", "总结", "摘要", "归纳", "文档", "文件", "报告"]
                if any(kw in task_input for kw in doc_keywords):
                    for sk in agent_skills:
                        if sk.get("id") == "doc_summary":
                            matched_skill = sk
                            break
                # 如果还是没匹配，使用第一个技能作为默认
                if not matched_skill and agent_skills:
                    matched_skill = agent_skills[0]
            
            if matched_skill:
                tool_schema = matched_skill.get("tool_schema")
                handler = matched_skill.get("handler")
                if tool_schema and handler:
                    tool_name = tool_schema.get("function", {}).get("name", "")
                    tool_args = {}
                    params = tool_schema.get("function", {}).get("parameters", {}).get("properties", {})
                    if "prompt" in params:
                        tool_args["prompt"] = task_input
                    elif "text" in params:
                        tool_args["text"] = task_input
                    elif "url" in params:
                        tool_args["url"] = task_input
                    else:
                        first_param = next(iter(params), None)
                        if first_param:
                            tool_args[first_param] = task_input

                    yield json.dumps({"type": "tool_start", "tool_name": tool_name}, ensure_ascii=False) + "\n"
                    # 直接调用 handler 并传递 files 上下文
                    context = {"tool_args": tool_args, "files": files or [], "skill_id": matched_skill.get("id")}
                    tool_result = await asyncio.to_thread(handler, task_input, context)
                    result_msg = tool_result.get("message", "")
                    _t, _c = _parse_thinking(result_msg)
                    if _t and enable_thinking:
                        yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                        full_thinking += _t
                    if _c:
                        yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                        full_response += _c
        else:
            full_response = f"{worker_agent.name} 没有绑定任何技能" if lang == "zh" else f"{worker_agent.name} has no skills assigned"
            yield json.dumps({"type": "content", "content": full_response}, ensure_ascii=False) + "\n"
    else:
        if enable_thinking:
            worker_agent = _resolve_thinking_agent(worker_agent)
        role_desc = worker_agent.role or worker_agent.description or "一个AI助手"
        system_prompt = f"你是{worker_agent.name}，{role_desc}。\n\n请用中文回复。" if lang == "zh" else f"You are {worker_agent.name}, {role_desc}."

        worker_skill_ids = worker_agent.skills or []
        worker_tools = None
        if worker_skill_ids:
            agent_skills = get_skills_for_agent(worker_skill_ids)
            if agent_skills:
                if lang == "zh":
                    system_prompt += "\n\n你擅长以下技能，请根据任务需要使用："
                else:
                    system_prompt += "\n\nYou have the following skills, use them as needed:"
                for sk in agent_skills:
                    system_prompt += f"\n- {sk['name']}：{sk['description']}"
                worker_tools = get_tool_schemas_by_skill_ids(worker_skill_ids)

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": task_input}]

        response_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_call_chunks = []

        async for chunk in _stream_llm_real(messages, worker_agent, tools=worker_tools, enable_search=enable_search, enable_thinking=enable_thinking):
            chunk_type = chunk.get("type", "")
            chunk_content = chunk.get("content", "")

            if chunk_type == "thinking":
                thinking_parts.append(chunk_content)
                yield json.dumps({"type": "thinking", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "content":
                response_parts.append(chunk_content)
                yield json.dumps({"type": "content", "content": chunk_content}, ensure_ascii=False) + "\n"
            elif chunk_type == "tool_calls":
                tool_call_chunks.append(chunk["tool_calls"])

        if tool_call_chunks:
            aggregated = _aggregate_tool_calls(tool_call_chunks)
            
            # 限制：只执行第一个工具调用
            if len(aggregated) > 1:
                logger.warning(f"[worker] LLM返回了{len(aggregated)}个工具调用，只执行第一个")
                aggregated = aggregated[:1]
            
            for tc in aggregated:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")
                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                yield json.dumps({"type": "tool_start", "tool_name": func_name}, ensure_ascii=False) + "\n"
                import inspect as _inspect
                from skills import get_skill_by_tool_name as _get_skill_by_tool
                _skill = _get_skill_by_tool(func_name)
                if _skill and _skill.get("handler") and _inspect.isasyncgenfunction(_skill["handler"]):
                    _user_input = func_args.get("prompt") or func_args.get("text") or func_args.get("url") or str(func_args)
                    _ctx = {"tool_args": func_args, "files": files, "file_paths": files, "enable_thinking": enable_thinking}
                    async for _chunk in _skill["handler"](_user_input, _ctx):
                        if _chunk:
                            yield json.dumps({"type": "content", "content": _chunk}, ensure_ascii=False) + "\n"
                            response_parts.append(_chunk)
                else:
                    tool_result = await asyncio.to_thread(execute_tool_by_name, func_name, func_args, files)
                    result_msg = tool_result.get("message", "")
                    _t, _c = _parse_thinking(result_msg)
                    if _t and enable_thinking:
                        yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                    if _c:
                        yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                        response_parts.append(_c)

        full_response = "".join(response_parts)
        full_thinking = "".join(thinking_parts)

    if result is not None:
        result["response"] = full_response
        result["thinking"] = full_thinking


async def stream_worker_task(worker_agent, clean_input: str, original_input: str, session_id: str, memory, lang: str, enable_thinking: bool = False, file_infos: list = None, generate_title_fn=None) -> AsyncGenerator[str, None]:
    """完整的员工任务执行流程：执行 + 保存消息 + 生成标题"""
    result = {}
    try:
        async for chunk in stream_worker_content(worker_agent, clean_input, enable_thinking=enable_thinking, lang=lang, result=result):
            yield chunk

        full_response = result.get("response", "")
        full_thinking = result.get("thinking", "")

        memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
        ai_meta = {"agents": [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]}
        if full_thinking:
            ai_meta["thinking"] = full_thinking
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        done_event = {"type": "done", "agent_name": worker_agent.name, "model_id": worker_agent.model_id, "agents": [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]}
        msg_count = len(memory.get_messages(session_id))
        yield json.dumps(done_event, ensure_ascii=False) + "\n"

        if msg_count <= 2 and generate_title_fn:
            title = await generate_title_fn(worker_agent, original_input, full_response, lang)
            if title:
                yield json.dumps({"type": "title", "title": title}, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"员工 {worker_agent.name} 执行失败: {e}")
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"
