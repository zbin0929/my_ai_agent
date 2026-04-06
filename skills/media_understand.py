# -*- coding: utf-8 -*-
"""
音视频理解技能
==============

对音频/视频文件进行语音转文字（ASR）和内容分析。
支持 Whisper API 或本地 whisper 模型。
"""

import os
import sys
import re
import logging
import subprocess
import tempfile
from typing import Dict, Any, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
SUPPORTED_VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv"}
MAX_DURATION_SECONDS = 600  # 10分钟限制
_whisper_model = None
_whisper_model_size = None


def _get_config(key: str, default: str = "") -> str:
    from skills import get_skill_config
    val = get_skill_config("media_understand", key)
    return val if val else default


def _extract_audio_from_video(video_path: str) -> Optional[str]:
    """从视频中提取音频轨道"""
    try:
        tmp_f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_path = tmp_f.name
        tmp_f.close()
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", audio_path, "-y"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and os.path.exists(audio_path):
            return audio_path
        logger.warning(f"ffmpeg 提取音频失败: {result.stderr[:200]}")
        return None
    except FileNotFoundError:
        logger.warning("ffmpeg 未安装，无法从视频提取音频")
        return None
    except Exception as e:
        logger.error(f"提取音频异常: {e}")
        return None


def _transcribe_with_api(audio_path: str) -> Dict[str, Any]:
    """使用 API 进行语音转文字"""
    import httpx

    api_key = _get_config("api_key") or os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        return {"success": False, "message": "未配置 ASR API Key"}

    provider = _get_config("provider", "zhipu")

    try:
        if provider == "zhipu":
            # 智谱 ASR API
            url = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"
            headers = {"Authorization": f"Bearer {api_key}"}
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                data = {"model": "whisper-large-v3"}
                resp = httpx.post(url, headers=headers, files=files, data=data, timeout=120)
                resp.raise_for_status()
                result = resp.json()
                text = result.get("text", "")
                return {"success": True, "text": text}
        else:
            # OpenAI 兼容 Whisper API
            base_url = _get_config("base_url", "https://api.openai.com/v1")
            url = f"{base_url}/audio/transcriptions"
            headers = {"Authorization": f"Bearer {api_key}"}
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                data = {"model": "whisper-1"}
                resp = httpx.post(url, headers=headers, files=files, data=data, timeout=120)
                resp.raise_for_status()
                result = resp.json()
                text = result.get("text", "")
                return {"success": True, "text": text}
    except Exception as e:
        logger.error(f"ASR API 调用失败: {e}")
        return {"success": False, "message": f"语音识别失败: {e}"}


def _transcribe_local(audio_path: str) -> Dict[str, Any]:
    """使用本地 whisper 进行转写（模型缓存避免重复加载）"""
    global _whisper_model, _whisper_model_size
    try:
        import whisper
        model_size = _get_config("model_size", "base")
        if _whisper_model is None or _whisper_model_size != model_size:
            _whisper_model = whisper.load_model(model_size)
            _whisper_model_size = model_size
        result = _whisper_model.transcribe(audio_path, language="zh")
        text = result.get("text", "")
        return {"success": True, "text": text}
    except ImportError:
        return {"success": False, "message": "本地 whisper 未安装（pip install openai-whisper）"}
    except Exception as e:
        logger.error(f"本地转写失败: {e}")
        return {"success": False, "message": f"本地转写失败: {e}"}


def transcribe_media(filepath: str) -> Dict[str, Any]:
    """转写音视频文件"""
    if not os.path.exists(filepath):
        return {"success": False, "message": f"文件不存在: {filepath}"}

    ext = os.path.splitext(filepath)[1].lower()
    audio_path = filepath
    temp_audio = None

    # 如果是视频，先提取音频
    if ext in SUPPORTED_VIDEO_EXT:
        temp_audio = _extract_audio_from_video(filepath)
        if not temp_audio:
            return {"success": False, "message": "无法从视频中提取音频，请确认已安装 ffmpeg"}
        audio_path = temp_audio

    try:
        # 优先使用 API
        result = _transcribe_with_api(audio_path)
        if not result["success"]:
            # 降级到本地
            result = _transcribe_local(audio_path)
        return result
    finally:
        if temp_audio and os.path.exists(temp_audio):
            try:
                os.unlink(temp_audio)
            except Exception:
                pass


