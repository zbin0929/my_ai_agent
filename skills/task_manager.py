# -*- coding: utf-8 -*-
"""
任务管理技能
============

个人任务/待办事项管理，支持增删改查、优先级、状态跟踪。
数据持久化到本地 JSON 文件。
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

TASKS_FILE = os.path.join(project_root, "data", "user_tasks.json")
_tasks_lock = threading.Lock()

PRIORITY_MAP = {
    "高": "high", "紧急": "high", "重要": "high", "high": "high",
    "中": "medium", "一般": "medium", "普通": "medium", "medium": "medium",
    "低": "low", "不急": "low", "low": "low",
}

STATUS_MAP = {
    "待办": "todo", "todo": "todo", "未开始": "todo",
    "进行中": "in_progress", "doing": "in_progress", "在做": "in_progress",
    "已完成": "done", "done": "done", "完成": "done", "搞定": "done",
}

PRIORITY_ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_ICONS = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}


def _load_tasks() -> List[Dict[str, Any]]:
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_tasks(tasks: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    tmp_path = TASKS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, TASKS_FILE)


def add_task(title: str, priority: str = "medium", due_date: str = None) -> Dict[str, Any]:
    """添加任务"""
    with _tasks_lock:
        return _add_task_locked(title, priority, due_date)


def _add_task_locked(title: str, priority: str = "medium", due_date: str = None) -> Dict[str, Any]:
    tasks = _load_tasks()
    task = {
        "id": f"task_{int(time.time()*1000)}",
        "title": title,
        "priority": PRIORITY_MAP.get(priority, priority) if priority else "medium",
        "status": "todo",
        "due_date": due_date,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    _save_tasks(tasks)
    return {"success": True, "task": task}


def list_tasks(status_filter: str = None, priority_filter: str = None) -> Dict[str, Any]:
    """列出任务"""
    tasks = _load_tasks()
    if status_filter:
        s = STATUS_MAP.get(status_filter, status_filter)
        tasks = [t for t in tasks if t["status"] == s]
    if priority_filter:
        p = PRIORITY_MAP.get(priority_filter, priority_filter)
        tasks = [t for t in tasks if t["priority"] == p]
    # 按优先级排序
    order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda t: (order.get(t["priority"], 9), t.get("created_at", "")))
    return {"success": True, "tasks": tasks}


def update_task(task_id: str = None, title_keyword: str = None, status: str = None, priority: str = None) -> Dict[str, Any]:
    """更新任务状态或优先级"""
    with _tasks_lock:
        return _update_task_locked(task_id, title_keyword, status, priority)


def _update_task_locked(task_id: str = None, title_keyword: str = None, status: str = None, priority: str = None) -> Dict[str, Any]:
    tasks = _load_tasks()
    target = None
    if task_id:
        for t in tasks:
            if t["id"] == task_id:
                target = t
                break
    elif title_keyword:
        for t in tasks:
            if title_keyword in t["title"]:
                target = t
                break

    if not target:
        return {"success": False, "message": "未找到匹配的任务"}

    if status:
        target["status"] = STATUS_MAP.get(status, status)
    if priority:
        target["priority"] = PRIORITY_MAP.get(priority, priority)
    target["updated_at"] = datetime.now().isoformat()

    _save_tasks(tasks)
    return {"success": True, "task": target}


def delete_task(task_id: str = None, title_keyword: str = None) -> Dict[str, Any]:
    """删除任务"""
    with _tasks_lock:
        return _delete_task_locked(task_id, title_keyword)


def _delete_task_locked(task_id: str = None, title_keyword: str = None) -> Dict[str, Any]:
    tasks = _load_tasks()
    original_len = len(tasks)

    if task_id:
        tasks = [t for t in tasks if t["id"] != task_id]
    elif title_keyword:
        tasks = [t for t in tasks if title_keyword not in t["title"]]

    if len(tasks) == original_len:
        return {"success": False, "message": "未找到匹配的任务"}

    _save_tasks(tasks)
    return {"success": True, "message": "任务已删除"}


def _format_task(t: Dict[str, Any]) -> str:
    """格式化单个任务为 Markdown 行"""
    pi = PRIORITY_ICONS.get(t["priority"], "⚪")
    si = STATUS_ICONS.get(t["status"], "⬜")
    due = f" | 截止: {t['due_date']}" if t.get("due_date") else ""
    return f"{si} {pi} **{t['title']}**{due}  `{t['id']}`"


@register_skill(
    skill_id="task_manager",
    name="任务管理",
    description="管理个人待办事项：添加、查看、更新、删除任务，支持优先级和状态跟踪",
    triggers=["添加任务", "创建任务", "待办", "任务列表", "我的任务",
              "完成任务", "任务管理", "todo", "to-do", "帮我记一下",
              "删除任务", "标记完成"],
    icon="task",
    examples=[
        "添加任务：完成项目报告，优先级高",
        "查看我的待办任务",
        "标记「项目报告」为已完成",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "管理待办任务：添加、查看、更新状态、删除。当用户要求管理任务、待办事项时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作：add（添加）、list（查看）、update（更新）、delete（删除）",
                        "enum": ["add", "list", "update", "delete"],
                    },
                    "title": {
                        "type": "string",
                        "description": "任务标题（添加/查找时使用）",
                    },
                    "priority": {
                        "type": "string",
                        "description": "优先级：high、medium、low",
                        "enum": ["high", "medium", "low"],
                    },
                    "status": {
                        "type": "string",
                        "description": "状态：todo、in_progress、done",
                        "enum": ["todo", "in_progress", "done"],
                    },
                },
                "required": ["action"],
            },
        },
    },
)
def handle_task_manager(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}
    action = tool_args.get("action", "")

    # 从用户输入推断 action
    if not action:
        if any(kw in user_input for kw in ["添加", "创建", "新建", "记一下"]):
            action = "add"
        elif any(kw in user_input for kw in ["查看", "列表", "我的任务", "待办", "list"]):
            action = "list"
        elif any(kw in user_input for kw in ["完成", "标记", "更新", "改为"]):
            action = "update"
        elif any(kw in user_input for kw in ["删除", "移除", "去掉"]):
            action = "delete"
        else:
            action = "list"

    if action == "add":
        title = tool_args.get("title") or user_input
        for trigger in ["添加任务", "创建任务", "新建任务", "帮我记一下", "帮我", "任务"]:
            title = title.replace(trigger, "").strip()
        title = title.strip("：:，, ")
        if not title:
            return {"success": False, "message": "请提供任务标题。比如：「添加任务：完成项目报告」"}

        priority = tool_args.get("priority", "medium")
        # 从输入中检测优先级
        for kw, p in PRIORITY_MAP.items():
            if kw in user_input:
                priority = p
                title = title.replace(kw, "").strip("，, ")
                break

        result = add_task(title, priority)
        t = result["task"]
        return {"success": True, "message": f"📋 **任务已添加！**\n\n{_format_task(t)}"}

    elif action == "list":
        status_filter = tool_args.get("status")
        priority_filter = tool_args.get("priority")
        result = list_tasks(status_filter, priority_filter)
        tasks = result["tasks"]

        if not tasks:
            return {"success": True, "message": "📋 当前没有任务，使用「添加任务：xxx」来创建。"}

        lines = ["📋 **任务列表**\n"]
        for t in tasks:
            lines.append(_format_task(t))

        # 统计
        total = len(tasks)
        done = sum(1 for t in tasks if t["status"] == "done")
        lines.append(f"\n---\n共 {total} 个任务，已完成 {done} 个")
        return {"success": True, "message": "\n".join(lines)}

    elif action == "update":
        title_kw = tool_args.get("title") or ""
        status = tool_args.get("status") or ""

        if not title_kw:
            # 从输入中提取
            clean = user_input
            for trigger in ["标记完成", "完成任务", "更新任务", "标记", "完成", "为已完成"]:
                clean = clean.replace(trigger, "").strip()
            clean = clean.strip("「」""''")
            title_kw = clean

        if not status:
            if "完成" in user_input:
                status = "done"
            elif "进行" in user_input:
                status = "in_progress"

        result = update_task(title_keyword=title_kw, status=status, priority=tool_args.get("priority"))
        if not result["success"]:
            return {"success": False, "message": f"❌ {result['message']}"}
        return {"success": True, "message": f"📋 **任务已更新！**\n\n{_format_task(result['task'])}"}

    elif action == "delete":
        title_kw = tool_args.get("title") or ""
        if not title_kw:
            clean = user_input
            for trigger in ["删除任务", "移除任务", "去掉任务", "删除", "移除"]:
                clean = clean.replace(trigger, "").strip()
            clean = clean.strip("「」""''")
            title_kw = clean

        result = delete_task(title_keyword=title_kw)
        if not result["success"]:
            return {"success": False, "message": f"❌ {result['message']}"}
        return {"success": True, "message": f"📋 {result['message']}"}

    return {"success": False, "message": "请指定操作：添加、查看、更新或删除任务"}
