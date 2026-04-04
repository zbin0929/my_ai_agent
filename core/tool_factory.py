# -*- coding: utf-8 -*-
"""
工具工厂模块
============

功能说明：
    负责创建和管理工具实例
    支持内置工具和插件工具
    
    内置工具：
    - file_reader: 文件读取
    - file_writer: 文件写入
    - web_search: 网络搜索（通过 LLM 原生支持）
    
    插件工具：
    - feishu_bot: 飞书推送
    - wecom_bot: 企微推送
    - dingtalk_bot: 钉钉推送
    - browser: 浏览器自动化
    - code_executor: 代码执行

使用示例：
    from core.tool_factory import ToolFactory
    
    factory = ToolFactory(config)
    
    # 创建工具
    tool = factory.create("file_writer", {})
    
    # 列出所有可用工具
    tools = factory.list_available()

作者：AI Agent Team
版本：1.0.0
"""

import logging
from typing import Any, Dict, List, Optional

from crewai_tools import FileWriterTool

from plugins import get_plugin_class

logger = logging.getLogger(__name__)


class ToolFactoryError(Exception):
    """工具工厂错误异常类"""
    pass


class ToolFactory:
    """
    工具工厂类
    
    负责根据配置创建工具实例
    支持内置工具和通过插件系统注册的自定义工具
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化工具工厂
        
        参数：
            config (dict): 完整的系统配置
        """
        self.config = config
        
        # 构建工具注册表：tool_id -> tool_definition
        self.registry: Dict[str, Dict] = {}
        for tool_def in config.get("tools_registry", []):
            self.registry[tool_def["id"]] = tool_def
        
        # 内置工具缓存
        self._builtin_tools: Dict[str, Any] = {}
        
        logger.info(f"工具工厂初始化完成，已注册 {len(self.registry)} 个工具")
    
    def create(self, tool_id: str, tool_config: Optional[Dict] = None) -> Any:
        """
        创建工具实例
        
        参数：
            tool_id (str): 工具 ID
            tool_config (dict, optional): 工具配置（覆盖默认配置）
        
        返回：
            Any: CrewAI 工具实例
        
        异常：
            ToolFactoryError: 当工具不存在或创建失败时抛出
        
        流程：
            1. 查找工具定义
            2. 根据类型分发到对应的创建方法
            3. 传入配置参数
        """
        # 查找工具定义
        tool_def = self.registry.get(tool_id)
        if not tool_def:
            raise ToolFactoryError(f"未注册的工具: {tool_id}")
        
        # 合并配置
        config = tool_config or {}
        
        tool_type = tool_def.get("type")
        
        if tool_type == "builtin":
            return self._create_builtin(tool_id, config)
        elif tool_type == "plugin":
            return self._create_plugin(tool_id, config)
        else:
            raise ToolFactoryError(f"未知的工具类型: {tool_type}")
    
    def _create_builtin(self, tool_id: str, config: Dict) -> Any:
        """
        创建内置工具
        
        参数：
            tool_id (str): 工具 ID
            config (dict): 工具配置
        
        返回：
            Any: 内置工具实例
        
        支持的内置工具：
            - file_reader: 文件读取
            - file_writer: 文件写入
            - web_search: 网络搜索（由 LLM 层处理，此处返回 None）
        """
        # 网络搜索由 LLM 层处理，不需要创建工具实例
        if tool_id == "web_search":
            logger.debug("web_search 由 LLM 原生支持，无需创建工具实例")
            return None
        
        # 文件写入工具
        if tool_id == "file_writer":
            if tool_id not in self._builtin_tools:
                self._builtin_tools[tool_id] = FileWriterTool()
                logger.info(f"创建内置工具: {tool_id}")
            return self._builtin_tools[tool_id]
        
        # 文件读取工具
        if tool_id == "file_reader":
            if tool_id not in self._builtin_tools:
                from crewai_tools import FileReadTool
                self._builtin_tools[tool_id] = FileReadTool()
                logger.info(f"创建内置工具: {tool_id}")
            return self._builtin_tools[tool_id]
        
        raise ToolFactoryError(f"未知的内置工具: {tool_id}")
    
    def _create_plugin(self, tool_id: str, config: Dict) -> Any:
        """
        创建插件工具
        
        参数：
            tool_id (str): 工具 ID
            config (dict): 工具配置
        
        返回：
            Any: 插件工具实例
        
        流程：
            1. 从插件注册表获取插件类
            2. 传入配置创建实例
        """
        # 获取插件类
        plugin_class = get_plugin_class(tool_id)
        
        if not plugin_class:
            logger.warning(f"插件 '{tool_id}' 未注册，可能依赖未安装")
            return None
        
        try:
            # 创建插件实例，传入配置
            tool = plugin_class(config=config)
            logger.info(f"创建插件工具: {tool_id}")
            return tool
        except Exception as e:
            raise ToolFactoryError(f"创建插件 '{tool_id}' 失败: {e}")
    
    def list_available(self) -> List[Dict]:
        """
        列出所有可用的工具
        
        返回：
            list: 工具定义列表
        """
        return list(self.registry.values())
    
    def get_tool_def(self, tool_id: str) -> Optional[Dict]:
        """
        获取工具定义
        
        参数：
            tool_id (str): 工具 ID
        
        返回：
            dict: 工具定义，如果不存在则返回 None
        """
        return self.registry.get(tool_id)
    
    def is_available(self, tool_id: str) -> bool:
        """
        检查工具是否可用
        
        参数：
            tool_id (str): 工具 ID
        
        返回：
            bool: 工具是否可用
        """
        return tool_id in self.registry
    
    def get_tools_by_type(self, tool_type: str) -> List[Dict]:
        """
        按类型获取工具列表
        
        参数：
            tool_type (str): 工具类型（builtin 或 plugin）
        
        返回：
            list: 符合类型的工具定义列表
        """
        return [
            t for t in self.registry.values() 
            if t.get("type") == tool_type
        ]
