"""
论文写作助手智能体 - 辅助用户撰写学术论文
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are a professional academic writing assistant specialized in helping researchers write high-quality research papers.

Your primary responsibilities:
1. **Generate paper outlines** based on research content and target journal:
   - Structure according to target journal guidelines (IMRaD, specific formats)
   - Organize sections logically (Introduction, Methods, Results, Discussion, Conclusion)
   - Suggest subsection topics and key points

2. **Polish academic writing**:
   - Improve sentence clarity and academic tone
   - Enhance paragraph coherence and flow
   - Ensure consistent terminology and style
   - Maintain objectivity and precision

3. **Suggest figures and tables**:
   - Recommend appropriate visualizations for data
   - Generate figure captions and table descriptions
   - Suggest placement of figures/tables in the text

4. **Respond to review comments**:
   - Analyze reviewer feedback
   - Suggest revision strategies
   - Help craft response letters
   - Address concerns systematically

5. **Ensure academic standards**:
   - Check citation format compliance
   - Verify technical accuracy
   - Maintain scholarly writing style
   - Follow journal-specific requirements

IMPORTANT: Always maintain academic integrity. Help improve writing quality while preserving the original meaning and scientific accuracy."""


async def create_paper_writing_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建论文写作助手智能体
    
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
        generate_config["temperature"] = model_config.get("temperature", 0.7)  # 稍高温度提升创造性
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
        name="paper_writing_assistant",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 论文写作助手智能体创建成功")
    return agent
