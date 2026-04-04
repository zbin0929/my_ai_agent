# -*- coding: utf-8 -*-
import os
import json
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cache: Dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL: float = 30.0


def _load_all_models() -> List[dict]:
    global _cache_ts
    now = time.time()
    if _cache.get("models") and (now - _cache_ts) < _CACHE_TTL:
        return _cache["models"]
    models = []
    sys_file = os.path.join(_project_root, "config", "models.json")
    if os.path.exists(sys_file):
        try:
            with open(sys_file, "r", encoding="utf-8") as f:
                models.extend(json.load(f))
        except Exception:
            pass
    custom_file = os.path.join(_project_root, "data", "custom_models.json")
    if os.path.exists(custom_file):
        try:
            with open(custom_file, "r", encoding="utf-8") as f:
                models.extend(json.load(f))
        except Exception:
            pass
    _cache["models"] = models
    _cache_ts = now
    return models


def get_model_capabilities(model_id: str) -> List[str]:
    for m in _load_all_models():
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m.get("capabilities", [])
    return []


def model_supports_thinking(model_id: str) -> bool:
    for m in _load_all_models():
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m.get("supports_thinking", False)
    return False


def find_model_with_capabilities(required_caps: List[str]) -> Optional[dict]:
    for m in _load_all_models():
        if all(c in m.get("capabilities", []) for c in required_caps):
            return m
    return None


def find_thinking_model() -> Optional[str]:
    for m in _load_all_models():
        if m.get("supports_thinking") and m.get("builtin"):
            return m.get("model_id")
    return None


def get_model_by_id(model_id: str) -> Optional[dict]:
    for m in _load_all_models():
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m
    return None