def analyze_transcript(text: str, question: str = "") -> Dict[str, Any]:
    """使用 LLM 分析转写文本"""
    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        prompt = (
            "你是一个音视频内容分析助手。以下是音视频的转写文本。\n"
            "请进行以下分析：\n"
            "1. **内容摘要**（一段话概括）\n"
            "2. **关键信息**（重要的人名、时间、数字、结论等）\n"
            "3. **话题分段**（按主题划分段落）\n"
        )
        if question:
            prompt += f"\n用户特别想了解：{question}\n"

        response = llm.call(messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"转写文本：\n{text[:12000]}"},
        ])

        return {"success": True, "analysis": str(response).strip()}
    except Exception as e:
        logger.error(f"内容分析失败: {e}")
        return {"success": False, "message": f"分析失败: {e}"}


@register_skill(
    skill_id="media_understand",
    name="音视频理解",
    description="对音频/视频文件进行语音转文字和内容分析",
    triggers=["语音识别", "音频转文字", "视频转文字", "听一下", "转写",
              "音频分析", "视频分析", "ASR", "transcribe", "听写"],
    icon="video",
    examples=[
        "帮我把这段音频转成文字",
        "分析一下这个视频说了什么",
        "帮我转写这段录音",
    ],
    config_schema=[
        {
            "key": "provider",
            "label": "ASR 服务商",
            "description": "选择语音识别服务",
            "type": "select",
            "required": False,
            "default": "zhipu",
            "options": [
                {"value": "zhipu", "label": "智谱 AI (Whisper)"},
                {"value": "openai", "label": "OpenAI (Whisper)"},
                {"value": "local", "label": "本地 Whisper"},
            ],
        },
        {
            "key": "api_key",
            "label": "API Key",
            "description": "ASR 服务的 API Key",
            "type": "password",
            "required": False,
            "env_hint": "ZHIPU_API_KEY",
        },
        {
            "key": "base_url",
            "label": "API 地址",
            "description": "OpenAI 兼容 API 的 base_url",
            "type": "text",
            "required": False,
        },
        {
            "key": "model_size",
            "label": "本地模型大小",
            "description": "本地 Whisper 模型大小（仅本地模式）",
            "type": "select",
            "required": False,
            "default": "base",
            "options": [
                {"value": "tiny", "label": "tiny（最快）"},
                {"value": "base", "label": "base（推荐）"},
                {"value": "small", "label": "small"},
                {"value": "medium", "label": "medium"},
                {"value": "large", "label": "large（最准）"},
            ],
        },
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "transcribe_media",
            "description": "对音频/视频文件进行语音转文字和内容分析。用户上传音视频后要求转写、分析内容时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "用户的分析需求描述",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
)
def handle_media_understand(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    # 查找上传的音视频文件
    files = []
    if context:
        for key in ("files", "file_paths"):
            if context.get(key):
                files.extend(context[key])

    media_files = []
    for f in files:
        if os.path.exists(f):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_AUDIO_EXT or ext in SUPPORTED_VIDEO_EXT:
                media_files.append(f)

    if not media_files:
        return {
            "success": False,
            "message": "请先上传音频或视频文件，然后再要求转写/分析。\n支持格式：MP3、WAV、M4A、MP4、AVI、MKV 等",
        }

    filepath = media_files[0]
    fname = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    media_type = "视频" if ext in SUPPORTED_VIDEO_EXT else "音频"

    # 转写
    result = transcribe_media(filepath)
    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    text = result["text"]
    if not text:
        return {"success": False, "message": "语音识别未返回结果，可能音频质量不佳或格式不支持"}

    # 分析
    question = user_input
    for trigger in ["语音识别", "音频转文字", "视频转文字", "转写", "分析", "帮我"]:
        question = question.replace(trigger, "").strip()

    analysis_result = analyze_transcript(text, question)

    parts = [f"🎬 **{media_type}理解** — {fname}\n"]
    parts.append(f"### 转写文本\n\n{text[:3000]}{'...' if len(text) > 3000 else ''}\n")

    if analysis_result["success"]:
        parts.append(f"### 内容分析\n\n{analysis_result['analysis']}")

    parts.append(f"\n---\n*转写字数: {len(text)}*")

    return {"success": True, "message": "\n".join(parts)}
