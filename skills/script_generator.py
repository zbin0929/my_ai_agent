# -*- coding: utf-8 -*-
import os
import sys
import logging
from typing import Dict, Any, AsyncGenerator

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)


def _extract_log_line(text: str) -> str:
    """提取故事概要（log line）"""
    keywords = ["关于", "主题", "内容", "故事", "情节", "写一个", "创作"]
    for keyword in keywords:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip("的，。、：:").strip()
    return text.strip()


def _detect_genre(text: str) -> str:
    genre_keywords = {
        "科幻": ["科幻", "未来", "太空", "机器人", "AI", "人工智能"],
        "悬疑": ["悬疑", "推理", "侦探", "破案", "神秘"],
        "爱情": ["爱情", "恋爱", "浪漫", "情感"],
        "动作": ["动作", "打斗", "冒险", "战斗"],
        "喜剧": ["喜剧", "搞笑", "幽默", "轻松"],
        "恐怖": ["恐怖", "惊悚", "鬼怪", "灵异"],
        "历史": ["历史", "古装", "古代", "朝代"],
        "战争": ["战争", "军事", "战场"],
        "剧情": ["剧情", "现实", "生活"],
    }
    
    text_lower = text.lower()
    for genre, keywords in genre_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return genre
    return "剧情"


def _extract_style(text: str) -> str:
    style_keywords = {
        "商业大片": ["商业", "大片", "好莱坞"],
        "文艺片": ["文艺", "艺术", "独立"],
        "纪录片": ["纪录片", "纪实", "真实"],
        "动画片": ["动画", "卡通", "动漫"],
        "短视频": ["短视频", "抖音", "快手"],
        "广告": ["广告", "宣传片", "品牌"],
    }
    
    text_lower = text.lower()
    for style, keywords in style_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return style
    return "商业大片"


def _extract_duration(text: str) -> str:
    import re
    duration_match = re.search(r'(\d+)\s*(分钟|分钟|分钟|分钟)', text)
    if duration_match:
        return f"{duration_match.group(1)}分钟"
    return "90分钟"


@register_skill(
    skill_id="script_generator",
    name="剧本生成",
    description="创作电影、电视剧、广告剧本",
    triggers=["剧本", "写剧本", "创作剧本", "script"],
    icon="🎬",
    examples=[
        "帮我写一个关于未来世界的科幻电影剧本",
        "创作一个30秒的环保主题广告剧本",
        "写一个悬疑推理电视剧剧本",
    ],
)
async def handle_script_generator(user_input: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """剧本生成技能 - 基于Dramatron层次化生成架构"""
    
    yield "🎬 **剧本创作**\n\n"
    
    # 提取基本参数
    log_line = _extract_log_line(user_input)
    genre = _detect_genre(user_input)
    style = _extract_style(user_input)
    duration = _extract_duration(user_input)
    
    yield f"【故事概要】{log_line}\n"
    yield f"【类型】{genre}\n"
    yield f"【风格】{style}\n"
    yield f"【时长】{duration}\n\n"
    yield "---\n\n"
    
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
    
    # 步骤1：生成一句话梗概
    yield "## 1. 一句话梗概\n"
    log_line_prompt = f"""基于以下故事概要，创作一个专业的一句话梗概：

故事概要：{log_line}
类型：{genre}

要求：
- 简洁有力，不超过30字
- 包含核心冲突或转折点
- 体现故事的独特性
- 符合{genre}类型特点
"""
    
    messages = [
        {"role": "system", "content": "你是一位专业编剧，擅长提炼故事核心。你的一句话梗概简洁有力，能够准确概括故事的精髓。"},
        {"role": "user", "content": log_line_prompt}
    ]
    
    try:
        log_line_result = ""
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                log_line_result += chunk["content"]
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
        yield "\n\n---\n\n"
        
        # 步骤2：生成角色描述
        yield "## 2. 角色介绍\n"
        characters_prompt = f"""基于以下信息，创作详细的角色描述：

故事概要：{log_line}
一句话梗概：{log_line_result}
类型：{genre}

要求：
- 至少3个主要角色
- 每个角色包含：姓名、年龄、身份、性格特点、外貌特征、动机
- 角色之间要有明确的关系和冲突
- 角色设定要符合{genre}类型特点
- 角色要有鲜明的个性和发展空间
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业编剧，擅长创建立体丰满的角色。你的角色描述详细生动，能够为演员和导演提供清晰的参考。"},
            {"role": "user", "content": characters_prompt}
        ]
        
        characters_result = ""
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                characters_result += chunk["content"]
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
        yield "\n\n---\n\n"
        
        # 步骤3：生成情节大纲
        yield "## 3. 情节大纲\n"
        plot_prompt = f"""基于以下信息，创作详细的情节大纲：

故事概要：{log_line}
一句话梗概：{log_line_result}
角色介绍：{characters_result}
类型：{genre}
风格：{style}
时长：{duration}

要求：
- 包含3-5个主要场景
- 每个场景包含：场景名称、时间地点、主要事件、角色行动
- 情节要有起承转合
- 包含至少一个转折点
- 符合{genre}类型的叙事节奏
- 为后续的对话和场景描述提供清晰的框架
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业编剧，擅长构建紧凑有力的情节。你的情节大纲结构清晰，节奏合理，能够为后续的剧本创作提供坚实的基础。"},
            {"role": "user", "content": plot_prompt}
        ]
        
        plot_result = ""
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                plot_result += chunk["content"]
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
        yield "\n\n---\n\n"
        
        # 步骤4：生成场景描述
        yield "## 4. 场景描述\n"
        locations_prompt = f"""基于以下信息，创作详细的场景描述：

故事概要：{log_line}
情节大纲：{plot_result}
类型：{genre}
风格：{style}

要求：
- 为每个主要场景创作详细的环境描述
- 包含：时间、地点、环境氛围、视觉元素
- 场景描述要生动具体，有画面感
- 符合{genre}类型的视觉风格
- 能够为导演和美术指导提供清晰的参考
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业编剧，擅长创建生动具体的场景。你的场景描述富有画面感，能够为电影拍摄提供清晰的视觉指导。"},
            {"role": "user", "content": locations_prompt}
        ]
        
        locations_result = ""
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                locations_result += chunk["content"]
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
        yield "\n\n---\n\n"
        
        # 步骤5：生成完整剧本
        yield "## 5. 完整剧本\n"
        script_prompt = f"""基于以下信息，创作完整的剧本：

