# -*- coding: utf-8 -*-
"""
提醒/定时任务技能
==================

支持用户设置提醒和定时任务。
使用内存存储 + JSON 持久化，后台线程定时检查。
到期后通过日志记录（可扩展对接通知插件）。
"""

import os
import sys
import json
import re
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

REMINDERS_FILE = os.path.join(project_root, "data", "reminders.json")
_reminders: List[Dict[str, Any]] = []
_lock = threading.Lock()
_checker_started = False


MAX_REMINDERS = 200


def _load_reminders():
    global _reminders
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                _reminders = json.load(f)
        except Exception:
            _reminders = []
    else:
        _reminders = []


def _save_reminders():
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    # 清理超过 30 天的已触发/已取消提醒，防止无限增长
    global _reminders
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    _reminders = [
        r for r in _reminders
        if r["status"] == "pending" or r.get("created_at", "") > cutoff
    ]
    # 硬限制最大数量
    if len(_reminders) > MAX_REMINDERS:
        _reminders = _reminders[-MAX_REMINDERS:]
    tmp_path = REMINDERS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_reminders, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, REMINDERS_FILE)


def _start_checker():
    """启动后台检查线程"""
    global _checker_started
    if _checker_started:
        return
    _checker_started = True

    def _check_loop():
        while True:
            try:
                now = datetime.now().isoformat()
                with _lock:
                    for r in _reminders:
                        if r["status"] == "pending" and r["due_time"] <= now:
                            r["status"] = "triggered"
                            logger.info(f"⏰ 提醒到期: {r['content']} (设定时间: {r['due_time']})")
                    _save_reminders()
            except Exception as e:
                logger.error(f"提醒检查异常: {e}")
            time.sleep(30)

    t = threading.Thread(target=_check_loop, daemon=True, name="reminder-checker")
    t.start()


def _parse_time(text: str) -> Optional[datetime]:
    """从自然语言中解析时间"""
    now = datetime.now()

    # "X分钟后" / "X小时后" / "X天后"
    m = re.search(r'(\d+)\s*分钟后', text)
    if m:
        return now + timedelta(minutes=int(m.group(1)))
    m = re.search(r'(\d+)\s*小时后', text)
    if m:
        return now + timedelta(hours=int(m.group(1)))
    m = re.search(r'(\d+)\s*天后', text)
    if m:
        return now + timedelta(days=int(m.group(1)))

    # "明天X点" / "后天X点"
    m = re.search(r'明天\s*(\d{1,2})\s*[点时:]', text)
    if m:
        hour = int(m.group(1))
        return (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0)
    m = re.search(r'后天\s*(\d{1,2})\s*[点时:]', text)
    if m:
        hour = int(m.group(1))
        return (now + timedelta(days=2)).replace(hour=hour, minute=0, second=0)

    # "下午X点" / "上午X点" / "X点"
    m = re.search(r'下午\s*(\d{1,2})\s*[点时:]?(\d{0,2})', text)
    if m:
        hour = int(m.group(1))
        if hour < 12:
            hour += 12
        minute = int(m.group(2)) if m.group(2) else 0
        target = now.replace(hour=hour, minute=minute, second=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    m = re.search(r'上午\s*(\d{1,2})\s*[点时:]?(\d{0,2})', text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        target = now.replace(hour=hour, minute=minute, second=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    m = re.search(r'(\d{1,2})\s*[点时:](\d{0,2})', text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        target = now.replace(hour=hour, minute=minute, second=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "YYYY-MM-DD HH:MM" 格式
    m = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})', text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))

    return None


def add_reminder(content: str, due_time: str = None, raw_input: str = "") -> Dict[str, Any]:
    """添加提醒"""
    _start_checker()

    if due_time:
        try:
            dt = datetime.fromisoformat(due_time)
        except ValueError:
            dt = _parse_time(due_time)
    else:
        dt = _parse_time(raw_input or content)

    if not dt:
        return {"success": False, "message": "无法识别时间，请使用如「5分钟后」「明天9点」「下午3点」等格式"}

    reminder = {
        "id": f"rem_{int(time.time()*1000)}",
        "content": content,
        "due_time": dt.isoformat(),
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }

    with _lock:
        _load_reminders()
        _reminders.append(reminder)
        _save_reminders()

    return {
        "success": True,
        "reminder": reminder,
        "due_time_str": dt.strftime("%Y-%m-%d %H:%M"),
    }


def list_reminders(include_done: bool = False) -> Dict[str, Any]:
    """列出提醒"""
    with _lock:
        _load_reminders()
        if include_done:
            items = list(_reminders)
        else:
            items = [r for r in _reminders if r["status"] == "pending"]
    return {"success": True, "reminders": items}


def cancel_reminder(reminder_id: str) -> Dict[str, Any]:
    """取消提醒"""
    with _lock:
        _load_reminders()
        for r in _reminders:
            if r["id"] == reminder_id:
                r["status"] = "cancelled"
                _save_reminders()
                return {"success": True, "message": f"已取消提醒: {r['content']}"}
    return {"success": False, "message": "未找到该提醒"}


@register_skill(
    skill_id="reminder",
    name="提醒",
    description="设置定时提醒，支持自然语言时间（如「5分钟后」「明天9点」）",
    triggers=["提醒我", "设置提醒", "定时提醒", "闹钟", "提醒一下",
              "remind me", "别忘了", "记得提醒", "到时候提醒"],
    icon="bell",
    examples=[
        "提醒我5分钟后喝水",
        "明天9点提醒我开会",
        "下午3点提醒我发邮件",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "设置定时提醒。当用户要求提醒、设置闹钟、定时通知时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "提醒内容，如'喝水'、'开会'",
                    },
                    "due_time": {
                        "type": "string",
                        "description": "提醒时间，ISO格式或自然语言如'5分钟后'、'明天9点'",
                    },
                },
                "required": ["content"],
            },
        },
    },
)
def handle_reminder(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}

    # 查看提醒列表
    if any(kw in user_input for kw in ["查看提醒", "提醒列表", "有什么提醒", "list"]):
        result = list_reminders()
        if not result["reminders"]:
            return {"success": True, "message": "⏰ 当前没有待执行的提醒"}
        lines = ["⏰ **当前提醒列表**\n"]
        for r in result["reminders"]:
            dt = datetime.fromisoformat(r["due_time"])
            lines.append(f"- **{r['content']}** — {dt.strftime('%m-%d %H:%M')} [{r['id']}]")
        return {"success": True, "message": "\n".join(lines)}

    # 添加提醒
    content = tool_args.get("content") or user_input
    due_time = tool_args.get("due_time")

    # 清理触发词提取提醒内容
    for trigger in ["提醒我", "设置提醒", "定时提醒", "提醒一下", "记得提醒",
                     "别忘了", "帮我", "请"]:
        content = content.replace(trigger, "").strip()

    result = add_reminder(content, due_time=due_time, raw_input=user_input)
    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    msg = (
        f"⏰ **提醒已设置！**\n\n"
        f"**内容：** {result['reminder']['content']}\n"
        f"**时间：** {result['due_time_str']}\n"
        f"**ID：** `{result['reminder']['id']}`"
    )
    return {"success": True, "message": msg}
