# -*- coding: utf-8 -*-
import json
import asyncio
import inspect
import logging
from typing import AsyncGenerator

from core.chat_helpers import parse_thinking as _parse_thinking
from core.errors import friendly_error_message

logger = logging.getLogger(__name__)


def _is_async_generator(func):
    return inspect.isasyncgenfunction(func)


async def stream_skill_match(
    agent_config, matched, clean_input: str, original_input: str,
    session_id: str, memory, files, file_infos,
    generate_title_fn=None,
    enable_thinking=False, lang="zh",
) -> AsyncGenerator[str, None]:
    logger.info(f"[技能匹配] 命中技能: {matched['name']} (id={matched['id']}), 用户输入: {clean_input[:50]}")
    memory.add_message("user", original_input, session_id=session_id, metadata={"files": file_infos} if file_infos else None)
    yield json.dumps({"type": "skill", "skill_name": matched["name"], "skill_icon": matched["icon"]}, ensure_ascii=False) + "\n"
    try:
        handler = matched["handler"]
        logger.info(f"[技能执行] 开始执行技能 {matched['id']}, handler={handler.__name__}")

        full_content_parts = []
        full_thinking_parts = []

        if _is_async_generator(handler):
            async for chunk in handler(clean_input, {"files": files, "agent_config": agent_config, "enable_thinking": enable_thinking}):
                yield json.dumps({"type": "content", "content": chunk}, ensure_ascii=False) + "\n"
                full_content_parts.append(chunk)
            content = "".join(full_content_parts)
        else:
            result = await asyncio.to_thread(handler, clean_input, {"files": files, "agent_config": agent_config})
            logger.info(f"[技能执行] 技能 {matched['id']} 执行完成, success={result.get('success', False)}")
            result_msg = result.get("message", "") if isinstance(result, dict) else str(result)
            thinking, content = _parse_thinking(result_msg)

            if thinking and enable_thinking:
                full_thinking_parts.append(thinking)
                yield json.dumps({"type": "thinking", "content": thinking}, ensure_ascii=False) + "\n"
            if content:
                yield json.dumps({"type": "content", "content": content}, ensure_ascii=False) + "\n"

        ai_meta = {}
        if full_thinking_parts:
            ai_meta["thinking"] = "".join(full_thinking_parts)
        memory.add_message("assistant", content, session_id=session_id, metadata=ai_meta if ai_meta else None)

        msg_count = len(memory.get_messages(session_id))
        done_event = {"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id, "skill_used": matched["id"], "skill_name": matched["name"]}
        yield json.dumps(done_event, ensure_ascii=False) + "\n"

        if msg_count <= 2 and generate_title_fn:
            title = await generate_title_fn(agent_config, original_input, content, lang)
            if title:
                yield json.dumps({"type": "title", "title": title}, ensure_ascii=False) + "\n"

    except Exception as e:
        logger.warning(f"[技能执行] 技能 {matched['id']} 执行失败: {e}", exc_info=True)
        yield json.dumps({"type": "error", "content": friendly_error_message(e, lang)}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "done", "agent_name": agent_config.name, "model_id": agent_config.model_id}, ensure_ascii=False) + "\n"
