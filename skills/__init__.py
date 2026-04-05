# -*- coding: utf-8 -*-
"""
Skills / Tools 系统
===================

每个 Skill 是一个独立的执行单元，同时也是可挂载到 Agent 的 Tool。
支持内置技能 + 用户自定义技能。
"""

from typing import Dict, Any, Optional, List, Callable
import json
import os
import logging
import importlib

logger = logging.getLogger(__name__)

_SKILL_REGISTRY: Dict[str, Dict[str, Any]] = {}
_SKILL_CONFIGS: Dict[str, Dict[str, str]] = {}
_DISABLED_SKILLS: set = set()
_CUSTOM_SKILLS_FILE = None
_SKILL_CONFIGS_FILE = None

CAPABILITY_TOOL_MAP = {
    "image_gen": "image_generate",
    "tts": "tts",
    "web_scrape": "web_scrape",
}


def _get_custom_skills_file():
    global _CUSTOM_SKILLS_FILE
    if _CUSTOM_SKILLS_FILE is None:
        _CUSTOM_SKILLS_FILE = os.path.join(os.getcwd(), "data", "custom_skills.json")
    return _CUSTOM_SKILLS_FILE


def _get_skill_configs_file():
    global _SKILL_CONFIGS_FILE
    if _SKILL_CONFIGS_FILE is None:
        _SKILL_CONFIGS_FILE = os.path.join(os.getcwd(), "data", "skill_configs.json")
    return _SKILL_CONFIGS_FILE


def set_data_dir(data_dir: str):
    global _CUSTOM_SKILLS_FILE, _SKILL_CONFIGS_FILE
    os.makedirs(data_dir, exist_ok=True)
    _CUSTOM_SKILLS_FILE = os.path.join(data_dir, "custom_skills.json")
    _SKILL_CONFIGS_FILE = os.path.join(data_dir, "skill_configs.json")


def register_skill(
    skill_id: str,
    name: str,
    description: str,
    triggers: List[str],
    icon: str = "🔧",
    examples: Optional[List[str]] = None,
    builtin: bool = True,
    handler: Optional[Callable] = None,
    tool_schema: Optional[Dict] = None,
    config_schema: Optional[List[Dict[str, str]]] = None,
):
    def decorator(func: Callable):
        _SKILL_REGISTRY[skill_id] = {
            "id": skill_id,
            "name": name,
            "description": description,
            "triggers": triggers,
            "icon": icon,
            "examples": examples or [],
            "builtin": builtin,
            "handler": func,
            "prompt": None,
            "tool_schema": tool_schema,
            "config_schema": config_schema or [],
        }
        return func

    if handler is not None:
        _SKILL_REGISTRY[skill_id] = {
            "id": skill_id,
            "name": name,
            "description": description,
            "triggers": triggers,
            "icon": icon,
            "examples": examples or [],
            "builtin": builtin,
            "handler": handler,
            "prompt": None,
            "tool_schema": tool_schema,
            "config_schema": config_schema or [],
        }
        return handler

    return decorator


def register_custom_skill(
    skill_id: str,
    name: str,
    description: str,
    triggers: List[str],
    icon: str = "🔧",
    prompt: Optional[str] = None,
    examples: Optional[List[str]] = None,
):
    def _custom_handler(user_input: str, context: dict) -> dict:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)
        system_msg = prompt or f"你是{name}。{description}"
        resp = llm.call(messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_input},
        ])
        return {"success": True, "message": str(resp)}

    _SKILL_REGISTRY[skill_id] = {
        "id": skill_id,
        "name": name,
        "description": description,
        "triggers": triggers,
        "icon": icon,
        "examples": examples or [],
        "builtin": False,
        "handler": _custom_handler,
        "prompt": prompt,
        "tool_schema": None,
        "config_schema": [],
    }


def get_skills() -> List[Dict[str, Any]]:
    return list(_SKILL_REGISTRY.values())


def get_skill_by_id(skill_id: str) -> Optional[Dict[str, Any]]:
    return _SKILL_REGISTRY.get(skill_id)


def get_skills_for_agent(skill_ids: List[str]) -> List[Dict[str, Any]]:
    result = []
    for sid in skill_ids:
        skill = _SKILL_REGISTRY.get(sid)
        if skill:
            result.append(skill)
    return result


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    schemas = []
    for skill_id, skill in _SKILL_REGISTRY.items():
        if skill_id not in _DISABLED_SKILLS and skill.get("tool_schema"):
            schemas.append(skill["tool_schema"])
    return schemas


def get_unassigned_tool_schemas(assigned_skill_ids: set) -> List[Dict[str, Any]]:
    schemas = []
    for skill_id, skill in _SKILL_REGISTRY.items():
        if skill_id in _DISABLED_SKILLS:
            continue
        if skill_id in assigned_skill_ids:
            continue
        if skill.get("tool_schema"):
            schemas.append(skill["tool_schema"])
    return schemas


def get_tool_schemas_by_skill_ids(skill_ids: List[str]) -> List[Dict[str, Any]]:
    schemas = []
    for sid in skill_ids:
        skill = _SKILL_REGISTRY.get(sid)
        if skill and sid not in _DISABLED_SKILLS and skill.get("tool_schema"):
            schemas.append(skill["tool_schema"])
    return schemas


