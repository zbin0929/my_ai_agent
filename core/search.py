# -*- coding: utf-8 -*-
"""
搜索服务模块
============

独立的搜索服务，与模型调用完全解耦。
支持智谱 Search API，未来可扩展 Tavily / DuckDuckGo 等。
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

ZHIPU_SEARCH_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

_shared_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        return _shared_client
    async with _client_lock:
        if _shared_client is not None and not _shared_client.is_closed:
            return _shared_client
        _shared_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return _shared_client


def get_search_config() -> Dict[str, Any]:
    try:
        from core.config_loader import get_config
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = get_config(os.path.join(project_root, "config"))
        return config.get("search", {})
    except Exception:
        return {}


def get_search_api_key() -> Optional[str]:
    search_config = get_search_config()
    return search_config.get("api_key", "") or None


def get_search_provider() -> str:
    return get_search_config().get("provider", "zhipu_search")


def _get_search_model() -> str:
    search_config = get_search_config()
    return search_config.get("model", "glm-4-flash")


async def search_zhipu(query: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _get_search_model(),
        "messages": [
            {"role": "user", "content": query}
        ],
        "tools": [
            {
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_result": True,
                }
            }
        ],
        "stream": False,
    }

    try:
        client = await _get_shared_client()
        resp = await client.post(ZHIPU_SEARCH_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"智谱搜索 API 错误: {resp.status_code}")
            return ""

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})
        content = message.get("content", "")
        return content

    except Exception as e:
        logger.error(f"智谱搜索失败: {e}")
        return ""


async def do_search(query: str) -> str:
    api_key = get_search_api_key()
    if not api_key:
        logger.warning("搜索 API Key 未配置")
        return ""

    provider = get_search_provider()

    if provider == "zhipu_search":
        return await search_zhipu(query, api_key)

    logger.warning(f"不支持的搜索引擎: {provider}")
    return ""

