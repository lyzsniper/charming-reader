"""
文档数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
from models.sql import Document, DocumentKnowledgeBase


class DocumentDAO:
    """文档数据访问对象"""
    
    @staticmethod
    def create(
        db: Session,
        original_filename: str,
        storage_object_name: str,
        file_size: int,
        content_type: str = "application/pdf",
        is_processed: bool = False
    ) -> Document:
        """创建文档记录"""
        doc = Document(
            original_filename=original_filename,
            storage_object_name=storage_object_name,
            file_size=file_size,
            content_type=content_type,
            is_processed=is_processed
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    
    @staticmethod
    def get_by_id(db: Session, doc_id: UUID) -> Optional[Document]:
        """根据ID查询文档"""
        return db.query(Document).filter(Document.id == doc_id).first()
    
    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Document]:
        """查询文档列表"""
        return db.query(Document).offset(skip).limit(limit).all()
    
    @staticmethod
    def list_by_knowledge_base(db: Session, kb_id: UUID) -> List[Document]:
        """
        查询指定知识库下的文档
        兼容迁移前的数据库结构（如果 is_temporary 列不存在）
        """
        try:
            # 尝试正常查询
            return db.query(Document).join(DocumentKnowledgeBase).filter(
                DocumentKnowledgeBase.knowledge_base_id == kb_id
            ).all()
        except Exception as e:
            # 如果查询失败（可能是 is_temporary 列不存在），使用原始 SQL 查询
            # 只选择存在的列，排除 is_temporary
            sql = text("""
                SELECT d.id, d.original_filename, d.storage_object_name, 
                       d.storage_path, d.file_download_url, d.file_size, 
                       d.content_type, d.upload_date, d.content_markdown, 
                       d.is_processed
                FROM documents d
                JOIN document_knowledge_base dkb ON d.id = dkb.document_id
                WHERE dkb.knowledge_base_id = :kb_id
            """)
            result = db.execute(sql, {"kb_id": str(kb_id)})
            # 手动构建 Document 对象
            documents = []
            for row in result:
                doc = Document(
                    id=row.id,
                    original_filename=row.original_filename,
                    storage_object_name=row.storage_object_name,
                    storage_path=row.storage_path,
                    file_download_url=row.file_download_url,
                    file_size=row.file_size,
                    content_type=row.content_type,
                    upload_date=row.upload_date,
                    content_markdown=row.content_markdown,
                    is_processed=row.is_processed
                )
                documents.append(doc)
            return documents
    
    @staticmethod
    def update(db: Session, doc: Document) -> Document:
        """更新文档记录"""
        db.commit()
        db.refresh(doc)
        return doc
    
    @staticmethod
    def delete(db: Session, doc: Document) -> None:
        """删除文档记录"""
        db.delete(doc)
        db.commit()
    
    @staticmethod
    def count(db: Session) -> int:
        """统计文档总数"""
        return db.query(Document).count()

