"""
向量化服务（业务层）
负责文档的向量化处理 + 业务逻辑（知识库关联、数据库存储）
底层调用 rag.ingestion 的纯粹 RAG 方法
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from models.sql import Document, DocumentChunk
from dao import DocumentDAO, KnowledgeBaseDAO
from core.config import settings
from core.logger import LoggerFactory

# 引用 rag 目录的底层方法
from rag.ingestion import (
    convert_pdf_to_markdown,
    chunk_text,
    generate_embeddings,
    create_text_nodes,
    store_nodes_to_es,
    get_vector_store
)

logger = LoggerFactory.get_service_logger(__name__)


class VectorizationService:
    """向量化服务（业务层）- 调用 rag 底层方法 + 业务逻辑"""
    
    @staticmethod
    def store_to_postgres(
        db: Session,
        document_id: UUID,
        chunks: List[str],
        embeddings: List[List[float]]
    ):
        """
        存储分块和向量到 PostgreSQL（业务逻辑）
        """
        logger.info(f"开始存储到 PostgreSQL，文档 ID: {document_id}, 块数: {len(chunks)}")
        
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_record = DocumentChunk(
                document_id=document_id,
                content=chunk_text,
                embedding=embedding,
                chunk_index=idx
            )
            db.add(chunk_record)
        
        db.commit()
        logger.info(f"PostgreSQL 存储完成")
    
    @staticmethod
    def store_to_elasticsearch(
        db: Session,
        document_id: UUID,
        chunks: List[str],
        embeddings: List[List[float]],
        knowledge_base_ids: List[UUID]
    ):
        """
        存储到 Elasticsearch（业务逻辑：添加知识库关联 metadata）
        调用 rag.ingestion 的底层方法
        """
        logger.info(f"开始存储到 Elasticsearch，文档 ID: {document_id}")
        
        # 获取文档信息（业务逻辑）
        document = DocumentDAO.get_by_id(db, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # 构建每个 chunk 的 metadata（业务逻辑：知识库关联）
        metadata_list = []
        for idx in range(len(chunks)):
            metadata = {
                "document_id": str(document_id),
                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids],
                "chunk_index": idx,
                "filename": document.filename,
                "upload_date": document.upload_date.isoformat() if document.upload_date else None
            }
            metadata_list.append(metadata)
        
        # 调用 rag 底层方法创建节点并存储
        nodes = create_text_nodes(chunks, embeddings, metadata_list)
        node_count = store_nodes_to_es(nodes)
        
        logger.info(f"Elasticsearch 存储完成，共 {node_count} 个节点")
    
    @staticmethod
    def process_document_full(
        db: Session,
        document_id: UUID,
        file_path: str,
        knowledge_base_ids: List[UUID],
        chunk_size: int = 1024,
        overlap: int = 100,
        embedding_model: str = "text-embedding-v3"
    ):
        """
        完整的文档处理流程（业务层）：
        1. 调用 rag.ingestion 进行文档解析、分块、向量化
        2. 存储到 PostgreSQL（业务逻辑）
        3. 存储到 Elasticsearch（带知识库关联的业务逻辑）
        
        Args:
            db: 数据库会话
            document_id: 文档 UUID
            file_path: 文件路径
            knowledge_base_ids: 所属知识库 UUID 列表
            chunk_size: 分块大小
            overlap: 重叠大小
            embedding_model: 向量模型
        """
        logger.info("=" * 60)
        logger.info(f"开始完整文档处理流程（业务层）")
        logger.info(f"文档 ID: {document_id}")
        logger.info(f"文件路径: {file_path}")
        logger.info(f"知识库 IDs: {knowledge_base_ids}")
        logger.info("=" * 60)
        
        try:
            # ===== 调用 rag.ingestion 底层方法 =====
            logger.info("📄 步骤 1/3: 调用 RAG 底层方法进行文档解析、分块、向量化...")
            
            # 1. 转换为 Markdown（rag 底层方法）
            markdown_text = convert_pdf_to_markdown(file_path)
            logger.info(f"  ✓ Markdown 转换完成，长度: {len(markdown_text)}")
            
            # 2. 智能分块（rag 底层方法）
            chunks = chunk_text(
                markdown_text,
                chunk_size=chunk_size,
                chunk_overlap=overlap
            )
            logger.info(f"  ✓ 分块完成，共 {len(chunks)} 个块")
            
            # 3. 生成向量（rag 底层方法）
            all_embeddings = generate_embeddings(
                chunks,
                model=embedding_model,
                batch_size=10
            )
            logger.info(f"  ✓ 向量生成完成，维度: {len(all_embeddings[0]) if all_embeddings else 0}")
            
            # ===== 业务逻辑：更新文档记录 =====
            document = DocumentDAO.get_by_id(db, document_id)
            document.content_markdown = markdown_text
            db.commit()
            
            # ===== 业务逻辑：存储到 PostgreSQL =====
            logger.info("💾 步骤 2/3: 存储到 PostgreSQL...")
            VectorizationService.store_to_postgres(
                db=db,
                document_id=document_id,
                chunks=chunks,
                embeddings=all_embeddings
            )
            logger.info("  ✓ PostgreSQL 存储完成")
            
            # ===== 业务逻辑：存储到 Elasticsearch（带知识库关联）=====
            logger.info("🔍 步骤 3/3: 存储到 Elasticsearch（带知识库关联）...")
            VectorizationService.store_to_elasticsearch(
                db=db,
                document_id=document_id,
                chunks=chunks,
                embeddings=all_embeddings,
                knowledge_base_ids=knowledge_base_ids
            )
            logger.info("  ✓ Elasticsearch 存储完成")
            
            # ===== 标记为已处理 =====
            document.is_processed = True
            db.commit()
            
            logger.info("=" * 60)
            logger.info(f"✅ 文档处理完成！")
            logger.info(f"  - 总块数: {len(chunks)}")
            logger.info(f"  - 向量维度: {len(all_embeddings[0]) if all_embeddings else 0}")
            logger.info(f"  - 关联知识库: {len(knowledge_base_ids)} 个")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "document_id": str(document_id),
                "chunks_count": len(chunks),
                "vector_dimension": len(all_embeddings[0]) if all_embeddings else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 文档处理失败: {type(e).__name__}: {str(e)}")
            db.rollback()
            
            # 标记处理失败
            try:
                document = DocumentDAO.get_by_id(db, document_id)
                document.is_processed = False
                db.commit()
            except:
                pass
            
            raise


# 便捷函数
def process_uploaded_document(
    db: Session,
    document_id: UUID,
    file_path: str,
    knowledge_base_ids: List[UUID]
):
    """
    处理上传的文档（便捷函数 - 本地文件路径）
    """
    return VectorizationService.process_document_full(
        db=db,
        document_id=document_id,
        file_path=file_path,
        knowledge_base_ids=knowledge_base_ids
    )


def process_uploaded_document_from_minio(
    db: Session,
    document_id: UUID,
    storage_object_name: str,
    knowledge_base_ids: List[UUID]
):
    """
    处理从 MinIO 上传的文档（便捷函数）
    1. 从 MinIO 下载文件到临时目录
    2. 处理文档
    3. 清理临时文件
    """
    import tempfile
    import os
    from services.storage_service import get_storage_service
    
    storage_service = get_storage_service()
    temp_file_path = None
    
    try:
        # 1. 从 MinIO 下载到临时文件
        logger.info(f"📥 从 MinIO 下载文件: {storage_object_name}")
        file_data = storage_service.download_file(storage_object_name)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_data)
            temp_file_path = temp_file.name
        
        logger.info(f"✓ 文件下载到临时目录: {temp_file_path}")
        
        # 2. 处理文档
        result = VectorizationService.process_document_full(
            db=db,
            document_id=document_id,
            file_path=temp_file_path,
            knowledge_base_ids=knowledge_base_ids
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 从 MinIO 处理文档失败: {e}", exc_info=True)
        raise
        
    finally:
        # 3. 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"🗑️  临时文件已清理: {temp_file_path}")
            except Exception as e:
                logger.warning(f"⚠️  临时文件清理失败: {e}")

