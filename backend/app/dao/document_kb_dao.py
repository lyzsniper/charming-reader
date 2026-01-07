"""
文档知识库关联数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from uuid import UUID
from models.sql import DocumentKnowledgeBase


class DocumentKnowledgeBaseDAO:
    """文档知识库关联数据访问对象"""
    
    @staticmethod
    def create(db: Session, document_id: UUID, knowledge_base_id: UUID) -> DocumentKnowledgeBase:
        """创建文档知识库关联记录"""
        association = DocumentKnowledgeBase(
            document_id=document_id,
            knowledge_base_id=knowledge_base_id
        )
        db.add(association)
        db.commit()
        db.refresh(association)
        return association
    
    @staticmethod
    def get_by_doc_and_kb(
        db: Session, 
        document_id: UUID, 
        knowledge_base_id: UUID
    ) -> Optional[DocumentKnowledgeBase]:
        """查询文档和知识库的关联关系"""
        return db.query(DocumentKnowledgeBase).filter(
            and_(
                DocumentKnowledgeBase.document_id == document_id,
                DocumentKnowledgeBase.knowledge_base_id == knowledge_base_id
            )
        ).first()
    
    @staticmethod
    def delete_by_doc_and_kb(
        db: Session, 
        document_id: UUID, 
        knowledge_base_id: UUID
    ) -> int:
        """删除文档和知识库的关联关系"""
        count = db.query(DocumentKnowledgeBase).filter(
            and_(
                DocumentKnowledgeBase.document_id == document_id,
                DocumentKnowledgeBase.knowledge_base_id == knowledge_base_id
            )
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_document(db: Session, document_id: UUID) -> int:
        """删除文档的所有关联关系"""
        count = db.query(DocumentKnowledgeBase).filter(
            DocumentKnowledgeBase.document_id == document_id
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_knowledge_base(db: Session, knowledge_base_id: UUID) -> int:
        """删除知识库的所有关联关系"""
        count = db.query(DocumentKnowledgeBase).filter(
            DocumentKnowledgeBase.knowledge_base_id == knowledge_base_id
        ).delete()
        db.commit()
        return count

