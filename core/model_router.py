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
import json
import time
import hashlib
import threading
import logging
from typing import Dict, Any, List, Optional, Tuple

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


def _load_all_models() -> list:
    models = []
    sys_file = os.path.join(project_root, "config", "models.json")
    if os.path.exists(sys_file):
        try:
            with open(sys_file, "r", encoding="utf-8") as f:
                models.extend(json.load(f))
        except Exception:
            pass
    custom_file = os.path.join(project_root, "data", "custom_models.json")
    if os.path.exists(custom_file):
        try:
            with open(custom_file, "r", encoding="utf-8") as f:
                models.extend(json.load(f))
        except Exception:
            pass
    return models


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


def get_model_capabilities(model_id: str) -> list:
    for m in _load_all_models():
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m.get("capabilities", [])
    return []


def find_model_with_capabilities(required_caps: list) -> dict:
    candidates = [m for m in _load_all_models() if all(c in m.get("capabilities", []) for c in required_caps)]
    return candidates[0] if candidates else None


def _get_default_base_url(provider: str) -> str:
    """根据提供商获取默认 Base URL"""
    return PROVIDER_BASE_URLS.get(provider, "")


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


def build_llm_for_agent(agent_config):
    """根据 Agent 配置构建 LLM 实例（带缓存）

    优先级：
    1. Agent 自带的 custom_api_key + custom_base_url（或根据 provider 推断 base_url）
    2. 全局配置（通过 LLMFactory）
    """
    from crewai.llm import LLM

    if agent_config.custom_api_key:
        base_url = agent_config.custom_base_url or _get_default_base_url(agent_config.model_provider)
        if base_url:
            cache_key = _build_llm_cache_key(
                agent_config.model_id, agent_config.custom_api_key, base_url, agent_config.temperature
            )
            cached = _llm_cache_get(cache_key)
            if cached is not None:
                return cached
            logger.info(f"Agent '{agent_config.name}' 使用独立 API Key，提供商: {agent_config.model_provider}")
            llm = LLM(
                model=agent_config.model_id,
                api_key=agent_config.custom_api_key,
                base_url=base_url,
                temperature=agent_config.temperature,
            )
            _llm_cache_put(cache_key, llm)
            return llm

    from core.llm_factory import LLMFactory
    from core.config_loader import get_config

    config = get_config(os.path.join(project_root, "config"))
    factory = LLMFactory(config)
    provider_cfg = next(
        (p for p in config.get("llm_providers", []) if p["id"] == agent_config.model_provider),
        None,
    )
    api_key = ""
    base_url = ""
    if provider_cfg:
        base_url = provider_cfg.get("base_url", _get_default_base_url(agent_config.model_provider))
        provider_api_key = provider_cfg.get("api_key", "")
        if provider_api_key:
            api_key = provider_api_key
        else:
            env_key = provider_cfg.get("env_key", "")
            api_key = os.environ.get(env_key, "")
    else:
        base_url = _get_default_base_url(agent_config.model_provider)
    cache_key = _build_llm_cache_key(agent_config.model_id, api_key, base_url, agent_config.temperature)
    cached = _llm_cache_get(cache_key)
    if cached is not None:
        return cached
    llm = factory.create({
        "provider": agent_config.model_provider,
        "model": agent_config.model_id,
        "temperature": agent_config.temperature,
    })
    _llm_cache_put(cache_key, llm)
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
        api_key = fallback.get("api_key", "")
        if not api_key:
            try:
                from core.config_loader import get_config
                cfg = get_config(os.path.join(project_root, "config"))
                for p in cfg.get("llm_providers", []):
                    if p.get("id") == fallback.get("provider", ""):
                        provider_api_key = p.get("api_key", "")
                        if provider_api_key:
                            api_key = provider_api_key
                        else:
                            env_key = p.get("env_key", "")
                            api_key = os.environ.get(env_key, "")
                        break
            except Exception:
                pass
        return LLM(
            model=fallback["model_id"],
            api_key=api_key,
            base_url=fallback.get("base_url", ""),
            temperature=agent_config.temperature,
        )

    logger.warning(f"未找到支持 {required_caps} 的模型，使用默认模型")
    return build_llm_for_agent(agent_config)
