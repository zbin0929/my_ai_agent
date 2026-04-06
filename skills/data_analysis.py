# -*- coding: utf-8 -*-
"""
数据分析技能
============

分析 CSV/Excel 数据，生成统计报告和图表。
使用 LLM 生成 Python 分析代码，然后执行并返回结果。
"""

import os
import sys
import logging
import tempfile
import subprocess
import re
import time
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(project_root, "data", "analysis_output")
MAX_TIMEOUT = 60

# 危险代码模式检测（复用 code_execute 的安全检查逻辑）
_DANGEROUS_PATTERNS = [
    r"\bos\.system\b", r"\bsubprocess\b", r"\b__import__\b",
    r"\bopen\s*\(.*(\.\.|\/etc|\/var|\.env|passwd)",
    r"\bshutil\.rmtree\b", r"\bos\.remove\b", r"\bos\.unlink\b",
    r"\bexec\s*\(", r"\beval\s*\(",
]


def _check_code_safety(code: str) -> str:
    """检查 LLM 生成的代码是否包含危险操作"""
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return f"检测到潜在危险操作: {pattern}"
    return ""


def _read_data_preview(filepath: str, max_rows: int = 20) -> str:
    """读取数据文件的前几行作为预览"""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_rows:
                        break
                    lines.append(line.rstrip())
                return "\n".join(lines)
        elif ext in (".xlsx", ".xls"):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(filepath, read_only=True)
                ws = wb.active
                rows = []
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i >= max_rows:
                        break
                    rows.append(",".join(str(c) if c is not None else "" for c in row))
                wb.close()
                return "\n".join(rows)
            except ImportError:
                return "(需要 openpyxl 库来读取 Excel 文件)"
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()[:3000]
                return content
        else:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[:3000]
    except Exception as e:
        return f"(读取失败: {e})"


def _generate_analysis_code(data_preview: str, filepath: str, user_request: str) -> str:
    """使用 LLM 生成数据分析代码"""
    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        ext = os.path.splitext(filepath)[1].lower()
        output_dir = OUTPUT_DIR

        response = llm.call(messages=[
            {
                "role": "system",
                "content": (
                    "你是一个数据分析专家。根据用户需求生成 Python 数据分析代码。\n\n"
                    "要求：\n"
                    "1. 只输出可直接执行的 Python 代码，不要解释\n"
                    "2. 使用 pandas 读取数据\n"
                    "3. 如果需要图表，使用 matplotlib（设置中文字体: plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']）\n"
                    f"4. 图表保存到: {output_dir}/chart_<timestamp>.png\n"
                    "5. 最后 print 出分析结果摘要\n"
                    "6. 代码用 ```python ... ``` 包裹\n"
                    f"7. 数据文件路径: {filepath}\n"
                    f"8. 文件类型: {ext}\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"数据预览（前几行）:\n```\n{data_preview}\n```\n\n"
                    f"分析需求: {user_request}"
                ),
            },
        ])

        # 提取代码块
        code_str = str(response)
        match = re.search(r"```python\s*\n(.*?)```", code_str, re.DOTALL)
        if match:
            return match.group(1).strip()
        # 尝试无语言标记的代码块
        match = re.search(r"```\s*\n(.*?)```", code_str, re.DOTALL)
        if match:
            return match.group(1).strip()
        return code_str.strip()
    except Exception as e:
        logger.error(f"生成分析代码失败: {e}")
        return ""


def analyze_data(filepath: str, request: str) -> Dict[str, Any]:
    """执行数据分析"""
    if not os.path.exists(filepath):
        return {"success": False, "message": f"文件不存在: {filepath}"}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 读取数据预览
    preview = _read_data_preview(filepath)
    if not preview:
        return {"success": False, "message": "无法读取数据文件"}

    # 生成分析代码
    code = _generate_analysis_code(preview, filepath, request)
    if not code:
        return {"success": False, "message": "无法生成分析代码"}

    # 安全检查 LLM 生成的代码
    warning = _check_code_safety(code)
    if warning:
        return {"success": False, "message": f"⚗️ 安全检查未通过: {warning}", "code": code}

    # 执行代码
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_file = f.name

        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=MAX_TIMEOUT,
            cwd=OUTPUT_DIR,
        )

        stdout = result.stdout[:5000] if result.stdout else ""
        stderr = result.stderr[:2000] if result.stderr else ""

        # 查找生成的图表文件
        chart_files = []
        for fname in os.listdir(OUTPUT_DIR):
            fpath = os.path.join(OUTPUT_DIR, fname)
            if fname.endswith(".png") and os.path.getmtime(fpath) > time.time() - 120:
                chart_files.append(fpath)

        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "code": code,
            "chart_files": chart_files,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"分析执行超时（{MAX_TIMEOUT}秒）"}
    except Exception as e:
        logger.error(f"数据分析执行失败: {e}")
        return {"success": False, "message": f"执行失败: {e}"}
    finally:
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception:
                pass


@register_skill(
    skill_id="data_analysis",
    name="数据分析",
    description="分析 CSV/Excel 数据，生成统计报告和可视化图表",
    triggers=["数据分析", "分析数据", "统计分析", "画图表", "生成图表",
              "数据可视化", "柱状图", "折线图", "饼图", "趋势分析",
              "data analysis", "帮我分析数据"],
    icon="chart",
    examples=[
        "帮我分析这份 CSV 数据的趋势",
        "画一个销售额的柱状图",
        "统计一下各类别的数量分布",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "分析数据文件（CSV/Excel），生成统计报告和图表。用户上传数据文件后要求分析、画图表时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "分析需求描述，如'统计各类别数量'、'画销售趋势折线图'",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
)
def handle_data_analysis(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}
    request = tool_args.get("prompt") or user_input

    # 查找数据文件
    files = []
    if context:
        for key in ("files", "file_paths"):
            if context.get(key):
                files.extend(context[key])
    
    data_files = [f for f in files if os.path.exists(f) and os.path.splitext(f)[1].lower() in (".csv", ".xlsx", ".xls", ".json", ".tsv")]
    
    if not data_files:
        return {
            "success": False,
            "message": "请先上传数据文件（CSV、Excel、JSON），然后再要求数据分析。",
        }

    filepath = data_files[0]
    fname = os.path.basename(filepath)

    result = analyze_data(filepath, request)
    if not result["success"]:
        if result.get("code"):
            return {
                "success": False,
                "message": (
                    f"❌ 数据分析执行失败\n\n"
                    f"**生成的代码：**\n```python\n{result['code']}\n```\n\n"
                    f"**错误：**\n```\n{result.get('stderr', result.get('message', ''))}\n```"
                ),
            }
        return {"success": False, "message": f"❌ {result['message']}"}

    parts = [f"📊 **数据分析结果** — {fname}\n"]

    if result["stdout"]:
        parts.append(f"**分析摘要：**\n```\n{result['stdout']}\n```")

    if result.get("chart_files"):
        parts.append("\n**生成的图表：**")
        for chart in result["chart_files"]:
            chart_name = os.path.basename(chart)
            parts.append(f"- 📈 `{chart_name}`")

    parts.append(f"\n<details><summary>查看分析代码</summary>\n\n```python\n{result['code']}\n```\n</details>")

    return {"success": True, "message": "\n".join(parts)}
