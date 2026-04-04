# -*- coding: utf-8 -*-
"""
飞书机器人推送插件
==================

功能说明：
    向飞书群聊发送消息，支持文本和富文本格式
    使用飞书自定义机器人 Webhook API
    
    使用前提：
    1. 在飞书群中添加自定义机器人
    2. 获取 Webhook URL
    3. （可选）配置加签密钥

配置示例（config.yaml）：
    tools:
      - id: "feishu_bot"
        config:
          webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
          secret: "your_sign_secret"

作者：AI Agent Team
版本：1.0.0
"""

import hmac
import hashlib
import base64
import time
import logging
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, Field

from plugins import register_plugin
from plugins.base import BasePluginTool

logger = logging.getLogger(__name__)


class FeishuBotInput(BaseModel):
    """
    飞书机器人工具的输入模型
    
    属性：
        message: 要发送的消息内容
        msg_type: 消息类型，默认 text
    """
    message: str = Field(description="要发送到飞书群的消息内容")
    msg_type: str = Field(default="text", description="消息类型: text 或 post")


@register_plugin("feishu_bot")
class FeishuBotTool(BasePluginTool):
    """
    飞书机器人推送工具
    
    通过飞书自定义机器人 Webhook 向群聊发送消息
    支持文本消息和富文本消息
    
    配置项：
        webhook_url: 飞书机器人的 Webhook 地址（必填）
        secret: 加签密钥（可选，用于安全验证）
    """
    
    name: str = "feishu_bot"
    description: str = (
        "飞书机器人推送工具，用于向飞书群聊发送消息。"
        "输入要发送的消息内容，工具会将消息推送到配置的飞书群。"
    )
    args_schema: Type[BaseModel] = FeishuBotInput
    
    def _run(self, message: str, msg_type: str = "text", **kwargs) -> str:
        """
        发送消息到飞书群
        
        参数：
            message (str): 消息内容
            msg_type (str): 消息类型，"text" 或 "post"
        
        返回：
            str: 发送结果描述
        
        流程：
            1. 获取 Webhook URL 和密钥
            2. 构建请求体（如有密钥则签名）
            3. 发送 HTTP POST 请求
            4. 检查响应状态
        """
        # 获取配置
        webhook_url = self.get_config("webhook_url")
        if not webhook_url:
            return "❌ 错误: 未配置飞书 Webhook URL"
        
        secret = self.get_config("secret")
        
        # 构建请求体
        body = self._build_request_body(message, msg_type, secret)
        
        # 发送请求
        try:
            response = httpx.post(
                webhook_url,
                json=body,
                timeout=10.0,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            
            # 检查飞书 API 响应码
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                self.log_info(f"消息发送成功: {message[:50]}...")
                return f"✅ 消息已成功发送到飞书群"
            else:
                error_msg = result.get("msg", str(result))
                self.log_error(f"发送失败: {error_msg}")
                return f"❌ 发送失败: {error_msg}"
                
        except httpx.TimeoutException:
            self.log_error("发送超时")
            return "❌ 发送超时，请检查网络连接"
        except Exception as e:
            self.log_error(f"发送异常: {e}")
            return f"❌ 发送失败: {e}"
    
    def _build_request_body(
        self, 
        message: str, 
        msg_type: str, 
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建飞书 API 请求体
        
        参数：
            message: 消息内容
            msg_type: 消息类型
            secret: 加签密钥
        
        返回：
            dict: 请求体字典
        
        说明：
            如果配置了密钥，会自动添加签名验证
            签名算法: HMAC-SHA256(timestamp + "\n" + secret)
        """
        body: Dict[str, Any] = {"msg_type": msg_type}
        
        # 根据消息类型构建内容
        if msg_type == "text":
            body["content"] = {"text": message}
        elif msg_type == "post":
            body["content"] = {
                "post": {
                    "zh_cn": {
                        "title": "智能体通知",
                        "content": [[{"tag": "text", "text": message}]]
                    }
                }
            }
        
        # 添加签名（如果配置了密钥）
        if secret:
            timestamp = str(int(time.time()))
            sign = self._generate_sign(timestamp, secret)
            body["timestamp"] = timestamp
            body["sign"] = sign
        
        return body
    
    def _generate_sign(self, timestamp: str, secret: str) -> str:
        """
        生成飞书签名
        
        参数：
            timestamp (str): 时间戳字符串
            secret (str): 加签密钥
        
        返回：
            str: Base64 编码的签名
        
        算法：
            1. 拼接 timestamp + "\n" + secret
            2. 使用 HMAC-SHA256 计算签名
            3. Base64 编码输出
        """
        string_to_sign = f"{timestamp}\n{secret}"
        
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign
