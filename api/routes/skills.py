# -*- coding: utf-8 -*-
import os
import json
import tempfile
from fastapi import APIRouter, HTTPException
from filelock import FileLock
from api.schemas import SkillCreate, SkillUpdate
from api.deps import DATA_DIR

router = APIRouter()

SKILLS_FILE = os.path.join(DATA_DIR, "custom_skills.json")
SKILLS_LOCK = FileLock(SKILLS_FILE + ".lock", timeout=10)


def _load_custom_skills() -> list:
    with SKILLS_LOCK:
        if os.path.exists(SKILLS_FILE):
            with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    return []


def _save_custom_skills(skills: list):
    with SKILLS_LOCK:
        dir_name = os.path.dirname(SKILLS_FILE)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(skills, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, SKILLS_FILE)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


@router.get("")
async def list_skills():
    from skills import (
        set_data_dir, load_builtin_skills, load_skill_configs,
        load_disabled, get_skills, get_skill_configs, get_disabled_skills,
    )
    set_data_dir(DATA_DIR)
    load_builtin_skills()
    load_skill_configs()
    load_disabled()

    disabled = get_disabled_skills()

    builtin = []
    for s in get_skills():
        sid = s["id"]
        builtin.append({
            "id": sid,
            "name": s["name"],
            "description": s["description"],
            "icon": s["icon"],
            "triggers": s.get("triggers", []),
            "examples": s.get("examples", []),
            "builtin": True,
            "enabled": sid not in disabled,
            "config_schema": s.get("config_schema", []),
            "config": get_skill_configs(sid),
        })

    custom_raw = _load_custom_skills()
    custom = []
    for s in custom_raw:
        custom.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "icon": s.get("icon", "🔧"),
            "triggers": s.get("triggers", []),
            "examples": s.get("examples", []),
            "builtin": False,
            "enabled": s.get("enabled", True),
            "config_schema": [],
            "config": {},
        })
    return {"skills": builtin + custom}


@router.post("")
async def create_skill(req: SkillCreate):
    skills = _load_custom_skills()
    if any(s["id"] == req.id for s in skills):
        raise HTTPException(status_code=400, detail="Skill ID already exists")
    new_skill = {
        "id": req.id,
        "name": req.name,
        "description": req.description,
        "triggers": req.triggers,
        "icon": req.icon or "🔧",
        "prompt": req.prompt,
        "examples": req.examples or [],
        "enabled": True,
    }
    skills.append(new_skill)
    _save_custom_skills(skills)
    return new_skill


@router.put("/{skill_id}")
async def update_skill(skill_id: str, req: SkillUpdate):
    skills = _load_custom_skills()
    found = None
    for s in skills:
        if s["id"] == skill_id:
            found = s
            break
    if not found:
        raise HTTPException(status_code=404, detail="Skill not found")
    updates = req.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if v is not None:
            found[k] = v
    _save_custom_skills(skills)
    return found


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    skills = _load_custom_skills()
    new_skills = [s for s in skills if s["id"] != skill_id]
    if len(new_skills) == len(skills):
        raise HTTPException(status_code=404, detail="Skill not found")
    _save_custom_skills(new_skills)
    return {"ok": True}


@router.patch("/{skill_id}/toggle")
async def toggle_skill(skill_id: str):
    skills = _load_custom_skills()
    found = None
    for s in skills:
        if s["id"] == skill_id:
            found = s
            break
    if not found:
        raise HTTPException(status_code=404, detail="Skill not found")
    found["enabled"] = not found.get("enabled", True)
    _save_custom_skills(skills)
    return found


@router.get("/{skill_id}/config")
async def get_skill_config_api(skill_id: str):
    from skills import set_data_dir, load_builtin_skills, load_skill_configs, get_skill_configs, get_skill_by_id
    set_data_dir(DATA_DIR)
    load_builtin_skills()
    load_skill_configs()

    skill = get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {
        "skill_id": skill_id,
        "config_schema": skill.get("config_schema", []),
        "config": get_skill_configs(skill_id),
    }


@router.put("/{skill_id}/config")
async def save_skill_config_api(skill_id: str, config: dict):
    from skills import set_data_dir, load_builtin_skills, load_skill_configs, get_skill_by_id, save_skill_configs
    set_data_dir(DATA_DIR)
    load_builtin_skills()
    load_skill_configs()

    skill = get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    save_skill_configs(skill_id, config)
    return {"ok": True, "skill_id": skill_id, "config": config}
