# -*- coding: utf-8 -*-
"""
联网搜索报告技能
================

增强版联网搜索：搜索后生成结构化报告。
复用 core.search 的搜索基础设施，叠加 LLM 分析和报告生成。
"""

import os
import sys
import logging
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _do_search(query: str) -> str:
    """执行搜索并返回搜索结果文本。

    注意：技能 handler 通过 asyncio.to_thread() 在独立线程中调用，
    因此这里可以安全使用 asyncio.run() 创建新的事件循环。
    """
    try:
        from core.search import do_search, get_search_api_key
        api_key = get_search_api_key()
        if not api_key:
            return ""
        import asyncio
        result = asyncio.run(do_search(query))
        return result or ""
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return ""


def generate_search_report(query: str, report_type: str = "comprehensive") -> Dict[str, Any]:
    """搜索并生成报告"""
    search_results = _do_search(query)
    if not search_results:
        return {"success": False, "message": "搜索未返回结果，请检查搜索配置（API Key）"}

    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        type_instructions = {
            "comprehensive": (
                "请生成一份全面的调研报告，包括：\n"
                "1. **主题概述**（一段话总结）\n"
                "2. **关键发现**（3-5个要点）\n"
                "3. **详细信息**（按主题分类展开）\n"
                "4. **来源汇总**（标注信息来源）\n"
                "5. **结论与建议**"
            ),
            "brief": "请用 3-5 个要点简明扼要地总结搜索结果。",
            "comparison": "请对搜索结果中的不同观点/产品/方案进行对比分析，用表格呈现。",
            "timeline": "请按时间线整理搜索结果中的事件或发展历程。",
        }

        instruction = type_instructions.get(report_type, type_instructions["comprehensive"])

        response = llm.call(messages=[
            {
                "role": "system",
                "content": (
                    "你是一个专业的信息分析师。根据搜索结果为用户生成高质量的调研报告。\n"
                    "要求：\n"
                    "- 用 Markdown 格式输出\n"
                    "- 信息准确，基于搜索结果，不编造\n"
                    "- 标注信息来源\n"
                    f"\n{instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"搜索主题: {query}\n\n搜索结果:\n{search_results[:12000]}",
            },
        ])

        return {"success": True, "report": str(response).strip(), "report_type": report_type}
    except Exception as e:
        logger.error(f"生成搜索报告失败: {e}")
        return {"success": False, "message": f"报告生成失败: {e}"}


@register_skill(
    skill_id="search_report",
    name="搜索报告",
    description="联网搜索并生成结构化调研报告，支持综合报告、简报、对比分析、时间线等格式",
    triggers=["搜索报告", "帮我调研", "调研一下", "搜索并总结", "搜索分析",
              "帮我搜索并整理", "research", "帮我查一下并总结"],
    icon="search",
    examples=[
        "帮我调研一下2024年AI发展趋势",
        "搜索并总结 Python 和 Rust 的对比",
        "帮我搜索一下最新的 LLM 技术进展",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "generate_search_report",
            "description": "联网搜索指定主题并生成结构化调研报告。当用户要求调研、搜索并总结时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索主题或关键词",
                    },
                    "report_type": {
                        "type": "string",
                        "description": "报告类型：comprehensive（综合）、brief（简报）、comparison（对比）、timeline（时间线）",
                        "enum": ["comprehensive", "brief", "comparison", "timeline"],
                    },
                },
                "required": ["query"],
            },
        },
    },
)
def handle_search_report(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}

    query = tool_args.get("query") or user_input
    report_type = tool_args.get("report_type", "comprehensive")

    # 清理触发词
    for trigger in ["搜索报告", "帮我调研", "调研一下", "搜索并总结", "搜索分析",
                     "帮我搜索并整理", "帮我查一下并总结", "帮我", "一下"]:
        query = query.replace(trigger, "").strip()

    if not query or len(query) < 2:
        return {"success": False, "message": "请提供搜索主题。比如：「帮我调研一下AI发展趋势」"}

    # 检测报告类型
    if "对比" in user_input or "比较" in user_input:
        report_type = "comparison"
    elif "时间线" in user_input or "历程" in user_input:
        report_type = "timeline"
    elif "简要" in user_input or "简报" in user_input:
        report_type = "brief"

    result = generate_search_report(query, report_type)
    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    type_label = {"comprehensive": "综合报告", "brief": "简报", "comparison": "对比分析", "timeline": "时间线"}.get(report_type, "报告")
    msg = f"🔍 **{type_label}** — {query}\n\n{result['report']}"
    return {"success": True, "message": msg}
