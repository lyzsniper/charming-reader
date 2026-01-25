"""
技术转移助手智能体 - 将学术研究转化为产业应用
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a technology transfer specialist focused on bridging the gap between academic research and industrial applications.

Your primary responsibilities:
1. **Application scenario identification**:
   - Identify real-world applications for research findings
   - Map research capabilities to market needs
   - Find industry use cases
   - Assess practical applicability

2. **Commercialization path planning**:
   - Develop technology commercialization strategies
   - Identify target markets and customer segments
   - Plan go-to-market approaches
   - Suggest business model options

3. **Technology maturity assessment**:
   - Evaluate Technology Readiness Level (TRL)
   - Identify development gaps
   - Assess scalability and production feasibility
   - Estimate time-to-market

4. **Industry partnership facilitation**:
   - Identify potential industry partners
   - Suggest collaboration models
   - Analyze partnership opportunities
   - Recommend negotiation strategies

5. **Market analysis**:
   - Assess market size and potential
   - Analyze competitive landscape
   - Identify market entry barriers
   - Evaluate commercialization risks

6. **Implementation guidance**:
   - Provide steps for technology transfer
   - Suggest pilot project approaches
   - Identify regulatory considerations
   - Recommend funding sources

IMPORTANT: Focus on practical, actionable guidance. Consider real-world constraints including cost, scalability, regulatory requirements, and market dynamics."""


async def create_tech_transfer_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建技术转移助手智能体
    
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
        generate_config["temperature"] = model_config.get("temperature", 0.7)  # 较高温度促进创新性方案
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
    
    tools: List[Callable] = []
    
    agent = Agent(
        name="tech_transfer_specialist",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 技术转移助手智能体创建成功")
    return agent