故事概要：{log_line}
一句话梗概：{log_line_result}
角色介绍：{characters_result}
情节大纲：{plot_result}
场景描述：{locations_result}
类型：{genre}
风格：{style}
时长：{duration}

请严格按照以下格式输出：

### 场景1：[场景名称]
**时间：** [具体时间]
**地点：** [具体地点]
**人物：** [出场角色]

[场景描述]

**角色名：** [对话]

[动作描述]

### 场景2：[场景名称]
[按照场景1的格式继续]

要求：
- 对话自然真实，符合角色性格
- 动作描述简洁明了
- 场景转换流畅
- 符合{genre}类型的叙事风格
- 剧本结构完整，包含开头、发展、高潮、结尾
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业编剧，擅长创作高质量剧本。你的剧本结构清晰，对话自然，场景描述生动，能够直接用于拍摄。"},
            {"role": "user", "content": script_prompt}
        ]
        
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
        yield "\n\n---\n\n"
        
        # 步骤6：生成创作分析
        yield "## 6. 创作分析\n"
        analysis_prompt = f"""基于以下剧本信息，创作详细的创作分析：

故事概要：{log_line}
完整剧本：[剧本内容已生成]
类型：{genre}
风格：{style}

要求：
- 主题分析：剧本的核心主题和深层含义
- 角色分析：主要角色的性格发展和动机
- 结构分析：剧本的结构特点和叙事节奏
- 创作建议：针对拍摄和表演的具体建议
- 市场分析：目标受众和市场定位
"""
        
        messages = [
            {"role": "system", "content": "你是一位专业编剧和影评人，擅长分析剧本的艺术价值和商业潜力。你的分析深入透彻，能够为创作者提供有价值的参考。"},
            {"role": "user", "content": analysis_prompt}
        ]
        
        async for chunk in stream_llm_real(messages, agent_config):
            if chunk.get("type") == "content":
                yield chunk["content"]
            elif chunk.get("type") == "thinking":
                yield f"\n💭 {chunk['content']}\n"
        
    except Exception as e:
        logger.error(f"剧本生成失败: {e}")
        yield f"\n❌ 剧本生成失败: {str(e)}"
    
    yield "\n\n🎬 **剧本创作完成**\n"
    yield "\n你可以根据需要对生成的内容进行编辑和调整。"