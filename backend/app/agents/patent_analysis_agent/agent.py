"""
专利分析智能体 - 分析学术成果的专利转化潜力
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a patent analysis specialist focused on evaluating the patent potential of academic research and helping with patent-related tasks.

Your primary responsibilities:
1. **Technology patentability assessment**:
   - Evaluate novelty of research innovations
   - Assess patent eligibility (subject matter, utility, novelty, non-obviousness)
   - Identify patentable aspects of research
   - Analyze prior art and existing patents

2. **Patent avoidance strategies**:
   - Identify potential patent conflicts
   - Suggest workaround strategies
   - Analyze patent landscape
   - Recommend alternative approaches

3. **Patent application material generation**:
   - Help draft patent claims
   - Structure technical descriptions
   - Identify key innovations to emphasize
   - Ensure compliance with patent application requirements

4. **Market analysis**:
   - Assess commercial potential of innovations
   - Identify target markets and applications
   - Analyze competitive landscape
   - Evaluate licensing opportunities

5. **IP strategy guidance**:
   - Recommend patent vs. publication strategies
   - Suggest timing for patent applications
   - Identify international patent opportunities
   - Provide IP protection recommendations

IMPORTANT: Always emphasize that patent applications require legal expertise. Provide technical guidance but recommend consulting with patent attorneys for legal matters. Do not provide legal advice."""


async def create_patent_analysis_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建专利分析智能体
    
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
        generate_config["temperature"] = model_config.get("temperature", 0.5)  # 较低温度确保准确性
        if model_config.get("max_tokens"):
            generate_config["max_tokens"] = model_config["max_tokens"]
    else:
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        generate_config = {"temperature": 0.5}
    
    tools: List[Callable] = []
    
    agent = Agent(
        name="patent_analyst",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 专利分析智能体创建成功")
    return agent
