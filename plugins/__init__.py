# -*- coding: utf-8 -*-
"""
Plugins 模块包
===============

功能说明：
    工具插件系统的入口模块
    提供插件注册和发现机制

使用示例：
    from plugins import list_plugins, get_plugin_class
    
    # 列出所有已注册的插件
    plugins = list_plugins()
    
    # 获取指定插件的类
    cls = get_plugin_class("feishu_bot")

作者：AI Agent Team
版本：1.0.0
"""

from typing import Dict, Type, Optional

# 插件注册表：plugin_id -> plugin_class
_PLUGIN_REGISTRY: Dict[str, Type] = {}


def register_plugin(plugin_id: str):
    """
    插件注册装饰器
    
    参数：
        plugin_id (str): 插件唯一标识符
    
    使用示例：
        @register_plugin("feishu_bot")
        class FeishuBotTool(BasePluginTool):
            ...
    """
    def decorator(cls):
        _PLUGIN_REGISTRY[plugin_id] = cls
        return cls
    return decorator


def get_plugin_class(plugin_id: str) -> Optional[Type]:
    """
    获取已注册的插件类
    
    参数：
        plugin_id (str): 插件 ID
    
    返回：
        Type: 插件类，如果不存在则返回 None
    """
    return _PLUGIN_REGISTRY.get(plugin_id)


def list_plugins() -> Dict[str, Type]:
    """
    列出所有已注册的插件
    
    返回：
        Dict[str, Type]: 插件 ID -> 插件类的映射
    """
    return _PLUGIN_REGISTRY.copy()


def _auto_discover():
    """
    自动发现和加载插件
    
    说明：
        导入所有插件模块，触发 @register_plugin 装饰器注册
        新增插件只需要在 plugins/ 目录下创建文件并使用装饰器即可
    """
    import importlib
    
    plugin_modules = [
        "plugins.feishu_bot",
        "plugins.wecom_bot",
        "plugins.dingtalk_bot",
        "plugins.browser",
        "plugins.code_executor",
    ]
    
    for module_name in plugin_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass  # 插件依赖未安装，跳过


# 自动发现插件
_auto_discover()
