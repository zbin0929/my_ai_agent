# -*- coding: utf-8 -*-
"""
任务编排器模块
==============

功能说明：
    负责根据配置创建和编排 CrewAI Task 实例
    支持以下特性：
    - 从 YAML 配置动态创建任务
    - 自动处理任务依赖关系（context）
    - 支持变量替换（{topic} 等）
    - 多种执行模式（顺序、并行、层级）

使用示例：
    from core.task_orchestrator import TaskOrchestrator
    
    orchestrator = TaskOrchestrator(config, agent_factory)
    tasks = orchestrator.create_all()
    result = orchestrator.execute(inputs={"topic": "AI趋势"})

作者：AI Agent Team
版本：1.0.0
"""

import re
import logging
from typing import Any, Dict, List, Optional

from crewai import Task, Crew, Process

logger = logging.getLogger(__name__)


class TaskOrchestratorError(Exception):
    """任务编排器错误异常类"""
    pass


class TaskOrchestrator:
    """
    任务编排器类
    
    负责创建任务、处理依赖关系和执行工作流
    """
    
    # 变量占位符正则：匹配 {variable_name} 格式
    _VAR_PATTERN = re.compile(r'\{(\w+)\}')
    
    def __init__(self, config: Dict[str, Any], agent_factory: Any):
        """
        初始化任务编排器
        
        参数：
            config (dict): 完整的系统配置
            agent_factory: Agent 工厂实例，用于获取 Agent
        """
        self.config = config
        self.agent_factory = agent_factory
        
        # 预索引：task_id -> task_config（O(1) 查找）
        self._task_configs: Dict[str, Dict] = {}
        for t in config.get("tasks", []):
            if "id" in t:
                self._task_configs[t["id"]] = t
        
        # 任务对象缓存：task_id -> Task 实例
        self._tasks: Dict[str, Task] = {}
        
        # 执行结果
        self._last_result = None
        
        logger.info("任务编排器初始化完成")
    
    def create_task(self, task_id: str) -> Task:
        """
        创建单个任务
        
        参数：
            task_id (str): 任务 ID
        
        返回：
            Task: CrewAI Task 实例
        
        流程：
            1. 查找任务配置
            2. 获取执行此任务的 Agent
            3. 处理任务依赖（context）
            4. 创建 Task 实例
        """
        if task_id in self._tasks:
            logger.debug(f"从缓存获取任务: {task_id}")
            return self._tasks[task_id]
        
        task_config = self._find_task_config(task_id)
        if not task_config:
            raise TaskOrchestratorError(f"未找到任务配置: {task_id}")
        
        # 获取执行此任务的 Agent
        agent_id = task_config.get("agent")
        agent = self.agent_factory.get_agent(agent_id)
        if not agent:
            try:
                agent = self.agent_factory.create(agent_id)
            except Exception as e:
                raise TaskOrchestratorError(
                    f"任务 '{task_id}' 引用的 Agent '{agent_id}' 创建失败: {e}"
                )
        
        # 处理任务依赖
        context_tasks = self._resolve_context(task_config.get("context", []))
        
        # 创建 Task
        try:
            task = Task(
                description=task_config.get("description", ""),
                agent=agent,
                expected_output=task_config.get("expected_output", ""),
                context=context_tasks if context_tasks else None,
            )
            
            self._tasks[task_id] = task
            logger.info(f"成功创建任务: {task_id}")
            
            return task
        except Exception as e:
            raise TaskOrchestratorError(f"创建任务 '{task_id}' 失败: {e}")
    
    def create_all(self) -> List[Task]:
        """
        创建所有已启用的任务
        
        返回：
            List[Task]: 按配置顺序排列的任务列表
        
        说明：
            任务的创建顺序很重要，因为后续任务可能依赖前面的任务
            因此按照配置文件中的顺序依次创建
        """
        tasks = []
        
        for task_cfg in self.config.get("tasks", []):
            if not task_cfg.get("enabled", True):
                logger.info(f"跳过已禁用的任务: {task_cfg.get('id')}")
                continue
            
            try:
                task = self.create_task(task_cfg["id"])
                tasks.append(task)
            except Exception as e:
                logger.error(f"创建任务 '{task_cfg.get('id')}' 失败: {e}")
        
        logger.info(f"共创建 {len(tasks)} 个任务")
        return tasks
    
    def _find_task_config(self, task_id: str) -> Optional[Dict]:
        """查找任务配置（O(1) 预索引查找）"""
        return self._task_configs.get(task_id)
    
    def _resolve_context(self, context_ids: List[str]) -> List[Task]:
        """
        解析任务依赖关系
        
        参数：
            context_ids (list): 依赖的任务 ID 列表
        
        返回：
            list: 依赖的 Task 实例列表
        
        说明：
            确保依赖的任务已经创建，然后再返回它们的实例
        """
        context_tasks = []
        
        for dep_id in context_ids:
            if dep_id in self._tasks:
                context_tasks.append(self._tasks[dep_id])
            else:
                # 尝试创建依赖的任务
                try:
                    dep_task = self.create_task(dep_id)
                    context_tasks.append(dep_task)
                except Exception as e:
                    logger.warning(f"无法创建依赖任务 '{dep_id}': {e}")
        
        return context_tasks
    
    def execute(
        self, 
        inputs: Optional[Dict[str, Any]] = None,
        mode: Optional[str] = None
    ) -> Any:
        """
        执行任务工作流
        
        参数：
            inputs (dict, optional): 运行时变量，用于替换任务描述中的占位符
                                    例如: {"topic": "AI趋势", "num_points": 3}
            mode (str, optional): 执行模式，覆盖配置中的设置
                                可选: "sequential", "parallel", "hierarchical"
        
        返回：
            Any: 执行结果
        
        流程：
            1. 清除旧的任务缓存（确保使用新的 inputs）
            2. 创建所有任务
            3. 根据 inputs 替换任务描述中的变量
            4. 选择执行模式
            5. 创建 Crew 并执行
        """
        # 清除缓存，确保使用新的 inputs
        self._tasks.clear()
        self.agent_factory.clear_cache()
        
        # 创建所有任务
        tasks = self.create_all()
        
        if not tasks:
            raise TaskOrchestratorError("没有可执行的任务")
        
        # 如果有 inputs，替换任务描述中的变量
        if inputs:
            self._apply_inputs(tasks, inputs)
        
        # 获取所有 Agent
        agents_dict = self.agent_factory.create_all()
        agents_list = list(agents_dict.values())
        
        # 确定执行模式
        exec_mode = mode or self.config.get("execution", {}).get("mode", "sequential")
        process = self._get_process(exec_mode)
        
        # 创建 Crew 并执行
        try:
            crew = Crew(
                agents=agents_list,
                tasks=tasks,
                process=process,
                verbose=True
            )
            
            logger.info(f"开始执行工作流，模式: {exec_mode}，任务数: {len(tasks)}")
            
            result = crew.kickoff(inputs=inputs or {})
            
            self._last_result = result
            logger.info("工作流执行完成")
            
            return result
        except Exception as e:
            raise TaskOrchestratorError(f"执行工作流失败: {e}")
    
    def _apply_inputs(self, tasks: List[Task], inputs: Dict[str, Any]) -> None:
        """
        将运行时变量应用到任务描述中
        
        参数：
            tasks (list): 任务列表
            inputs (dict): 变量映射，例如 {"topic": "AI", "num_points": 3}
        
        说明：
            替换任务描述和期望输出中的 {variable} 占位符
            未匹配的占位符会保留原样
        """
        for task in tasks:
            if hasattr(task, 'description') and task.description:
                task.description = self._replace_vars(task.description, inputs)
            if hasattr(task, 'expected_output') and task.expected_output:
                task.expected_output = self._replace_vars(task.expected_output, inputs)
    
    def _replace_vars(self, text: str, inputs: Dict[str, Any]) -> str:
        """
        替换字符串中的变量占位符
        
        参数：
            text (str): 包含占位符的文本
            inputs (dict): 变量映射
        
        返回：
            str: 替换后的文本
        
        示例：
            >>> self._replace_vars("研究 {topic} 的趋势", {"topic": "AI"})
            '研究 AI 的趋势'
        """
        def replacer(match):
            var_name = match.group(1)
            if var_name in inputs:
                return str(inputs[var_name])
            return match.group(0)  # 未匹配则保留原样
        
        return self._VAR_PATTERN.sub(replacer, text)
    
    def _get_process(self, mode: str) -> Process:
        """
        获取 CrewAI 执行模式
        
        参数：
            mode (str): 模式名称
        
        返回：
            Process: CrewAI Process 枚举值
        """
        mode_map = {
            "sequential": Process.sequential,
            "parallel": Process.sequential,
            "hierarchical": Process.hierarchical,
        }
        
        process = mode_map.get(mode)
        if not process:
            logger.warning(f"未知的执行模式 '{mode}'，使用默认的顺序执行")
            process = Process.sequential
        elif mode == "parallel":
            logger.info("parallel 模式：CrewAI 尚不原生支持 parallel Process，将使用 sequential 代替")
        
        return process
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取已创建的任务实例"""
        return self._tasks.get(task_id)
    
    def list_task_configs(self, enabled_only: bool = False) -> List[Dict]:
        """获取任务配置列表"""
        tasks = self.config.get("tasks", [])
        if enabled_only:
            return [t for t in tasks if t.get("enabled", True)]
        return tasks
    
    def get_last_result(self) -> Any:
        """获取最近一次执行的结果"""
        return self._last_result
    
    def validate_workflow(self) -> List[str]:
        """
        验证工作流的完整性
        
        返回：
            list: 警告消息列表（空列表表示无问题）
        
        检查项：
            1. 所有依赖的任务是否存在
            2. 是否存在循环依赖
            3. 引用的 Agent 是否有效
        """
        warnings = []
        task_ids = {t.get("id") for t in self.config.get("tasks", [])}
        agent_ids = {a.get("id") for a in self.config.get("agents", [])}
        
        for task_cfg in self.config.get("tasks", []):
            task_id = task_cfg.get("id")
            
            # 检查依赖任务是否存在
            for ctx_id in task_cfg.get("context", []):
                if ctx_id not in task_ids:
                    warnings.append(
                        f"任务 '{task_id}' 依赖不存在的任务: {ctx_id}"
                    )
            
            # 检查 Agent 是否存在
            agent_id = task_cfg.get("agent")
            if agent_id and agent_id not in agent_ids:
                warnings.append(
                    f"任务 '{task_id}' 引用不存在的 Agent: {agent_id}"
                )
        
        # 检查循环依赖
        if self._has_circular_dependency():
            warnings.append("检测到循环依赖")
        
        return warnings
    
    def _has_circular_dependency(self) -> bool:
        """
        检测是否存在循环依赖
        
        返回：
            bool: True 表示存在循环依赖
        
        使用深度优先搜索（DFS）检测
        """
        tasks = self.config.get("tasks", [])
        
        # 构建依赖图
        graph = {}
        for task in tasks:
            task_id = task.get("id")
            graph[task_id] = task.get("context", [])
        
        # DFS 检测环
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def clear_cache(self) -> None:
        """清除任务缓存"""
        self._tasks.clear()
        logger.info("任务缓存已清除")
