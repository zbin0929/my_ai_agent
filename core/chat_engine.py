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
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.security import sanitize_file_id, is_safe_upload_path, is_sensitive_request, get_reject_message, is_safe_url
from core.model_router import build_llm_for_task, build_llm_for_agent
from core.prompt_builder import build_system_prompt, build_title_prompt
from core.errors import friendly_error_message
from core.memory import get_memory_manager
from core.agents import get_agent_manager
from core.search import get_search_api_key, do_search

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(project_root, "data")
_skills_loaded = False
_skills_lock = __import__("threading").Lock()
_shared_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


def _get_memory():
    return get_memory_manager(_DATA_DIR)


def _get_agent_manager():
    return get_agent_manager(_DATA_DIR)


async def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        return _shared_client
    async with _client_lock:
        if _shared_client is not None and not _shared_client.is_closed:
            return _shared_client
        _shared_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return _shared_client


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


def _parse_thinking(text: str) -> tuple[str, str]:
    thinking = ""
    content = text
    think_patterns = [
        (r'<think[^>]*>(.*?)</think\s*>', re.DOTALL),
        (r'<thinking[^>]*>(.*?)</thinking\s*>', re.DOTALL),
    ]
    for pattern, flags in think_patterns:
        m = re.search(pattern, content, flags)
        if m:
            thinking = m.group(1).strip()
            content = content[:m.start()] + content[m.end():]
            content = content.strip()
            break
    
    THINK_START = "<think_process>"
    THINK_END = "</think_process>"
    if not thinking and content.startswith(THINK_START):
        parts = content.split("\n\n", 1)
        if len(parts) == 2:
            thinking = parts[0][len(THINK_START):].strip()
            content = parts[1].strip()
        else:
            if content.endswith(THINK_END):
                thinking = content[len(THINK_START):-len(THINK_END)].strip()
                content = ""
    
    return thinking, content


def _get_lang() -> str:
    return "zh"


def _get_agent_api_key(agent_config) -> str:
    key, _ = _resolve_agent_connection(agent_config)
    return key


def _resolve_agent_connection(agent_config) -> Tuple[str, str]:
    if agent_config.custom_api_key:
        api_key = agent_config.custom_api_key
        base_url = agent_config.custom_base_url or ""
        return api_key, base_url

    try:
        from core.config_loader import get_config
        config = get_config(os.path.join(project_root, "config"))
        for provider in config.get("llm_providers", []):
            if provider["id"] == agent_config.model_provider:
                provider_api_key = provider.get("api_key", "")
                if provider_api_key:
                    return provider_api_key, provider.get("base_url", "")
                env_key = provider.get("env_key", "")
                api_key = os.environ.get(env_key, "")
                if api_key:
                    return api_key, provider.get("base_url", "")
                return "", provider.get("base_url", "")
    except Exception:
        pass

    return "", ""


def _resolve_file_paths(files: List[str], upload_dir: str) -> List[str]:
    if not files:
        return []
    resolved = []
    for f in files:
        if os.path.isabs(f):
            resolved.append(f)
        else:
            path = os.path.join(upload_dir, f)
            if os.path.exists(path):
                resolved.append(path)
    return resolved


def _parse_mentions(user_input: str) -> Tuple[str, List[str]]:
    mentions = re.findall(r'@(\S+)', user_input)
    clean = re.sub(r'@\S+\s*', '', user_input).strip()
    return clean, mentions


from core.model_info import (
    get_model_capabilities as _get_model_capabilities,
    model_supports_thinking as _model_supports_thinking,
    find_thinking_model as _find_thinking_model,
    find_model_with_capabilities as _find_model_with_capabilities,
)


def _model_supports_tool_use(model_id: str) -> bool:
    return "tool_use" in _get_model_capabilities(model_id)


def _resolve_thinking_agent(agent_config):
    if not getattr(agent_config, 'enable_thinking', False):
        return agent_config
    if _model_supports_thinking(agent_config.model_id):
        return agent_config
    thinking_model_id = _find_thinking_model()
    if thinking_model_id:
        from dataclasses import asdict
        override = asdict(agent_config)
        override["model_id"] = thinking_model_id
        from core.agents import AgentConfig
        return AgentConfig(**override)
    return agent_config


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


