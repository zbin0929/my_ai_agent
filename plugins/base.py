# -*- coding: utf-8 -*-
"""
工具插件基类
============

功能说明：
    所有自定义工具插件的基类
    提供统一的接口和通用功能
    
    子类需要实现：
    - _run() 方法：工具的核心逻辑
    - name 属性：工具名称
    - description 属性：工具描述

使用示例：
    from plugins.base import BasePluginTool
    
    class MyTool(BasePluginTool):
        name = "my_tool"
        description = "我的自定义工具"
        
        def _run(self, query: str) -> str:
            return f"处理结果: {query}"

作者：AI Agent Team
版本：1.0.0
"""

import logging
from typing import Any, Dict, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BasePluginTool(BaseTool):
    """
    工具插件基类
    
    所有自定义工具必须继承此类并实现 _run 方法
    
    属性：
        name (str): 工具名称，必须唯一
        description (str): 工具描述，Agent 会根据此描述决定是否使用
        config (dict): 工具配置，从 YAML 配置文件中读取
    """
    
    # 工具名称（子类必须覆盖）
    name: str = "base_plugin"
    
    # 工具描述（子类必须覆盖）
    description: str = "基础插件工具"
    
    # 工具配置（从配置文件传入）
    config: Dict[str, Any] = Field(default_factory=dict)
    
    def _run(self, query: str, **kwargs) -> str:
        """
        工具执行的核心方法
        
        参数：
            query (str): 输入查询
            **kwargs: 其他参数
        
        返回：
            str: 工具执行结果
        
        说明：
            子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _run 方法")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        参数：
            key (str): 配置键名
            default (Any): 默认值
        
        返回：
            Any: 配置值
        """
        return self.config.get(key, default)
    
    def validate_config(self) -> bool:
        """
        验证配置是否完整
        
        返回：
            bool: 配置是否有效
        
        说明：
            子类可以覆盖此方法进行自定义验证
        """
        return True
    
    def log_info(self, message: str) -> None:
        """记录信息日志"""
        logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str) -> None:
        """记录错误日志"""
        logger.error(f"[{self.name}] {message}")
    
    def log_warning(self, message: str) -> None:
        """记录警告日志"""
        logger.warning(f"[{self.name}] {message}")
