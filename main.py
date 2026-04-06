# -*- coding: utf-8 -*-
"""
多Agent智能体系统 - 主入口文件
================================

功能说明：
    本文件是整个系统的入口点，负责：
    1. 初始化系统（加载配置、创建工厂）
    2. 解析命令行参数
    3. 执行工作流

使用方式：
    # 使用默认配置运行
    python main.py
    
    # 指定主题运行
    python main.py --topic "AI技术趋势"
    
    # 指定配置目录
    python main.py --config-dir ./my_config
    
    # 验证配置但不执行
    python main.py --validate

作者：AI Agent Team
版本：5.14.0
"""

import sys
import argparse
import logging

# 加载 .env 文件中的环境变量（如 API Key）
from dotenv import load_dotenv
load_dotenv()

# 导入核心模块
from core import (
    ConfigLoader,
    LLMFactory,
    AgentFactory,
    TaskOrchestrator,
)


def setup_logging(log_level: str = "INFO") -> None:
    """
    配置日志系统
    
    参数：
        log_level (str): 日志级别，默认 INFO
                        可选: DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    说明：
        日志会同时输出到控制台和文件
        文件日志保存在 logs/ 目录下
    """
    # 创建日志目录（使用项目根目录的绝对路径，避免受工作目录影响）
    import os
    _project_root = os.path.dirname(os.path.abspath(__file__))
    _log_dir = os.path.join(_project_root, "logs")
    os.makedirs(_log_dir, exist_ok=True)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout),
            # 文件输出
            logging.FileHandler(os.path.join(_log_dir, "agent_system.log"), encoding="utf-8"),
        ]
    )


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数
    
    返回：
        argparse.Namespace: 解析后的参数
    
    支持的参数：
        --config-dir: 配置文件目录，默认 "config"
        --topic: 研究主题，默认 "人工智能智能体 2026年最新趋势"
        --validate: 仅验证配置，不执行
        --verbose: 启用详细日志
        --mode: 执行模式 (sequential/parallel/hierarchical)
    """
    parser = argparse.ArgumentParser(
        description="多Agent智能体系统 - 基于CrewAI的多Agent协作系统"
    )
    
    parser.add_argument(
        "--config-dir",
        type=str,
        default="config",
        help="配置文件目录路径（默认: config）"
    )
    
    parser.add_argument(
        "--topic",
        type=str,
        default="人工智能智能体 2026年最新趋势",
        help="研究主题，会替换配置中的 {topic} 占位符"
    )
    
    parser.add_argument(
        "--num-points",
        type=int,
        default=3,
        help="总结要点数量，会替换配置中的 {num_points} 占位符"
    )
    
    parser.add_argument(
        "--word-count",
        type=int,
        default=200,
        help="报告字数，会替换配置中的 {word_count} 占位符"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        default="report.txt",
        help="输出文件名，会替换配置中的 {output_file} 占位符"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "parallel", "hierarchical"],
        default=None,
        help="执行模式（覆盖配置文件中的设置）"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅验证配置文件，不执行任务"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用 DEBUG 级别的详细日志"
    )
    
    return parser.parse_args()


def main() -> None:
    """
    主函数
    
    流程：
        1. 解析命令行参数
        2. 配置日志
        3. 加载配置文件
        4. 初始化系统组件（LLM工厂、Agent工厂、任务编排器）
        5. 验证工作流
        6. 执行工作流
        7. 输出结果
    
    异常处理：
        所有异常会被捕获并以友好的格式输出
    """
    # 步骤1：解析命令行参数
    args = parse_args()
    
    # 步骤2：配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("多Agent智能体系统启动")
    logger.info("=" * 60)
    
    try:
        # 步骤3：加载配置文件
        logger.info(f"正在加载配置文件，目录: {args.config_dir}")
        config_loader = ConfigLoader(args.config_dir)
        config = config_loader.load()
        
        logger.info(f"系统名称: {config.get('system', {}).get('name', '未命名')}")
        logger.info(f"系统版本: {config.get('system', {}).get('version', '未知')}")
        
        # 步骤4：初始化系统组件
        logger.info("正在初始化系统组件...")
        
        # 创建 LLM 工厂
        llm_factory = LLMFactory(config)
        logger.info(f"LLM 工厂初始化完成，已注册 {len(llm_factory.list_providers())} 个提供商")
        
        # 创建 Agent 工厂（暂时不传入 tool_factory，后续补充）
        agent_factory = AgentFactory(config, llm_factory)
        logger.info(f"Agent 工厂初始化完成，已配置 {len(agent_factory.list_agent_configs())} 个 Agent")
        
        # 创建任务编排器
        orchestrator = TaskOrchestrator(config, agent_factory)
        logger.info(f"任务编排器初始化完成，已配置 {len(orchestrator.list_task_configs())} 个任务")
        
        # 步骤5：如果只是验证模式，到这里就结束
        if args.validate:
            logger.info("验证模式：检查工作流完整性...")
            warnings = orchestrator.validate_workflow()
            
            if warnings:
                logger.warning("发现以下问题：")
                for w in warnings:
                    logger.warning(f"  - {w}")
            else:
                logger.info("✓ 工作流验证通过，所有配置正确")
            
            # 输出配置摘要
            print("\n" + "=" * 60)
            print("配置摘要")
            print("=" * 60)
            
            # 输出 LLM 配置
            print(f"\n📋 默认 LLM: {config['default_llm']['provider']}/{config['default_llm']['model']}")
            
            # 输出已注册的提供商
            print(f"\n🤖 已注册提供商 ({len(llm_factory.list_providers())}):")
            for p in llm_factory.list_providers():
                models = ", ".join(m["id"] for m in p.get("models", []))
                print(f"   - {p['name']} ({p['id']}): {models}")
            
            # 输出 Agent 配置
            enabled_agents = agent_factory.list_agent_configs(enabled_only=True)
            all_agents = agent_factory.list_agent_configs()
            print(f"\n👥 Agent ({len(enabled_agents)}/{len(all_agents)} 已启用):")
            for a in all_agents:
                status = "✓" if a.get("enabled", True) else "✗"
                tools = ", ".join(t["id"] for t in a.get("tools", []))
                print(f"   {status} {a['id']}: {a.get('role', '未定义')} (工具: {tools or '无'})")
            
            # 输出任务配置
            enabled_tasks = orchestrator.list_task_configs(enabled_only=True)
            all_tasks = orchestrator.list_task_configs()
            print(f"\n📋 任务 ({len(enabled_tasks)}/{len(all_tasks)} 已启用):")
            for t in all_tasks:
                status = "✓" if t.get("enabled", True) else "✗"
                ctx = ", ".join(t.get("context", []))
                print(f"   {status} {t['id']}: Agent={t.get('agent')}, 依赖=[{ctx}]")
            
            print("\n" + "=" * 60)
            return
        
        # 步骤6：执行工作流
        logger.info("准备执行工作流...")
        
        # 构建运行时变量
        inputs = {
            "topic": args.topic,
            "num_points": args.num_points,
            "word_count": args.word_count,
            "output_file": args.output_file,
        }
        
        logger.info(f"运行参数: {inputs}")
        
        # 执行
        result = orchestrator.execute(
            inputs=inputs,
            mode=args.mode
        )
        
        # 步骤7：输出结果
        print("\n" + "=" * 60)
        print("执行结果")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        logger.info("工作流执行完成")
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        sys.exit(0)
    except Exception as e:
        logger.error(f"系统错误: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


# 入口点
if __name__ == "__main__":
    main()
