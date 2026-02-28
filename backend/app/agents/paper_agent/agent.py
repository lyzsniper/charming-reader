"""
Paper Agent - 使用 Skills 系统的学术研究助手
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from skills.manager import skills_manager
from typing import List, Callable, Optional, Dict, Any
from core.db import SessionLocal
from dao.tool_dao import ToolDAO
from dao.agent_config_dao import AgentConfigDAO
from tools.runtime_tool_factory import build_tool_callable

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are an academic research assistant. 
Your goal is to help users find and understand academic papers.
You have access to a scholar search tool to find real papers and a knowledge retriever to look up information in uploaded documents.
Always cite your sources when providing information from papers.

IMPORTANT: When using tools, you must use the EXACT tool names that are available in your tools list. 
Do not invent tool names. If a tool doesn't exist or fails, gracefully handle the error and try alternative approaches.
Tool failures should not block the conversation - provide helpful feedback and continue with available methods."""


async def create_agent_with_skills(
    model_config: Optional[dict] = None,
    db_session: Optional[Any] = None,
    agent_config_id: Optional[Any] = None
) -> Agent:
    """
    创建带有激活技能的 Agent
    
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
        logger.info(f"已注入 {len(skills_manager.get_active_skills())} 个激活技能到 Agent")
    
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

    # 从数据库加载Tools（用于配置中心创建的工具）
    db_owned = False
    if db_session is None:
        db_session = SessionLocal()
        db_owned = True
    try:
        # 优先使用指定Agent配置的工具，其次默认配置，最后加载所有active工具
        default_agent = AgentConfigDAO.get_default(db_session)
        tool_records = []
        if agent_config_id:
            agent_with_relations = AgentConfigDAO.get_by_id(db_session, agent_config_id, load_relations=True)
            if agent_with_relations:
                tool_records = [rel.tool for rel in agent_with_relations.agent_tools]
            else:
                logger.warning(f"未找到指定Agent配置: {agent_config_id}，将回退到默认配置")
        if not tool_records and default_agent:
            agent_with_relations = AgentConfigDAO.get_by_id(db_session, default_agent.id, load_relations=True)
            if agent_with_relations:
                tool_records = [rel.tool for rel in agent_with_relations.agent_tools]
        if not tool_records:
            tool_records = ToolDAO.list_all(db_session, status="active")

        tool_callables = [build_tool_callable(tool) for tool in tool_records]
        # 去重：避免与MCP工具重复
        tool_map = {tool.__name__: tool for tool in tools}
        for tool_callable in tool_callables:
            if tool_callable.__name__ not in tool_map:
                tool_map[tool_callable.__name__] = tool_callable
        tools = list(tool_map.values())
    except Exception as e:
        logger.error(f"加载数据库工具失败: {type(e).__name__}: {e}")
    finally:
        if db_owned and db_session is not None:
            db_session.close()
    
    # 使用传入的模型配置，如果没有则使用默认配置
    if model_config:
        model_name = model_config.get("model", settings.DEFAULT_LLM_MODEL)
        api_key = model_config.get("api_key") or settings.QWEN_API_KEY
        base_url = model_config.get("base_url") or settings.QWEN_BASE_URL
        provider = model_config.get("provider") or "openai"
        
        # 构建模型名称，如果provider不是openai，可能需要调整格式
        if provider == "openai":
            full_model_name = f"openai/{model_name}"
        else:
            full_model_name = f"{provider}/{model_name}" if provider else f"openai/{model_name}"
        
        logger.info(f"使用模型配置: model={full_model_name}, provider={provider}")
        
        model = LiteLlm(
            model=full_model_name,
            api_base=base_url,
            api_key=api_key,
            custom_llm_provider="openai"  # 对于兼容OpenAI的API，统一使用openai提供商
        )
        
        # 构建生成配置
        generate_config = {}
        if model_config.get("temperature") is not None:
            generate_config["temperature"] = model_config["temperature"]
        else:
            generate_config["temperature"] = 0.7
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
        generate_config = {"temperature": 0.7}
    
    # 创建 Agent（每次创建新的以应用最新的 instruction）
    agent = Agent(
        name="academic_researcher",
        model=model,
        tools=tools,  # 包含GitHub MCP工具（如果激活）
        instruction=full_instruction,
        generate_content_config=generate_config
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
