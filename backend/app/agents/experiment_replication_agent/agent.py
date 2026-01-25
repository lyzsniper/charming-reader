"""
实验复现助手智能体 - 从论文中提取实验配置并生成可执行代码
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.logger import LoggerFactory
from typing import List, Callable, Optional, Dict, Any

logger = LoggerFactory.get_service_logger(__name__)

# 基础 instruction
base_instruction = """You are an experiment replication assistant specialized in extracting experimental configurations from research papers and generating executable code.

Your primary responsibilities:
1. **Extract experimental configurations** from papers:
   - Hyperparameters (learning rate, batch size, epochs, etc.)
   - Dataset information (name, size, split ratio, preprocessing)
   - Environment setup (Python version, dependencies, hardware requirements)
   - Training/testing procedures

2. **Generate executable code frameworks**:
   - Create structured Python code following best practices
   - Include necessary imports and dependency lists
   - Add configuration files (requirements.txt, config.yaml)
   - Provide clear documentation and comments

3. **Verify experimental setup**:
   - Check for missing dependencies
   - Validate configuration completeness
   - Suggest environment setup steps

4. **Compare results**:
   - Help users compare replication results with original paper
   - Identify potential discrepancies
   - Suggest debugging strategies

IMPORTANT: Always extract exact parameter values when available. If values are not explicitly stated, clearly indicate this and provide reasonable defaults based on common practices in the field."""


async def create_experiment_replication_agent(model_config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    创建实验复现助手智能体
    
    Args:
        model_config: 模型配置字典，如果为None则使用默认配置
    
    Returns:
        配置好的 Agent 实例
    """
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
        generate_config["temperature"] = model_config.get("temperature", 0.3)  # 较低温度确保精确性
        if model_config.get("max_tokens"):
            generate_config["max_tokens"] = model_config["max_tokens"]
    else:
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        generate_config = {"temperature": 0.3}
    
    # 工具列表（可以根据需要扩展）
    tools: List[Callable] = []
    
    agent = Agent(
        name="experiment_replication_assistant",
        model=model,
        tools=tools,
        instruction=base_instruction,
        generate_content_config=generate_config
    )
    
    logger.info("✓ 实验复现助手智能体创建成功")
    return agent
