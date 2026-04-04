# -*- coding: utf-8 -*-
"""
Agent 工厂模块
==============

功能说明：
    负责根据配置动态创建 CrewAI Agent 实例
    支持以下特性：
    - 从 YAML 配置动态创建 Agent
    - 基于 Agent 模板快速创建
    - 自动为 Agent 分配工具和 LLM
    - Agent 实例缓存

使用示例：
    from core.agent_factory import AgentFactory
    
    factory = AgentFactory(config, llm_factory, tool_factory)
    agent = factory.create("researcher")
    agents = factory.create_all()

作者：AI Agent Team
版本：1.0.0
"""

import logging
from typing import Any, Dict, List, Optional

from crewai import Agent

logger = logging.getLogger(__name__)


class AgentFactoryError(Exception):
    """Agent 工厂错误异常类"""
    pass


class AgentFactory:
    """
    Agent 工厂类
    
    负责根据配置创建 CrewAI Agent 实例
    """
    
    def __init__(
        self, 
        config: Dict[str, Any], 
        llm_factory: Any,
        tool_factory: Optional[Any] = None
    ):
        """
        初始化 Agent 工厂
        
        参数：
            config (dict): 完整的系统配置
            llm_factory: LLM 工厂实例，用于创建 LLM
            tool_factory: 工具工厂实例，用于创建工具（可选）
        """
        self.config = config
        self.llm_factory = llm_factory
        self.tool_factory = tool_factory
        
        # 构建模板映射
        self.templates: Dict[str, Dict] = {}
        for template in config.get("agent_templates", []):
            self.templates[template["id"]] = template
        
        # Agent 实例缓存
        self._agents: Dict[str, Agent] = {}
        
        logger.info(f"Agent 工厂初始化完成，已加载 {len(self.templates)} 个模板")
    
    def create(self, agent_id: str) -> Agent:
        """
        根据配置创建单个 Agent
        
        参数：
            agent_id (str): Agent 的唯一标识符
        
        返回：
            Agent: CrewAI Agent 实例
        """
        if agent_id in self._agents:
            logger.debug(f"从缓存获取 Agent: {agent_id}")
            return self._agents[agent_id]
        
        agent_config = self._find_agent_config(agent_id)
        if not agent_config:
            raise AgentFactoryError(f"未找到 Agent 配置: {agent_id}")
        
        merged_config = self._merge_template(agent_config)
        
        llm_config = merged_config.get("llm")
        if llm_config:
            llm = self.llm_factory.create(llm_config)
        else:
            llm = self.llm_factory.create()
        
        tools = self._create_tools(merged_config.get("tools", []))
        
        try:
            agent = Agent(
                role=merged_config.get("role", "助手"),
                goal=merged_config.get("goal", "完成任务"),
                backstory=merged_config.get("backstory", "你是一个AI助手"),
                llm=llm,
                tools=tools,
                verbose=merged_config.get("verbose", True),
                max_iter=merged_config.get("max_iter", 15),
                allow_delegation=merged_config.get("allow_delegation", False),
            )
            
            self._agents[agent_id] = agent
            logger.info(f"成功创建 Agent: {agent_id} ({merged_config.get('role')})")
            
            return agent
        except Exception as e:
            raise AgentFactoryError(f"创建 Agent '{agent_id}' 失败: {e}")
    
    def create_all(self) -> Dict[str, Agent]:
        """
        创建所有已启用的 Agent
        
        返回：
            Dict[str, Agent]: Agent ID -> Agent 实例的映射
        """
        agents = {}
        
        for agent_cfg in self.config.get("agents", []):
            if not agent_cfg.get("enabled", True):
                logger.info(f"跳过已禁用的 Agent: {agent_cfg.get('id')}")
                continue
            
            try:
                agent = self.create(agent_cfg["id"])
                agents[agent_cfg["id"]] = agent
            except Exception as e:
                logger.error(f"创建 Agent '{agent_cfg.get('id')}' 失败: {e}")
        
        logger.info(f"共创建 {len(agents)} 个 Agent")
        return agents
    
    def _find_agent_config(self, agent_id: str) -> Optional[Dict]:
        """查找 Agent 配置"""
        for agent in self.config.get("agents", []):
            if agent.get("id") == agent_id:
                return agent.copy()
        return None
    
    def _merge_template(self, agent_config: Dict) -> Dict:
        """
        合并模板配置
        
        如果 Agent 关联了模板，会将模板的默认配置作为基础，
        然后用 Agent 自身的配置覆盖
        """
        template_id = agent_config.get("template")
        
        if not template_id or template_id not in self.templates:
            return agent_config
        
        template = self.templates[template_id]
        template_defaults = template.get("default_config", {})
        
        merged = template_defaults.copy()
        
        skip_keys = {"id", "name", "template", "enabled", "tools", "llm"}
        for key, value in agent_config.items():
            if key not in skip_keys and value is not None:
                merged[key] = value
        
        if "tools" in agent_config:
            merged["tools"] = agent_config["tools"]
        elif "suggested_tools" in template_defaults:
            merged["tools"] = [{"id": tid, "config": {}} for tid in template_defaults["suggested_tools"]]
        
        if "llm" in agent_config and agent_config["llm"]:
            merged["llm"] = agent_config["llm"]
        elif "suggested_llm" in template_defaults:
            merged["llm"] = template_defaults["suggested_llm"]
        
        logger.debug(f"已合并模板 '{template_id}' 到 Agent")
        return merged
    
    def _create_tools(self, tools_config: List[Dict]) -> list:
        """创建工具列表"""
        if not self.tool_factory or not tools_config:
            return []
        
        tools = []
        for tool_cfg in tools_config:
            try:
                tool = self.tool_factory.create(tool_cfg["id"], tool_cfg.get("config", {}))
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"创建工具 '{tool_cfg.get('id')}' 失败: {e}")
        
        return tools
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取已创建的 Agent 实例"""
        return self._agents.get(agent_id)
    
    def list_agent_configs(self, enabled_only: bool = False) -> List[Dict]:
        """获取 Agent 配置列表"""
        agents = self.config.get("agents", [])
        if enabled_only:
            return [a for a in agents if a.get("enabled", True)]
        return agents
    
    def list_templates(self) -> List[Dict]:
        """获取所有 Agent 模板"""
        return list(self.templates.values())
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def clear_cache(self) -> None:
        """清除 Agent 实例缓存"""
        self._agents.clear()
        logger.info("Agent 实例缓存已清除")
