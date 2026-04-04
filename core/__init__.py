# -*- coding: utf-8 -*-
"""
Core 模块包
===========

功能说明：
    包含所有核心组件的初始化和导出
    提供统一的入口点访问所有工厂和加载器

使用示例：
    from core import ConfigLoader, LLMFactory, AgentFactory, TaskOrchestrator, ToolFactory
    
    config = ConfigLoader("config").load()
    llm_factory = LLMFactory(config)
    tool_factory = ToolFactory(config)
    agent_factory = AgentFactory(config, llm_factory, tool_factory)
    orchestrator = TaskOrchestrator(config, agent_factory)

作者：AI Agent Team
版本：1.0.0
"""

from .config_loader import ConfigLoader, get_config, get_loader
from .llm_factory import LLMFactory
from .agent_factory import AgentFactory
from .task_orchestrator import TaskOrchestrator
from .tool_factory import ToolFactory
from .agents import AgentManager, AgentConfig, get_agent_manager
from .memory import MemoryManager, get_memory_manager
from .security import sanitize_file_id, is_safe_upload_path, is_sensitive_request
from .model_router import build_llm_for_task, build_llm_for_agent
from .prompt_builder import build_system_prompt, build_title_prompt
from .errors import AppError, friendly_error_message

from typing import Dict, Any

import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


__all__ = [
    "ConfigLoader",
    "LLMFactory",
    "AgentFactory",
    "TaskOrchestrator",
    "ToolFactory",
    "AgentManager",
    "AgentConfig",
    "get_agent_manager",
    "MemoryManager",
    "get_memory_manager",
    "get_config",
    "get_loader",
    "initialize_system",
    "sanitize_file_id",
    "is_safe_upload_path",
    "is_sensitive_request",
    "build_llm_for_task",
    "build_llm_for_agent",
    "build_system_prompt",
    "build_title_prompt",
    "AppError",
    "friendly_error_message",
]


def initialize_system(config_dir: str = "config") -> Dict[str, Any]:
    """
    初始化系统组件
    
    参数：
        config_dir (str): 配置文件目录
    
    返回：
        dict: 包含所有工厂实例的字典
    """
    config_loader = ConfigLoader(config_dir)
    config = config_loader.load()
    
    llm_factory = LLMFactory(config)
    tool_factory = ToolFactory(config)
    agent_factory = AgentFactory(config, llm_factory, tool_factory)
    orchestrator = TaskOrchestrator(config, agent_factory)
    
    return {
        "config": config,
        "config_loader": config_loader,
        "llm_factory": llm_factory,
        "tool_factory": tool_factory,
        "agent_factory": agent_factory,
        "orchestrator": orchestrator
    }
