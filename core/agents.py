# -*- coding: utf-8 -*-
"""
Agent 管理模块
==============

管理 AI Agent 的配置，包括创建、更新、删除和查询。
Agent 配置持久化存储在 data/agents.json 中。
默认 Agent（id="default"）不可删除，作为系统默认对话角色。
"""

import os
import json
import logging
import uuid
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置数据类 — 定义一个 AI 助手（员工）的完整配置"""
    id: str = "default"
    name: str = "GymClaw"
    avatar: str = "GC"
    description: str = ""
    role: str = ""
    model_provider: str = "zhipu"
    model_id: Optional[str] = None
    temperature: float = 0.7
    enable_thinking: bool = False
    enable_search: bool = False
    custom_api_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    is_default: bool = False
    skills: Optional[List[str]] = None
    agent_type: Optional[str] = None
    enabled: bool = True

    def get_agent_type(self) -> str:
        """自动推导 Agent 类型：
        - runner: 纯执行型，只绑定工具型技能，不走 LLM
        - agent: 纯智能型，只有模型，走 LLM 对话
        - smart: 混合型，有模型 + 有技能，LLM + FC 工具
        """
        if self.agent_type and self.agent_type in ("runner", "agent", "smart"):
            return self.agent_type

        has_skills = bool(self.skills)
        has_model = bool(self.model_id)

        if has_skills and not has_model:
            return "runner"
        if has_skills and has_model:
            return "smart"
        return "agent"


class AgentManager:
    """Agent 管理器 — 负责 Agent 配置的 CRUD 操作和持久化"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "agents.json")
        self._agents: Dict[str, AgentConfig] = {}  # Agent 缓存字典
        os.makedirs(data_dir, exist_ok=True)

    def load(self) -> Dict[str, AgentConfig]:
        """加载所有 Agent 配置 — 优先从缓存读取，否则从文件加载"""
        if self._agents:
            return self._agents

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    valid_fields = set(AgentConfig.__dataclass_fields__.keys())
                    for item in data:
                        filtered = {k: v for k, v in item.items() if k in valid_fields}
                        agent = AgentConfig(**filtered)
                        self._agents[agent.id] = agent
                    logger.info(f"已加载 {len(self._agents)} 个 Agent 配置")
                    return self._agents
            except Exception as e:
                logger.warning(f"加载配置失败，使用默认: {e}")

        # 首次运行：创建默认 Agent
        default = AgentConfig(id="default", name="GymClaw", avatar="GC", is_default=True, model_id="glm-4-flash-250414")
        self._agents = {"default": default}
        self._save()
        return self._agents

    def _save(self) -> None:
        data = [asdict(agent) for agent in self._agents.values()]
        tmp_path = self.config_file + ".tmp"
        try:
            if HAS_FILELOCK:
                lock = FileLock(self.config_file + ".lock", timeout=5)
                with lock:
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_path, self.config_file)
            else:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self.config_file)
        except Exception as e:
            logger.error(f"保存 Agent 配置失败: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise

    def get_agent(self, agent_id: str = "default") -> Optional[AgentConfig]:
        """根据 ID 获取 Agent 配置"""
        agents = self.load()
        return agents.get(agent_id)

    def get_default_agent(self) -> AgentConfig:
        """获取默认 Agent — 优先查找 is_default=True 的，否则返回 id=default 的"""
        agents = self.load()
        for agent in agents.values():
            if agent.is_default:
                return agent
        return agents.get("default", AgentConfig(id="default", name="GymClaw", is_default=True))

    def list_agents(self) -> List[AgentConfig]:
        """获取所有 Agent 列表"""
        agents = self.load()
        return list(agents.values())

    def list_workers(self) -> List[AgentConfig]:
        """获取所有非默认的已启用员工 Agent 列表"""
        return [a for a in self.list_agents() if not a.is_default and a.enabled]

    def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """根据名称模糊匹配 Agent（支持 @提及），跳过已休息的 Agent"""
        agents = self.load()
        name_lower = name.lower().strip()
        for agent in agents.values():
            if not agent.is_default and not agent.enabled:
                continue
            if agent.name.lower() == name_lower:
                return agent
        for agent in agents.values():
            if not agent.is_default and not agent.enabled:
                continue
            if name_lower in agent.name.lower():
                return agent
        return None

    def create_agent(self, **kwargs) -> AgentConfig:
        """创建新 Agent — 自动生成唯一 ID，保存后返回"""
        agents = self.load()
        agent_id = kwargs.pop("id", f"agent_{uuid.uuid4().hex[:8]}")
        agent = AgentConfig(id=agent_id, **kwargs)
        agents[agent_id] = agent
        self._agents = agents
        self._save()
        logger.info(f"创建 Agent: {agent.name} ({agent.id})")
        return agent

    def update_agent(self, agent_id: str, **kwargs) -> Optional[AgentConfig]:
        """更新 Agent 配置 — 只更新传入的非 None 字段"""
        agents = self.load()
        if agent_id not in agents:
            return None
        agent = agents[agent_id]
        CLEARABLE_FIELDS = {"custom_api_key", "custom_base_url", "role", "description", "skills"}
        for key, value in kwargs.items():
            if key in CLEARABLE_FIELDS:
                if value is None or value == "":
                    if hasattr(agent, key):
                        setattr(agent, key, None)
                elif hasattr(agent, key):
                    setattr(agent, key, value)
            elif value is not None and hasattr(agent, key):
                setattr(agent, key, value)
        self._agents = agents
        self._save()
        logger.info(f"更新 Agent: {agent.name} ({agent.id})")
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent — 默认 Agent（is_default=True）不可删除"""
        agents = self.load()
        if agent_id not in agents:
            return False
        agent = agents[agent_id]
        if agent.is_default:
            logger.warning("不能删除默认 Agent")
            return False
        del agents[agent_id]
        self._agents = agents
        self._save()
        logger.info(f"删除 Agent: {agent.name} ({agent.id})")
        return True


# 全局单例
_global_manager: Optional[AgentManager] = None
_global_manager_lock = threading.Lock()


def get_agent_manager(data_dir: str = "data") -> AgentManager:
    """获取全局 Agent 管理器单例"""
    global _global_manager
    normalized_dir = os.path.abspath(data_dir)
    if _global_manager is not None:
        existing_dir = os.path.abspath(_global_manager.data_dir)
        if existing_dir != normalized_dir:
            logger.warning(f"[AgentManager] data_dir 不一致：已初始化={existing_dir}，请求={normalized_dir}，使用已有实例")
        return _global_manager
    with _global_manager_lock:
        if _global_manager is not None:
            return _global_manager
        _global_manager = AgentManager(data_dir)
        return _global_manager
