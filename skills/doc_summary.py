# -*- coding: utf-8 -*-
"""
文档总结技能
============

对上传的文档进行结构化总结、关键信息提取、要点归纳。
支持 PDF、Word、Excel、CSV、TXT、代码文件等。
"""

import os
import sys
import logging
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB 限制


def _read_file_content(filepath: str) -> str:
    """读取文件内容，复用 core.file_reader"""
    if os.path.getsize(filepath) > MAX_FILE_SIZE:
        logger.warning(f"文件过大跳过: {filepath} ({os.path.getsize(filepath)} bytes)")
        return ""
    try:
        from core.file_reader import read_file_content
        return read_file_content(filepath)
    except ImportError:
        # fallback：直接读取文本文件
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""


def _find_uploaded_files(context: Dict[str, Any]) -> list:
    """从上下文中查找上传的文件路径"""
    files = []
    if context:
        for key in ("files", "file_paths"):
            if context.get(key):
                files.extend(context[key])
        tool_args = context.get("tool_args", {})
        if tool_args.get("file_path"):
            files.append(tool_args["file_path"])
    return files


SUMMARY_MODES = {
    "总结": "summary",
    "摘要": "summary",
    "归纳": "summary",
    "要点": "keypoints",
    "关键信息": "keypoints",
    "提取": "extract",
    "分析": "analysis",
    "对比": "compare",
}


def _detect_mode(text: str) -> str:
    """检测用户期望的总结模式"""
    for keyword, mode in SUMMARY_MODES.items():
        if keyword in text:
            return mode
    return "summary"


def _build_prompt(mode: str, filename: str = "") -> str:
    """根据模式构建 system prompt"""
    base = f"你是专业的文档分析助手。以下是文档内容"
    if filename:
        base += f"（文件名: {filename}）"
    base += "。\n\n"

    if mode == "keypoints":
        return base + "请提取文档的关键信息要点，用编号列表输出，每个要点一句话概括。"
    elif mode == "extract":
        return base + "请从文档中提取结构化信息（如日期、数字、人名、地点、金额等），用表格或列表形式输出。"
    elif mode == "analysis":
        return base + "请对文档内容进行深度分析，包括：主题、结构、核心观点、数据趋势、潜在问题，用 Markdown 格式输出。"
    elif mode == "compare":
        return base + "请对文档中的内容进行对比分析，找出异同点，用表格形式呈现。"
    else:
        return base + (
            "请对文档进行结构化总结，包括：\n"
            "1. **一句话摘要**（不超过50字）\n"
            "2. **核心要点**（3-5个要点）\n"
            "3. **详细内容**（按文档结构展开）\n"
            "4. **结论/建议**（如适用）\n\n"
            "用 Markdown 格式输出。"
        )


def summarize_document(content: str, mode: str = "summary", filename: str = "", question: str = "") -> Dict[str, Any]:
    """调用 LLM 总结文档"""
    if not content or len(content.strip()) < 10:
        return {"success": False, "message": "文档内容为空或过短，无法总结"}

    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        system_prompt = _build_prompt(mode, filename)

        # 限制内容长度避免超出上下文窗口
        max_content = 15000
        truncated = len(content) > max_content
        doc_content = content[:max_content]

        user_msg = f"文档内容：\n---\n{doc_content}\n---"
        if truncated:
            user_msg += f"\n\n（文档过长，已截取前 {max_content} 字符，总长度 {len(content)} 字符）"
        if question:
            user_msg += f"\n\n用户的具体问题：{question}"

        response = llm.call(messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ])

        return {"success": True, "summary": str(response).strip(), "mode": mode}
    except Exception as e:
        logger.error(f"文档总结失败: {e}")
        return {"success": False, "message": f"文档总结失败: {e}"}


@register_skill(
    skill_id="doc_summary",
    name="文档总结",
    description="对上传的文档进行结构化总结、要点提取、深度分析",
    triggers=["总结文档", "文档总结", "帮我总结", "归纳一下", "提取要点",
              "文档分析", "分析文档", "总结一下", "帮我归纳", "文件总结",
              "摘要", "总结报告"],
    icon="file",
    examples=[
        "帮我总结一下这份文档的要点",
        "分析一下上传的报告",
        "提取这个文件中的关键数据",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": "对文档进行总结、要点提取或深度分析。用户上传文档后要求总结、归纳、分析时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "用户的总结需求描述",
                    },
                    "mode": {
                        "type": "string",
                        "description": "总结模式：summary（总结）、keypoints（要点）、extract（提取）、analysis（分析）",
                        "enum": ["summary", "keypoints", "extract", "analysis"],
                    },
                },
                "required": ["prompt"],
            },
        },
    },
)
def handle_doc_summary(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}
    mode = tool_args.get("mode") or _detect_mode(user_input)

    # 查找上传的文件
    files = _find_uploaded_files(context)
    if not files:
        return {
            "success": False,
            "message": "请先上传文档，然后再要求总结。支持 PDF、Word、Excel、CSV、TXT、代码文件等。",
        }

    all_content = []
    filenames = []
    for fp in files:
        if os.path.exists(fp):
            content = _read_file_content(fp)
            if content:
                fname = os.path.basename(fp)
                all_content.append(f"=== {fname} ===\n{content}")
                filenames.append(fname)

    if not all_content:
        return {"success": False, "message": "无法读取上传的文件内容，请确认文件格式受支持"}

    combined = "\n\n".join(all_content)
    fname_str = "、".join(filenames)

    # 清理用户输入获取具体问题
    question = user_input
    for trigger in ["总结文档", "文档总结", "帮我总结", "归纳一下", "提取要点",
                     "文档分析", "分析文档", "总结一下", "帮我归纳", "摘要",
                     "帮我", "一下", "这份", "这个", "文档", "文件"]:
        question = question.replace(trigger, "").strip()

    result = summarize_document(combined, mode=mode, filename=fname_str, question=question)

    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    mode_label = {"summary": "总结", "keypoints": "要点提取", "extract": "信息提取", "analysis": "深度分析"}.get(mode, "总结")
    msg = (
        f"📄 **文档{mode_label}** — {fname_str}\n\n"
        f"{result['summary']}"
    )
    return {"success": True, "message": msg}
