# -*- coding: utf-8 -*-
import os
import sys
import logging
from typing import Dict, Any, AsyncGenerator

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _extract_original_prompt(text: str) -> str:
    keywords = ["提示词", "prompt", "优化", "改进"]
    for keyword in keywords:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip("的，。、：:")
    return text


def _detect_target_model(text: str) -> str:
    model_keywords = {
        "GPT-4": ["gpt-4", "GPT-4", "GPT4"],
        "GPT-3.5": ["gpt-3.5", "GPT-3.5", "GPT3.5"],
        "Claude": ["claude", "Claude"],
        "DeepSeek": ["deepseek", "DeepSeek"],
        "Midjourney": ["midjourney", "Midjourney", "MJ"],
        "Stable Diffusion": ["stable diffusion", "Stable Diffusion", "SD"],
    }
    
    text_lower = text.lower()
    for model, keywords in model_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return model
    return "通用"


def _detect_use_case(text: str) -> str:
    use_cases = {
        "文本生成": ["写作", "创作", "生成文本", "文章", "故事"],
        "图像生成": ["画图", "生成图片", "图像", "插画", "设计"],
        "代码生成": ["编程", "代码", "开发", "写代码"],
        "数据分析": ["分析", "数据", "统计", "报告"],
        "翻译": ["翻译", "translate"],
        "问答": ["问答", "问题", "解答"],
    }
    
    text_lower = text.lower()
    for use_case, keywords in use_cases.items():
        if any(keyword in text_lower for keyword in keywords):
            return use_case
    return "通用"


@register_skill(
    skill_id="prompt_optimizer",
    name="提示词优化",
    description="优化和改进AI提示词，提升生成效果",
    triggers=["提示词", "优化提示词", "改进prompt", "prompt优化"],
    icon="✨",
    examples=[
        "优化这个提示词：写一个关于环保的故事",
        "帮我改进这个Midjourney提示词",
        "将这个简单的提示词优化为专业的",
    ],
)
async def handle_prompt_optimizer(user_input: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """提示词优化技能"""
    
    yield "✨ **提示词优化**\n\n"
    
    original_prompt = _extract_original_prompt(user_input)
    target_model = _detect_target_model(user_input)
    use_case = _detect_use_case(user_input)
    
    yield f"【原始提示词】\n{original_prompt}\n\n"
    yield f"【目标模型】{target_model}\n"
    yield f"【使用场景】{use_case}\n\n"
    yield "---\n\n"
    
    prompt = f"""你是一位专业的提示词工程师，请优化以下提示词：

【原始提示词】
{original_prompt}

【目标模型】{target_model}
【使用场景】{use_case}

请严格按照以下格式输出：

## 优化分析
- **原始提示词问题：** [分析原始提示词的不足之处]
- **优化方向：** [说明优化的重点和策略]
- **预期改进：** [说明优化后预期达到的效果]

## 优化后的提示词

### 基础版本
[提供一个简洁明了的优化版本]

### 专业版本
[提供一个结构化、详细的优化版本，包含角色设定、任务描述、输出要求等]

### 高级版本
[提供一个包含思维链、示例、约束条件的高级版本]

## 使用建议
- **适用场景：** [说明优化后提示词的最佳使用场景]
- **参数建议：** [如适用，提供temperature、max_tokens等参数建议]
- **注意事项：** [使用时需要注意的事项]

## 变体建议
提供2-3个针对不同需求的变体版本：

### 变体1：[变体名称]
[变体提示词]

### 变体2：[变体名称]
[变体提示词]
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
            temperature=0.7,
            enable_thinking=True
        )
    
    messages = [
        {"role": "system", "content": "你是一位专业的提示词工程师，精通各种AI模型的提示词优化技巧。你能够准确识别提示词的问题，并提供结构化、专业化的优化方案。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
    except Exception as e:
        logger.error(f"提示词优化失败: {e}")
        yield f"\n❌ 提示词优化失败: {str(e)}"