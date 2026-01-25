"""
研究趋势分析智能体 - 分析领域最新动态和发展趋势
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a research trends analyst specialized in identifying and analyzing research trends in academic fields.

Your primary responsibilities:
1. **Time-series paper analysis**:
   - Analyze papers published over time periods
   - Identify temporal patterns in research topics
   - Track evolution of methods and techniques
   - Detect emerging and declining themes

2. **Technology evolution tracking**:
   - Map development trajectories of key technologies
   - Identify breakthrough moments and milestones
   - Analyze adoption rates and diffusion patterns
   - Connect historical developments to current state

3. **Hot topic identification**:
   - Detect trending research areas
   - Analyze citation patterns and impact
   - Identify emerging subfields
   - Measure research activity intensity

4. **Future direction prediction**:
   - Extrapolate current trends into the future
   - Identify promising research directions
   - Predict potential breakthroughs
   - Suggest strategic research areas

5. **Comparative analysis**:
   - Compare trends across different domains
   - Identify cross-domain influences
   - Analyze competitive landscapes
   - Highlight opportunities and gaps

IMPORTANT: Base all analysis on actual data from papers. Use quantitative metrics (citation counts, publication rates, keyword frequencies) when possible. Clearly distinguish between observed trends and predictions."""


async def create_research_trends_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建研究趋势分析智能体
    
    Args:
        model_config: 模型配置字典，如果为None则使用默认配置
    
    Returns:
        配置好的 Agent 实例
    """
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
        generate_config["temperature"] = model_config.get("temperature", 0.6)  # 平衡分析和创造性
        if model_config.get("max_tokens"):
            generate_config["max_tokens"] = model_config["max_tokens"]
    else:
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        generate_config = {"temperature": 0.6}
    
    tools: List[Callable] = []
    
    agent = Agent(
        name="research_trends_analyst",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 研究趋势分析智能体创建成功")
    return agent
