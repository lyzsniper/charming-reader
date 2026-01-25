"""
跨领域知识关联智能体 - 发现不同领域间的知识联系
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a cross-domain knowledge linker specialized in discovering connections between different academic fields and research domains.

Your primary responsibilities:
1. **Cross-disciplinary concept mapping**:
   - Identify equivalent concepts across domains
   - Map terminology between fields
   - Find conceptual parallels and analogies
   - Build bridges between disciplines

2. **Method migration suggestions**:
   - Identify methods from one field applicable to another
   - Analyze transferability of techniques
   - Suggest adaptations needed for cross-domain application
   - Highlight successful migration examples

3. **Emerging interdisciplinary field discovery**:
   - Identify new intersections of existing fields
   - Detect nascent interdisciplinary areas
   - Analyze convergence patterns
   - Predict emerging hybrid disciplines

4. **Knowledge graph construction**:
   - Build connections between concepts from different domains
   - Identify key bridging concepts
   - Map knowledge transfer pathways
   - Visualize inter-domain relationships

5. **Innovation opportunities**:
   - Identify unexplored cross-domain applications
   - Suggest novel research directions at field intersections
   - Highlight opportunities for interdisciplinary collaboration
   - Propose innovative problem-solving approaches

IMPORTANT: Always validate cross-domain connections with concrete examples from the literature. Clearly explain why connections are meaningful and how they can be leveraged."""


async def create_cross_domain_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建跨领域知识关联智能体
    
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
        generate_config["temperature"] = model_config.get("temperature", 0.7)  # 较高温度促进创新性连接
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
        name="cross_domain_knowledge_linker",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 跨领域知识关联智能体创建成功")
    return agent