def execute_tool_by_name(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """通过工具名称执行对应的技能
    
    参数:
        tool_name: 工具名称(如"generate_image")
        arguments: 工具参数(如{"prompt": "一只猫"})
    
    返回:
        技能执行结果字典
    """
    for skill_id, skill in _SKILL_REGISTRY.items():
        schema = skill.get("tool_schema")
        if schema:
            func_info = schema.get("function", {})
            if func_info.get("name") == tool_name:
                handler = skill.get("handler")
                if handler:
                    try:
                        # 技能函数签名: handler(user_input, context)
                        # 从arguments中提取prompt/text/url作为user_input
                        user_input = arguments.get("prompt") or arguments.get("text") or arguments.get("url") or str(arguments)
                        context = {"tool_args": arguments, "skill_id": skill_id}
                        return handler(user_input, context)
                    except Exception as e:
                        return {"success": False, "message": f"工具执行失败: {str(e)}"}
    return {"success": False, "message": f"未找到工具: {tool_name}"}


def get_skill_by_tool_name(tool_name: str) -> Optional[Dict[str, Any]]:
    """通过工具名称查找对应的技能"""
    for skill_id, skill in _SKILL_REGISTRY.items():
        schema = skill.get("tool_schema")
        if schema:
            func_info = schema.get("function", {})
            if func_info.get("name") == tool_name:
                return skill
    return None


def match_skill(user_input: str) -> Optional[Dict[str, Any]]:
    text = user_input.lower()
    best_match = None
    best_score = 0

    for skill_id, skill in _SKILL_REGISTRY.items():
        if skill_id in _DISABLED_SKILLS:
            continue
        if not skill.get("handler"):
            continue

        score = 0
        for trigger in skill.get("triggers", []):
            trigger_lower = trigger.lower()
            if trigger_lower in text:
                score += len(trigger_lower)

        if score > best_score:
            best_score = score
            best_match = skill

    return best_match


def match_skill_for_agent(user_input: str, agent_skill_ids: List[str]) -> Optional[Dict[str, Any]]:
    if not agent_skill_ids:
        return None
    text = user_input.lower()
    best_match = None
    best_score = 0

    for sid in agent_skill_ids:
        skill = _SKILL_REGISTRY.get(sid)
        if not skill or sid in _DISABLED_SKILLS or not skill.get("handler"):
            continue

        score = 0
        for trigger in skill.get("triggers", []):
            trigger_lower = trigger.lower()
            if trigger_lower in text:
                score += len(trigger_lower)

        if score > best_score:
            best_score = score
            best_match = skill

    return best_match


def load_builtin_skills():
    skill_modules = [
        "skills.image_generate",
        "skills.tts",
        "skills.web_scrape",
    ]
    for module_name in skill_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            logger.warning(f"技能模块加载失败: {module_name} - {e}")


def load_custom_skills():
    filepath = _get_custom_skills_file()
    if not filepath or not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            customs = json.load(f)
        for s in customs:
            register_custom_skill(
                skill_id=s["id"],
                name=s["name"],
                description=s["description"],
                triggers=s["triggers"],
                icon=s.get("icon", "🔧"),
                prompt=s["prompt"],
                examples=s.get("examples", []),
            )
    except Exception as e:
        logger.warning(f"加载自定义技能失败: {e}")


def load_disabled():
    global _DISABLED_SKILLS
    filepath = _get_custom_skills_file()
    if not filepath:
        return
    disabled_file = filepath.replace("custom_skills.json", "disabled_skills.json")
    if os.path.exists(disabled_file):
        try:
            with open(disabled_file, "r", encoding="utf-8") as f:
                _DISABLED_SKILLS = set(json.load(f))
        except Exception:
            _DISABLED_SKILLS = set()


def get_disabled_skills() -> set:
    return _DISABLED_SKILLS.copy()


def _save_custom_skills():
    filepath = _get_custom_skills_file()
    if not filepath:
        return
    customs = []
    for skill_id, skill in _SKILL_REGISTRY.items():
        if not skill.get("builtin", True) and skill.get("prompt"):
            customs.append({
                "id": skill_id,
                "name": skill["name"],
                "description": skill["description"],
                "triggers": skill["triggers"],
                "icon": skill["icon"],
                "prompt": skill["prompt"],
                "examples": skill.get("examples", []),
            })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(customs, f, ensure_ascii=False, indent=2)


def _save_disabled():
    filepath = _get_custom_skills_file()
    if not filepath:
        return
    disabled_file = filepath.replace("custom_skills.json", "disabled_skills.json")
    with open(disabled_file, "w", encoding="utf-8") as f:
        json.dump(list(_DISABLED_SKILLS), f)


def load_skill_configs():
    global _SKILL_CONFIGS
    filepath = _get_skill_configs_file()
    if not filepath or not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            _SKILL_CONFIGS = json.load(f)
    except Exception as e:
        logger.warning(f"加载技能配置失败: {e}")


def get_skill_config(skill_id: str, key: str) -> Optional[str]:
    return _SKILL_CONFIGS.get(skill_id, {}).get(key)


def get_skill_configs(skill_id: str) -> Dict[str, str]:
    return _SKILL_CONFIGS.get(skill_id, {})


def get_all_skill_configs() -> Dict[str, Dict[str, str]]:
    return _SKILL_CONFIGS.copy()


def save_skill_configs(skill_id: str, configs: Dict[str, str]):
    global _SKILL_CONFIGS
    _SKILL_CONFIGS[skill_id] = configs
    filepath = _get_skill_configs_file()
    if not filepath:
        return
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(_SKILL_CONFIGS, f, ensure_ascii=False, indent=2)
