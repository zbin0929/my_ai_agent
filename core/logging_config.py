# -*- coding: utf-8 -*-
"""
日志配置模块
============

统一配置日志格式、级别和输出目标。
支持同时输出到控制台和日志文件，日志文件按大小自动轮转。

优化记录：
- [日志持久化] 新增模块，使用 RotatingFileHandler 自动轮转（10MB/文件，保留5份）
- [错误分离] error.log 单独记录 ERROR 级别日志，便于快速排查问题
- [噪音过滤] httpx/httpcore/uvicorn.access 设为 WARNING 级别，减少无用日志
"""

import os
import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> None:
    """
    初始化日志系统

    Args:
        log_dir: 日志文件存放目录
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
    """
    os.makedirs(log_dir, exist_ok=True)
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 根 logger 配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 避免重复添加 handler
    if root_logger.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出 — 按大小轮转，最大 10MB，保留 5 个备份
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志单独输出到 error.log
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
