# -*- coding: utf-8 -*-
"""
依赖注入模块
============

提供全局共享的路径常量和工厂函数，供各路由模块导入使用。
路径常量在模块加载时初始化，确保 data 目录结构存在。
"""

import os
import sys

# 项目根目录（api/deps.py 的上上级目录）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 数据存储根目录
DATA_DIR = os.path.join(project_root, "data")
# 用户上传文件存储目录
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
# Agent 记忆/摘要存储目录
MEMORY_DIR = os.path.join(DATA_DIR, "memory")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)


def get_memory():
    """获取全局记忆管理器单例"""
    from core.memory import get_memory_manager
    return get_memory_manager(DATA_DIR)


def get_agent_manager():
    """获取全局 Agent 管理器单例"""
    from core.agents import get_agent_manager
    return get_agent_manager(DATA_DIR)


def get_config_loader():
    """加载 config/ 目录下的配置文件（config.yaml 等），使用全局单例避免重复解析"""
    from core.config_loader import get_config
    return get_config(os.path.join(project_root, "config"))


def get_llm_factory():
    """获取 LLM 工厂实例，用于创建不同提供商的 LLM 客户端"""
    from core.llm_factory import LLMFactory
    return LLMFactory(get_config_loader())
