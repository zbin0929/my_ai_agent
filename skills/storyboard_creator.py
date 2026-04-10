# -*- coding: utf-8 -*-
import os
import sys
import logging
from typing import Dict, Any, AsyncGenerator

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _extract_script_content(text: str) -> str:
    keywords = ["剧本", "script", "内容", "故事"]
    for keyword in keywords:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip("的，。、：:")
    return text


def _detect_format(text: str) -> str:
    if "表格" in text or "table" in text.lower():
        return "表格格式"
    elif "详细" in text or "detail" in text.lower():
        return "详细描述"
    return "标准格式"


def _extract_shot_count(text: str) -> int:
    import re
    match = re.search(r'(\d+)\s*(个|镜头|shot)', text)
    if match:
        return int(match.group(1))
    return 8


@register_skill(
    skill_id="storyboard_creator",
    name="分镜创作",
    description="根据剧本或创意生成分镜描述",
    triggers=["分镜", "生成分镜", "分镜设计", "storyboard"],
    icon="🎨",
    examples=[
        "根据这个剧本生成分镜：[剧本内容]",
        "帮我设计一个广告的分镜，需要8个镜头",
        "为这个场景创建详细的分镜描述",
    ],
)
async def handle_storyboard_creator(user_input: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """分镜创作技能"""
    
    yield "🎨 **分镜创作**\n\n"
    
    script_content = _extract_script_content(user_input)
    format_type = _detect_format(user_input)
    shot_count = _extract_shot_count(user_input)
    
    yield f"【格式】{format_type}\n"
    yield f"【镜头数量】{shot_count}个\n\n"
    yield "---\n\n"
    
    prompt = f"""你是一位专业分镜师，请根据以下内容创作详细的分镜设计：

【剧本/创意内容】
{script_content}

【格式要求】{format_type}
【镜头数量】{shot_count}个

请严格按照以下格式输出：

## 分镜总览
- 总镜头数：{shot_count}
- 预估时长：[根据镜头数估算]
- 风格基调：[根据内容判断]

## 详细分镜

### 镜头1：[镜头名称]
- **景别：** [远景/全景/中景/近景/特写]
- **角度：** [平视/俯视/仰视/侧视]
- **运镜：** [固定/推/拉/摇/移/跟]
- **时长：** [具体秒数]
- **画面描述：** [详细的画面内容描述]
- **音效/音乐：** [背景音乐或音效说明]
- **备注：** [拍摄注意事项]

### 镜头2：[镜头名称]
[按照镜头1的格式继续]

### 镜头3：[镜头名称]
[按照镜头1的格式继续]

[继续到第{shot_count}个镜头]

## 拍摄建议
- **灯光：** [灯光设置建议]
- **色彩：** [色调和色彩搭配建议]
- **道具：** [所需道具清单]
- **场地：** [拍摄场地要求]
"""

    from core.llm_stream import stream_llm_real
    from core.agents import get_agent_manager
    from api.deps import DATA_DIR
    
    manager = get_agent_manager(DATA_DIR)
    agent_config = manager.get_agent("creative_expert")
    
    if not agent_config:
        logger.warning("未找到creative_expert代理，使用默认配置")
        from core.agents import AgentConfig
        agent_config = AgentConfig(
            id="creative_expert",
            name="创作专家",
            model_provider="deepseek",
            model_id="deepseek-chat",
            temperature=0.8,
            enable_thinking=True
        )
    
    messages = [
        {"role": "system", "content": "你是一位专业分镜师，擅长将剧本转化为视觉化的分镜设计。你的分镜描述清晰、专业，具有可操作性。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
    except Exception as e:
        logger.error(f"分镜创作失败: {e}")
        yield f"\n❌ 分镜创作失败: {str(e)}"