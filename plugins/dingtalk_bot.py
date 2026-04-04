# -*- coding: utf-8 -*-
"""
钉钉机器人推送插件
==================

功能说明：
    向钉钉群聊发送消息
    使用钉钉自定义机器人 Webhook API
    支持加签安全验证
    
    使用前提：
    1. 在钉钉群中添加自定义机器人
    2. 获取 Webhook URL
    3. （可选）配置加签密钥

配置示例（config.yaml）：
    tools:
      - id: "dingtalk_bot"
        config:
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
          secret: "your_sign_secret"

作者：AI Agent Team
版本：1.0.0
"""

import hmac
import hashlib
import base64
import time
import urllib.parse
import logging
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, Field

from plugins import register_plugin
from plugins.base import BasePluginTool

logger = logging.getLogger(__name__)


class DingtalkBotInput(BaseModel):
    """
    钉钉机器人工具的输入模型
    
    属性：
        message: 要发送的消息内容
    """
    message: str = Field(description="要发送到钉钉群的消息内容")


@register_plugin("dingtalk_bot")
class DingtalkBotTool(BasePluginTool):
    """
    钉钉机器人推送工具
    
    通过钉钉自定义机器人 Webhook 向群聊发送消息
    支持 Markdown 格式和加签验证
    
    配置项：
        webhook_url: 钉钉机器人的 Webhook 地址（必填）
        secret: 加签密钥（可选，用于安全验证）
    """
    
    name: str = "dingtalk_bot"
    description: str = (
        "钉钉机器人推送工具，用于向钉钉群聊发送消息。"
        "输入要发送的消息内容，工具会将消息推送到配置的钉钉群。"
    )
    args_schema: Type[BaseModel] = DingtalkBotInput
    
    def _run(self, message: str, **kwargs) -> str:
        """
        发送消息到钉钉群
        
        参数：
            message (str): 消息内容
        
        返回：
            str: 发送结果描述
        
        流程：
            1. 获取 Webhook URL 和密钥
            2. 如有密钥，计算签名并追加到 URL
            3. 构建 Markdown 格式请求体
            4. 发送 HTTP POST 请求
            5. 检查响应状态
        """
        # 获取配置
        webhook_url = self.get_config("webhook_url")
        if not webhook_url:
            return "❌ 错误: 未配置钉钉 Webhook URL"
        
        secret = self.get_config("secret")
        
        # 如果有密钥，计算签名
        if secret:
            webhook_url = self._sign_url(webhook_url, secret)
        
        # 构建请求体 - 使用 markdown 格式
        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": "智能体通知",
                "text": message
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
            
            # 钉钉 API 返回码 0 表示成功
            if result.get("errcode") == 0:
                self.log_info(f"消息发送成功: {message[:50]}...")
                return "✅ 消息已成功发送到钉钉群"
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
    
    def _sign_url(self, webhook_url: str, secret: str) -> str:
        """
        生成带签名的 Webhook URL
        
        参数：
            webhook_url (str): 原始 Webhook URL
            secret (str): 加签密钥
        
        返回：
            str: 带签名参数的 URL
        
        算法：
            1. 获取当前时间戳（毫秒）
            2. 拼接 timestamp + "\n" + secret
            3. HMAC-SHA256 计算签名
            4. Base64 编码后 URL 编码
            5. 追加 timestamp 和 sign 参数到 URL
        """
        timestamp = str(round(time.time() * 1000))
        
        string_to_sign = f"{timestamp}\n{secret}"
        
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        return f"{webhook_url}&timestamp={timestamp}&sign={sign}"
