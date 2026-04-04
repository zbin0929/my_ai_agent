# -*- coding: utf-8 -*-
"""
企业微信机器人推送插件
======================

功能说明：
    向企业微信群聊发送消息
    使用企业微信自定义机器人 Webhook API
    
    使用前提：
    1. 在企业微信群中添加自定义机器人
    2. 获取 Webhook URL

配置示例（config.yaml）：
    tools:
      - id: "wecom_bot"
        config:
          webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

作者：AI Agent Team
版本：1.0.0
"""

import logging
from typing import Any, Dict, Type

import httpx
from pydantic import BaseModel, Field

from plugins import register_plugin
from plugins.base import BasePluginTool

logger = logging.getLogger(__name__)


class WecomBotInput(BaseModel):
    """
    企微机器人工具的输入模型
    
    属性：
        message: 要发送的消息内容
    """
    message: str = Field(description="要发送到企业微信群的消息内容")


@register_plugin("wecom_bot")
class WecomBotTool(BasePluginTool):
    """
    企业微信机器人推送工具
    
    通过企业微信自定义机器人 Webhook 向群聊发送消息
    支持文本和 Markdown 格式
    
    配置项：
        webhook_url: 企微机器人的 Webhook 地址（必填）
    """
    
    name: str = "wecom_bot"
    description: str = (
        "企业微信机器人推送工具，用于向企微群聊发送消息。"
        "输入要发送的消息内容，工具会将消息推送到配置的企微群。"
    )
    args_schema: Type[BaseModel] = WecomBotInput
    
    def _run(self, message: str, **kwargs) -> str:
        """
        发送消息到企业微信群
        
        参数：
            message (str): 消息内容
        
        返回：
            str: 发送结果描述
        
        流程：
            1. 获取 Webhook URL
            2. 构建请求体（支持 Markdown）
            3. 发送 HTTP POST 请求
            4. 检查响应状态
        """
        # 获取配置
        webhook_url = self.get_config("webhook_url")
        if not webhook_url:
            return "❌ 错误: 未配置企微 Webhook URL"
        
        # 构建请求体 - 使用 markdown 格式
        body = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }
        
        # 发送请求
        try:
            response = httpx.post(
                webhook_url,
                json=body,
                timeout=10.0,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            
            # 企微 API 返回码 0 表示成功
            if result.get("errcode") == 0:
                self.log_info(f"消息发送成功: {message[:50]}...")
                return "✅ 消息已成功发送到企微群"
            else:
                error_msg = result.get("errmsg", str(result))
                self.log_error(f"发送失败: {error_msg}")
                return f"❌ 发送失败: {error_msg}"
                
        except httpx.TimeoutException:
            self.log_error("发送超时")
            return "❌ 发送超时，请检查网络连接"
        except Exception as e:
            self.log_error(f"发送异常: {e}")
            return f"❌ 发送失败: {e}"
