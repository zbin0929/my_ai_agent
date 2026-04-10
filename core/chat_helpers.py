# -*- coding: utf-8 -*-
"""
聊天辅助函数模块
================

解析、消息构建、提示词组装等工具函数。
从 chat_engine.py 提取。
"""

import os
import re
import asyncio
import logging
from typing import List, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.security import sanitize_file_id, is_safe_upload_path

logger = logging.getLogger(__name__)


def parse_thinking(text: str) -> tuple[str, str]:
    thinking = ""
    content = text
    think_patterns = [
        (r'<think[^>]*>(.*?)</think\s*>', re.DOTALL),
        (r'<thinking[^>]*>(.*?)</thinking\s*>', re.DOTALL),
    ]
    for pattern, flags in think_patterns:
        m = re.search(pattern, content, flags)
        if m:
            thinking = m.group(1).strip()
            content = content[:m.start()] + content[m.end():]
            content = content.strip()
            break
    
    THINK_START = "<think_process>"
    THINK_END = "</think_process>"
    if not thinking and content.startswith(THINK_START):
        parts = content.split("\n\n", 1)
        if len(parts) == 2:
            thinking = parts[0][len(THINK_START):].strip()
            content = parts[1].strip()
        else:
            if content.endswith(THINK_END):
                thinking = content[len(THINK_START):-len(THINK_END)].strip()
                content = ""
    
    return thinking, content


def get_lang() -> str:
    """获取当前语言设置，默认中文"""
    return "zh"


def resolve_file_paths(files: List[str], upload_dir: str) -> List[str]:
    if not files:
        return []
    resolved = []
    for f in files:
        if os.path.isabs(f):
            # 安全检查：绝对路径必须在 upload_dir 内
            if is_safe_upload_path(upload_dir, f):
                resolved.append(f)
        else:
            path = os.path.join(upload_dir, f)
            if os.path.exists(path) and is_safe_upload_path(upload_dir, path):
                resolved.append(path)
    return resolved


def parse_mentions(user_input: str) -> Tuple[str, List[str]]:
    mentions = re.findall(r'@(\S+)', user_input)
    clean = re.sub(r'@\S+\s*', '', user_input).strip()
    return clean, mentions


def build_history_text(context_messages: list, agent_name: str) -> str:
    if not context_messages:
        return ""
    parts = []
    for msg in context_messages[-20:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"用户: {content}")
        elif role == "assistant":
            parts.append(f"{agent_name}: {content}")
    return "\n".join(parts)


def _build_file_content_sync(files: List[str], user_input: str, upload_dir: str) -> str:
    if not files:
        return user_input
    resolved = resolve_file_paths(files, upload_dir)
    file_parts = []
    for f in resolved:
        if not is_safe_upload_path(upload_dir, f):
            continue
        file_id = sanitize_file_id(f)
        try:
            from core.file_reader import read_file
            result = read_file(f)
            if result.get("success"):
                content = result["content"]
                if len(content) > 30000:
                    content = content[:30000] + "\n... [内容已截断]"
                file_parts.append(f"[文件 {file_id}]:\n{content}")
            else:
                file_parts.append(f"[文件 {file_id}]: ({result.get('message', '无法读取')})")
        except Exception:
            file_parts.append(f"[文件 {file_id}]: (无法读取)")
    file_text = "\n\n".join(file_parts)
    if file_text:
        return f"{user_input}\n\n---\n附件内容:\n{file_text}"
    return user_input


async def build_file_content(files: List[str], user_input: str, upload_dir: str) -> str:
    if not files:
        return user_input
    return await asyncio.to_thread(_build_file_content_sync, files, user_input, upload_dir)


def build_chat_messages(system_prompt: str, history_text_or_messages, user_content: str) -> list:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    # 支持两种格式：结构化消息列表（优先）或旧版文本格式
    if isinstance(history_text_or_messages, list):
        for msg in history_text_or_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    elif isinstance(history_text_or_messages, str) and history_text_or_messages:
        for line in history_text_or_messages.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("用户: ") or line.startswith("用户:"):
                messages.append({"role": "user", "content": line.split(": ", 1)[-1]})
            elif ": " in line:
                messages.append({"role": "assistant", "content": line.split(": ", 1)[-1]})
    messages.append({"role": "user", "content": user_content})
    return messages