def _build_history_text(context_messages: list, agent_name: str) -> str:
    if not context_messages:
        return ""
    parts = []
    for msg in context_messages[-20:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"用户: {content}")
        elif role == "assistant":
            parts.append(f"{agent_name}: {content}")
    return "\n".join(parts)


def _build_file_content_sync(files: List[str], user_input: str, upload_dir: str) -> str:
    if not files:
        return user_input
    resolved = _resolve_file_paths(files, upload_dir)
    file_parts = []
    for f in resolved:
        if not is_safe_upload_path(upload_dir, f):
            continue
        file_id = sanitize_file_id(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read(5000)
                file_parts.append(f"[文件 {file_id}]:\n{content}")
        except Exception:
            file_parts.append(f"[文件 {file_id}]: (无法读取)")
    file_text = "\n\n".join(file_parts)
    if file_text:
        return f"{user_input}\n\n---\n附件内容:\n{file_text}"
    return user_input


async def _build_file_content(files: List[str], user_input: str, upload_dir: str) -> str:
    if not files:
        return user_input
    return await asyncio.to_thread(_build_file_content_sync, files, user_input, upload_dir)


def _build_chat_messages(system_prompt: str, history_text: str, user_content: str) -> list:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_text:
        messages.append({"role": "system", "content": f"对话历史:\n{history_text}"})
    messages.append({"role": "user", "content": user_content})
    return messages


def _build_manager_system_prompt(agent_config, lang: str = "zh") -> str:
    manager = _get_agent_manager()
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
                _ensure_skills()
                from skills import get_skills_for_agent
                agent_skills = get_skills_for_agent(w.skills)
                if agent_skills:
                    info += "，技能：" + "、".join(s["name"] for s in agent_skills)
            base_prompt += info + "\n"
        base_prompt += "\n当需要用到团队成员的能力时，使用对应的 assign_to 工具来分配任务。\n"

    if lang == "zh":
        base_prompt += "\n请用中文回复。"
    else:
        base_prompt += "\nPlease respond in English."

    return base_prompt


async def _stream_llm_real(messages, agent_config, tools=None, enable_search=False, enable_thinking=False) -> AsyncGenerator[dict, None]:
    api_key, base_url = _resolve_agent_connection(agent_config)

    if not base_url:
        from core.model_router import PROVIDER_BASE_URLS
        base_url = PROVIDER_BASE_URLS.get(agent_config.model_provider, "")

    if not base_url or not api_key:
        yield {"type": "content", "content": "配置错误：缺少 API Key 或 Base URL"}
        return

    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"

    safe, safe_err = is_safe_url(url)
    if not safe:
        logger.warning(f"SSRF 防护拦截: {safe_err}")
        yield {"type": "content", "content": f"请求被安全策略拦截: {safe_err}"}
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 解析正确的模型 ID
    from core.model_router import resolve_model_id
    actual_model_id = resolve_model_id(agent_config.model_id)

    payload = {
        "model": actual_model_id,
        "messages": messages,
        "stream": True,
    }

    # GLM-4.7-Flash 支持通过 enable_thinking 参数切换思考模式
    if enable_thinking:
        payload["enable_thinking"] = True
    else:
        payload["enable_thinking"] = False

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    if enable_search:
        search_key = get_search_api_key()
        if search_key and api_key and search_key == api_key:
            search_tool = {
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_engine": "search_std",
                    "search_result": True,
                }
            }
            if "tools" not in payload:
                payload["tools"] = []
            payload["tools"].append(search_tool)

    # [DEBUG] 记录发送给 LLM 的 payload（用于排查 400 错误）
    logger.debug(f"[_stream_llm_real] actual_model={actual_model_id}, original_model={agent_config.model_id}, tools_count={len(tools) if tools else 0}, payload_keys={list(payload.keys())}")
    if tools:
        logger.debug(f"[_stream_llm_real] tools={json.dumps(tools, ensure_ascii=False)[:500]}")

    thinking_buffer = ""
    content_buffer = ""
    in_thinking = False
    THINK_START = "<think>"
    THINK_END = "</think>"

    try:
        client = await _get_shared_client()
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                logger.warning(f"LLM API 错误: status={resp.status_code}, body={body[:500]}")
                detail = ""
                try:
                    import json as _json
                    err_data = _json.loads(body)
                    detail = err_data.get("error", {}).get("message", "") or err_data.get("message", "") or err_data.get("msg", "")
                except Exception:
                    pass
                user_msg = f"API 请求失败（状态码 {resp.status_code}）"
                if detail:
                    user_msg += f"：{detail}"
                else:
                    user_msg += "，请稍后重试。"
                yield {"type": "content", "content": user_msg}
                return

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    # Flush any remaining content in buffer before breaking
                    if content_buffer:
                        if in_thinking:
                            if enable_thinking:
                                yield {"type": "thinking", "content": content_buffer}
                        else:
                            yield {"type": "content", "content": content_buffer}
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choice = data.get("choices", [{}])[0]
                delta = choice.get("delta", {})

                if delta.get("reasoning_content"):
                    if enable_thinking:
                        yield {"type": "thinking", "content": delta["reasoning_content"]}

                if delta.get("content"):
                    content_chunk = delta["content"]
                    
                    content_buffer += content_chunk
                    
                    while True:
                        if not in_thinking:
                            start_idx = content_buffer.find(THINK_START)
                            if start_idx != -1:
                                if start_idx > 0:
                                    yield {"type": "content", "content": content_buffer[:start_idx]}
                                content_buffer = content_buffer[start_idx + len(THINK_START):]
                                in_thinking = True
                            else:
                                if len(content_buffer) >= len(THINK_START):
                                    yield {"type": "content", "content": content_buffer[:-len(THINK_START)+1]}
                                    content_buffer = content_buffer[-len(THINK_START)+1:]
                                break
                        else:
                            end_idx = content_buffer.find(THINK_END)
                            if end_idx != -1:
                                if end_idx > 0 and enable_thinking:
                                    yield {"type": "thinking", "content": content_buffer[:end_idx]}
                                content_buffer = content_buffer[end_idx + len(THINK_END):]
                                in_thinking = False
                            else:
                                if len(content_buffer) >= len(THINK_END):
                                    thinking_part = content_buffer[:-len(THINK_END)+1]
                                    if thinking_part and enable_thinking:
                                        yield {"type": "thinking", "content": thinking_part}
                                    content_buffer = content_buffer[-len(THINK_END)+1:]
                                break

                if delta.get("tool_calls"):
                    yield {"type": "tool_calls", "tool_calls": delta["tool_calls"]}

    except httpx.TimeoutException:
        yield {"type": "content", "content": "请求超时，请稍后再试。"}
    except Exception as e:
        yield {"type": "content", "content": f"连接错误: {str(e)}"}


