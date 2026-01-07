"""
知识库数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from models.sql import KnowledgeBase


class KnowledgeBaseDAO:
    """知识库数据访问对象"""
    
    @staticmethod
    def create(db: Session, name: str, description: Optional[str] = None) -> KnowledgeBase:
        """创建知识库记录"""
        kb = KnowledgeBase(name=name, description=description)
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return kb
    
    @staticmethod
    def get_by_id(db: Session, kb_id: UUID) -> Optional[KnowledgeBase]:
        """根据ID查询知识库"""
        return db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[KnowledgeBase]:
        """根据名称查询知识库"""
        return db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()
    
    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """查询知识库列表"""
        return db.query(KnowledgeBase).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, kb: KnowledgeBase) -> KnowledgeBase:
        """更新知识库记录"""
        db.commit()
        db.refresh(kb)
        return kb
    
    @staticmethod
    def delete(db: Session, kb: KnowledgeBase) -> None:
        """删除知识库记录"""
        db.delete(kb)
        db.commit()
    
    @staticmethod
    def count(db: Session) -> int:
        """统计知识库总数"""
        return db.query(KnowledgeBase).count()

