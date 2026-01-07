import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://jensenlyz:1014@localhost:35432/paperagent"
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:39200")
    INDEX_NAME: str = "paper_index"
    
    # MinIO Object Storage
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:39000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "paperagent")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "paperagent123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "paperagent-files")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"  # HTTP by default

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    QWEN_API_KEY: Optional[str] = "sk-cd56dabdcb3f4a55b2117493385b6bfa"
    GLM_API_KEY: Optional[str] = "5c7354f232cd43ddb5de5d49d1f2a12d.7FWkazXBCKVFgRIh"
    TAVILY_API_KEY: Optional[str] = None
    
    # Model Configuration
    # Default model to use if not specified
    DEFAULT_LLM_MODEL: str = "qwen-flash-2025-07-28"
    
    # Embedding Configuration
    # For LiteLLM, we need to prefix the model with the provider
    EMBEDDING_MODEL: str = "openai/text-embedding-v3" # Using Qwen via OpenAI-compatible endpoint

    
    # Provider Base URLs (for OpenAI-compatible endpoints)
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEEPSEEK_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1" # Standard DeepSeek API URL, usually compatible
    
    # LiteLLM Model Aliases/Mappings (optional, but helpful for consistency)
    # Format: "provider/model_name"
    # Examples:
    # "openai/gpt-4o"
    # "deepseek/deepseek-chat" (if using litellm native provider) or "openai/deepseek-chat" (if using openai compatible)
    
    # Skills Configuration
    SKILLS_DIR: str = ".claude/skills"
    SKILLS_AUTO_ACTIVATION: bool = True
    SKILLS_MAX_CONCURRENT: int = 3
    
    class Config:
        env_file = ".env"
        extra = "ignore" # Allow extra fields in .env

settings = Settings()
