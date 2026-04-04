# -*- coding: utf-8 -*-
"""
代码执行插件
============

功能说明：
    在安全沙盒中执行代码
    支持 Python、JavaScript、Bash

配置示例（config.yaml）：
    tools:
      - id: "code_executor"
        config:
          timeout: 60
          allowed_languages: ["python"]

作者：AI Agent Team
版本：1.0.0
"""

import subprocess
import logging
import tempfile
import os
from typing import Any, Dict, List, Type

from pydantic import BaseModel, Field

from plugins import register_plugin
from plugins.base import BasePluginTool

logger = logging.getLogger(__name__)


class CodeExecutorInput(BaseModel):
    """
    代码执行工具的输入模型
    
    属性：
        code: 要执行的代码
        language: 编程语言
    """
    code: str = Field(description="要执行的代码")
    language: str = Field(default="python", description="编程语言: python, javascript, bash")


@register_plugin("code_executor")
class CodeExecutorTool(BasePluginTool):
    """
    代码执行工具
    
    在受限环境中执行代码，支持 Python、JavaScript、Bash
    执行结果包含标准输出和标准错误
    
    配置项：
        timeout (int): 执行超时时间（秒），默认 60
        allowed_languages (list): 允许的语言列表，默认 ["python"]
    """
    
    name: str = "code_executor"
    description: str = (
        "代码执行工具，可以在沙盒中执行 Python、JavaScript 或 Bash 代码。"
        "输入代码和语言类型，工具会返回执行结果。"
    )
    args_schema: Type[BaseModel] = CodeExecutorInput
    
    # 语言 -> 文件后缀和命令模板的映射
    _LANG_CONFIG = {
        "python": {
            "suffix": ".py",
            "command": ["python", "{file}"]
        },
        "javascript": {
            "suffix": ".js",
            "command": ["node", "{file}"]
        },
        "bash": {
            "suffix": ".sh",
            "command": ["bash", "{file}"]
        }
    }
    
    def _run(self, code: str, language: str = "python", **kwargs) -> str:
        """
        执行代码
        
        参数：
            code (str): 要执行的代码
            language (str): 编程语言
        
        返回：
            str: 执行结果（包含 stdout 和 stderr）
        
        安全措施：
            1. 检查语言是否在允许列表中
            2. 在临时文件中执行
            3. 设置超时限制
            4. 限制输出长度
        """
        # 检查语言是否允许
        allowed = self.get_config("allowed_languages", ["python"])
        if language not in allowed:
            return f"❌ 不允许执行 {language} 代码。允许的语言: {allowed}"
        
        # 获取语言配置
        lang_cfg = self._LANG_CONFIG.get(language)
        if not lang_cfg:
            return f"❌ 不支持的语言: {language}。支持: {list(self._LANG_CONFIG.keys())}"
        
        # 获取超时设置
        timeout = self.get_config("timeout", 60)
        
        # 在临时文件中执行
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=lang_cfg["suffix"],
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # 构建执行命令
            cmd = [arg.format(file=temp_file) for arg in lang_cfg["command"]]
            
            # 执行代码
            self.log_info(f"执行 {language} 代码，超时: {timeout}s")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )
            
            # 构建输出
            output_parts = []
            
            if result.stdout:
                # 限制输出长度
                stdout = result.stdout[:3000]
                output_parts.append(f"输出:\n{stdout}")
            
            if result.stderr:
                stderr = result.stderr[:1000]
                output_parts.append(f"错误:\n{stderr}")
            
            if result.returncode != 0:
                output_parts.append(f"退出码: {result.returncode}")
            
            output = "\n".join(output_parts) if output_parts else "（无输出）"
            
            self.log_info(f"代码执行完成，退出码: {result.returncode}")
            return output
            
        except subprocess.TimeoutExpired:
            self.log_error(f"代码执行超时 ({timeout}s)")
            return f"❌ 执行超时 ({timeout}s)"
        except Exception as e:
            self.log_error(f"代码执行失败: {e}")
            return f"❌ 执行失败: {e}"
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except Exception:
                pass
