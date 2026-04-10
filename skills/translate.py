# -*- coding: utf-8 -*-
import os
import sys
import logging
from typing import Dict, Any, AsyncGenerator

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024

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
    text_lower = text.lower()
    for keyword, lang in LANG_MAP.items():
        if keyword in text_lower:
            return lang
    chinese_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return "English" if chinese_count > len(text) * 0.3 else "Chinese"


def _clean_input(text: str) -> str:
    for trigger in ["翻译", "帮我翻译", "翻译一下", "翻译成", "translate",
                     "翻译为", "请翻译", "翻译下"]:
        text = text.replace(trigger, "").strip()
    for keyword in LANG_MAP:
        text = text.replace(keyword, "").strip()
    text = text.strip("：:，, 。.")
    return text.strip()


def _read_file_content(filepath: str) -> str:
    if os.path.getsize(filepath) > MAX_FILE_SIZE:
        logger.warning(f"文件过大跳过: {filepath}")
        return ""
    try:
        from core.file_reader import read_file
        result = read_file(filepath)
        if result.get("success"):
            return result["content"]
        return ""
    except Exception:
        return ""


def _find_uploaded_files(context: Dict[str, Any]) -> list:
    files = []
    upload_dir = os.path.join(project_root, "data", "uploads")
    if context:
        for key in ("files", "file_paths"):
            if context.get(key):
                for f in context[key]:
                    if not os.path.isabs(f):
                        full_path = os.path.join(upload_dir, f)
                        if os.path.exists(full_path):
                            files.append(full_path)
                        else:
                            files.append(f)
                    else:
                        files.append(f)
        tool_args = context.get("tool_args", {})
        if tool_args.get("file_path"):
            fp = tool_args["file_path"]
            if not os.path.isabs(fp):
                full_path = os.path.join(upload_dir, fp)
                if os.path.exists(full_path):
                    files.append(full_path)
                else:
                    files.append(fp)
            else:
                files.append(fp)
    return files


def translate_text(text: str, target_lang: str = None) -> Dict[str, Any]:
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


async def stream_translate(text: str, target_lang: str, enable_thinking: bool = False) -> AsyncGenerator[str, None]:
    try:
        from core.agents import get_agent_manager
        from core.llm_stream import stream_llm_real
        from api.deps import DATA_DIR

        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a professional translator. Translate the following text into {target_lang}. "
                    "Only output the translation, nothing else. Preserve the original formatting (markdown, line breaks, etc)."
                ),
            },
            {"role": "user", "content": text},
        ]

        async for chunk in stream_llm_real(messages, agent_config, enable_thinking=enable_thinking):
            chunk_type = chunk.get("type", "")
            chunk_content = chunk.get("content", "")
            if chunk_type == "content" and chunk_content:
                yield chunk_content
    except Exception as e:
        logger.error(f"流式翻译失败: {e}")
        yield f"\n\n翻译失败: {e}"


@register_skill(
    skill_id="translate",
    name="翻译",
    description="多语言翻译，自动检测源语言，支持中英日韩法德西等语言互译，支持翻译上传的文档",
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
async def handle_translate(user_input: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
    tool_args = context.get("tool_args", {}) if context else {}
    target_lang = tool_args.get("target_lang") or _detect_target_lang(user_input)

    uploaded_files = _find_uploaded_files(context)
    file_content = ""
    filenames = []
    if uploaded_files:
        for fp in uploaded_files:
            if os.path.exists(fp):
                content = _read_file_content(fp)
                if content:
                    file_content += content + "\n\n"
                    filenames.append(os.path.basename(fp))

    direct_text = _clean_input(user_input)

    if file_content:
        text_to_translate = file_content
        fname_str = "、".join(filenames)
        header = f"🌐 **文档翻译** → {target_lang} — {fname_str}\n\n"
        yield header

        max_content = 50000
        if len(text_to_translate) > max_content:
            text_to_translate = text_to_translate[:max_content]

        enable_thinking = context.get("enable_thinking", False) if context else False
        async for chunk in stream_translate(text_to_translate, target_lang, enable_thinking=enable_thinking):
            yield chunk

    elif direct_text:
        header = f"🌐 **翻译结果** → {target_lang}\n\n**原文：**\n{direct_text}\n\n**译文：**\n"
        yield header

        enable_thinking = context.get("enable_thinking", False) if context else False
        async for chunk in stream_translate(direct_text, target_lang, enable_thinking=enable_thinking):
            yield chunk

    else:
        yield "请提供要翻译的文本，或上传文档后再说「翻译这份文档」。比如：「帮我翻译：今天天气真好」"
