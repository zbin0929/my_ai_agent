# -*- coding: utf-8 -*-
"""
邮件发送技能
============

通过 SMTP 发送邮件，支持 HTML 格式和附件。
需要在技能配置中设置 SMTP 服务器信息。
"""

import os
import sys
import re
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _get_config(key: str, default: str = "") -> str:
    from skills import get_skill_config
    val = get_skill_config("email_send", key)
    return val if val else default


def _generate_email_content(subject: str, body_hint: str) -> Dict[str, str]:
    """使用 LLM 润色邮件内容"""
    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        response = llm.call(messages=[
            {
                "role": "system",
                "content": (
                    "你是一个专业的邮件写作助手。根据用户提供的主题和要点，"
                    "撰写一封正式得体的邮件。\n"
                    "要求：\n"
                    "1. 直接输出邮件正文，不要输出主题行\n"
                    "2. 语言简洁专业\n"
                    "3. 包含称呼和落款\n"
                    "4. 如果用户提供的是中文，用中文写"
                ),
            },
            {"role": "user", "content": f"邮件主题: {subject}\n要点: {body_hint}"},
        ])
        return {"subject": subject, "body": str(response).strip()}
    except Exception as e:
        logger.warning(f"LLM 润色邮件失败: {e}")
        return {"subject": subject, "body": body_hint}


def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    html: bool = False,
) -> Dict[str, Any]:
    """发送邮件"""
    smtp_host = _get_config("smtp_host")
    smtp_port = int(_get_config("smtp_port", "587"))
    smtp_user = _get_config("smtp_user")
    smtp_pass = _get_config("smtp_pass")
    from_addr = _get_config("from_addr") or smtp_user

    if not all([smtp_host, smtp_user, smtp_pass]):
        return {
            "success": False,
            "message": "邮件服务未配置，请在技能设置中配置 SMTP 服务器信息（服务器地址、端口、用户名、密码）",
        }

    # 验证邮箱格式
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', to):
        return {"success": False, "message": f"邮箱格式不正确: {to}"}

    server = None
    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        # 添加附件（限制单个附件 20MB）
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath) and os.path.getsize(filepath) < 20 * 1024 * 1024:
                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(filepath)}",
                        )
                        msg.attach(part)

        # 发送
        use_ssl = smtp_port == 465
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()

        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to], msg.as_string())

        return {"success": True, "message": f"邮件已发送到 {to}"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP 认证失败，请检查用户名和密码"}
    except smtplib.SMTPConnectError:
        return {"success": False, "message": f"无法连接 SMTP 服务器 {smtp_host}:{smtp_port}"}
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return {"success": False, "message": f"发送失败: {e}"}
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


@register_skill(
    skill_id="email_send",
    name="邮件发送",
    description="发送邮件，支持 LLM 润色邮件内容、HTML 格式和附件",
    triggers=["发邮件", "发送邮件", "邮件", "帮我发一封邮件", "send email",
              "写邮件", "发一封", "邮件给"],
    icon="mail",
    examples=[
        "发一封邮件给 test@example.com，主题是会议纪要",
        "帮我写一封邮件发给同事，说明项目进度",
        "发邮件通知客户项目已完成",
    ],
    config_schema=[
        {
            "key": "smtp_host",
            "label": "SMTP 服务器",
            "description": "如 smtp.gmail.com、smtp.qq.com、smtp.163.com",
            "type": "text",
            "required": True,
        },
        {
            "key": "smtp_port",
            "label": "SMTP 端口",
            "description": "TLS 用 587，SSL 用 465",
            "type": "number",
            "required": True,
            "default": "587",
        },
        {
            "key": "smtp_user",
            "label": "邮箱账号",
            "description": "用于登录的邮箱地址",
            "type": "text",
            "required": True,
        },
        {
            "key": "smtp_pass",
            "label": "邮箱密码/授权码",
            "description": "邮箱密码或授权码（推荐使用授权码）",
            "type": "password",
            "required": True,
        },
        {
            "key": "from_addr",
            "label": "发件人地址",
            "description": "显示的发件人地址，默认与账号相同",
            "type": "text",
            "required": False,
        },
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "发送邮件。当用户要求发邮件、写邮件时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "收件人邮箱地址",
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题",
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件正文内容或要点",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
)
def handle_email_send(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}

    to = tool_args.get("to", "")
    subject = tool_args.get("subject", "")
    body = tool_args.get("body", "")

    # 尝试从用户输入中提取邮箱
    if not to:
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
        if emails:
            to = emails[0]

    if not to:
        return {"success": False, "message": "请提供收件人邮箱地址。比如：「发邮件给 test@example.com，主题：会议通知」"}

    if not subject:
        return {"success": False, "message": "请提供邮件主题"}

    # LLM 润色邮件内容
    if body and len(body) < 200:
        polished = _generate_email_content(subject, body)
        body = polished["body"]

    # 查找附件
    attachments = []
    if context:
        for key in ("files", "file_paths"):
            if context.get(key):
                attachments.extend(context[key])

    result = send_email(to, subject, body, attachments=attachments if attachments else None)

    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    attachment_info = f"\n**附件：** {len(attachments)} 个文件" if attachments else ""
    msg = (
        f"📧 **邮件已发送！**\n\n"
        f"**收件人：** {to}\n"
        f"**主题：** {subject}{attachment_info}\n\n"
        f"**正文预览：**\n{body[:200]}{'...' if len(body) > 200 else ''}"
    )
    return {"success": True, "message": msg}
