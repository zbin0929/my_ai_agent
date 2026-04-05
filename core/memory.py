# -*- coding: utf-8 -*-
"""
长期记忆模块
============

聊天历史持久化存储，支持多会话管理。
- 每个会话独立存储，按时间戳命名
- 支持自动摘要（对话过长时压缩历史）
- 支持上下文窗口管理（只送最近 N 条给 LLM）

优化记录：
- [并发修复] 移除 _current_session 共享状态，所有方法改为显式传递 session_id，
  解决多请求并发时会话互相覆盖的问题
- [数据统一] data_dir 统一为 data/memory，合并原 sessions/ 和 memory/ 双目录
- [原子写入] _safe_write_json 使用 tmp+rename 保证写入原子性
- [并发保护] 引入 filelock 防止多进程同时写入同一 JSON 文件
- [安全加固] 增加 _sanitize_session_id 和 _is_safe_path 防止路径遍历攻击
"""

import os
import json
import time
import re
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ChatSession:
    id: str
    title: str = "新对话"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None


class MemoryManager:
    MAX_CONTEXT_MESSAGES = 50
    MAX_SESSION_MESSAGES = 5000
    SUMMARY_THRESHOLD = 100
    CACHE_TTL = 30

    def __init__(self, data_dir: str = "data"):
        self.data_dir = os.path.join(data_dir, "memory")
        os.makedirs(self.data_dir, exist_ok=True)
        self._cache: Dict[str, tuple] = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def _sanitize_session_id(session_id: str) -> str:
        """安全清理会话ID，防止路径遍历攻击"""
        if not session_id:
            return ""
        # 只允许字母数字、连字符和下划线
        return re.sub(r'[^a-zA-Z0-9_\-]', "", session_id)

    def _is_safe_path(self, target_path: str) -> bool:
        try:
            base_dir = os.path.abspath(self.data_dir)
            target_path = os.path.abspath(target_path)
            return target_path.startswith(base_dir + os.sep) or target_path == base_dir
        except Exception:
            return False

    def _cache_get(self, session_id: str) -> Optional[ChatSession]:
        with self._cache_lock:
            entry = self._cache.get(session_id)
            if entry is None:
                return None
            session, ts = entry
            if time.time() - ts > self.CACHE_TTL:
                del self._cache[session_id]
                return None
            return session

    def _cache_put(self, session_id: str, session: ChatSession) -> None:
        with self._cache_lock:
            self._cache[session_id] = (session, time.time())

    def _cache_invalidate(self, session_id: str) -> None:
        with self._cache_lock:
            self._cache.pop(session_id, None)

    def _session_file(self, session_id: str) -> str:
        # 清理会话ID，防止路径遍历
        session_id = self._sanitize_session_id(session_id)
        if not session_id:
            raise ValueError("Invalid session_id")
        return os.path.join(self.data_dir, f"{session_id}.json")

    def _index_file(self) -> str:
        return os.path.join(self.data_dir, "_index.json")

    def create_session(self, title: str = "新对话", session_id: Optional[str] = None) -> ChatSession:
        if not session_id:
            session_id = f"sess_{int(time.time() * 1000)}"
        session_id = self._sanitize_session_id(session_id)
        session = ChatSession(id=session_id, title=title)
        self._save_session(session)
        self._update_index(session)
        logger.info(f"创建新会话: {session_id}")
        return session

    def load_session(self, session_id: str) -> Optional[ChatSession]:
        session_id = self._sanitize_session_id(session_id)
        if not session_id:
            return None

        cached = self._cache_get(session_id)
        if cached is not None:
            logger.debug(f"[Memory] load_session: 从缓存加载 session_id={session_id}, msg_count={len(cached.messages)}")
            return cached

        filepath = self._session_file(session_id)
        if not self._is_safe_path(filepath):
            logger.error(f"Access denied for session file: {filepath}")
            return None

        if not os.path.exists(filepath):
            logger.debug(f"[Memory] load_session: 文件不存在 session_id={session_id}")
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = ChatSession(
                id=data["id"],
                title=data.get("title", "新对话"),
                created_at=data.get("created_at", time.time()),
                updated_at=data.get("updated_at", time.time()),
                messages=data.get("messages", []),
                summary=data.get("summary"),
            )
            self._cache_put(session_id, session)
            logger.debug(f"[Memory] load_session: 从文件加载 session_id={session_id}, msg_count={len(session.messages)}")
            return session
        except Exception as e:
            logger.error(f"加载会话失败: {session_id} - {e}")
            return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        index_file = self._index_file()
        if not os.path.exists(index_file):
            return []
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            return sessions
        except Exception:
            return []

    def add_message(self, role: str, content: str, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        session = self._resolve_session(session_id)
        msg: Dict[str, Any] = {"role": role, "content": content, "timestamp": time.time()}
        if metadata:
            msg.update(metadata)
        session.messages.append(msg)
        session.updated_at = time.time()

        if len(session.messages) == 1 and role == "user":
            session.title = content[:30] + ("..." if len(content) > 30 else "")

        if len(session.messages) > self.MAX_SESSION_MESSAGES:
            self._trim_session(session)

        self._save_session(session)
        self._update_index(session)
        logger.debug(f"[Memory] add_message: session_id={session_id}, role={role}, msg_count={len(session.messages)}")

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._resolve_session(session_id)
        return session.messages

    def get_context_messages(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._resolve_session(session_id)
        return session.messages[-self.MAX_CONTEXT_MESSAGES:]

    def get_summary(self, session_id: str) -> Optional[str]:
        session = self._resolve_session(session_id)
        return session.summary

    def generate_summary(self, session_id: str) -> str:
        session = self._resolve_session(session_id)

        if not session.messages:
            session.summary = ""
            return ""

        history_lines = []
        for msg in session.messages[-30:]:
            role = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role}: {msg['content'][:200]}")
        history_text = "\n".join(history_lines)

        try:
            from core.agents import get_agent_manager
            from api.deps import DATA_DIR
            manager = get_agent_manager(DATA_DIR)
            agent_config = manager.get_agent("default")
            from core.model_router import build_llm_for_agent
            llm = build_llm_for_agent(agent_config)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个对话摘要助手。请用2-3句话总结以下对话的关键内容，"
                        "包括用户的核心需求和助手的解决方案。用中文回复。"
                    ),
                },
                {"role": "user", "content": f"请总结以下对话：\n\n{history_text}"},
            ]
            response = llm.call(messages=messages)
            summary = str(response).strip()
        except Exception as e:
            logger.warning(f"生成摘要失败: {e}")
            summary = ""
            for msg in session.messages[-5:]:
                if msg["role"] == "user":
                    summary += msg["content"][:50] + "; "
            summary = summary.strip().rstrip(";") or "对话记录"

        session.summary = summary
        self._save_session(session)
        return summary

    def clear_session(self, session_id: str) -> None:
        session = self._resolve_session(session_id)
        session.messages = []
        session.summary = None
        session.updated_at = time.time()
        self._save_session(session)
        self._update_index(session)

    def update_session_meta(self, session_id: str, title: Optional[str] = None, pinned: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        session_id = self._sanitize_session_id(session_id)
        if not session_id:
            return None
        session = self.load_session(session_id)
        if not session:
            return None
        if title is not None:
            session.title = title
        session.updated_at = time.time()
        self._save_session(session)
        entry = {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": len(session.messages),
            "summary": session.summary,
            "pinned": pinned if pinned is not None else False,
        }
        sessions = self.list_sessions()
        found = False
        for i, s in enumerate(sessions):
            if s["id"] == session_id:
                sessions[i] = entry
                found = True
                break
        if not found:
            sessions.append(entry)
        self._write_index(sessions)
        return entry

    def delete_session(self, session_id: str) -> None:
        session_id = self._sanitize_session_id(session_id)
        if not session_id:
            return

        self._cache_invalidate(session_id)

        filepath = self._session_file(session_id)
        # 安全检查
        if not self._is_safe_path(filepath):
            logger.error(f"Access denied for session file: {filepath}")
            return
        
        if os.path.exists(filepath):
            if HAS_FILELOCK:
                lock = FileLock(filepath + ".lock", timeout=5)
                with lock:
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                os.remove(filepath)

        sessions = self.list_sessions()
        sessions = [s for s in sessions if s["id"] != session_id]
        self._write_index(sessions)

    def _resolve_session(self, session_id: str) -> ChatSession:
        """根据 session_id 加载会话，不存在则自动创建
        
        [优化] 替代原 get_current_session()，不再依赖实例级 _current_session 状态，
        每次调用独立解析，保证并发安全
        """
        if not session_id:
            raise ValueError("session_id is required")
        session = self.load_session(session_id)
        if session:
            return session
        session = ChatSession(id=session_id, title="新对话")
        self._save_session(session)
        self._update_index(session)
        return session

    def _trim_session(self, session: ChatSession) -> None:
        keep = self.MAX_SESSION_MESSAGES // 2
        if not session.summary:
            old_lines = []
            for msg in session.messages[:keep]:
                role = "用户" if msg["role"] == "user" else "助手"
                old_lines.append(f"{role}: {msg['content'][:100]}")
            session.summary = "历史摘要: " + "; ".join(old_lines)[:500]
        session.messages = session.messages[-keep:]

    def rebuild_index(self) -> int:
        entries = []
        for fname in os.listdir(self.data_dir):
            if not fname.endswith(".json") or fname.startswith("_"):
                continue
            filepath = os.path.join(self.data_dir, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id", fname[:-5])
                entries.append({
                    "id": sid,
                    "title": data.get("title", "新对话"),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("messages", [])),
                    "summary": data.get("summary"),
                })
            except Exception as e:
                logger.warning(f"rebuild_index: 跳过损坏文件 {fname}: {e}")
        entries.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        self._write_index(entries)
        logger.info(f"rebuild_index: 从磁盘恢复 {len(entries)} 个会话")
        return len(entries)

    def _save_session(self, session: ChatSession) -> None:
        filepath = self._session_file(session.id)
        data = {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": session.messages,
            "summary": session.summary,
        }
        self._safe_write_json(filepath, data)
        self._cache_put(session.id, session)

    def _update_index(self, session: ChatSession) -> None:
        index_file = self._index_file()
        entry = {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": len(session.messages),
            "summary": session.summary,
        }
        if HAS_FILELOCK:
            lock = FileLock(index_file + ".lock", timeout=5)
            with lock:
                self._update_index_inner(index_file, entry)
        else:
            self._update_index_inner(index_file, entry)

    def _update_index_inner(self, index_file: str, entry: Dict) -> None:
        sessions = []
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except Exception:
                sessions = []
        found = False
        for i, s in enumerate(sessions):
            if s["id"] == entry["id"]:
                sessions[i] = entry
                found = True
                break
        if not found:
            sessions.append(entry)
        tmp_path = index_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, index_file)

    def _write_index(self, sessions: List[Dict]) -> None:
        self._safe_write_json(self._index_file(), sessions)

    @staticmethod
    def _safe_write_json(filepath: str, data: Any) -> None:
        tmp_path = filepath + ".tmp"
        try:
            if HAS_FILELOCK:
                lock = FileLock(filepath + ".lock", timeout=5)
                with lock:
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_path, filepath)
            else:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, filepath)
        except Exception as e:
            logger.error(f"写入文件失败: {filepath} - {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise


_global_memory: Optional[MemoryManager] = None
_global_memory_dir: Optional[str] = None
_global_memory_lock = threading.Lock()


def get_memory_manager(data_dir: str = "data") -> MemoryManager:
    global _global_memory, _global_memory_dir
    if _global_memory is not None:
        return _global_memory
    with _global_memory_lock:
        if _global_memory is not None:
            return _global_memory
        normalized_dir = os.path.abspath(data_dir)
        _global_memory = MemoryManager(data_dir)
        _global_memory_dir = normalized_dir
        logger.info(f"[Memory] 创建全局单例，data_dir={normalized_dir}")
        return _global_memory
