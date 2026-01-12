"""
配置验证模块
在应用启动时验证所有必需的配置项
"""
from typing import List, Tuple
from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


def validate_config() -> Tuple[bool, List[str]]:
    """
    验证应用配置
    
    Returns:
        (is_valid, errors): 是否有效和错误列表
    """
    errors: List[str] = []
    
    # 验证数据库配置
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL 未配置")
    elif not settings.DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
        errors.append("DATABASE_URL 格式不正确，应为 postgresql://...")
    
    # 验证 Elasticsearch 配置
    if not settings.ELASTICSEARCH_URL:
        errors.append("ELASTICSEARCH_URL 未配置")
    elif not settings.ELASTICSEARCH_URL.startswith(("http://", "https://")):
        errors.append("ELASTICSEARCH_URL 格式不正确，应为 http://... 或 https://...")
    
    if not settings.INDEX_NAME:
        errors.append("INDEX_NAME 未配置")
    
    # 验证 MinIO 配置
    if not settings.MINIO_ENDPOINT:
        errors.append("MINIO_ENDPOINT 未配置")
    
    if not settings.MINIO_ACCESS_KEY:
        errors.append("MINIO_ACCESS_KEY 未配置")
    
    if not settings.MINIO_SECRET_KEY:
        errors.append("MINIO_SECRET_KEY 未配置")
    
    if not settings.MINIO_BUCKET:
        errors.append("MINIO_BUCKET 未配置")
    
    # 验证模型配置（至少需要一个 API Key）
    has_api_key = any([
        settings.OPENAI_API_KEY,
        settings.DEEPSEEK_API_KEY,
        settings.QWEN_API_KEY,
        settings.GLM_API_KEY,
    ])
    
    if not has_api_key:
        errors.append("至少需要配置一个模型的 API Key (OPENAI_API_KEY, DEEPSEEK_API_KEY, QWEN_API_KEY, GLM_API_KEY)")
    
    # 验证默认模型配置
    if not settings.DEFAULT_LLM_MODEL:
        errors.append("DEFAULT_LLM_MODEL 未配置")
    
    if not settings.EMBEDDING_MODEL:
        errors.append("EMBEDDING_MODEL 未配置")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("✓ 配置验证通过")
    else:
        logger.error(f"✗ 配置验证失败，发现 {len(errors)} 个错误:")
        for error in errors:
            logger.error(f"  - {error}")
    
    return is_valid, errors


def check_config_on_startup() -> None:
    """
    在应用启动时检查配置
    如果配置无效，记录警告但不阻止启动（允许在运行时修复）
    """
    is_valid, errors = validate_config()
    
    if not is_valid:
        logger.warning("=" * 60)
        logger.warning("⚠ 配置验证失败！")
        logger.warning("应用将继续启动，但某些功能可能无法正常工作。")
        logger.warning("=" * 60)
        logger.warning("请检查 .env 文件并修复以下配置问题：")
        for error in errors:
            logger.warning(f"  - {error}")
        logger.warning("=" * 60)
    else:
        logger.info("✓ 所有配置验证通过")
