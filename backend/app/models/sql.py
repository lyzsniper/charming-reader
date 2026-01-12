from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Table, JSON
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
    # 是否为临时文件（聊天时上传的文件）
    is_temporary = Column(Boolean, default=False, index=True)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    # 与知识库的多对多关系
    knowledge_bases = relationship("KnowledgeBase", secondary="document_knowledge_base", back_populates="documents")
    # 与Session的关联（临时文件）
    session_associations = relationship("DocumentSession", back_populates="document", cascade="all, delete-orphan")
    
    @property
    def filename(self):
        """兼容性属性：返回原始文件名"""
        return self.original_filename

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chunk_index = Column(Integer)
    
    # Qwen text-embedding-v4 默认 1024 维
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))  # text-embedding-v4 默认维度 

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

# ===== ADK Session 持久化表 =====

# Session 表：存储 ADK 会话
class Session(Base):
    __tablename__ = "adk_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(String, nullable=False, index=True)  # ADK session_id
    user_id = Column(String, nullable=False, index=True)  # ADK user_id
    app_name = Column(String, nullable=False, default="paper_agent", index=True)  # ADK app_name
    state = Column(JSON, nullable=True)  # Session.state 数据（JSON格式）
    custom_metadata = Column(JSON, nullable=True)  # 额外的元数据（避免使用保留字 metadata）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 与消息的关系
    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan", order_by="SessionMessage.created_at")
    
    # 唯一约束：app_name + user_id + session_id 唯一
    __table_args__ = (
        # 为了支持多应用和多用户
        # UniqueConstraint('app_name', 'user_id', 'session_id', name='uix_session'),
    )

# SessionMessage 表：存储会话消息（Events）
class SessionMessage(Base):
    __tablename__ = "adk_session_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("adk_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'model'
    content = Column(JSON, nullable=False)  # Content 对象的 JSON 表示
    custom_metadata = Column(JSON, nullable=True)  # 额外的元数据（避免使用保留字 metadata）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 与 Session 的关系
    session = relationship("Session", back_populates="messages")

# 文档会话关联表（用于临时文件）
class DocumentSession(Base):
    __tablename__ = "document_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)  # ADK session_id (String类型)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 与 Document 的关系
    document = relationship("Document", back_populates="session_associations")

