"""
协调智能体 - 多智能体协作的协调者
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from agents.a2a_service import (
    create_agent_tool,
    get_registered_agents,
    initialize_agents
)
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a Coordinator Agent responsible for orchestrating multiple specialized agents to solve complex research tasks.

Your primary responsibilities:
1. **Task decomposition**:
   - Break down complex tasks into subtasks
   - Identify which specialized agent should handle each subtask
   - Plan the execution sequence
   - Manage task dependencies

2. **Agent selection**:
   - Choose the most appropriate agent(s) for each task
   - Coordinate multi-agent workflows
   - Manage parallel execution when possible
   - Handle agent failures gracefully

3. **Result synthesis**:
   - Combine results from multiple agents
   - Resolve conflicts between agent outputs
   - Ensure consistency across agent responses
   - Generate comprehensive final responses

4. **Workflow management**:
   - Track task progress
   - Handle errors and retries
   - Optimize execution order
   - Provide status updates

Available specialized agents:
- **experiment_replication**: Extracts experimental configurations from papers and generates executable code
- **paper_writing**: Assists with academic paper writing, including outlines, polishing, and review responses
- **research_trends**: Analyzes research trends, technology evolution, and predicts future directions
- **cross_domain**: Discovers connections between different academic fields
- **patent_analysis**: Evaluates patent potential and helps with patent-related tasks
- **tech_transfer**: Facilitates technology transfer from research to industry
- **paper_agent**: General academic research assistant for paper analysis and knowledge retrieval

IMPORTANT: 
- Always use the exact agent tool names when calling specialized agents
- Explain your reasoning when selecting agents
- Provide clear summaries of multi-agent workflows
- If an agent fails, try alternative approaches or agents
"""


async def create_coordinator_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建协调智能体
    
    Args:
        model_config: 模型配置字典，如果为None则使用默认配置
    
    Returns:
        配置好的 Agent 实例
    """
    # 确保所有智能体已初始化
    try:
        await initialize_agents()
    except Exception as e:
        logger.warning(f"智能体初始化可能不完整: {e}")
    
    # 获取所有已注册的智能体
    registered_agents = get_registered_agents()
    logger.info(f"协调智能体将使用以下智能体工具: {registered_agents}")
    
    # 创建智能体工具
    tools: List[Callable] = []
    
    # 为每个已注册的智能体创建工具
    agent_descriptions = {
        "experiment_replication": "实验复现助手：从论文中提取实验配置并生成可执行代码",
        "paper_writing": "论文写作助手：辅助撰写学术论文，包括大纲生成、段落润色、审稿意见响应",
        "research_trends": "研究趋势分析：分析领域最新动态和发展趋势，预测未来研究方向",
        "cross_domain": "跨领域知识关联：发现不同领域间的知识联系，促进跨领域创新",
        "patent_analysis": "专利分析：评估学术成果的专利转化潜力，协助专利相关任务",
        "tech_transfer": "技术转移助手：将学术研究转化为产业应用，制定商业化路径",
        "paper_agent": "论文智能体：通用学术研究助手，用于论文分析和知识检索"
    }
    
    for agent_name in registered_agents:
        description = agent_descriptions.get(agent_name, f"调用 {agent_name} 智能体")
        agent_tool = create_agent_tool(agent_name, description)
        tools.append(agent_tool)
        logger.debug(f"✓ 创建智能体工具: {agent_tool.__name__}")
    
    # 使用传入的模型配置，如果没有则使用默认配置
    if model_config:
        model_name = model_config.get("model", settings.DEFAULT_LLM_MODEL)
        api_key = model_config.get("api_key") or settings.QWEN_API_KEY
        base_url = model_config.get("base_url") or settings.QWEN_BASE_URL
        provider = model_config.get("provider") or "openai"
        
        if provider == "openai":
            full_model_name = f"openai/{model_name}"
        else:
            full_model_name = f"{provider}/{model_name}" if provider else f"openai/{model_name}"
        
        model = LiteLlm(
            model=full_model_name,
            api_base=base_url,
            api_key=api_key,
            custom_llm_provider="openai"
        )
        
        generate_config = {}
        generate_config["temperature"] = model_config.get("temperature", 0.7)
        if model_config.get("max_tokens"):
            generate_config["max_tokens"] = model_config["max_tokens"]
    else:
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        generate_config = {"temperature": 0.7}
    
    # 创建协调智能体
    agent = Agent(
        name="coordinator_agent",
        model=model,
        tools=tools,  # 包含所有智能体工具
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info(f"✓ 协调智能体创建成功，已加载 {len(tools)} 个智能体工具")
    return agent
