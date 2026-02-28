"""
Skill 数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from models.sql import Skill, SkillResource


class SkillDAO:
    """Skill数据访问对象"""
    
    @staticmethod
    def create(db: Session, skill_data: Dict[str, Any]) -> Skill:
        """创建Skill记录"""
        skill = Skill(**skill_data)
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return skill
    
    @staticmethod
    def get_by_id(db: Session, skill_id: UUID) -> Optional[Skill]:
        """根据ID查询Skill"""
        return db.query(Skill).filter(Skill.id == skill_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Skill]:
        """根据名称查询Skill"""
        return db.query(Skill).filter(Skill.name == name).first()
    
    @staticmethod
    def list_all(
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Skill]:
        """查询Skill列表，支持过滤"""
        query = db.query(Skill)
        
        if category:
            query = query.filter(Skill.category == category)
        if status:
            query = query.filter(Skill.status == status)
        if source_type:
            query = query.filter(Skill.source_type == source_type)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def search(
        db: Session,
        query_text: str,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Skill]:
        """搜索Skill（按名称、描述、标签）"""
        query = db.query(Skill)
        
        # 构建搜索条件
        search_filter = or_(
            Skill.name.ilike(f"%{query_text}%"),
            Skill.display_name.ilike(f"%{query_text}%"),
            Skill.description.ilike(f"%{query_text}%")
        )
        query = query.filter(search_filter)
        
        if category:
            query = query.filter(Skill.category == category)
        if status:
            query = query.filter(Skill.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, skill_id: UUID, updates: Dict[str, Any]) -> Optional[Skill]:
        """更新Skill记录"""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return None
        
        for key, value in updates.items():
            setattr(skill, key, value)
        
        db.commit()
        db.refresh(skill)
        return skill
    
    @staticmethod
    def delete(db: Session, skill_id: UUID) -> bool:
        """删除Skill记录"""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return False
        
        db.delete(skill)
        db.commit()
        return True
    
    @staticmethod
    def increment_activation_count(db: Session, skill_id: UUID) -> bool:
        """增加激活计数"""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return False
        
        skill.activation_count += 1
        db.commit()
        return True
    
    @staticmethod
    def increment_download_count(db: Session, skill_id: UUID) -> bool:
        """增加下载计数"""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return False
        
        skill.download_count += 1
        db.commit()
        return True
    
    @staticmethod
    def get_popular_skills(db: Session, limit: int = 10) -> List[Skill]:
        """获取热门Skill（按激活次数排序）"""
        return db.query(Skill).filter(
            Skill.status == 'active'
        ).order_by(
            Skill.activation_count.desc()
        ).limit(limit).all()
    
    @staticmethod
    def count(
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> int:
        """统计Skill数量"""
        query = db.query(func.count(Skill.id))
        
        if query_text:
            search_filter = or_(
                Skill.name.ilike(f"%{query_text}%"),
                Skill.display_name.ilike(f"%{query_text}%"),
                Skill.description.ilike(f"%{query_text}%")
            )
            query = query.filter(search_filter)
        if category:
            query = query.filter(Skill.category == category)
        if status:
            query = query.filter(Skill.status == status)
        
        return query.scalar()


class SkillResourceDAO:
    """SkillResource数据访问对象"""
    
    @staticmethod
    def create(db: Session, resource_data: Dict[str, Any]) -> SkillResource:
        """创建SkillResource记录"""
        resource = SkillResource(**resource_data)
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource
    
    @staticmethod
    def get_by_id(db: Session, resource_id: UUID) -> Optional[SkillResource]:
        """根据ID查询SkillResource"""
        return db.query(SkillResource).filter(SkillResource.id == resource_id).first()
    
    @staticmethod
    def list_by_skill(db: Session, skill_id: UUID) -> List[SkillResource]:
        """查询指定Skill的所有资源"""
        return db.query(SkillResource).filter(
            SkillResource.skill_id == skill_id
        ).all()
    
    @staticmethod
    def delete(db: Session, resource_id: UUID) -> bool:
        """删除SkillResource记录"""
        resource = db.query(SkillResource).filter(SkillResource.id == resource_id).first()
        if not resource:
            return False
        
        db.delete(resource)
        db.commit()
        return True
    
    @staticmethod
    def delete_by_skill(db: Session, skill_id: UUID) -> int:
        """删除指定Skill的所有资源"""
        count = db.query(SkillResource).filter(
            SkillResource.skill_id == skill_id
        ).delete()
        db.commit()
        return count
