"""
模型配置业务逻辑层（Service）
处理业务逻辑，调用 DAO 层进行数据操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from dao import ModelConfigurationDAO
from models.sql import ModelConfiguration
from models.schemas import ModelConfigurationCreate, ModelConfigurationUpdate
from core.config import settings
from core.logger import LoggerFactory
import os

# 创建日志记录器
logger = LoggerFactory.get_service_logger(__name__)


class ModelConfigurationService:
    """模型配置业务逻辑服务"""
    
    @staticmethod
    def create_model_configuration(
        db: Session, 
        config_create: ModelConfigurationCreate
    ) -> ModelConfiguration:
        """
        创建模型配置
        业务逻辑：检查名称是否重复、处理激活状态
        """
        # 检查名称是否已存在
        existing = ModelConfigurationDAO.get_by_name(db, config_create.name)
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"模型配置名称 '{config_create.name}' 已存在"
            )
        
        # 如果设置为激活，先将其他模型设为非激活
        if config_create.is_active:
            ModelConfigurationDAO.deactivate_all(db)
        
        return ModelConfigurationDAO.create(
            db=db,
            name=config_create.name,
            model_name=config_create.model_name,
            api_key=config_create.api_key,
            base_url=config_create.base_url,
            provider=config_create.provider,
            description=config_create.description,
            is_active=config_create.is_active,
            temperature=config_create.temperature,
            max_tokens=config_create.max_tokens,
            top_p=config_create.top_p,
            frequency_penalty=config_create.frequency_penalty,
            presence_penalty=config_create.presence_penalty
        )
    
    @staticmethod
    def get_model_configuration_by_id(db: Session, config_id: UUID) -> ModelConfiguration:
        """
        根据ID获取模型配置
        业务逻辑：不存在时抛出异常
        """
        config = ModelConfigurationDAO.get_by_id(db, config_id)
        if not config:
            raise HTTPException(
                status_code=404, 
                detail=f"模型配置 ID={config_id} 不存在"
            )
        return config
    
    @staticmethod
    def get_active_model_configuration(db: Session) -> Optional[ModelConfiguration]:
        """获取当前激活的模型配置"""
        return ModelConfigurationDAO.get_active(db)
    
    @staticmethod
    def list_model_configurations(
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelConfiguration]:
        """获取模型配置列表"""
        return ModelConfigurationDAO.list_all(db, skip, limit)
    
    @staticmethod
    def update_model_configuration(
        db: Session, 
        config_id: UUID, 
        config_update: ModelConfigurationUpdate
    ) -> ModelConfiguration:
        """
        更新模型配置
        业务逻辑：检查名称是否重复、处理激活状态
        """
        # 获取配置
        config = ModelConfigurationService.get_model_configuration_by_id(db, config_id)
        
        # 如果要更新名称，检查新名称是否重复
        if config_update.name is not None and config_update.name != config.name:
            existing = ModelConfigurationDAO.get_by_name(db, config_update.name)
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"模型配置名称 '{config_update.name}' 已存在"
                )
            config.name = config_update.name
        
        # 更新其他字段
        if config_update.model_name is not None:
            config.model_name = config_update.model_name
        if config_update.api_key is not None:
            config.api_key = config_update.api_key
        if config_update.base_url is not None:
            config.base_url = config_update.base_url
        if config_update.provider is not None:
            config.provider = config_update.provider
        if config_update.description is not None:
            config.description = config_update.description
        # 更新模型参数
        if config_update.temperature is not None:
            config.temperature = config_update.temperature
        if config_update.max_tokens is not None:
            config.max_tokens = config_update.max_tokens
        if config_update.top_p is not None:
            config.top_p = config_update.top_p
        if config_update.frequency_penalty is not None:
            config.frequency_penalty = config_update.frequency_penalty
        if config_update.presence_penalty is not None:
            config.presence_penalty = config_update.presence_penalty
        
        # 处理激活状态
        if config_update.is_active is not None:
            if config_update.is_active and not config.is_active:
                # 要激活当前配置，先将其他配置设为非激活
                ModelConfigurationDAO.deactivate_all(db)
            config.is_active = config_update.is_active
        
        return ModelConfigurationDAO.update(db, config)
    
    @staticmethod
    def delete_model_configuration(db: Session, config_id: UUID) -> None:
        """
        删除模型配置
        业务逻辑：检查是否存在、防止删除激活的配置
        """
        config = ModelConfigurationService.get_model_configuration_by_id(db, config_id)
        
        if config.is_active:
            raise HTTPException(
                status_code=400, 
                detail="不能删除当前激活的模型配置，请先激活其他配置"
            )
        
        ModelConfigurationDAO.delete(db, config)
    
    @staticmethod
    def activate_model(db: Session, config_id: UUID) -> ModelConfiguration:
        """
        激活指定的模型配置
        业务逻辑：将其他配置设为非激活，激活指定配置
        """
        logger.info(f"开始激活模型配置: id={config_id}")
        config = ModelConfigurationService.get_model_configuration_by_id(db, config_id)
        
        # 将所有配置设为非激活
        ModelConfigurationDAO.deactivate_all(db)
        
        # 激活指定配置
        config.is_active = True
        result = ModelConfigurationDAO.update(db, config)
        logger.info(f"成功激活模型配置: id={config_id}, model={config.model_name}")
        return result
    
    @staticmethod
    def get_model_for_agent(db: Session, model_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        获取 Agent 使用的模型配置
        业务逻辑：优先使用指定的model_id，其次使用用户配置的激活模型，最后使用默认配置
        
        Args:
            model_id: 指定的模型配置ID，如果为None则使用激活的模型
        """
        # 优先使用指定的model_id
        if model_id:
            user_config = ModelConfigurationDAO.get_by_id(db, model_id)
            if user_config:
                logger.info(f"使用指定的模型配置: id={model_id}, model={user_config.model_name}")
                return {
                    "model": user_config.model_name,
                    "api_key": user_config.api_key,
                    "base_url": user_config.base_url,
                    "provider": user_config.provider,
                    "temperature": user_config.temperature,
                    "max_tokens": user_config.max_tokens,
                    "top_p": user_config.top_p,
                    "frequency_penalty": user_config.frequency_penalty,
                    "presence_penalty": user_config.presence_penalty,
                    "source": "user",
                    "description": user_config.description
                }
            else:
                logger.warning(f"指定的模型配置不存在: id={model_id}，使用默认配置")
        
        # 尝试获取用户配置的激活模型
        user_config = ModelConfigurationService.get_active_model_configuration(db)
        
        if user_config and user_config.model_name:
            logger.info(f"使用用户配置的模型: {user_config.model_name}")
            return {
                "model": user_config.model_name,
                "api_key": user_config.api_key,
                "base_url": user_config.base_url,
                "provider": user_config.provider,
                "temperature": user_config.temperature,
                "max_tokens": user_config.max_tokens,
                "top_p": user_config.top_p,
                "frequency_penalty": user_config.frequency_penalty,
                "presence_penalty": user_config.presence_penalty,
                "source": "user",
                "description": user_config.description
            }
        
        # 使用默认配置
        logger.info(f"使用系统默认模型: {settings.DEFAULT_LLM_MODEL}")
        return {
            "model": settings.DEFAULT_LLM_MODEL,
            "api_key": settings.QWEN_API_KEY or settings.GLM_API_KEY or settings.OPENAI_API_KEY,
            "base_url": settings.QWEN_BASE_URL,
            "provider": "openai",
            "temperature": 0.7,
            "max_tokens": None,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
            "source": "default",
            "description": "系统默认模型"
        }
    
    @staticmethod
    def get_current_model_info(db: Session) -> Dict[str, Any]:
        """
        获取当前使用的模型信息（用于前端显示）
        业务逻辑：返回当前生效的模型配置摘要信息
        """
        config = ModelConfigurationService.get_model_for_agent(db)
        return {
            "model_name": config["model"],
            "source": config["source"],
            "description": config.get("description", "")
        }

