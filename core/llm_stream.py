# -*- coding: utf-8 -*-
"""
LLM 流式请求模块
================

管理 httpx 客户端、API 连接解析、流式调用 LLM 和工具调用聚合。
从 chat_engine.py 提取。
"""

import json
import asyncio
import logging
import httpx
from typing import Optional, AsyncGenerator, Tuple

from core.security import is_safe_url
from core.search import get_search_api_key

logger = logging.getLogger(__name__)

_shared_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        return _shared_client
    async with _client_lock:
        if _shared_client is not None and not _shared_client.is_closed:
            return _shared_client
        _shared_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return _shared_client


def resolve_agent_connection(agent_config) -> Tuple[str, str]:
    from core.model_router import resolve_provider_credentials
    return resolve_provider_credentials(agent_config)


def get_agent_api_key(agent_config) -> str:
    key, _ = resolve_agent_connection(agent_config)
    return key


async def stream_llm_real(messages, agent_config, tools=None, enable_search=False, enable_thinking=False) -> AsyncGenerator[dict, None]:
    api_key, base_url = resolve_agent_connection(agent_config)

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

    # enable_thinking 仅对支持该参数的提供商生效（如智谱 GLM 系列）
    _thinking_providers = {"zhipu"}
    if agent_config.model_provider in _thinking_providers:
        payload["enable_thinking"] = bool(enable_thinking)

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
    logger.debug(f"[stream_llm_real] actual_model={actual_model_id}, original_model={agent_config.model_id}, tools_count={len(tools) if tools else 0}, payload_keys={list(payload.keys())}")
    if tools:
        logger.debug(f"[stream_llm_real] tools={json.dumps(tools, ensure_ascii=False)[:500]}")

    thinking_buffer = ""
    content_buffer = ""
    in_thinking = False
    THINK_START = "<think>"
    THINK_END = "</think>"

    try:
        client = await get_shared_client()
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
        logger.error(f"LLM 流式请求异常: {e}", exc_info=True)
        from core.errors import friendly_error_message
        yield {"type": "content", "content": friendly_error_message(e)}


def aggregate_tool_calls(chunks: list) -> list:
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
