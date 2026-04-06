import re
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from api.schemas import SessionCreate, SessionUpdate
from api.deps import DATA_DIR
from core.security import sanitize_file_id
from core.memory import get_memory_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_memory():
    return get_memory_manager(DATA_DIR)


def _sanitize_session_id(session_id: str) -> str:
    return sanitize_file_id(session_id)


@router.get("")
async def list_sessions():
    index = _get_memory().list_sessions()

    for s in index:
        for field in ("created_at", "updated_at"):
            val = s.get(field)
            if isinstance(val, (int, float)):
                try:
                    s[field] = datetime.fromtimestamp(val).isoformat()
                except Exception:
                    pass
        if "pinned" not in s:
            s["pinned"] = False

    pinned = [s for s in index if s.get("pinned")]
    unpinned = [s for s in index if not s.get("pinned")]
    unpinned.sort(key=lambda s: s.get("updated_at", s.get("created_at", "")), reverse=True)
    return {"sessions": pinned + unpinned}


@router.post("")
async def create_session(body: SessionCreate = None):
    session_id = uuid.uuid4().hex[:12]
    title = (body.title if body else None) or "新对话"
    session = _get_memory().create_session(session_id=session_id, title=title)
    created = session.created_at
    updated = session.updated_at
    if isinstance(created, (int, float)):
        try:
            created = datetime.fromtimestamp(created).isoformat()
        except Exception:
            pass
    if isinstance(updated, (int, float)):
        try:
            updated = datetime.fromtimestamp(updated).isoformat()
        except Exception:
            pass
    return {
        "id": session.id,
        "title": session.title,
        "pinned": False,
        "created_at": created,
        "updated_at": updated,
    }


@router.patch("/{session_id}")
async def update_session(session_id: str, body: SessionUpdate):
    result = _get_memory().update_session_meta(
        session_id,
        title=body.title,
        pinned=body.pinned,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    for field in ("created_at", "updated_at"):
        val = result.get(field)
        if isinstance(val, (int, float)):
            try:
                result[field] = datetime.fromtimestamp(val).isoformat()
            except Exception:
                pass
    if "pinned" not in result:
        result["pinned"] = False
    return result


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    session_id = _sanitize_session_id(session_id)
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    _get_memory().delete_session(session_id)
    return {"ok": True}


@router.delete("")
async def clear_all_sessions():
    index = _get_memory().list_sessions()
    for s in index:
        sid = s.get("id")
        if sid:
            _get_memory().delete_session(sid)
    return {"ok": True, "deleted_count": len(index)}


@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str):
    original_id = session_id
    session_id = _sanitize_session_id(session_id)
    logger.info(f"[Sessions] get_messages: original={original_id}, sanitized={session_id}")
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    memory = _get_memory()
    logger.info(f"[Sessions] memory instance id={id(memory)}, data_dir={memory.data_dir}")
    session = memory.load_session(session_id)
    if not session:
        logger.warning(f"[Sessions] session not found: {session_id}")
        return {"messages": [], "summary": "", "title": ""}

    messages = session.messages
    title = session.title
    summary = session.summary or ""
    if not summary:
        for m in messages:
            if m.get("role") == "assistant" and m.get("content"):
                summary = m["content"][:80]
                break
    logger.info(f"[Sessions] returning {len(messages)} messages for session {session_id}")
    return {"messages": messages, "summary": summary, "title": title}


@router.post("/{session_id}/share")
async def share_session(session_id: str):
    session_id = _sanitize_session_id(session_id)
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = _get_memory().load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    share_id = uuid.uuid4().hex[:8]
    return {"share_id": share_id, "share_url": f"/share/{share_id}"}


@router.get("/{session_id}/export")
async def export_session(session_id: str, format: str = "markdown"):
    """导出会话为 Markdown 格式"""
    session_id = _sanitize_session_id(session_id)
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = _get_memory().load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if format not in ("markdown", "md"):
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'markdown'.")

    lines = [f"# {session.title}\n"]
    if session.summary:
        lines.append(f"> **摘要**: {session.summary}\n")
    lines.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    lines.append("---\n")

    for msg in session.messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        ts = msg.get("timestamp")
        time_str = ""
        if ts:
            try:
                time_str = f" *({datetime.fromtimestamp(ts).strftime('%H:%M:%S')})*"
            except Exception:
                pass

        if role == "user":
            lines.append(f"### 🧑 用户{time_str}\n")
        elif role == "assistant":
            agent_name = ""
            agents = msg.get("agents", [])
            if agents:
                agent_name = f" ({agents[0].get('name', '')})"
            lines.append(f"### 🤖 助手{agent_name}{time_str}\n")
        elif role == "system":
            lines.append(f"### ⚙️ 系统{time_str}\n")
        else:
            lines.append(f"### {role}{time_str}\n")

        lines.append(content + "\n")

        # 附件
        files = msg.get("files", [])
        if files:
            lines.append("\n**附件:**")
            for f in files:
                fname = f.get("filename", f.get("file_id", ""))
                lines.append(f"- 📎 {fname}")
            lines.append("")

        lines.append("")

    md_content = "\n".join(lines)
    safe_title = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', session.title).strip()[:30]
    filename = f"{safe_title}_{session_id}.md"

    return PlainTextResponse(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
