from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
import uuid
from core.db import Base

# 知识库表
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 与文档的多对多关系
    documents = relationship("Document", secondary="document_knowledge_base", back_populates="knowledge_bases")

# 文档知识库关联表
class DocumentKnowledgeBase(Base):
    __tablename__ = "document_knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

# 文档表（扩展）
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # 原始文件名（用户上传的文件名）
    original_filename = Column(String, nullable=False)
    # MinIO 对象名称（UUID.pdf）
    storage_object_name = Column(String, nullable=False, unique=True, index=True)
    # 存储桶名称/路径信息
    storage_path = Column(String, nullable=True)
    # 文件下载链接（预签名URL或公共URL）
    file_download_url = Column(String, nullable=True)
    # 文件大小（字节）
    file_size = Column(Integer, nullable=True)
    # 文件类型（MIME type）
    content_type = Column(String, default="application/pdf")
    # 上传日期
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    # Markdown 内容（处理后）
    content_markdown = Column(Text, nullable=True)
    # 是否已处理（向量化）
    is_processed = Column(Boolean, default=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    # 与知识库的多对多关系
    knowledge_bases = relationship("KnowledgeBase", secondary="document_knowledge_base", back_populates="documents")
    
    @property
    def filename(self):
        """兼容性属性：返回原始文件名"""
        return self.original_filename

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536)) # Assuming 1536 dim for standard embeddings, can adjust
    chunk_index = Column(Integer)

    document = relationship("Document", back_populates="chunks")

# 模型配置表
class ModelConfiguration(Base):
    __tablename__ = "model_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    model_name = Column(String, nullable=False)  # 模型名称，如 gpt-4, qwen-flash 等
    api_key = Column(String, nullable=True)  # API Key
    base_url = Column(String, nullable=True)  # 基础 URL
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)  # 是否为当前激活的模型
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

