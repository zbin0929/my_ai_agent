# -*- coding: utf-8 -*-
"""
模型路由模块
============

负责：
- 检测文件所需的模型能力
- 根据能力要求路由到合适的模型
- 构建 LLM 实例

优化记录：
- [模块拆分] 从原 chat_engine.py 拆分出来，职责单一化
- [配置缓存] 使用 get_config() 单例替代 ConfigLoader() 直接实例化，避免重复解析 YAML
- [Agent Key] 每个 Agent 可配置独立的 API Key，优先使用 Agent 自带的 Key
"""

import os
import time
import hashlib
import threading
import logging
from typing import Dict, Any, Optional, Tuple

from core.model_info import _load_all_models, get_model_capabilities, find_model_with_capabilities

logger = logging.getLogger(__name__)

_LLM_CACHE: Dict[str, Tuple[Any, float]] = {}
_LLM_CACHE_LOCK = threading.Lock()
_LLM_CACHE_TTL = 300

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg"}
SPREADSHEET_EXTENSIONS = {".xls", ".xlsx", ".csv", ".tsv"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}

PROVIDER_BASE_URLS = {
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "moonshot": "https://api.moonshot.cn/v1",
}


def detect_required_capabilities(files: list = None) -> list:
    caps = []
    if not files:
        return caps
    for f in files:
        ext = os.path.splitext(f)[1].lower() if isinstance(f, str) else ""
        if ext in IMAGE_EXTENSIONS:
            caps.append("vision")
        if ext in SPREADSHEET_EXTENSIONS:
            caps.append("spreadsheet")
    return list(set(caps))


def resolve_model_id(agent_model_id: str) -> str:
    """根据 Agent 配置的 model_id 查找正确的 provider model_id
    
    优先从 config/models.json 查找匹配的模型定义，返回定义中的 model_id
    如果找不到，则返回原始的 agent_model_id
    """
    for m in _load_all_models():
        if m.get("id") == agent_model_id:
            provider_model_id = m.get("model_id")
            if provider_model_id:
                return provider_model_id
    return agent_model_id


def _get_default_base_url(provider: str) -> str:
    """根据提供商获取默认 Base URL"""
    return PROVIDER_BASE_URLS.get(provider, "")


def resolve_provider_credentials(agent_config) -> Tuple[str, str]:
    """统一解析 Agent 的 API Key 和 Base URL

    优先级：
    1. Agent 自带的 custom_api_key + custom_base_url
    2. Provider 配置中的 api_key
    3. Provider 配置中 env_key 对应的环境变量

    Returns:
        (api_key, base_url)
    """
    if agent_config.custom_api_key:
        base_url = agent_config.custom_base_url or _get_default_base_url(agent_config.model_provider)
        return agent_config.custom_api_key, base_url

    try:
        from core.config_loader import get_config
        config = get_config(os.path.join(project_root, "config"))
        for provider in config.get("llm_providers", []):
            if provider["id"] == agent_config.model_provider:
                base_url = provider.get("base_url", _get_default_base_url(agent_config.model_provider))
                provider_api_key = provider.get("api_key", "")
                if provider_api_key:
                    return provider_api_key, base_url
                env_key = provider.get("env_key", "")
                api_key = os.environ.get(env_key, "")
                return api_key, base_url
    except Exception:
        pass

    return "", _get_default_base_url(agent_config.model_provider)


def _resolve_api_key_for_provider(provider_id: str) -> str:
    """从 provider 配置中解析 API Key"""
    try:
        from core.config_loader import get_config
        config = get_config(os.path.join(project_root, "config"))
        for p in config.get("llm_providers", []):
            if p["id"] == provider_id:
                provider_api_key = p.get("api_key", "")
                if provider_api_key:
                    return provider_api_key
                env_key = p.get("env_key", "")
                return os.environ.get(env_key, "")
    except Exception:
        pass
    return ""


def _llm_cache_get(cache_key: str) -> Optional[Any]:
    with _LLM_CACHE_LOCK:
        entry = _LLM_CACHE.get(cache_key)
        if entry is None:
            return None
        llm_instance, ts = entry
        if time.time() - ts > _LLM_CACHE_TTL:
            del _LLM_CACHE[cache_key]
            return None
        return llm_instance


def _llm_cache_put(cache_key: str, llm_instance: Any) -> None:
    with _LLM_CACHE_LOCK:
        if len(_LLM_CACHE) > 64:
            oldest_key = min(_LLM_CACHE, key=lambda k: _LLM_CACHE[k][1])
            del _LLM_CACHE[oldest_key]
        _LLM_CACHE[cache_key] = (llm_instance, time.time())


def _build_llm_cache_key(model_id: str, api_key: str, base_url: str, temperature: float) -> str:
    raw = f"{model_id}|{api_key}|{base_url}|{temperature}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


_llm_factory_instance: Optional[Any] = None
_llm_factory_lock = threading.Lock()


def _get_llm_factory(config: Dict[str, Any]) -> Any:
    global _llm_factory_instance
    if _llm_factory_instance is not None:
        return _llm_factory_instance
    with _llm_factory_lock:
        if _llm_factory_instance is not None:
            return _llm_factory_instance
        from core.llm_factory import LLMFactory
        _llm_factory_instance = LLMFactory(config)
        return _llm_factory_instance


def build_llm_for_agent(agent_config):
    """根据 Agent 配置构建 LLM 实例（带缓存）

    优先级：
    1. Agent 自带的 custom_api_key + custom_base_url（或根据 provider 推断 base_url）
    2. 全局配置（通过 LLMFactory）
    """
    from crewai.llm import LLM

    api_key, base_url = resolve_provider_credentials(agent_config)
    actual_model_id = resolve_model_id(agent_config.model_id)

    if api_key and base_url:
        cache_key = _build_llm_cache_key(actual_model_id, api_key, base_url, agent_config.temperature)
        cached = _llm_cache_get(cache_key)
        if cached is not None:
            return cached
        llm = LLM(
            model=actual_model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=agent_config.temperature,
        )
        _llm_cache_put(cache_key, llm)
        return llm

    from core.config_loader import get_config
    config = get_config(os.path.join(project_root, "config"))
    factory = _get_llm_factory(config)
    llm = factory.create({
        "provider": agent_config.model_provider,
        "model": actual_model_id,
        "temperature": agent_config.temperature,
    })
    return llm


def build_llm_for_task(agent_config, files: list = None):
    """根据文件类型智能路由到合适的模型"""
    required_caps = detect_required_capabilities(files)
    agent_model_caps = get_model_capabilities(agent_config.model_id)

    if all(c in agent_model_caps for c in required_caps):
        return build_llm_for_agent(agent_config)

    fallback = find_model_with_capabilities(required_caps)

    if fallback:
        logger.info(f"模型能力路由: {agent_config.model_id} 不支持 {required_caps}，切换到 {fallback['model_id']}")
        from crewai.llm import LLM
        api_key = fallback.get("api_key", "") or _resolve_api_key_for_provider(fallback.get("provider", ""))
        return LLM(
            model=fallback["model_id"],
            api_key=api_key,
            base_url=fallback.get("base_url", ""),
            temperature=agent_config.temperature,
        )

    logger.warning(f"未找到支持 {required_caps} 的模型，使用默认模型")
    return build_llm_for_agent(agent_config)
