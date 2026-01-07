"""
知识库业务逻辑层（Service）
处理业务逻辑，调用 DAO 层进行数据操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from dao import KnowledgeBaseDAO
from models.sql import KnowledgeBase
from models.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from core.logger import LoggerFactory

# 创建日志记录器
logger = LoggerFactory.get_service_logger(__name__)


class KnowledgeBaseService:
    """知识库业务逻辑服务"""
    
    @staticmethod
    def create_knowledge_base(db: Session, kb_create: KnowledgeBaseCreate) -> KnowledgeBase:
        """
        创建知识库
        业务逻辑：检查名称是否重复
        """
        logger.info(f"开始创建知识库: name={kb_create.name}")
        
        # 检查名称是否已存在
        existing = KnowledgeBaseDAO.get_by_name(db, kb_create.name)
        if existing:
            logger.warning(f"知识库名称已存在: {kb_create.name}")
            raise HTTPException(status_code=400, detail=f"知识库名称 '{kb_create.name}' 已存在")
        
        kb = KnowledgeBaseDAO.create(db, kb_create.name, kb_create.description)
        logger.info(f"成功创建知识库: id={kb.id}, name={kb.name}")
        return kb
    
    @staticmethod
    def get_knowledge_base_by_id(db: Session, kb_id: UUID) -> KnowledgeBase:
        """
        根据ID获取知识库
        业务逻辑：不存在时抛出异常
        """
        logger.debug(f"查询知识库: id={kb_id}")
        kb = KnowledgeBaseDAO.get_by_id(db, kb_id)
        if not kb:
            logger.warning(f"知识库不存在: id={kb_id}")
            raise HTTPException(status_code=404, detail=f"知识库 ID={kb_id} 不存在")
        logger.debug(f"找到知识库: id={kb.id}, name={kb.name}")
        return kb
    
    @staticmethod
    def list_knowledge_bases(db: Session, skip: int = 0, limit: int = 100) -> List[KnowledgeBase]:
        """获取知识库列表"""
        return KnowledgeBaseDAO.list_all(db, skip, limit)
    
    @staticmethod
    def update_knowledge_base(
        db: Session, 
        kb_id: UUID, 
        kb_update: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        """
        更新知识库
        业务逻辑：检查是否存在、名称是否重复
        """
        # 获取知识库
        kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
        
        # 如果要更新名称，检查新名称是否重复
        if kb_update.name is not None and kb_update.name != kb.name:
            existing = KnowledgeBaseDAO.get_by_name(db, kb_update.name)
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"知识库名称 '{kb_update.name}' 已存在"
                )
            kb.name = kb_update.name
        
        # 更新描述
        if kb_update.description is not None:
            kb.description = kb_update.description
        
        return KnowledgeBaseDAO.update(db, kb)
    
    @staticmethod
    def delete_knowledge_base(db: Session, kb_id: UUID) -> None:
        """
        删除知识库
        业务逻辑：检查是否存在、级联删除关联关系
        """
        logger.info(f"开始删除知识库: id={kb_id}")
        kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
        KnowledgeBaseDAO.delete(db, kb)
        logger.info(f"成功删除知识库: id={kb_id}, name={kb.name}")
    
    @staticmethod
    def get_document_count(kb: KnowledgeBase) -> int:
        """获取知识库中的文档数量"""
        return len(kb.documents) if kb.documents else 0

