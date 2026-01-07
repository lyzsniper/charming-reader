"""
模型配置数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from models.sql import ModelConfiguration


class ModelConfigurationDAO:
    """模型配置数据访问对象"""
    
    @staticmethod
    def create(
        db: Session,
        name: str,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = False
    ) -> ModelConfiguration:
        """创建模型配置记录"""
        config = ModelConfiguration(
            name=name,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            description=description,
            is_active=is_active
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def get_by_id(db: Session, config_id: UUID) -> Optional[ModelConfiguration]:
        """根据ID查询模型配置"""
        return db.query(ModelConfiguration).filter(
            ModelConfiguration.id == config_id
        ).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[ModelConfiguration]:
        """根据名称查询模型配置"""
        return db.query(ModelConfiguration).filter(
            ModelConfiguration.name == name
        ).first()
    
    @staticmethod
    def get_active(db: Session) -> Optional[ModelConfiguration]:
        """查询当前激活的模型配置"""
        return db.query(ModelConfiguration).filter(
            ModelConfiguration.is_active == True
        ).first()
    
    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[ModelConfiguration]:
        """查询模型配置列表"""
        return db.query(ModelConfiguration).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, config: ModelConfiguration) -> ModelConfiguration:
        """更新模型配置记录"""
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def delete(db: Session, config: ModelConfiguration) -> None:
        """删除模型配置记录"""
        db.delete(config)
        db.commit()
    
    @staticmethod
    def deactivate_all(db: Session) -> None:
        """将所有模型配置设为非激活状态"""
        db.query(ModelConfiguration).update({"is_active": False})
        db.commit()
    
    @staticmethod
    def count(db: Session) -> int:
        """统计模型配置总数"""
        return db.query(ModelConfiguration).count()

