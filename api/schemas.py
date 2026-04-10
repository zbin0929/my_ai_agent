# -*- coding: utf-8 -*-
"""
请求/响应数据模型
================

使用 Pydantic BaseModel 定义所有 API 接口的请求体结构，
提供自动类型校验和 OpenAPI 文档生成。
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求 — 发送消息给 AI"""
    message: str = Field(..., max_length=50000)       # 用户输入的消息内容
    session_id: Optional[str] = None                  # 会话 ID（为空时创建新会话）
    agent_id: Optional[str] = Field(default=None, pattern=r'^[a-zA-Z0-9_\-.]+$')
    files: Optional[List[str]] = None                 # 附件文件路径列表
    file_infos: Optional[List[dict]] = None           # 附件文件元信息（文件名、大小等）
    enable_thinking: Optional[bool] = False           # 是否启用深度思考（覆盖 Agent 配置）
    enable_search: Optional[bool] = False             # 是否启用联网搜索


class SessionCreate(BaseModel):
    """创建新会话"""
    title: Optional[str] = None                       # 会话标题（为空时自动生成）


class SessionUpdate(BaseModel):
    """更新会话信息"""
    title: Optional[str] = None                       # 新标题
    pinned: Optional[bool] = None                     # 是否置顶


class AgentCreate(BaseModel):
    """创建自定义 Agent（员工）"""
    name: str                                         # Agent 名称
    avatar: Optional[str] = "🤖"                      # 头像 emoji
    role: Optional[str] = ""
    model_id: Optional[str] = None
    model_provider: Optional[str] = "zhipu"
    temperature: Optional[float] = 0.7
    enable_thinking: Optional[bool] = False
    enable_search: Optional[bool] = False
    custom_api_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    description: Optional[str] = ""
    skills: Optional[List[str]] = None
    agent_type: Optional[str] = None
    enabled: Optional[bool] = True


class AgentUpdate(BaseModel):
    """更新 Agent 配置"""
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    temperature: Optional[float] = None
    enable_thinking: Optional[bool] = None
    enable_search: Optional[bool] = None
    custom_api_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    enabled: Optional[bool] = None


class ModelCreate(BaseModel):
    """创建自定义模型配置"""
    name: str                                         # 模型显示名称
    provider: str                                     # 提供商（openai/deepseek/zhipu 等）
    model_id: str                                     # 模型标识（如 gpt-4o、deepseek-chat）
    base_url: str                                     # API Base URL
    api_key: str                                      # API 密钥
    supports_thinking: Optional[bool] = False         # 是否支持思考/推理输出
    description: Optional[str] = ""                   # 模型描述
    capabilities: Optional[List[str]] = None          # 能力标签（text/vision/ocr 等）


class ModelUpdate(BaseModel):
    """更新自定义模型配置"""
    name: Optional[str] = None
    provider: Optional[str] = None
    model_id: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    supports_thinking: Optional[bool] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None


class SkillCreate(BaseModel):
    """创建自定义技能"""
    name: str                                         # 技能名称
    description: str                                  # 技能描述
    triggers: List[str]                               # 触发关键词列表
    icon: Optional[str] = "🔧"                        # 图标
    skill_type: str                                   # 技能类型：prompt（提示词型）或 api（API 调用型）
    system_prompt: Optional[str] = None               # prompt 类型的系统提示词
    api_url: Optional[str] = None                     # api 类型的目标 URL
    api_method: Optional[str] = "POST"                # HTTP 方法
    api_headers: Optional[dict] = None                # 自定义请求头
    api_body_template: Optional[str] = None           # 请求体模板（支持 {input} 占位符）


class SkillUpdate(BaseModel):
    """更新自定义技能"""
    name: Optional[str] = None
    description: Optional[str] = None
    triggers: Optional[List[str]] = None
    icon: Optional[str] = None
    enabled: Optional[bool] = None
    skill_type: Optional[str] = None
    system_prompt: Optional[str] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[dict] = None
    api_body_template: Optional[str] = None


class NotifyConfigUpdate(BaseModel):
    """更新通知推送配置"""
    feishu_webhook: Optional[str] = None              # 飞书机器人 Webhook URL
    feishu_secret: Optional[str] = None               # 飞书机器人加签密钥
    wecom_webhook: Optional[str] = None               # 企业微信机器人 Webhook URL
    dingtalk_webhook: Optional[str] = None            # 钉钉机器人 Webhook URL
    dingtalk_secret: Optional[str] = None             # 钉钉机器人加签密钥


class NotifyTestRequest(BaseModel):
    """测试通知推送"""
    platform: str                                     # 平台标识：feishu / wecom / dingtalk
    message: Optional[str] = "测试消息：AI 助手通知连接成功！"
