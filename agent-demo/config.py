"""
简化的配置模块 - 仅用于 Agent Skills 验证
"""
import os
from typing import Optional
from pathlib import Path

# 获取项目根目录（向上两级到 charming-reader）
PROJECT_ROOT = Path(__file__).parent.parent

class Settings:
    """简化的配置类"""
    
    # API Keys（从环境变量或直接设置）
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    QWEN_API_KEY: Optional[str] = os.getenv("QWEN_API_KEY", "sk-cd56dabdcb3f4a55b2117493385b6bfa")
    GLM_API_KEY: Optional[str] = os.getenv("GLM_API_KEY", "5c7354f232cd43ddb5de5d49d1f2a12d.7FWkazXBCKVFgRIh")
    
    # Model Configuration
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "qwen-flash-2025-07-28")
    
    # Provider Base URLs
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEEPSEEK_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Skills Configuration
    # 技能目录：指向项目根目录的 .claude/skills
    SKILLS_DIR: str = str(PROJECT_ROOT / ".claude" / "skills")
    SKILLS_AUTO_ACTIVATION: bool = True
    SKILLS_MAX_CONCURRENT: int = 3

settings = Settings()
