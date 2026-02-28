"""
Agent Config 数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from models.sql import (
    AgentTemplate, AgentConfig, AgentSkill, AgentTool,
    SkillActivationLog, AgentExecutionLog
)


class AgentTemplateDAO:
    """AgentTemplate数据访问对象"""
    
    @staticmethod
    def create(db: Session, template_data: Dict[str, Any]) -> AgentTemplate:
        """创建AgentTemplate记录"""
        template = AgentTemplate(**template_data)
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    
    @staticmethod
    def get_by_id(db: Session, template_id: UUID) -> Optional[AgentTemplate]:
        """根据ID查询AgentTemplate"""
        return db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[AgentTemplate]:
        """根据名称查询AgentTemplate"""
        return db.query(AgentTemplate).filter(AgentTemplate.name == name).first()
    
    @staticmethod
    def list_all(
        db: Session,
        category: Optional[str] = None,
        is_builtin: Optional[bool] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentTemplate]:
        """查询AgentTemplate列表"""
        query = db.query(AgentTemplate)
        
        if category:
            query = query.filter(AgentTemplate.category == category)
        if is_builtin is not None:
            query = query.filter(AgentTemplate.is_builtin == is_builtin)
        if is_public is not None:
            query = query.filter(AgentTemplate.is_public == is_public)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, template_id: UUID, updates: Dict[str, Any]) -> Optional[AgentTemplate]:
        """更新AgentTemplate记录"""
        template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()
        if not template:
            return None
        
        for key, value in updates.items():
            setattr(template, key, value)
        
        db.commit()
        db.refresh(template)
        return template
    
    @staticmethod
    def delete(db: Session, template_id: UUID) -> bool:
        """删除AgentTemplate记录"""
        template = db.query(AgentTemplate).filter(AgentTemplate.id == template_id).first()
        if not template:
            return False
        
        db.delete(template)
        db.commit()
        return True


class AgentConfigDAO:
    """AgentConfig数据访问对象"""
    
    @staticmethod
    def create(db: Session, config_data: Dict[str, Any]) -> AgentConfig:
        """创建AgentConfig记录"""
        config = AgentConfig(**config_data)
        db.add(config)
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def get_by_id(db: Session, config_id: UUID, load_relations: bool = False) -> Optional[AgentConfig]:
        """根据ID查询AgentConfig"""
        query = db.query(AgentConfig)
        
        if load_relations:
            query = query.options(
                joinedload(AgentConfig.template),
                joinedload(AgentConfig.model_config),
                joinedload(AgentConfig.agent_skills).joinedload(AgentSkill.skill),
                joinedload(AgentConfig.agent_tools).joinedload(AgentTool.tool)
            )
        
        return query.filter(AgentConfig.id == config_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[AgentConfig]:
        """根据名称查询AgentConfig"""
        return db.query(AgentConfig).filter(AgentConfig.name == name).first()
    
    @staticmethod
    def get_default(db: Session, user_id: Optional[str] = None) -> Optional[AgentConfig]:
        """获取默认AgentConfig"""
        query = db.query(AgentConfig).filter(AgentConfig.is_default == True)
        
        if user_id:
            query = query.filter(AgentConfig.user_id == user_id)
        
        return query.first()
    
    @staticmethod
    def list_all(
        db: Session,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentConfig]:
        """查询AgentConfig列表"""
        query = db.query(AgentConfig)
        
        if user_id:
            query = query.filter(AgentConfig.user_id == user_id)
        if status:
            query = query.filter(AgentConfig.status == status)
        
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def search(
        db: Session,
        query_text: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentConfig]:
        """搜索AgentConfig（按名称、显示名称）"""
        query = db.query(AgentConfig)
        search_filter = or_(
            AgentConfig.name.ilike(f"%{query_text}%"),
            AgentConfig.display_name.ilike(f"%{query_text}%")
        )
        query = query.filter(search_filter)

        if user_id:
            query = query.filter(AgentConfig.user_id == user_id)
        if status:
            query = query.filter(AgentConfig.status == status)

        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, config_id: UUID, updates: Dict[str, Any]) -> Optional[AgentConfig]:
        """更新AgentConfig记录"""
        config = db.query(AgentConfig).filter(AgentConfig.id == config_id).first()
        if not config:
            return None
        
        for key, value in updates.items():
            setattr(config, key, value)
        
        db.commit()
        db.refresh(config)
        return config
    
    @staticmethod
    def delete(db: Session, config_id: UUID) -> bool:
        """删除AgentConfig记录"""
        config = db.query(AgentConfig).filter(AgentConfig.id == config_id).first()
        if not config:
            return False
        
        db.delete(config)
        db.commit()
        return True
    
    @staticmethod
    def set_default(db: Session, config_id: UUID, user_id: Optional[str] = None) -> bool:
        """设置为默认Agent配置"""
        # 先取消其他默认配置
        query = db.query(AgentConfig).filter(AgentConfig.is_default == True)
        if user_id:
            query = query.filter(AgentConfig.user_id == user_id)
        
        for config in query.all():
            config.is_default = False
        
        # 设置当前配置为默认
        config = db.query(AgentConfig).filter(AgentConfig.id == config_id).first()
        if not config:
            return False
        
        config.is_default = True
        db.commit()
        return True
    
    @staticmethod
    def count(
        db: Session,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> int:
        """统计AgentConfig数量"""
        query = db.query(func.count(AgentConfig.id))
        
        if query_text:
            search_filter = or_(
                AgentConfig.name.ilike(f"%{query_text}%"),
                AgentConfig.display_name.ilike(f"%{query_text}%")
            )
            query = query.filter(search_filter)
        if user_id:
            query = query.filter(AgentConfig.user_id == user_id)
        if status:
            query = query.filter(AgentConfig.status == status)
        
        return query.scalar()


class AgentSkillDAO:
    """AgentSkill关联数据访问对象"""
    
    @staticmethod
    def create(db: Session, association_data: Dict[str, Any]) -> AgentSkill:
        """创建AgentSkill关联"""
        association = AgentSkill(**association_data)
        db.add(association)
        db.commit()
        db.refresh(association)
        return association
    
    @staticmethod
    def get(db: Session, agent_config_id: UUID, skill_id: UUID) -> Optional[AgentSkill]:
        """查询AgentSkill关联"""
        return db.query(AgentSkill).filter(
            and_(
                AgentSkill.agent_config_id == agent_config_id,
                AgentSkill.skill_id == skill_id
            )
        ).first()
    
    @staticmethod
    def list_by_agent(db: Session, agent_config_id: UUID) -> List[AgentSkill]:
        """查询Agent的所有Skill关联"""
        return db.query(AgentSkill).filter(
            AgentSkill.agent_config_id == agent_config_id
        ).order_by(AgentSkill.priority.desc()).all()
    
    @staticmethod
    def list_by_skill(db: Session, skill_id: UUID) -> List[AgentSkill]:
        """查询使用某Skill的所有Agent"""
        return db.query(AgentSkill).filter(
            AgentSkill.skill_id == skill_id
        ).all()
    
    @staticmethod
    def delete(db: Session, agent_config_id: UUID, skill_id: UUID) -> bool:
        """删除AgentSkill关联"""
        association = db.query(AgentSkill).filter(
            and_(
                AgentSkill.agent_config_id == agent_config_id,
                AgentSkill.skill_id == skill_id
            )
        ).first()
        
        if not association:
            return False
        
        db.delete(association)
        db.commit()
        return True
    
    @staticmethod
    def delete_by_agent(db: Session, agent_config_id: UUID) -> int:
        """删除Agent的所有Skill关联"""
        count = db.query(AgentSkill).filter(
            AgentSkill.agent_config_id == agent_config_id
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_skill(db: Session, skill_id: UUID) -> int:
        """删除Skill的所有Agent关联"""
        count = db.query(AgentSkill).filter(
            AgentSkill.skill_id == skill_id
        ).delete()
        db.commit()
        return count


class AgentToolDAO:
    """AgentTool关联数据访问对象"""
    
    @staticmethod
    def create(db: Session, association_data: Dict[str, Any]) -> AgentTool:
        """创建AgentTool关联"""
        association = AgentTool(**association_data)
        db.add(association)
        db.commit()
        db.refresh(association)
        return association
    
    @staticmethod
    def get(db: Session, agent_config_id: UUID, tool_id: UUID) -> Optional[AgentTool]:
        """查询AgentTool关联"""
        return db.query(AgentTool).filter(
            and_(
                AgentTool.agent_config_id == agent_config_id,
                AgentTool.tool_id == tool_id
            )
        ).first()
    
    @staticmethod
    def list_by_agent(db: Session, agent_config_id: UUID) -> List[AgentTool]:
        """查询Agent的所有Tool关联"""
        return db.query(AgentTool).filter(
            AgentTool.agent_config_id == agent_config_id
        ).all()
    
    @staticmethod
    def list_by_tool(db: Session, tool_id: UUID) -> List[AgentTool]:
        """查询使用某Tool的所有Agent"""
        return db.query(AgentTool).filter(
            AgentTool.tool_id == tool_id
        ).all()
    
    @staticmethod
    def delete(db: Session, agent_config_id: UUID, tool_id: UUID) -> bool:
        """删除AgentTool关联"""
        association = db.query(AgentTool).filter(
            and_(
                AgentTool.agent_config_id == agent_config_id,
                AgentTool.tool_id == tool_id
            )
        ).first()
        
        if not association:
            return False
        
        db.delete(association)
        db.commit()
        return True
    
    @staticmethod
    def delete_by_agent(db: Session, agent_config_id: UUID) -> int:
        """删除Agent的所有Tool关联"""
        count = db.query(AgentTool).filter(
            AgentTool.agent_config_id == agent_config_id
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_tool(db: Session, tool_id: UUID) -> int:
        """删除Tool的所有Agent关联"""
        count = db.query(AgentTool).filter(
            AgentTool.tool_id == tool_id
        ).delete()
        db.commit()
        return count
