# -*- coding: utf-8 -*-
"""
Agent 管理路由
===============

提供 Agent 的 CRUD 接口：列表、创建、更新、删除。
默认 Agent（id="default"）不可删除。
列表和详情返回时附带模型的 capabilities 和 skills 信息。
"""

import json
import os
from dataclasses import asdict
from fastapi import APIRouter, HTTPException
from api.schemas import AgentCreate, AgentUpdate
from api.deps import get_agent_manager, DATA_DIR
from core.model_info import get_model_capabilities as _get_model_capabilities

router = APIRouter()


def _agent_with_capabilities(agent) -> dict:
    data = asdict(agent)
    data["capabilities"] = _get_model_capabilities(agent.model_id)
    return data


@router.get("")
async def list_agents():
    """获取所有 Agent 列表（附带模型 capabilities）"""
    manager = get_agent_manager()
    agents = manager.list_agents()
    return {"agents": [_agent_with_capabilities(a) for a in agents]}


_skills_loaded = False
_skills_load_lock = __import__("threading").Lock()


def _ensure_skills_loaded():
    global _skills_loaded
    if _skills_loaded:
        return
    with _skills_load_lock:
        if _skills_loaded:
            return
        from skills import set_data_dir, load_builtin_skills, load_custom_skills, load_skill_configs, load_disabled
        set_data_dir(DATA_DIR)
        load_builtin_skills()
        load_custom_skills()
        load_skill_configs()
        load_disabled()
        _skills_loaded = True


@router.get("/available-skills")
async def get_available_skills():
    from skills import get_skills, get_skill_configs, get_disabled_skills

    _ensure_skills_loaded()

    disabled = get_disabled_skills()

    result = []
    for s in get_skills():
        sid = s["id"]
        if sid in disabled:
            continue
        schema = s.get("config_schema", [])
        config = get_skill_configs(sid)
        has_required = any(item.get("required") for item in schema)
        all_configured = all(config.get(item["key"]) for item in schema if item.get("required"))
        result.append({
            "id": sid,
            "name": s["name"],
            "description": s["description"],
            "icon": s["icon"],
            "config_status": "none" if not has_required else ("ok" if all_configured else "missing"),
        })
    return {"skills": result}


@router.post("")
async def create_agent(req: AgentCreate):
    """创建新 Agent（员工）— 支持角色、模型、温度、API Key、技能绑定等配置"""
    manager = get_agent_manager()
    kwargs = {
        "name": req.name,
        "avatar": req.avatar,
        "role": req.role,
        "description": req.description,
        "model_id": req.model_id,
        "model_provider": req.model_provider,
        "temperature": req.temperature,
        "enable_search": req.enable_search,
        "enable_thinking": req.enable_thinking,
        "custom_api_key": req.custom_api_key,
        "custom_base_url": req.custom_base_url,
    }
    if req.skills is not None:
        kwargs["skills"] = req.skills
    if req.agent_type is not None:
        kwargs["agent_type"] = req.agent_type
    agent = manager.create_agent(**kwargs)
    return _agent_with_capabilities(agent)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, req: AgentUpdate):
    """更新 Agent 配置 — 只更新请求中提供的字段"""
    manager = get_agent_manager()
    updates = req.model_dump(exclude_unset=True)
    agent = manager.update_agent(agent_id, **updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_with_capabilities(agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """删除 Agent — 默认 Agent 不可删除"""
    manager = get_agent_manager()
    if agent_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default agent")
    ok = manager.delete_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}
