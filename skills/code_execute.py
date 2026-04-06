# -*- coding: utf-8 -*-
"""
代码执行技能
============

在安全沙盒中执行 Python/JavaScript/Bash 代码。
限制超时、输出长度，禁止危险操作。
"""

import os
import sys
import subprocess
import tempfile
import logging
import re
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

# 安全限制
MAX_TIMEOUT = 30
MAX_OUTPUT_LENGTH = 5000
ALLOWED_LANGUAGES = {"python", "javascript", "bash"}

LANG_CONFIG = {
    "python": {"suffix": ".py", "cmd": [sys.executable, "{file}"]},
    "javascript": {"suffix": ".js", "cmd": ["node", "{file}"]},
    "bash": {"suffix": ".sh", "cmd": ["bash", "{file}"]},
}

# 危险模式检测（基础防护，非完美沙盒）
DANGEROUS_PATTERNS = {
    "python": [
        r"\bos\.system\b", r"\bsubprocess\b", r"\b__import__\b",
        r"\bopen\s*\(.*(\/etc|\/var|\.env|passwd)", r"\bshutil\.rmtree\b",
        r"\bos\.remove\b", r"\bos\.unlink\b",
    ],
    "bash": [
        r"\brm\s+-rf\b", r"\bdd\s+if=", r"\b>(\/dev\/|\/etc\/)",
        r"\bcurl\b.*\|\s*bash", r"\bwget\b.*\|\s*sh",
    ],
}


def _check_dangerous(code: str, language: str) -> str:
    """检查代码是否包含危险操作，返回警告信息或空字符串"""
    patterns = DANGEROUS_PATTERNS.get(language, [])
    for pattern in patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return f"检测到潜在危险操作: {pattern}"
    return ""


def execute_code(code: str, language: str = "python") -> Dict[str, Any]:
    """执行代码并返回结果"""
    if language not in ALLOWED_LANGUAGES:
        return {"success": False, "message": f"不支持的语言: {language}，支持: {', '.join(ALLOWED_LANGUAGES)}"}

    lang_cfg = LANG_CONFIG.get(language)
    if not lang_cfg:
        return {"success": False, "message": f"语言配置缺失: {language}"}

    # 安全检查
    warning = _check_dangerous(code, language)
    if warning:
        return {"success": False, "message": f"⚠️ 安全检查未通过: {warning}"}

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=lang_cfg["suffix"], delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        cmd = [arg.format(file=temp_file) for arg in lang_cfg["cmd"]]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_TIMEOUT,
            cwd=tempfile.gettempdir(),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        stdout = result.stdout[:MAX_OUTPUT_LENGTH] if result.stdout else ""
        stderr = result.stderr[:1000] if result.stderr else ""

        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"执行超时（{MAX_TIMEOUT}秒限制）"}
    except FileNotFoundError:
        interpreter = lang_cfg["cmd"][0]
        return {"success": False, "message": f"未找到 {language} 解释器（{interpreter}），请确认已安装"}
    except Exception as e:
        logger.error(f"代码执行异常: {e}")
        return {"success": False, "message": f"执行失败: {e}"}
    finally:
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception:
                pass


def _detect_language(text: str) -> str:
    """从用户输入中检测代码语言"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["javascript", "js ", "node"]):
        return "javascript"
    if any(kw in text_lower for kw in ["bash", "shell", "sh "]):
        return "bash"
    return "python"


def _extract_code_block(text: str) -> str:
    """从 Markdown 代码块中提取代码"""
    # 匹配 ```python ... ``` 或 ```js ... ``` 等
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


@register_skill(
    skill_id="code_execute",
    name="代码执行",
    description="在安全沙盒中执行 Python/JavaScript/Bash 代码，返回运行结果",
    triggers=["执行代码", "运行代码", "跑一下代码", "帮我运行", "代码执行", "run code",
              "执行python", "执行js", "执行bash", "跑一段代码", "帮我跑"],
    icon="code",
    examples=[
        "帮我执行这段 Python 代码：print('Hello')",
        "运行代码：for i in range(5): print(i)",
        "帮我跑一下这个脚本",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "在安全沙盒中执行代码。支持 Python、JavaScript、Bash。当用户要求执行、运行代码时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的代码内容",
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言：python、javascript、bash，默认 python",
                        "enum": ["python", "javascript", "bash"],
                    },
                },
                "required": ["code"],
            },
        },
    },
)
def handle_code_execute(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}

    code = tool_args.get("code") or _extract_code_block(user_input)
    language = tool_args.get("language") or _detect_language(user_input)

    if not code or len(code.strip()) < 3:
        return {
            "success": False,
            "message": "请提供要执行的代码。比如：「帮我执行 print('Hello World')」",
        }

    result = execute_code(code, language)

    if result.get("message"):
        return {"success": False, "message": f"❌ {result['message']}"}

    parts = [f"💻 **代码执行结果** ({language})\n"]
    parts.append(f"```{language}\n{code}\n```\n")

    if result["stdout"]:
        parts.append(f"**输出：**\n```\n{result['stdout']}\n```")
    if result["stderr"]:
        parts.append(f"**错误信息：**\n```\n{result['stderr']}\n```")
    if not result["stdout"] and not result["stderr"]:
        parts.append("（无输出）")

    status = "✅ 成功" if result["success"] else f"❌ 退出码 {result['returncode']}"
    parts.append(f"\n**状态：** {status}")

    return {"success": result["success"], "message": "\n".join(parts)}