def _aggregate_tool_calls(chunks: list) -> list:
    aggregated = {}
    for chunk_list in chunks:
        for chunk in chunk_list:
            idx = chunk.get("index", 0)
            if idx not in aggregated:
                aggregated[idx] = {"index": idx, "id": "", "function": {"name": "", "arguments": ""}, "type": "function"}
            if chunk.get("id"):
                aggregated[idx]["id"] = chunk["id"]
            if chunk.get("function", {}).get("name"):
                if not aggregated[idx]["function"]["name"]:
                    aggregated[idx]["function"]["name"] = chunk["function"]["name"]
            if chunk.get("function", {}).get("arguments"):
                aggregated[idx]["function"]["arguments"] += chunk["function"]["arguments"]
    return sorted(aggregated.values(), key=lambda x: x["index"])


async def _stream_worker_task(worker_agent, clean_input: str, original_input: str, session_id: str, memory, lang: str, enable_thinking: bool = False, file_infos: list = None) -> AsyncGenerator[str, None]:
    from skills import get_tool_schemas_by_skill_ids, get_skills_for_agent, execute_tool_by_name

    worker_type = worker_agent.get_agent_type()

    if worker_type == "runner":
        worker_skill_ids = worker_agent.skills or []
        full_response = ""
        if worker_skill_ids:
            agent_skills = get_skills_for_agent(worker_skill_ids)
            for sk in agent_skills:
                tool_schema = sk.get("tool_schema")
                if tool_schema:
                    tool_name = tool_schema.get("function", {}).get("name", "")
                    tool_args = {}
                    params = tool_schema.get("function", {}).get("parameters", {}).get("properties", {})
                    if "prompt" in params:
                        tool_args["prompt"] = clean_input
                    elif "text" in params:
                        tool_args["text"] = clean_input
                    elif "url" in params:
                        tool_args["url"] = clean_input
                    else:
                        first_param = next(iter(params), None)
                        if first_param:
                            tool_args[first_param] = clean_input

                    yield json.dumps({"type": "tool_start", "tool_name": tool_name}, ensure_ascii=False) + "\n"
                    tool_result = await asyncio.to_thread(execute_tool_by_name, tool_name, tool_args)
                    result_msg = tool_result.get("message", "")
                    _t, _c = _parse_thinking(result_msg)
                    if _t and enable_thinking:
                        yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                    if _c:
                        yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                        full_response += _c
        else:
            full_response = f"{worker_agent.name} 没有绑定任何技能" if lang == "zh" else f"{worker_agent.name} has no skills assigned"
            yield json.dumps({"type": "content", "content": full_response}, ensure_ascii=False) + "\n"

        memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
        ai_meta = {"agents": [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]}
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta)

        done_event = {"type": "done", "agent_name": worker_agent.name, "model_id": worker_agent.model_id, "agents": [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]}
        msg_count = len(memory.get_messages(session_id))
        if msg_count <= 2:
            title = await _generate_title(worker_agent, original_input, full_response, lang)
            done_event["title"] = title
        yield json.dumps(done_event, ensure_ascii=False) + "\n"
        return

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

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": clean_input}]

    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    tool_call_chunks = []

    try:
        async for chunk in _stream_llm_real(messages, worker_agent, tools=worker_tools, enable_thinking=enable_thinking):
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
            aggregated = _aggregate_tool_calls(tool_call_chunks)
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

        memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
        ai_meta = {}
        if full_thinking:
            ai_meta["thinking"] = full_thinking
        ai_meta["agents"] = [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        done_event = {"type": "done", "agent_name": worker_agent.name, "model_id": worker_agent.model_id, "agents": [{"name": worker_agent.name, "model_id": worker_agent.model_id, "role": "worker"}]}
        msg_count = len(memory.get_messages(session_id))
        if msg_count <= 2:
            title = await _generate_title(worker_agent, original_input, full_response, lang)
            done_event["title"] = title
        yield json.dumps(done_event, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"员工 {worker_agent.name} 执行失败: {e}")
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"


async def _stream_with_fc(agent_config, clean_input: str, original_input: str, session_id: str, memory, files, file_infos, enable_search=False, enable_thinking=False, lang="zh") -> AsyncGenerator[str, None]:
    """主管 FC 模式 — 通过 Function Calling 调度员工和工具"""
    if enable_thinking:
        agent_config = _resolve_thinking_agent(agent_config)
    from skills import get_unassigned_tool_schemas, get_tool_schemas_by_skill_ids, execute_tool_by_name, get_skills_for_agent

    _ensure_skills()

    system_prompt = _build_manager_system_prompt(agent_config, lang)
    context_messages = memory.get_context_messages(session_id)
    history_text = _build_history_text(context_messages, agent_config.name)
    upload_dir = os.path.join(project_root, "data", "uploads")
    user_content = await _build_file_content(files, clean_input, upload_dir)
    messages = _build_chat_messages(system_prompt, history_text, user_content)

    memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)

    manager = _get_agent_manager()
    workers = manager.list_workers()
    worker_map = {}
    worker_skills_map: dict = {}
    agents_involved = [{"name": agent_config.name, "model_id": agent_config.model_id, "role": "manager"}]

    assigned_skill_ids: set = set()
    worker_tool_definitions = []
    for w in workers:
        if w.skills:
            for sid in w.skills:
                assigned_skill_ids.add(sid)
            worker_skills_map[w.name] = w.skills

        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', w.name).lower()
        role_desc = w.role or w.description or "通用助手"
        desc = f"将任务分配给员工「{w.name}」处理。{w.name}的职责：{role_desc}。使用的模型：{w.model_id}。"
        if w.skills:
            agent_skills = get_skills_for_agent(w.skills)
            if agent_skills:
                desc += "擅长技能：" + "、".join(s["name"] for s in agent_skills) + "。"
        worker_tool_definitions.append({
            "type": "function",
            "function": {
                "name": f"assign_to_{safe_name}",
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": f"要交给{w.name}处理的任务描述",
                        },
                    },
                    "required": ["task"],
                },
            },
        })
        worker_map[f"assign_to_{safe_name}"] = w

    tools = get_unassigned_tool_schemas(assigned_skill_ids) + worker_tool_definitions

    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    tool_call_chunks = []

    try:
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
                tool_call_chunks.append(chunk["tool_calls"])

        full_response = "".join(full_response_parts)
        full_thinking = "".join(full_thinking_parts)

        if tool_call_chunks:
            aggregated = _aggregate_tool_calls(tool_call_chunks)

            for tc in aggregated:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")

                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                if func_name.startswith("assign_to_") and func_name in worker_map:
                    worker = worker_map[func_name]
                    if enable_thinking:
                        worker = _resolve_thinking_agent(worker)
                    task_desc = func_args.get("task", clean_input)
                    yield json.dumps({"type": "worker", "worker_name": worker.name, "worker_model": worker.model_id}, ensure_ascii=False) + "\n"

                    agents_involved.append({"name": worker.name, "model_id": worker.model_id, "role": "worker"})

                    worker_type = worker.get_agent_type()

                    if worker_type == "runner":
                        worker_skill_ids = worker.skills or []
                        if worker_skill_ids:
                            agent_skills = get_skills_for_agent(worker_skill_ids)
                            for sk in agent_skills:
                                tool_schema = sk.get("tool_schema")
                                if tool_schema:
                                    tool_name = tool_schema.get("function", {}).get("name", "")
                                    tool_args = {}
                                    params = tool_schema.get("function", {}).get("parameters", {}).get("properties", {})
                                    if "prompt" in params:
                                        tool_args["prompt"] = task_desc
                                    elif "text" in params:
                                        tool_args["text"] = task_desc
                                    elif "url" in params:
                                        tool_args["url"] = task_desc
                                    else:
                                        first_param = next(iter(params), None)
                                        if first_param:
                                            tool_args[first_param] = task_desc

                                    yield json.dumps({"type": "tool_start", "tool_name": tool_name}, ensure_ascii=False) + "\n"
                                    tool_result = await asyncio.to_thread(execute_tool_by_name, tool_name, tool_args)
                                    result_msg = tool_result.get("message", "")
                                    _t, _c = _parse_thinking(result_msg)
                                    if _t and enable_thinking:
                                        yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                                    if _c:
                                        yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                                        full_response += _c
                        else:
                            yield json.dumps({"type": "content", "content": f"执行员 {worker.name} 没有绑定任何技能"}, ensure_ascii=False) + "\n"

                    else:
                        worker_prompt = f"你是{worker.name}，{worker.role or worker.description or '一个AI助手'}。\n\n"
                        worker_skill_ids = worker.skills or []
                        worker_tools = None
                        if worker_skill_ids:
                            agent_skills = get_skills_for_agent(worker_skill_ids)
                            if agent_skills:
                                worker_prompt += "你擅长以下技能，请根据任务需要使用："
                                for sk in agent_skills:
                                    worker_prompt += f"\n- {sk['name']}：{sk['description']}"
                                worker_prompt += "\n"
                                worker_tools = get_tool_schemas_by_skill_ids(worker_skill_ids)

                        worker_messages = [
                            {"role": "system", "content": worker_prompt},
                            {"role": "user", "content": task_desc},
                        ]

                        worker_response_parts: list[str] = []
                        worker_thinking_parts: list[str] = []
                        worker_tool_call_chunks = []

                        async for w_chunk in _stream_llm_real(worker_messages, worker, tools=worker_tools, enable_search=enable_search, enable_thinking=enable_thinking):
                            w_type = w_chunk.get("type", "")
                            w_content = w_chunk.get("content", "")
                            if w_type == "thinking":
                                worker_thinking_parts.append(w_content)
                                yield json.dumps({"type": "thinking", "content": w_content}, ensure_ascii=False) + "\n"
                            elif w_type == "content":
                                worker_response_parts.append(w_content)
                                yield json.dumps({"type": "content", "content": w_content}, ensure_ascii=False) + "\n"
                            elif w_type == "tool_calls":
                                worker_tool_call_chunks.append(w_chunk["tool_calls"])

                        if worker_tool_call_chunks:
                            w_aggregated = _aggregate_tool_calls(worker_tool_call_chunks)
                            for wtc in w_aggregated:
                                w_func_name = wtc.get("function", {}).get("name", "")
                                w_func_args_str = wtc.get("function", {}).get("arguments", "{}")
                                try:
                                    w_func_args = json.loads(w_func_args_str)
                                except json.JSONDecodeError:
                                    w_func_args = {}

                                yield json.dumps({"type": "tool_start", "tool_name": w_func_name}, ensure_ascii=False) + "\n"
                                tool_result = await asyncio.to_thread(execute_tool_by_name, w_func_name, w_func_args)
                                result_msg = tool_result.get("message", "")
                                _t, _c = _parse_thinking(result_msg)
                                if _t and enable_thinking:
                                    yield json.dumps({"type": "thinking", "content": _t}, ensure_ascii=False) + "\n"
                                if _c:
                                    yield json.dumps({"type": "content", "content": _c}, ensure_ascii=False) + "\n"
                                    worker_response_parts.append(_c)

                        full_response += "".join(worker_response_parts)
                        full_thinking += "".join(worker_thinking_parts)

                else:
                    yield json.dumps({"type": "tool_start", "tool_name": func_name}, ensure_ascii=False) + "\n"
                    tool_result = await asyncio.to_thread(execute_tool_by_name, func_name, func_args)
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
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        msg_count = len(memory.get_messages(session_id))
        if msg_count > 0 and msg_count % memory.SUMMARY_THRESHOLD == 0:
            try:
                await asyncio.to_thread(memory.generate_summary, session_id)
            except Exception as e:
                logger.warning(f"自动摘要失败: {e}")

        done_event = {"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id}
        if len(agents_involved) > 1:
            done_event["agents"] = agents_involved
        if msg_count <= 2:
            title = await _generate_title(agent_config, original_input, full_response, lang)
            done_event["title"] = title

        yield json.dumps(done_event, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"FC 流式对话失败: {e}")
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"


async def _stream_normal_chat(agent_config, clean_input: str, original_input: str, session_id: str, memory, files, file_infos, enable_thinking=False, enable_search=False, lang="zh") -> AsyncGenerator[str, None]:
    if enable_thinking:
        agent_config = _resolve_thinking_agent(agent_config)
    system_prompt = build_system_prompt(agent_config.name, lang=lang, enable_thinking=enable_thinking)
    context_messages = memory.get_context_messages(session_id)
    history_text = _build_history_text(context_messages, agent_config.name)
    upload_dir = os.path.join(project_root, "data", "uploads")
    user_content = await _build_file_content(files, clean_input, upload_dir)
    messages = _build_chat_messages(system_prompt, history_text, user_content)

    full_response_parts: list[str] = []
    full_thinking_parts: list[str] = []
    tool_call_chunks = []

    memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)

    try:
        async for chunk in _stream_llm_real(messages, agent_config, enable_search=enable_search, enable_thinking=enable_thinking):
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

        ai_meta = {}
        if full_thinking:
            ai_meta["thinking"] = full_thinking
        memory.add_message("assistant", full_response, session_id=session_id, metadata=ai_meta if ai_meta else None)

        msg_count = len(memory.get_messages(session_id))
        if msg_count > 0 and msg_count % memory.SUMMARY_THRESHOLD == 0:
            try:
                await asyncio.to_thread(memory.generate_summary, session_id)
            except Exception as e:
                logger.warning(f"自动摘要失败: {e}")

        done_event = {"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id}
        if msg_count <= 2:
            title = await _generate_title(agent_config, original_input, full_response, lang)
            done_event["title"] = title

        yield json.dumps(done_event, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.error(f"流式对话失败: {e}")
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"


def get_welcome_message(agent_name: str = "GymClaw") -> str:
    return (
        f"你好！我是 {agent_name}，你的 AI 助手。\n\n"
        "我可以帮你：\n"
        "- 💬 聊天对话\n"
        "- 🖼️ 生成图片\n"
        "- 🔊 文字转语音\n"
        "- 🌐 抓取网页内容\n\n"
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
    4. FC 调度：主管模型支持 tool_use → FC 调度员工和工具
    5. 关键词匹配：匹配内置技能
    6. 普通对话
    """
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
                async for chunk in _stream_worker_task(worker, clean_input, user_input, session_id, memory, lang, enable_thinking=enable_thinking, file_infos=file_infos):
                    yield chunk
                return

    # 路径 2：安全检查
    if is_sensitive_request(clean_input):
        yield json.dumps({"type": "content", "content": get_reject_message(lang)}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "done", "agent_name": agent.name, "model_id": agent.model_id}, ensure_ascii=False) + "\n"
        return

    # 路径 3：FC 调度
    if _model_supports_tool_use(agent.model_id):
        async for chunk in _stream_with_fc(agent, clean_input, user_input, session_id, memory, files, file_infos, enable_search=search_via_tool, enable_thinking=enable_thinking, lang=lang):
            yield chunk
        return

    # 路径 4：关键词匹配
    _ensure_skills()
    from skills import match_skill, match_skill_for_agent
    matched = None
    if agent.skills:
        matched = match_skill_for_agent(clean_input, agent.skills)
    if not matched:
        matched = match_skill(clean_input)
    if matched:
        memory.add_message("user", user_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
        yield json.dumps({"type": "skill", "skill_name": matched["name"], "skill_icon": matched["icon"]}, ensure_ascii=False) + "\n"
        try:
            handler = matched["handler"]
            result = await asyncio.to_thread(handler, clean_input, {"files": files, "agent_config": agent})
            result_msg = result.get("message", "") if isinstance(result, dict) else str(result)
            thinking, content = _parse_thinking(result_msg)

            if thinking and enable_thinking:
                yield json.dumps({"type": "thinking", "content": thinking}, ensure_ascii=False) + "\n"
            if content:
                yield json.dumps({"type": "content", "content": content}, ensure_ascii=False) + "\n"

            ai_meta = {}
            if thinking and enable_thinking:
                ai_meta["thinking"] = thinking
            memory.add_message("assistant", content, session_id=session_id, metadata=ai_meta if ai_meta else None)

            msg_count = len(memory.get_messages(session_id))
            done_event = {"type": "done", "agent_name": agent.name, "model_id": agent.model_id, "skill_used": matched["id"], "skill_name": matched["name"]}
            if msg_count <= 2:
                title = await _generate_title(agent, user_input, content, lang)
                done_event["title"] = title
            yield json.dumps(done_event, ensure_ascii=False) + "\n"
            return
        except Exception as e:
            logger.warning(f"技能执行失败，降级为普通对话: {e}")

    # 路径 5：普通对话
    async for chunk in _stream_normal_chat(agent, clean_input, user_input, session_id, memory, files, file_infos, enable_thinking=enable_thinking, enable_search=search_via_tool, lang=lang):
        yield chunk
