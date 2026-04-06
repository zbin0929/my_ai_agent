# -*- coding: utf-8 -*-
"""
图片生成技能
============

使用智谱 CogView API 根据文字描述生成图片。
"""

import os
import sys
import re
import time
import logging
from typing import Dict, Any

import httpx

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _sanitize_filename(filename: str) -> str:
    """安全清理文件名，防止路径遍历攻击"""
    if not filename:
        return ""
    # 只允许字母数字、连字符和下划线
    return re.sub(r'[^a-zA-Z0-9_\-]', "", filename)


def _get_config(key: str, default: str = "") -> str:
    from skills import get_skill_config
    val = get_skill_config("image_generate", key)
    if val:
        return val
    return default


VALID_SIZES = {
    "1024x1024", "768x1344", "864x1152",
    "1344x768", "1152x864", "1440x720", "720x1440",
}


def generate_image(prompt: str, size: str = None) -> Dict[str, Any]:
    api_key = _get_config("api_key") or os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        return {"success": False, "message": "未配置 API Key，请在技能设置中配置图片生成 API Key，或设置环境变量 ZHIPU_API_KEY"}

    model = _get_config("model", "cogview-4-250304")
    if size and size in VALID_SIZES:
        pass  # 使用传入的 size
    else:
        size = _get_config("size", "1024x1024")

    try:
        api_url = "https://open.bigmodel.cn/api/paas/v4/images/generations"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
        }

        resp = httpx.post(api_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        images = data.get("data", [])
        if not images:
            return {"success": False, "message": "API 返回为空，请重试"}

        image_url = images[0].get("url", "")

        images_dir = os.path.join(project_root, "data", "generated_images")
        os.makedirs(images_dir, exist_ok=True)

        # 安全清理文件名
        safe_name = _sanitize_filename(prompt[:20].replace(" ", "_"))
        if not safe_name:
            safe_name = "generated"
        filename = f"{safe_name}_{int(time.time())}.png"
        filepath = os.path.join(images_dir, filename)

        if image_url:
            img_resp = httpx.get(image_url, timeout=60)
            with open(filepath, "wb") as f:
                f.write(img_resp.content)

        # 返回本地API URL，避免外部URL签名过期问题
        local_url = f"/api/files/images/{filename}"
        return {
            "success": True,
            "url": local_url,
            "original_url": image_url,
            "filepath": filepath,
            "filename": filename,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"图片生成 API 错误: {e.response.status_code} {e.response.text}")
        return {"success": False, "message": f"API 调用失败 ({e.response.status_code}): {e.response.text[:200]}"}
    except Exception as e:
        logger.error(f"图片生成失败: {e}")
        return {"success": False, "message": f"图片生成失败: {e}"}


# 关键词 → 尺寸映射，用于关键词匹配路径解析用户意图
_SIZE_KEYWORDS = {
    "竖版": "768x1344", "竖图": "768x1344", "竖屏": "768x1344",
    "手机壁纸": "768x1344", "海报": "768x1344", "portrait": "768x1344",
    "横版": "1344x768", "横图": "1344x768", "横屏": "1344x768",
    "封面": "1344x768", "桌面壁纸": "1344x768", "landscape": "1344x768",
    "横幅": "1440x720", "banner": "1440x720",
    "长图": "720x1440",
}


def _detect_size_from_text(text: str) -> tuple:
    """从用户输入中检测尺寸意图，返回 (size, cleaned_text)"""
    text_lower = text.lower()
    for keyword, size in _SIZE_KEYWORDS.items():
        if keyword in text_lower:
            cleaned = text.replace(keyword, "").strip()
            return size, cleaned
    return None, text


@register_skill(
    skill_id="image_generate",
    name="图片生成",
    description="根据文字描述生成图片（使用智谱 CogView）",
    triggers=["生成图片", "画一张", "画一个", "画一幅", "帮我画", "生成一张图", "AI画图",
              "创建图片", "画图", "帮我生成图", "生成一张", "画一个图", "画张图"],
    icon="image",
    examples=[
        "帮我画一只可爱的猫咪",
        "生成一张科技感的未来城市图片",
        "画一幅日落时分的海边风景",
    ],
    config_schema=[
        {
            "key": "provider",
            "label": "服务商",
            "description": "选择图片生成的 API 服务商",
            "type": "select",
            "required": False,
            "default": "zhipu",
            "options": [
                {"value": "zhipu", "label": "智谱 AI (CogView)"},
            ],
        },
        {
            "key": "api_key",
            "label": "API Key",
            "description": "对应服务商的 API Key",
            "type": "password",
            "required": True,
            "env_hint": "ZHIPU_API_KEY",
        },
        {
            "key": "model",
            "label": "模型",
            "description": "图片生成使用的模型",
            "type": "select",
            "required": True,
            "default": "cogview-4-250304",
            "options": [
                {"value": "cogview-4-250304", "label": "CogView-4"},
                {"value": "cogview-4", "label": "CogView-4 (旧版)"},
            ],
        },
        {
            "key": "size",
            "label": "图片尺寸",
            "description": "生成图片的分辨率",
            "type": "select",
            "required": True,
            "default": "1024x1024",
            "options": [
                {"value": "1024x1024", "label": "1024 × 1024"},
                {"value": "768x1344", "label": "768 × 1344"},
                {"value": "864x1152", "label": "864 × 1152"},
                {"value": "1344x768", "label": "1344 × 768"},
                {"value": "1152x864", "label": "1152 × 864"},
                {"value": "1440x720", "label": "1440 × 720"},
                {"value": "720x1440", "label": "720 × 1440"},
            ],
        },
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "根据文字描述生成图片。当用户要求画图、生成图片时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "图片的描述文字，如'一只可爱的猫咪'、'科技感的未来城市'",
                    },
                    "size": {
                        "type": "string",
                        "description": "图片尺寸。正方形用1024x1024，竖版/海报/手机壁纸用768x1344或864x1152，横版/封面/桌面壁纸用1344x768或1152x864，超宽横幅用1440x720，超高竖幅用720x1440。默认1024x1024",
                        "enum": ["1024x1024", "768x1344", "864x1152", "1344x768", "1152x864", "1440x720", "720x1440"],
                    },
                },
                "required": ["prompt"],
            },
        },
    },
)
def handle_image_generate(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = user_input
    for trigger in ["生成图片", "画一张", "画一个", "画一幅", "帮我画", "生成一张图",
                     "AI画图", "创建图片", "画图", "帮我生成图", "帮我", "请帮我",
                     "帮我生成", "的图片", "的图", "图片"]:
        prompt = prompt.replace(trigger, "").strip()

    if not prompt:
        return {
            "success": False,
            "message": "请告诉我你想生成什么图片？比如：「帮我画一只可爱的猫咪」",
        }

    # 从 context 中获取 FC 传入的 size，或从用户文本中检测尺寸意图
    size = None
    tool_args = context.get("tool_args", {}) if context else {}
    if tool_args.get("size"):
        size = tool_args["size"]
    else:
        size, prompt = _detect_size_from_text(prompt)

    result = generate_image(prompt, size=size)

    if result["success"]:
        # 使用本地URL，避免外部URL签名过期
        local_url = result.get("url", "")
        msg = (
            f"🎨 **图片已生成！**\n\n"
            f"**描述：** {prompt}\n\n"
        )
        if local_url:
            # 使用 markdown 图片语法，前端会渲染为可点击预览的图片
            msg += f"![生成的图片]({local_url})"
        return {"success": True, "message": msg, "image_url": local_url}
    else:
        return {"success": False, "message": f"❌ {result['message']}"}
