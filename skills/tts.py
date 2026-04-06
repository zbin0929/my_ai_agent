# -*- coding: utf-8 -*-
"""
语音合成技能
============

使用 Edge-TTS（微软 TTS 引擎）将文字转为语音。
支持中英文，多种音色可选。
"""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "zh_female": "zh-CN-XiaoxiaoNeural",
    "zh_male": "zh-CN-YunxiNeural",
    "zh_female_gentle": "zh-CN-XiaoyiNeural",
    "zh_male_narrator": "zh-CN-YunjianNeural",
    "en_female": "en-US-JennyNeural",
    "en_male": "en-US-GuyNeural",
    "ja_female": "ja-JP-NanamiNeural",
    "ko_female": "ko-KR-SunHiNeural",
}


async def _synthesize(text: str, voice: str, output_path: str, rate: str = "+0%") -> bool:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        return False


def text_to_speech(text: str, voice_key: str = "zh_female", rate: str = "+0%") -> Dict[str, Any]:
    try:
        import edge_tts
    except ImportError:
        return {
            "success": False,
            "message": "语音合成需要安装 edge-tts：pip install edge-tts",
        }

    voice = VOICE_MAP.get(voice_key, VOICE_MAP["zh_female"])

    audio_dir = os.path.join(project_root, "data", "tts_output")
    os.makedirs(audio_dir, exist_ok=True)

    safe_name = text[:20].replace(" ", "_").replace("/", "_")
    filename = f"tts_{safe_name}_{int(time.time())}.mp3"
    filepath = os.path.join(audio_dir, filename)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                success = loop.run_in_executor(
                    pool,
                    lambda: asyncio.run(_synthesize(text, voice, filepath, rate)),
                )
                success = asyncio.get_event_loop().run_until_complete(success)
        else:
            success = loop.run_until_complete(_synthesize(text, voice, filepath, rate))
    except RuntimeError:
        success = asyncio.run(_synthesize(text, voice, filepath, rate))

    if success and os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        return {
            "success": True,
            "filepath": filepath,
            "filename": filename,
            "file_size": file_size,
            "voice": voice,
        }
    else:
        return {"success": False, "message": "语音合成失败，请重试"}


def detect_voice_key(text: str) -> str:
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in text)
    has_english = any(c.isascii() and c.isalpha() for c in text)

    if has_chinese and not has_english:
        return "zh_female"
    elif has_english and not has_chinese:
        return "en_female"
    elif has_chinese:
        return "zh_female"
    else:
        return "en_female"


@register_skill(
    skill_id="tts",
    name="语音合成",
    description="将文字转为语音（TTS），支持中英日韩多语言",
    triggers=["语音合成", "朗读", "念出来", "读出来", "转语音", "文字转语音", "TTS",
              "说一遍", "读一遍", "朗读一下", "转为语音", "生成语音"],
    icon="audio",
    examples=[
        "帮我朗读一下这段话：今天天气真好",
        "把这段文字转成语音",
        "语音合成：Hello, welcome to AI assistant",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "text_to_speech",
            "description": "将文字转为语音。当用户要求朗读、转语音、TTS时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要转为语音的文字内容",
                    },
                },
                "required": ["text"],
            },
        },
    },
)
def handle_tts(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    text = user_input
    for trigger in ["语音合成", "朗读", "念出来", "读出来", "转语音", "文字转语音",
                     "TTS", "说一遍", "读一遍", "朗读一下", "转为语音", "生成语音",
                     "帮我", "请帮我", "帮我朗读一下", "这段话", "这段文字",
                     "把", "一下", "：", "："]:
        text = text.replace(trigger, "").strip()

    if not text:
        return {
            "success": False,
            "message": "请告诉我你想把什么文字转成语音？比如：「帮我朗读一下：今天天气真好」",
        }

    if len(text) > 5000:
        text = text[:5000]

    voice_key = detect_voice_key(text)

    voice_names = {
        "zh_female": "晓晓（中文女声）",
        "en_female": "Jenny（英文女声）",
        "ja_female": "Nanami（日文女声）",
        "ko_female": "SunHi（韩文女声）",
    }

    result = text_to_speech(text, voice_key)

    if result["success"]:
        size_kb = result["file_size"] / 1024
        # 安全：不暴露本地路径，只返回文件名和下载URL
        filename = result["filename"]
        download_url = f"/api/files/tts/{filename}"
        msg = (
            f"🔊 **语音已生成！**\n\n"
            f"**文本：** {text[:100]}{'...' if len(text) > 100 else ''}\n\n"
            f"**音色：** {voice_names.get(voice_key, voice_key)}\n\n"
            f"**大小：** {size_kb:.1f} KB\n\n"
            f"[点击下载音频]({download_url})"
        )
        return {"success": True, "message": msg, "audio_url": download_url, "filename": filename}
    else:
        return {"success": False, "message": f"❌ {result['message']}"}
