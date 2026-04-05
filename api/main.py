# -*- coding: utf-8 -*-
"""
FastAPI 应用入口
================

初始化 FastAPI 应用实例，注册 CORS 中间件、静态文件挂载和所有 API 路由。
启动命令：uvicorn api.main:app --host 0.0.0.0 --port 8000

优化记录：
- [速率限制] 集成 slowapi 实现 API 速率限制，默认 60次/分钟
- [日志持久化] 集成 core.logging_config，日志同时输出到控制台和文件（自动轮转）
- [健康检查] /api/health 增加 LLM 可用性检测
- [异常处理] 统一 AppError 和兆底异常处理，隐藏内部错误细节
"""

import os
import sys
import time
import logging

# 将项目根目录加入 Python 路径，使其他模块可正常导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.errors import AppError
from core.logging_config import setup_logging
from api.routes import chat, sessions, agents, skills, models, files

# [优化] 初始化日志系统 — 同时输出到控制台和文件（RotatingFileHandler 自动轮转）
setup_logging(
    log_dir=os.path.join(project_root, "logs"),
    level=os.environ.get("LOG_LEVEL", "INFO"),
)

logger = logging.getLogger(__name__)

# [优化] 速率限制器 — 防止 API 滥用，默认每分钟 60 次请求
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

APP_VERSION = "5.11.0"

# [安全加固] Admin Token 认证 — 保护配置修改类接口
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
_security_scheme = HTTPBearer(auto_error=False)


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(_security_scheme)):
    """验证管理员身份 — 配置修改接口必须携带 Authorization: Bearer <ADMIN_TOKEN>"""
    if not _ADMIN_TOKEN:
        return  # 未配置 ADMIN_TOKEN 时跳过认证（开发模式）
    if not credentials or credentials.credentials != _ADMIN_TOKEN:
        from fastapi.responses import JSONResponse
        raise AppError("未授权访问，请提供有效的管理员令牌", code="UNAUTHORIZED", status_code=401)


@asynccontextmanager
async def lifespan(application: FastAPI):
    yield
    try:
        from core.chat_engine import _shared_client as chat_client_ref
        import core.chat_engine as chat_mod
        if chat_mod._shared_client and not chat_mod._shared_client.is_closed:
            await chat_mod._shared_client.aclose()
            logger.info("已关闭 chat_engine httpx client")
    except Exception as e:
        logger.warning(f"关闭 chat_engine httpx client 失败: {e}")
    try:
        import core.search as search_mod
        if search_mod._shared_client and not search_mod._shared_client.is_closed:
            await search_mod._shared_client.aclose()
            logger.info("已关闭 search httpx client")
    except Exception as e:
        logger.warning(f"关闭 search httpx client 失败: {e}")


app = FastAPI(title="GymClaw API", version=APP_VERSION, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ==================== 全局异常处理 ====================

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """统一处理业务异常，返回结构化错误响应"""
    logger.warning(f"AppError [{exc.code}]: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """兜底异常处理，隐藏内部错误细节"""
    logger.error(f"Unhandled error: {exc} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "服务内部错误，请稍后再试"},
    )


# ==================== 请求日志中间件 ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求耗时和状态码，便于性能分析"""
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    if duration_ms > 1000:  # 超过 1 秒的慢请求特别标记
        logger.warning(f"SLOW {request.method} {request.url.path} → {response.status_code} ({duration_ms:.0f}ms)")
    else:
        logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.0f}ms)")
    return response


# ==================== 跨域配置 ====================

# 跨域配置 — 允许前端开发服务器（localhost:3000）访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载上传文件目录为静态文件服务，前端可直接通过 /uploads/xxx 访问文件
upload_dir = os.path.join(project_root, "data", "uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# 注册各功能模块的 API 路由
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])          # 聊天对话
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])  # 会话管理
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])    # Agent 管理
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])    # 技能管理
app.include_router(models.router, prefix="/api/models", tags=["models"])    # 模型管理
app.include_router(files.router, prefix="/api/files", tags=["files"])       # 文件上传/下载


@app.get("/api/health")
async def health():
    """[优化] 健康检查接口，返回服务状态、版本号和 LLM 可用性检测"""
    llm_status = "unknown"
    try:
        from core.model_info import _load_all_models
        models = _load_all_models()
        llm_status = "available" if models else "no_providers"
    except Exception:
        llm_status = "unavailable"
    return {"status": "ok", "version": APP_VERSION, "llm": llm_status}


@app.get("/api/config/search")
async def get_search_config_api():
    """返回联网搜索配置（脱敏）"""
    try:
        from core.search import get_search_config, get_search_api_key
        search_cfg = get_search_config()
        api_key = get_search_api_key()
        masked_key = ""
        if api_key:
            if len(api_key) > 8:
                masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
            else:
                masked_key = "****"
        return {
            "provider": search_cfg.get("provider", "zhipu_search"),
            "api_key_configured": bool(api_key),
            "api_key_masked": masked_key,
        }
    except Exception:
        return {"provider": "zhipu_search", "api_key_configured": False, "api_key_masked": ""}


@app.put("/api/config/search")
async def update_search_config_api(data: dict, _=Depends(require_admin)):
    """更新联网搜索配置"""
    import yaml
    provider = data.get("provider", "zhipu_search")
    api_key = data.get("api_key", "")
    if not provider:
        return {"error": "provider is required"}
    try:
        config_path = os.path.join(project_root, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not raw:
            raw = {}
        raw["search"] = {
            "provider": provider,
            "api_key": api_key or "",
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        from core.config_loader import _global_loader
        if _global_loader is not None:
            _global_loader.config["search"] = raw["search"]
        return {"message": "ok"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/config/providers")
async def get_providers_config_api():
    try:
        from core.config_loader import get_config
        config = get_config(os.path.join(project_root, "config"))
        providers = []
        for p in config.get("llm_providers", []):
            env_key = p.get("env_key", "")
            provider_api_key = p.get("api_key", "")
            resolved_key = provider_api_key or os.environ.get(env_key, "")
            masked = ""
            if resolved_key:
                if len(resolved_key) > 8:
                    masked = resolved_key[:4] + "*" * (len(resolved_key) - 8) + resolved_key[-4:]
                else:
                    masked = "****"
            providers.append({
                "id": p["id"],
                "name": p.get("name", p["id"]),
                "type": p.get("type", ""),
                "env_key": env_key,
                "api_key_configured": bool(resolved_key),
                "api_key_masked": masked,
                "supports_search": p.get("supports_search", False),
                "base_url": p.get("base_url", ""),
                "models": [{"id": m["id"], "name": m.get("name", m["id"])} for m in p.get("models", [])],
            })
        return {"providers": providers}
    except Exception:
        return {"providers": []}


@app.put("/api/config/providers/{provider_id}")
async def update_provider_config_api(provider_id: str, data: dict, _=Depends(require_admin)):
    import yaml
    api_key = data.get("api_key", "")
    if not provider_id:
        return {"error": "provider_id is required"}
    try:
        config_path = os.path.join(project_root, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not raw:
            return {"error": "config file is empty"}
        found = False
        for p in raw.get("llm_providers", []):
            if p.get("id") == provider_id:
                p["api_key"] = api_key or ""
                found = True
                break
        if not found:
            return {"error": f"provider {provider_id} not found"}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        from core.config_loader import _global_loader
        if _global_loader is not None:
            for p in _global_loader.config.get("llm_providers", []):
                if p.get("id") == provider_id:
                    p["api_key"] = api_key or ""
                    break
        return {"message": "ok"}
    except Exception as e:
        return {"error": str(e)}
