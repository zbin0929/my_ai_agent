# -*- coding: utf-8 -*-
"""
错误处理模块
============

定义业务异常类层级和用户友好的错误消息转换。

优化记录：
- [模块拆分] 从原 chat_engine.py 拆分出来，统一错误处理
- [异常层级] AppError → ConfigError/LLMError/SkillError，结构化错误码
- [友好消息] friendly_error_message 将内部异常转为用户可读文案
"""

import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ConfigError(AppError):
    """配置错误"""
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR", status_code=500)


class LLMError(AppError):
    """LLM 调用错误"""
    def __init__(self, message: str, code: str = "LLM_ERROR"):
        super().__init__(message, code=code, status_code=502)


class SkillError(AppError):
    """技能执行错误"""
    def __init__(self, message: str):
        super().__init__(message, code="SKILL_ERROR", status_code=500)


class AuthError(AppError):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, code="AUTH_ERROR", status_code=401)


class RateLimitError(AppError):
    """速率限制错误"""
    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message, code="RATE_LIMIT", status_code=429)


def friendly_error_message(error: Exception, lang: str = "zh") -> str:
    """
    将后端异常转换为用户友好的错误提示。
    隐藏敏感细节，只返回通用的、可操作的提示信息。
    """
    # 如果是我们自定义的异常，直接返回消息
    if isinstance(error, AppError):
        return error.message

    error_str = str(error).lower()

    if lang == "zh":
        if any(kw in error_str for kw in ["insufficient_quota", "quota", "billing", "余额", "429", "rate_limit"]):
            return "模型服务调用频率超限或余额不足，请稍后再试，或在设置中切换到其他模型。"
        if any(kw in error_str for kw in ["invalid_api_key", "unauthorized", "authentication", "401", "403"]):
            return "模型认证失败，请检查 API Key 配置是否正确。"
        if any(kw in error_str for kw in ["model_not_found", "not_found", "does not exist"]):
            return "当前选择的模型不可用，请在设置中切换到其他模型。"
        if any(kw in error_str for kw in ["timeout", "timed out", "connection", "network"]):
            return "网络连接超时，请检查网络后重试。"
        return "抱歉，AI 服务暂时不可用，请稍后再试。"
    else:
        if any(kw in error_str for kw in ["insufficient_quota", "quota", "billing", "429", "rate_limit"]):
            return "Model service rate limited or quota exceeded. Please try again later or switch to another model."
        if any(kw in error_str for kw in ["invalid_api_key", "unauthorized", "authentication", "401", "403"]):
            return "Model authentication failed. Please check your API Key configuration."
        if any(kw in error_str for kw in ["model_not_found", "not_found", "does not exist"]):
            return "The selected model is unavailable. Please switch to another model in settings."
        if any(kw in error_str for kw in ["timeout", "timed out", "connection", "network"]):
            return "Network connection timed out. Please check your network and try again."
        return "Sorry, the AI service is temporarily unavailable. Please try again later."
