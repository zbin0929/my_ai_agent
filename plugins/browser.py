# -*- coding: utf-8 -*-
"""
浏览器自动化插件
================

功能说明：
    使用 Playwright 进行浏览器自动化操作
    支持网页抓取、截图、表单填写等

配置示例（config.yaml）：
    tools:
      - id: "browser"
        config:
          headless: true
          timeout: 30

作者：AI Agent Team
版本：1.0.0
"""

import logging
from typing import Any, Dict, Type

from pydantic import BaseModel, Field

from plugins import register_plugin
from plugins.base import BasePluginTool

logger = logging.getLogger(__name__)


class BrowserInput(BaseModel):
    """
    浏览器工具的输入模型
    
    属性：
        action: 要执行的操作（open, screenshot, click, extract）
        url: 目标 URL
        selector: CSS 选择器（用于 click/extract）
    """
    action: str = Field(
        description="操作类型: open(打开), screenshot(截图), click(点击), extract(提取)"
    )
    url: str = Field(default="", description="目标 URL")
    selector: str = Field(default="", description="CSS 选择器")


@register_plugin("browser")
class BrowserTool(BasePluginTool):
    """
    浏览器自动化工具
    
    使用 Playwright 进行浏览器自动化操作
    支持打开网页、截图、点击元素、提取内容
    
    配置项：
        headless (bool): 是否使用无头模式，默认 True
        timeout (int): 操作超时时间（秒），默认 30
    """
    
    name: str = "browser"
    description: str = (
        "浏览器自动化工具，可以打开网页、截图、点击元素和提取页面内容。"
        "使用 action 参数指定操作: open, screenshot, click, extract。"
        "需要安装 playwright: pip install playwright && playwright install"
    )
    args_schema: Type[BaseModel] = BrowserInput
    
    def _run(self, action: str, url: str = "", selector: str = "", **kwargs) -> str:
        """
        执行浏览器操作
        
        参数：
            action (str): 操作类型
            url (str): 目标 URL
            selector (str): CSS 选择器
        
        返回：
            str: 操作结果
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return "❌ 错误: 未安装 playwright。请运行: pip install playwright && playwright install"
        
        headless = self.get_config("headless", True)
        timeout = self.get_config("timeout", 30) * 1000  # 转为毫秒
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=headless)
                page = browser.new_page()
                page.set_default_timeout(timeout)
                
                result = ""
                
                if action == "open":
                    # 打开网页并提取文本内容
                    page.goto(url)
                    title = page.title()
                    content = page.inner_text("body")[:2000]  # 限制长度
                    result = f"页面标题: {title}\n\n内容:\n{content}"
                
                elif action == "screenshot":
                    # 截图保存
                    page.goto(url) if url else None
                    import os
                    os.makedirs("data/screenshots", exist_ok=True)
                    filepath = f"data/screenshots/screenshot_{int(time.time())}.png"
                    page.screenshot(path=filepath)
                    result = f"截图已保存: {filepath}"
                
                elif action == "click":
                    # 点击元素
                    if url:
                        page.goto(url)
                    page.click(selector)
                    result = f"已点击元素: {selector}"
                
                elif action == "extract":
                    # 提取元素内容
                    if url:
                        page.goto(url)
                    content = page.inner_text(selector)
                    result = f"提取内容:\n{content[:2000]}"
                
                else:
                    result = f"未知操作: {action}，支持: open, screenshot, click, extract"
                
                browser.close()
                self.log_info(f"浏览器操作完成: {action}")
                return result
                
        except Exception as e:
            self.log_error(f"浏览器操作失败: {e}")
            return f"❌ 操作失败: {e}"


# 需要导入 time 模块
import time
