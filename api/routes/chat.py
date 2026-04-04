# -*- coding: utf-8 -*-
"""
聊天对话路由
============

提供聊天消息的流式（SSE）和非流式两种接口，
以及欢迎语获取接口。

优化记录：
- [速率限制] 流式接口 20次/分钟，非流式接口 30次/分钟，防止滥用
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from api.schemas import ChatRequest
from api.deps import get_memory
from slowapi import Limiter
from slowapi.util import get_remote_address

# [优化] 速率限制器 — 防止聊天接口被滥用
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, req: ChatRequest):
    """
    流式聊天接口（SSE）

    前端通过此接口建立 SSE 连接，逐步接收 AI 回复内容。
    每个 chunk 是一个 JSON 字符串，包含 type（content/done）和对应数据。
    """
    from core.chat_engine import stream_message

    async def event_generator():
        async for chunk in stream_message(
            user_input=req.message,
            agent_id=req.agent_id or "default",
            session_id=req.session_id,
            files=req.files,
            enable_thinking=req.enable_thinking,
            enable_search=req.enable_search,
        ):
            yield chunk

    return EventSourceResponse(event_generator())


@router.post("/send")
@limiter.limit("30/minute")
async def chat_send(request: Request, req: ChatRequest):
    """
    非流式聊天接口

    等待 AI 完整回复后一次性返回。适用于不需要流式输出的场景。
    """
    from core.chat_engine import process_message

    result = await process_message(
        user_input=req.message,
        agent_id=req.agent_id or "default",
        session_id=req.session_id,
        files=req.files,
        enable_thinking=req.enable_thinking,
        enable_search=req.enable_search,
    )
    return result


@router.get("/welcome")
async def get_welcome():
    """
    获取欢迎语

    返回默认 Agent 的欢迎消息，用于新会话初始展示。
    """
    from core.agents import get_agent_manager
    from api.deps import DATA_DIR

    manager = get_agent_manager(DATA_DIR)
    agent = manager.get_default_agent()
    return {"message": f"你好！我是 **{agent.name}**。有什么我可以帮你的？", "agent_name": agent.name}
