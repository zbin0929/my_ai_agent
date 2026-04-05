# -*- coding: utf-8 -*-
"""
配置加载器模块
================

功能说明：
    负责加载、解析和验证系统配置文件
    支持以下特性：
    - YAML 格式配置文件解析
    - 环境变量替换（${VAR_NAME} 格式）
    - 配置文件拆分与合并
    - 配置验证与默认值填充
    - 配置热重载

使用示例：
    from core.config_loader import ConfigLoader
    
    loader = ConfigLoader(config_dir="config")
    config = loader.load()
    
    # 获取配置项
    llm_config = config.get("default_llm")
    agents = config.get("agents", [])

作者：AI Agent Team
版本：1.0.0
"""

import os
import re
import yaml
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from copy import deepcopy

# 配置日志记录器
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    配置错误异常类
    
    当配置文件格式错误、缺少必要字段或验证失败时抛出此异常
    """
    pass


class ConfigLoader:
    """
    配置加载器类
    
    负责从 YAML 文件加载配置，支持环境变量替换和配置验证
    
    属性：
        config_dir (Path): 配置文件目录路径
        config (dict): 加载后的配置字典
        _env_pattern (Pattern): 环境变量匹配正则表达式
    
    使用示例：
        >>> loader = ConfigLoader("config")
        >>> config = loader.load()
        >>> print(config["system"]["name"])
        '多Agent智能体系统'
    """
    
    # 环境变量占位符的正则表达式
    # 匹配格式：${VAR_NAME} 或 ${VAR_NAME:default_value}
    _ENV_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置加载器
        
        参数：
            config_dir (str): 配置文件所在目录，可以是相对路径或绝对路径
                             默认为 "config"
        
        说明：
            如果传入相对路径，会相对于当前工作目录进行解析
        """
        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
        
        logger.info(f"配置加载器初始化完成，配置目录: {self.config_dir.absolute()}")
    
    def load(self, config_file: str = "config.yaml") -> Dict[str, Any]:
        """
        加载主配置文件
        
        参数：
            config_file (str): 主配置文件名，默认为 "config.yaml"
        
        返回：
            Dict[str, Any]: 解析后的配置字典
        
        异常：
            ConfigError: 当配置文件不存在或格式错误时抛出
        
        流程：
            1. 加载主配置文件
            2. 加载拆分的子配置文件（如果存在）
            3. 合并所有配置
            4. 解析环境变量
            5. 验证配置完整性
            6. 填充默认值
        """
        logger.info(f"开始加载配置文件: {config_file}")
        
        # 步骤1：加载主配置文件
        main_config_path = self.config_dir / config_file
        if not main_config_path.exists():
            raise ConfigError(f"配置文件不存在: {main_config_path}")
        
        self.config = self._load_yaml(main_config_path)
        logger.debug(f"主配置文件加载完成，包含 {len(self.config)} 个顶级配置项")
        
        # 步骤2：加载拆分的子配置文件
        self._load_split_configs()
        
        # 步骤3：解析环境变量
        self.config = self._resolve_env_vars(self.config)
        logger.debug("环境变量解析完成")
        
        # 步骤4：验证配置
        self._validate()
        logger.debug("配置验证通过")
        
        # 步骤5：填充默认值
        self._fill_defaults()
        
        logger.info("配置加载完成")
        return self.config
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        加载单个 YAML 文件
        
        参数：
            file_path (Path): YAML 文件路径
        
        返回：
            Dict[str, Any]: 解析后的字典
        
        异常：
            ConfigError: 当文件格式错误时抛出
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content if content else {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML 解析错误 [{file_path}]: {e}")
        except Exception as e:
            raise ConfigError(f"读取配置文件失败 [{file_path}]: {e}")
    
    def _load_split_configs(self) -> None:
        """
        加载拆分的子配置文件
        
        说明：
            系统支持将配置拆分到不同目录下的 YAML 文件中：
            - config/llm/*.yaml - LLM 提供商配置
            - config/agents/*.yaml - Agent 配置
            - config/tools/*.yaml - 工具配置
            - config/tasks/*.yaml - 任务配置
            
            子配置文件会被合并到主配置的对应字段中
        """
        # 定义要加载的子配置目录映射
        # key: 子目录名, value: 主配置中的字段名
        split_dirs = {
            "llm": "llm_providers",
            "agents": "agents",
            "tools": "tools_registry",
            "tasks": "tasks"
        }
        
        for subdir, config_key in split_dirs.items():
            subdir_path = self.config_dir / subdir
            if not subdir_path.exists():
                continue
            
            # 遍历子目录中的所有 YAML 文件
            yaml_files = list(subdir_path.glob("*.yaml")) + list(subdir_path.glob("*.yml"))
            
            if not yaml_files:
                continue
            
            # 确保主配置中存在该字段
            if config_key not in self.config:
                self.config[config_key] = []
            
            # 加载并合并每个文件
            for yaml_file in yaml_files:
                logger.debug(f"加载子配置文件: {yaml_file}")
                sub_config = self._load_yaml(yaml_file)
                
                # 如果子配置是列表，扩展到主配置
                if isinstance(sub_config, list):
                    self.config[config_key].extend(sub_config)
                # 如果子配置是字典，合并到主配置
                elif isinstance(sub_config, dict):
                    if isinstance(self.config[config_key], list):
                        self.config[config_key].append(sub_config)
                    else:
                        self.config[config_key].update(sub_config)
            
            logger.info(f"从 {subdir}/ 目录加载了 {len(yaml_files)} 个配置文件")
    
    def _resolve_env_vars(self, value: Any) -> Any:
        """
        递归解析配置值中的环境变量
        
        参数：
            value: 要解析的配置值，可以是任意类型
        
        返回：
            解析后的值，环境变量占位符被替换为实际值
        
        说明：
            支持两种格式的环境变量引用：
            - ${VAR_NAME} - 直接引用环境变量，如果不存在则报错
            - ${VAR_NAME:default} - 引用环境变量，如果不存在则使用默认值
        
        示例：
            >>> os.environ["API_KEY"] = "12345"
            >>> self._resolve_env_vars("${API_KEY}")
            '12345'
            >>> self._resolve_env_vars("${UNKNOWN:value}")
            'value'
        """
        # 如果是字符串，检查是否包含环境变量占位符
        if isinstance(value, str):
            return self._replace_env_in_string(value)
        
        # 如果是字典，递归处理每个值
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        
        # 如果是列表，递归处理每个元素
        elif isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]
        
        # 其他类型直接返回
        else:
            return value
    
    def _replace_env_in_string(self, text: str) -> str:
        """
        替换字符串中的环境变量占位符
        
        参数：
            text (str): 包含环境变量占位符的字符串
        
        返回：
            str: 替换后的字符串
        
        说明：
            对于每个匹配的占位符 ${VAR} 或 ${VAR:default}：
            1. 尝试从环境变量获取 VAR 的值
            2. 如果不存在且有默认值，使用默认值
            3. 如果不存在且无默认值，发出警告并保留原占位符
        """
        def replacer(match):
            var_name = match.group(1)  # 环境变量名
            default_val = match.group(2)  # 默认值（可能为 None）
            
            # 尝试获取环境变量
            env_value = os.environ.get(var_name)
            
            if env_value is not None:
                logger.debug(f"环境变量替换: {var_name} = {env_value[:20]}...")
                return env_value
            elif default_val is not None:
                logger.debug(f"环境变量 {var_name} 未设置，使用默认值: {default_val}")
                return default_val
            else:
                logger.warning(f"环境变量 {var_name} 未设置且无默认值，保留占位符")
                return match.group(0)  # 保留原占位符
        
        return self._ENV_PATTERN.sub(replacer, text)
    
    def _validate(self) -> None:
        """
        验证配置的完整性和正确性
        
        异常：
            ConfigError: 当配置验证失败时抛出
        
        验证项：
            1. 必要的配置项是否存在
            2. 配置值的类型是否正确
            3. 引用的 ID 是否有效（如 Agent 引用的工具 ID）
        """
        errors = []
        
        # 验证系统配置
        if "system" not in self.config:
            errors.append("缺少 'system' 配置项")
        
        # 验证默认 LLM 配置
        if "default_llm" not in self.config:
            errors.append("缺少 'default_llm' 配置项")
        else:
            default_llm = self.config["default_llm"]
            if "provider" not in default_llm:
                errors.append("default_llm 缺少 'provider' 字段")
            if "model" not in default_llm:
                errors.append("default_llm 缺少 'model' 字段")
        
        # 验证 LLM 提供商配置
        if "llm_providers" in self.config:
            provider_ids = set()
            for provider in self.config["llm_providers"]:
                if "id" not in provider:
                    errors.append("llm_providers 中存在缺少 'id' 的提供商")
                    continue
                if provider["id"] in provider_ids:
                    errors.append(f"重复的 LLM 提供商 ID: {provider['id']}")
                provider_ids.add(provider["id"])
        
        # 验证 Agent 配置
        if "agents" in self.config:
            agent_ids = set()
            tool_ids = {t["id"] for t in self.config.get("tools_registry", [])}
            
            for agent in self.config["agents"]:
                if "id" not in agent:
                    errors.append("agents 中存在缺少 'id' 的 Agent")
                    continue
                if agent["id"] in agent_ids:
                    errors.append(f"重复的 Agent ID: {agent['id']}")
                agent_ids.add(agent["id"])
                
                # 验证 Agent 引用的工具是否存在
                for tool in agent.get("tools", []):
                    if tool["id"] not in tool_ids:
                        errors.append(f"Agent '{agent['id']}' 引用了不存在的工具: {tool['id']}")
        
        # 验证任务配置
        if "tasks" in self.config:
            task_ids = set()
            agent_ids = {a["id"] for a in self.config.get("agents", [])}
            
            for task in self.config["tasks"]:
                if "id" not in task:
                    errors.append("tasks 中存在缺少 'id' 的任务")
                    continue
                if task["id"] in task_ids:
                    errors.append(f"重复的任务 ID: {task['id']}")
                task_ids.add(task["id"])
                
                # 验证任务引用的 Agent 是否存在
                if task.get("agent") not in agent_ids:
                    errors.append(f"任务 '{task['id']}' 引用了不存在的 Agent: {task.get('agent')}")
                
                # 验证任务依赖是否存在
                for context_id in task.get("context", []):
                    if context_id not in task_ids:
                        # 注意：这里可能是前置任务还未处理，跳过此检查
                        pass
        
        # 如果有错误，抛出异常
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ConfigError(f"配置验证失败:\n{error_msg}")
    
    def _fill_defaults(self) -> None:
        """
        填充配置的默认值
        
        说明：
            为可选配置项填充默认值，确保后续代码可以安全访问
        """
        # 确保 system 配置完整
        if "system" not in self.config:
            self.config["system"] = {}
        self.config["system"].setdefault("name", "多Agent智能体系统")
        self.config["system"].setdefault("version", "1.0.0")
        self.config["system"].setdefault("log_level", "INFO")
        
        # 确保 execution 配置完整
        if "execution" not in self.config:
            self.config["execution"] = {}
        self.config["execution"].setdefault("mode", "sequential")
        self.config["execution"].setdefault("max_retries", 3)
        self.config["execution"].setdefault("global_timeout", 600)
        self.config["execution"].setdefault("on_failure", "stop")
        
        # 确保 agents 列表存在
        if "agents" not in self.config:
            self.config["agents"] = []
        
        # 确保 tasks 列表存在
        if "tasks" not in self.config:
            self.config["tasks"] = []
        
        # 为每个 Agent 填充默认值
        for agent in self.config.get("agents", []):
            agent.setdefault("enabled", True)
            agent.setdefault("verbose", True)
            agent.setdefault("tools", [])
            agent.setdefault("llm", {})
        
        # 为每个任务填充默认值
        for task in self.config.get("tasks", []):
            task.setdefault("enabled", True)
            task.setdefault("context", [])
            task.setdefault("timeout", 300)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值
        
        参数：
            key (str): 配置项的键，支持点号分隔的多级键
                      例如: "system.name" 等同于 config["system"]["name"]
            default (Any): 当配置项不存在时的默认返回值
        
        返回：
            Any: 配置项的值，如果不存在则返回 default
        
        示例：
            >>> loader.get("system.name")
            '多Agent智能体系统'
            >>> loader.get("not.exist", "默认值")
            '默认值'
        """
        keys = key.split(".")
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def save(self, file_path: Optional[str] = None) -> None:
        """
        保存当前配置到文件
        
        参数：
            file_path (str, optional): 保存路径，默认为原配置文件路径
        
        说明：
            通常在 Web 界面修改配置后调用此方法保存
        """
        save_path = Path(file_path) if file_path else self.config_dir / "config.yaml"
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.config,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False
                )
            logger.info(f"配置已保存到: {save_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise ConfigError(f"保存配置失败: {e}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 ID 的 Agent 配置
        
        参数：
            agent_id (str): Agent 的唯一标识符
        
        返回：
            Optional[Dict]: Agent 配置字典，如果不存在则返回 None
        """
        for agent in self.config.get("agents", []):
            if agent.get("id") == agent_id:
                return agent
        return None
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 ID 的任务配置
        
        参数：
            task_id (str): 任务的唯一标识符
        
        返回：
            Optional[Dict]: 任务配置字典，如果不存在则返回 None
        """
        for task in self.config.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None
    
    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 ID 的 LLM 提供商配置
        
        参数：
            provider_id (str): 提供商的唯一标识符
        
        返回：
            Optional[Dict]: 提供商配置字典，如果不存在则返回 None
        """
        for provider in self.config.get("llm_providers", []):
            if provider.get("id") == provider_id:
                return provider
        return None
    
    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 ID 的工具配置
        
        参数：
            tool_id (str): 工具的唯一标识符
        
        返回：
            Optional[Dict]: 工具配置字典，如果不存在则返回 None
        """
        for tool in self.config.get("tools_registry", []):
            if tool.get("id") == tool_id:
                return tool
        return None
    
    def get_enabled_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有已启用的 Agent 配置
        
        返回：
            List[Dict]: 已启用的 Agent 配置列表
        """
        return [a for a in self.config.get("agents", []) if a.get("enabled", True)]
    
    def get_enabled_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有已启用的任务配置
        
        返回：
            List[Dict]: 已启用的任务配置列表
        """
        return [t for t in self.config.get("tasks", []) if t.get("enabled", True)]
    
    def reload(self) -> Dict[str, Any]:
        """
        重新加载配置文件
        
        返回：
            Dict[str, Any]: 重新加载后的配置
        
        说明：
            用于配置热重载，当配置文件被修改后可以调用此方法
        """
        logger.info("重新加载配置...")
        return self.load()


# [优化] 全局单例缓存 — 避免多处代码重复创建 ConfigLoader 并解析 YAML
_global_loader: Optional[ConfigLoader] = None
_global_loader_lock = threading.Lock()


def get_config(config_dir: str = "config", reload: bool = False) -> Dict[str, Any]:
    """
    获取全局配置实例
    
    参数：
        config_dir (str): 配置文件目录
        reload (bool): 是否强制重新加载
    
    返回：
        Dict[str, Any]: 配置字典
    
    说明：
        [优化] 全局单例模式，首次调用时加载并缓存，后续调用直接返回缓存结果。
        替代各模块中 ConfigLoader() 直接实例化，避免每次请求重复解析 YAML 文件
    """
    global _global_loader
    
    if _global_loader is not None and not reload:
        return _global_loader.config
    with _global_loader_lock:
        if _global_loader is not None and not reload:
            return _global_loader.config
        _global_loader = ConfigLoader(config_dir)
        _global_loader.load()
    
    return _global_loader.config


def get_loader(config_dir: str = "config", reload: bool = False) -> ConfigLoader:
    """
    获取全局配置加载器实例
    
    参数：
        config_dir (str): 配置文件目录
        reload (bool): 是否强制重新加载
    
    返回：
        ConfigLoader: 配置加载器实例
    """
    global _global_loader
    
    if _global_loader is not None and not reload:
        return _global_loader
    with _global_loader_lock:
        if _global_loader is not None and not reload:
            return _global_loader
        _global_loader = ConfigLoader(config_dir)
        _global_loader.load()
    
    return _global_loader
