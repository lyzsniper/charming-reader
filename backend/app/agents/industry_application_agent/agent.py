"""
产业应用智能体 - 使用 Skills 系统的产业应用助手
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from skills.manager import skills_manager
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are an industry application assistant specializing in technology trend analysis and competitive research.
Your goal is to help businesses and industry professionals understand the practical applications of academic research and analyze competitive landscapes.

Core capabilities:
1. Technology trend analysis: Identify emerging technologies and their market potential
2. Competitive intelligence: Analyze research activities of competitors and industry players
3. Market research: Translate academic findings into market insights
4. Technology adoption: Assess readiness and pathways for technology adoption
5. Risk assessment: Identify technological risks and opportunities
6. Strategic planning: Support strategic decision-making based on research trends
7. Patent analysis: Analyze patent landscapes and intellectual property trends
8. Commercialization potential: Evaluate research findings for commercial applications

When conducting industry analysis:
- Focus on practical applications and real-world impact
- Consider market size and growth potential
- Analyze competitive advantages and disadvantages
- Identify implementation challenges and solutions
- Assess regulatory and ethical considerations
- Evaluate ROI and business case implications
- Provide actionable insights for decision-making

IMPORTANT: When using tools, you must use the EXACT tool names that are available in your tools list.
Do not invent tool names. If a tool doesn't exist or fails, gracefully handle the error and try alternative approaches.
Tool failures should not block the conversation - provide helpful feedback and continue with available methods."""


async def create_agent_with_skills(model_config: Optional[dict] = None) -> Agent:
    """
    创建带有激活技能的产业应用智能体

    Args:
        model_config: 模型配置字典，包含 model, api_key, base_url, provider 等字段
                     如果为None，则使用默认配置

    Returns:
        配置好的 Agent 实例
    """
    # 获取激活的技能内容
    skills_prompt = skills_manager.get_skills_prompt_extension()

    # 合并 instruction
    full_instruction = base_instruction
    if skills_prompt:
        full_instruction = base_instruction + "\n\n" + skills_prompt
        logger.info(f"已注入 {len(skills_manager.get_active_skills())} 个激活技能到产业应用智能体")

    # 检查是否有GitHub skill激活
    tools: List[Callable] = []
    active_skills = skills_manager.get_active_skills()
    has_github_skill = any(skill.get('name') == "github-integration" for skill in active_skills)

    if has_github_skill:
        logger.info("检测到GitHub skill激活，正在加载GitHub MCP工具...")
        try:
            from tools.mcp_tool_adapter import get_github_mcp_tools
            github_tools = await get_github_mcp_tools()
            tools.extend(github_tools)
            logger.info(f"✓ 已加载 {len(github_tools)} 个GitHub MCP工具")
        except Exception as e:
            logger.error(f"加载GitHub MCP工具失败: {type(e).__name__}: {e}")

    # 使用传入的模型配置，如果没有则使用默认配置
    if model_config:
        model_name = model_config.get("model", settings.DEFAULT_LLM_MODEL)
        api_key = model_config.get("api_key") or settings.QWEN_API_KEY
        base_url = model_config.get("base_url") or settings.QWEN_BASE_URL
        provider = model_config.get("provider") or "openai"

        # 构建模型名称
        if provider == "openai":
            full_model_name = f"openai/{model_name}"
        else:
            full_model_name = f"{provider}/{model_name}" if provider else f"openai/{model_name}"

        logger.info(f"使用模型配置: model={full_model_name}, provider={provider}")

        model = LiteLlm(
            model=full_model_name,
            api_base=base_url,
            api_key=api_key,
            custom_llm_provider="openai"
        )

        # 构建生成配置
        generate_config = {}
        if model_config.get("temperature") is not None:
            generate_config["temperature"] = model_config["temperature"]
        else:
            generate_config["temperature"] = 0.5  # 产业分析需要逻辑性和准确性
        if model_config.get("max_tokens") is not None:
            generate_config["max_tokens"] = model_config["max_tokens"]
        if model_config.get("top_p") is not None:
            generate_config["top_p"] = model_config["top_p"]
        if model_config.get("frequency_penalty") is not None:
            generate_config["frequency_penalty"] = model_config["frequency_penalty"]
        if model_config.get("presence_penalty") is not None:
            generate_config["presence_penalty"] = model_config["presence_penalty"]
    else:
        # 使用默认配置
        logger.info(f"使用默认模型配置: {settings.DEFAULT_LLM_MODEL}")
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        generate_config = {"temperature": 0.5}

    # 创建 Agent
    agent = Agent(
        name="industry_application_assistant",
        model=model,
        tools=tools,
        instruction=full_instruction,
        generate_content_config=generate_config
    )

    return agent


def create_agent() -> Agent:
    """
    创建基础产业应用智能体（不包含技能）

    Returns:
        Agent 实例
    """
    # 初始化 LiteLLM Model
    model = LiteLlm(
        model="openai/" + settings.DEFAULT_LLM_MODEL,
        api_base=settings.QWEN_BASE_URL,
        api_key=settings.QWEN_API_KEY,
        custom_llm_provider="openai"
    )

    agent = Agent(
        name="industry_application_assistant",
        model=model,
        tools=[],
        instruction=base_instruction,
        generate_content_config={"temperature": 0.5}
    )

    return agent