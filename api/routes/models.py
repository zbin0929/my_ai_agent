# -*- coding: utf-8 -*-
"""
模型管理路由
============

管理系统内置和自定义 LLM 模型配置。
内置模型根据 API Key 可用性动态过滤显示。
自定义模型持久化存储在 data/custom_models.json 中。
"""

import os
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from api.schemas import ModelCreate, ModelUpdate
from api.deps import DATA_DIR
from core.errors import friendly_error_message
from core.security import encrypt_api_key, decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# 自定义模型持久化存储路径
MODELS_FILE = os.path.join(DATA_DIR, "custom_models.json")

# 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYSTEM_MODELS_FILE = os.path.join(project_root, "config", "models.json")


def _load_system_models() -> list:
    """从 config/models.json 加载系统内置模型列表"""
    if os.path.exists(SYSTEM_MODELS_FILE):
        try:
            with open(SYSTEM_MODELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载系统模型配置失败: {e}")
    return []


# 模块初始化时加载一次，避免每次请求都读磁盘
SYSTEM_MODELS = _load_system_models()


def _load_custom_models() -> list:
    """从 JSON 文件加载自定义模型列表"""
    if os.path.exists(MODELS_FILE):
        with open(MODELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_custom_models(models: list):
    """将自定义模型列表保存到 JSON 文件"""
    with open(MODELS_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, ensure_ascii=False, indent=2)


# 提供商到环境变量的映射 — 用于判断哪些内置模型可用
PROVIDER_ENV_MAP = {
    "zhipu": "ZHIPU_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
}


def _has_provider_key(provider: str) -> bool:
    """检查指定提供商的 API Key 是否已在环境变量中配置"""
    env_key = PROVIDER_ENV_MAP.get(provider, "")
    return bool(env_key and os.environ.get(env_key))


def get_model_capabilities(model_id: str) -> list:
    """获取指定模型的 capabilities 列表"""
    for m in SYSTEM_MODELS:
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m.get("capabilities", [])
    custom = _load_custom_models()
    for m in custom:
        if m.get("model_id") == model_id or m.get("id") == model_id:
            return m.get("capabilities", [])
    return []


def find_model_with_capabilities(required_caps: list) -> dict:
    """查找支持指定能力集的第一个可用模型"""
    custom = _load_custom_models()
    candidates = [m for m in SYSTEM_MODELS + custom if all(c in m.get("capabilities", []) for c in required_caps)]
    return candidates[0] if candidates else None


@router.get("")
async def list_models():
    """
    获取可用模型列表

    只返回已配置 API Key 的内置模型 + 自定义模型（自带 API Key 或提供商已配置）。
    未配置 API Key 的内置模型不会显示，避免用户选择后报错。
    """
    custom = _load_custom_models()
    # 过滤：只显示已配置 API Key 的内置模型
    available_system = [m for m in SYSTEM_MODELS if _has_provider_key(m.get("provider", ""))]
    # 过滤：自定义模型需要自带 API Key 或提供商已配置
    available_custom = [m for m in custom if m.get("api_key") or _has_provider_key(m.get("provider", ""))]
    # 返回自定义模型（api_key 脱敏）
    display_custom = []
    for m in available_custom:
        display = {**m}
        if display.get("api_key"):
            display["api_key"] = mask_api_key(decrypt_api_key(display["api_key"]))
        display_custom.append(display)
    return {"models": available_system + display_custom, "builtin_count": len(available_system), "custom_count": len(available_custom)}


@router.post("")
async def create_model(data: ModelCreate):
    """添加自定义模型配置"""
    models = _load_custom_models()
    # 根据名称生成唯一 ID
    model_id = data.name.lower().replace(" ", "-")
    for m in models:
        if m["id"] == model_id:
            raise HTTPException(status_code=400, detail="Model ID already exists")
    new_model = {
        "id": model_id,
        "name": data.name,
        "provider": data.provider,
        "model_id": data.model_id,
        "base_url": data.base_url,
        "api_key": encrypt_api_key(data.api_key) if data.api_key else None,
        "description": data.description or "",
        "supports_thinking": data.supports_thinking or False,
        "capabilities": data.capabilities or [],
        "builtin": False,
    }
    models.append(new_model)
    _save_custom_models(models)
    return new_model


@router.put("/{model_id}")
async def update_model(model_id: str, data: ModelUpdate):
    """更新自定义模型配置 — 只更新提供的字段"""
    models = _load_custom_models()
    # 查找目标模型
    found = None
    for m in models:
        if m["id"] == model_id:
            found = m
            break
    if not found:
        raise HTTPException(status_code=404, detail="Model not found")
    if data.name is not None:
        found["name"] = data.name
    if data.provider is not None:
        found["provider"] = data.provider
    if data.model_id is not None:
        found["model_id"] = data.model_id
    if data.base_url is not None:
        found["base_url"] = data.base_url
    if data.api_key is not None:
        if "***" not in data.api_key:
            found["api_key"] = encrypt_api_key(data.api_key)
    if data.supports_thinking is not None:
        found["supports_thinking"] = data.supports_thinking
    if data.description is not None:
        found["description"] = data.description
    if data.capabilities is not None:
        found["capabilities"] = data.capabilities
    _save_custom_models(models)
    return found


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """删除自定义模型"""
    models = _load_custom_models()
    new_models = [m for m in models if m["id"] != model_id]
    if len(new_models) == len(models):
        raise HTTPException(status_code=404, detail="Model not found")
    _save_custom_models(new_models)
    return {"ok": True}


@router.post("/{model_id}/test")
async def test_model(model_id: str):
    """
    测试模型连接

    尝试用指定模型发送一条简单消息，验证 API Key 和网络连通性。
    同时搜索自定义模型和内置模型。
    """
    models = _load_custom_models()
    # 先在自定义模型中查找
    found = None
    for m in models:
        if m["id"] == model_id:
            found = m
            break
    # 再在内置模型中查找
    if not found:
        for sm in SYSTEM_MODELS:
            if sm["id"] == model_id:
                found = sm
                break
    if not found:
        raise HTTPException(status_code=404, detail="Model not found")

    # 获取 API Key：优先使用模型自带的，否则从环境变量读取
    api_key = decrypt_api_key(found.get("api_key", "")) or os.environ.get(PROVIDER_ENV_MAP.get(found["provider"], ""), "")

    try:
        from crewai.llm import LLM
        llm = LLM(
            model=found["model_id"],
            api_key=api_key,
            base_url=found["base_url"],
        )
        response = llm.call("你好，请回复'连接成功'")

        supports_fc = False
        try:
            test_llm = LLM(
                model=found["model_id"],
                api_key=api_key,
                base_url=found["base_url"],
            )
            test_llm.call(
                messages=[{"role": "user", "content": "test"}],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }],
            )
            supports_fc = True
        except Exception:
            pass

        detected_capabilities = []
        if supports_fc:
            detected_capabilities.append("tool_use")

        if not found.get("builtin", False):
            old_caps = found.get("capabilities", [])
            if old_caps != detected_capabilities:
                found["capabilities"] = detected_capabilities
                all_custom = _load_custom_models()
                for m in all_custom:
                    if m["id"] == model_id:
                        m["capabilities"] = detected_capabilities
                        break
                _save_custom_models(all_custom)

        return {
            "success": True,
            "message": "连接成功",
            "response": str(response)[:100],
            "capabilities": detected_capabilities,
        }
    except Exception as e:
        return {"success": False, "message": friendly_error_message(e)}
