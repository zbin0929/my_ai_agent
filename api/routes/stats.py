# -*- coding: utf-8 -*-
"""
用量统计 API
============

提供会话和消息的统计数据。
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter
from api.deps import DATA_DIR
from core.memory import get_memory_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_memory():
    return get_memory_manager(DATA_DIR)


@router.get("")
async def get_usage_stats():
    """获取用量统计数据"""
    memory = _get_memory()
    sessions = memory.list_sessions()
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    total_sessions = len(sessions)
    total_messages = 0
    today_messages = 0
    week_messages = 0
    month_messages = 0
    
    model_usage = {}  # model_id -> count
    skill_usage = {}  # skill_name -> count
    
    for s in sessions:
        session_id = s.get("id")
        if not session_id:
            continue
        session = memory.load_session(session_id)
        if not session:
            continue
        
        for msg in session.messages:
            total_messages += 1
            ts = msg.get("timestamp")
            if ts:
                try:
                    msg_time = datetime.fromtimestamp(ts)
                    if msg_time >= today_start:
                        today_messages += 1
                    if msg_time >= week_start:
                        week_messages += 1
                    if msg_time >= month_start:
                        month_messages += 1
                except Exception:
                    pass
            
            # Track model usage from assistant messages
            if msg.get("role") == "assistant":
                agents = msg.get("agents", [])
                for agent in agents:
                    model_id = agent.get("model_id", "unknown")
                    model_usage[model_id] = model_usage.get(model_id, 0) + 1
                
                skill_name = msg.get("skill_name")
                if skill_name:
                    skill_usage[skill_name] = skill_usage.get(skill_name, 0) + 1
    
    # Sort by usage count
    top_models = sorted(model_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    top_skills = sorted(skill_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "today_messages": today_messages,
        "week_messages": week_messages,
        "month_messages": month_messages,
        "top_models": [{"model": m, "count": c} for m, c in top_models],
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
    }
