"""
文档会话关联数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from models.sql import DocumentSession


class DocumentSessionDAO:
    """文档会话关联数据访问对象"""
    
    @staticmethod
    def create(db: Session, document_id: UUID, session_id: str) -> DocumentSession:
        """创建文档会话关联记录"""
        association = DocumentSession(
            document_id=document_id,
            session_id=session_id
        )
        db.add(association)
        db.commit()
        db.refresh(association)
        return association
    
    @staticmethod
    def get_by_doc_and_session(
        db: Session, 
        document_id: UUID, 
        session_id: str
    ) -> Optional[DocumentSession]:
        """查询文档和会话的关联关系"""
        return db.query(DocumentSession).filter(
            and_(
                DocumentSession.document_id == document_id,
                DocumentSession.session_id == session_id
            )
        ).first()
    
    @staticmethod
    def list_by_session(db: Session, session_id: str) -> List[DocumentSession]:
        """查询指定会话下的所有文档关联"""
        return db.query(DocumentSession).filter(
            DocumentSession.session_id == session_id
        ).all()
    
    @staticmethod
    def delete_by_doc_and_session(
        db: Session, 
        document_id: UUID, 
        session_id: str
    ) -> int:
        """删除文档和会话的关联关系"""
        count = db.query(DocumentSession).filter(
            and_(
                DocumentSession.document_id == document_id,
                DocumentSession.session_id == session_id
            )
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_document(db: Session, document_id: UUID) -> int:
        """删除文档的所有会话关联"""
        count = db.query(DocumentSession).filter(
            DocumentSession.document_id == document_id
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_by_session(db: Session, session_id: str) -> int:
        """删除会话的所有文档关联"""
        count = db.query(DocumentSession).filter(
            DocumentSession.session_id == session_id
        ).delete()
        db.commit()
        return count
