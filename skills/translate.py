# -*- coding: utf-8 -*-
"""
翻译技能
========

使用 LLM 进行多语言翻译，自动检测源语言。
支持中英日韩法德西等常见语言互译。
"""

import os
import sys
import logging
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

LANG_MAP = {
    "中文": "Chinese", "英文": "English", "英语": "English",
    "日文": "Japanese", "日语": "Japanese",
    "韩文": "Korean", "韩语": "Korean",
    "法文": "French", "法语": "French",
    "德文": "German", "德语": "German",
    "西班牙语": "Spanish", "俄语": "Russian",
    "阿拉伯语": "Arabic", "葡萄牙语": "Portuguese",
    "chinese": "Chinese", "english": "English",
    "japanese": "Japanese", "korean": "Korean",
    "french": "French", "german": "German",
    "spanish": "Spanish", "russian": "Russian",
}


def _detect_target_lang(text: str) -> str:
    """从用户输入中检测目标语言"""
    text_lower = text.lower()
    for keyword, lang in LANG_MAP.items():
        if keyword in text_lower:
            return lang
    # 如果输入主要是中文，默认翻译成英文；否则翻译成中文
    chinese_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return "English" if chinese_count > len(text) * 0.3 else "Chinese"


def _clean_input(text: str) -> str:
    """清理触发词，提取待翻译内容"""
    for trigger in ["翻译", "帮我翻译", "翻译一下", "翻译成", "translate",
                     "翻译为", "请翻译", "翻译下"]:
        text = text.replace(trigger, "").strip()
    # 移除目标语言关键词
    for keyword in LANG_MAP:
        text = text.replace(keyword, "").strip()
    # 清理多余标点
    text = text.strip("：:，, 。.")
    return text.strip()


def translate_text(text: str, target_lang: str = None) -> Dict[str, Any]:
    """调用 LLM 执行翻译"""
    if not target_lang:
        target_lang = _detect_target_lang(text)

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
                    f"You are a professional translator. Translate the following text into {target_lang}. "
                    "Only output the translation, nothing else. Preserve the original formatting (markdown, line breaks, etc)."
                ),
            },
            {"role": "user", "content": text},
        ])

        return {"success": True, "translation": str(response).strip(), "target_lang": target_lang}
    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return {"success": False, "message": f"翻译失败: {e}"}


@register_skill(
    skill_id="translate",
    name="翻译",
    description="多语言翻译，自动检测源语言，支持中英日韩法德西等语言互译",
    triggers=["翻译", "翻译一下", "翻译成", "帮我翻译", "translate",
              "翻译为", "翻译下"],
    icon="translate",
    examples=[
        "帮我翻译：今天天气真好",
        "翻译成日文：谢谢你的帮助",
        "translate: The quick brown fox jumps over the lazy dog",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "翻译文本到指定语言。当用户要求翻译时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要翻译的文本内容",
                    },
                    "target_lang": {
                        "type": "string",
                        "description": "目标语言，如 Chinese、English、Japanese、Korean、French、German、Spanish 等",
                    },
                },
                "required": ["text"],
            },
        },
    },
)
def handle_translate(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}

    text = tool_args.get("text") or _clean_input(user_input)
    target_lang = tool_args.get("target_lang") or _detect_target_lang(user_input)

    if not text or len(text.strip()) < 1:
        return {
            "success": False,
            "message": "请提供要翻译的文本。比如：「帮我翻译：今天天气真好」",
        }

    result = translate_text(text, target_lang)

    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    msg = (
        f"🌐 **翻译结果** → {result['target_lang']}\n\n"
        f"**原文：**\n{text}\n\n"
        f"**译文：**\n{result['translation']}"
    )
    return {"success": True, "message": msg}
