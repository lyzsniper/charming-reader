"""
Paper Agent - 使用 Skills 系统的学术研究助手
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from skills.manager import skills_manager

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are an academic research assistant. 
Your goal is to help users find and understand academic papers.
You have access to a scholar search tool to find real papers and a knowledge retriever to look up information in uploaded documents.
Always cite your sources when providing information from papers."""


def create_agent_with_skills() -> Agent:
    """
    创建带有激活技能的 Agent
    
    Returns:
        配置好的 Agent 实例
    """
    # 获取激活的技能内容
    skills_prompt = skills_manager.get_skills_prompt_extension()
    
    # 合并 instruction
    full_instruction = base_instruction
    if skills_prompt:
        full_instruction = base_instruction + "\n\n" + skills_prompt
        logger.info(f"已注入 {len(skills_manager.get_active_skills())} 个激活技能到 Agent")
    
    # 初始化 LiteLLM Model
    model = LiteLlm(
        model="openai/" + settings.DEFAULT_LLM_MODEL,
        api_base=settings.QWEN_BASE_URL,
        api_key=settings.QWEN_API_KEY,
        # 强制指定提供商为openai-compatible，避免模型映射问题
        custom_llm_provider="openai"
    )
    
    # 创建 Agent（每次创建新的以应用最新的 instruction）
    agent = Agent(
        name="academic_researcher",
        model=model,
        tools=[],  # 工具可以在外部配置
        instruction=full_instruction,
        generate_content_config={"temperature": 0.7}
    )
    
    return agent


def create_agent() -> Agent:
    """
    创建基础 Agent（不包含技能）
    
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
        name="academic_researcher",
        model=model,
        tools=[],
        instruction=base_instruction,
        generate_content_config={"temperature": 0.7}
    )
    
    return agent
