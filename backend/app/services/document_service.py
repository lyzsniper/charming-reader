"""
文档业务逻辑层（Service）
处理业务逻辑，调用 DAO 层进行数据操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from dao import DocumentDAO, DocumentKnowledgeBaseDAO, KnowledgeBaseDAO
from models.sql import Document
from models.schemas import DocumentCreate, DocumentUpdate
from core.logger import LoggerFactory

# 创建日志记录器
logger = LoggerFactory.get_service_logger(__name__)


class DocumentService:
    """文档业务逻辑服务"""
    
    @staticmethod
    def create_document(
        db: Session,
        original_filename: str,
        storage_object_name: str,
        file_size: int,
        content_type: str,
        knowledge_base_ids: List[UUID] = [],
        storage_path: Optional[str] = None,
        file_download_url: Optional[str] = None
    ) -> Document:
        """
        创建文档
        业务逻辑：验证知识库ID是否有效，创建文档并关联知识库
        """
        logger.info(f"开始创建文档: filename={original_filename}, kb_ids={knowledge_base_ids}")
        
        # 验证知识库ID是否都存在
        if knowledge_base_ids:
            for kb_id in knowledge_base_ids:
                kb = KnowledgeBaseDAO.get_by_id(db, kb_id)
                if not kb:
                    logger.warning(f"知识库不存在: id={kb_id}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"知识库 ID={kb_id} 不存在"
                    )
        
        # 创建文档
        doc = DocumentDAO.create(
            db,
            original_filename=original_filename,
            storage_object_name=storage_object_name,
            file_size=file_size,
            content_type=content_type,
            is_processed=False
        )
        
        # 更新新增字段（如果DAO不支持直接传参，则手动更新）
        if storage_path:
            doc.storage_path = storage_path
        if file_download_url:
            doc.file_download_url = file_download_url
        if storage_path or file_download_url:
            db.commit()
            db.refresh(doc)

        logger.info(f"文档创建成功: id={doc.id}, filename={doc.original_filename}")
        
        # 关联知识库
        if knowledge_base_ids:
            for kb_id in knowledge_base_ids:
                DocumentKnowledgeBaseDAO.create(db, doc.id, kb_id)
                logger.debug(f"文档关联知识库: doc_id={doc.id}, kb_id={kb_id}")
        
        # 重新加载文档以包含关联关系
        return DocumentDAO.get_by_id(db, doc.id)
    
    @staticmethod
    def get_document_by_id(db: Session, doc_id: UUID) -> Document:
        """
        根据ID获取文档
        业务逻辑：不存在时抛出异常
        """
        doc = DocumentDAO.get_by_id(db, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"文档 ID={doc_id} 不存在")
        return doc
    
    @staticmethod
    def list_documents(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        knowledge_base_id: Optional[UUID] = None
    ) -> List[Document]:
        """
        获取文档列表
        业务逻辑：支持按知识库筛选
        """
        if knowledge_base_id:
            # 验证知识库是否存在
            kb = KnowledgeBaseDAO.get_by_id(db, knowledge_base_id)
            if not kb:
                raise HTTPException(
                    status_code=404, 
                    detail=f"知识库 ID={knowledge_base_id} 不存在"
                )
            return DocumentDAO.list_by_knowledge_base(db, knowledge_base_id)
        
        return DocumentDAO.list_all(db, skip, limit)
    
    @staticmethod
    def update_document(db: Session, doc_id: UUID, doc_update: DocumentUpdate) -> Document:
        """
        更新文档
        业务逻辑：更新基本信息和知识库关联
        """
        # 获取文档
        doc = DocumentService.get_document_by_id(db, doc_id)
        
        # 更新文件名
        if doc_update.filename is not None:
            doc.filename = doc_update.filename
        
        # 更新知识库关联
        if doc_update.knowledge_base_ids is not None:
            # 验证知识库ID是否都存在
            for kb_id in doc_update.knowledge_base_ids:
                kb = KnowledgeBaseDAO.get_by_id(db, kb_id)
                if not kb:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"知识库 ID={kb_id} 不存在"
                    )
            
            # 删除现有关联
            DocumentKnowledgeBaseDAO.delete_by_document(db, doc_id)
            
            # 创建新关联
            for kb_id in doc_update.knowledge_base_ids:
                DocumentKnowledgeBaseDAO.create(db, doc_id, kb_id)
        
        # 更新文档
        doc = DocumentDAO.update(db, doc)
        
        # 重新加载以包含最新的关联关系
        return DocumentDAO.get_by_id(db, doc_id)
    
    @staticmethod
    def delete_document(db: Session, doc_id: UUID) -> None:
        """
        删除文档
        业务逻辑：检查是否存在、级联删除关联关系
        """
        doc = DocumentService.get_document_by_id(db, doc_id)
        DocumentDAO.delete(db, doc)
    
    @staticmethod
    def add_to_knowledge_base(db: Session, doc_id: UUID, kb_id: UUID) -> None:
        """
        将文档添加到知识库
        业务逻辑：验证文档和知识库是否存在、是否已关联
        """
        # 验证文档是否存在
        DocumentService.get_document_by_id(db, doc_id)
        
        # 验证知识库是否存在
        kb = KnowledgeBaseDAO.get_by_id(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 ID={kb_id} 不存在")
        
        # 检查是否已关联
        existing = DocumentKnowledgeBaseDAO.get_by_doc_and_kb(db, doc_id, kb_id)
        if existing:
            raise HTTPException(status_code=400, detail="文档已在该知识库中")
        
        # 创建关联
        DocumentKnowledgeBaseDAO.create(db, doc_id, kb_id)
    
    @staticmethod
    def remove_from_knowledge_base(db: Session, doc_id: UUID, kb_id: UUID) -> None:
        """
        从知识库移除文档
        业务逻辑：验证关联是否存在
        """
        # 验证文档是否存在
        DocumentService.get_document_by_id(db, doc_id)
        
        # 验证知识库是否存在
        kb = KnowledgeBaseDAO.get_by_id(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail=f"知识库 ID={kb_id} 不存在")
        
        # 删除关联
        count = DocumentKnowledgeBaseDAO.delete_by_doc_and_kb(db, doc_id, kb_id)
        if count == 0:
            raise HTTPException(status_code=404, detail="文档不在该知识库中")

