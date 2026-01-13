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

# ===== Chat 对话表（区别于ADK表） =====

# ChatSession 表：存储对话会话基本信息
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)  # 会话唯一标识符
    session_title = Column(String, nullable=True)  # 会话标题
    user_id = Column(String, nullable=False, index=True)  # 用户ID
    custom_metadata = Column(JSON, nullable=True)  # 额外元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 与消息和历史记录的关系
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    histories = relationship("ChatHistory", back_populates="session", cascade="all, delete-orphan", order_by="ChatHistory.turn_index")

# ChatMessage 表：存储对话的具体消息
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属会话
    role = Column(String, nullable=False)  # 角色类型：user, assistant, tool, system
    message_type = Column(String, nullable=False)  # 消息类型：user_message, ai_response, tool_result, system_assembled
    content = Column(Text, nullable=False)  # 消息内容
    message_metadata = Column(JSON, nullable=True)  # 额外信息（工具调用详情、RAG检索结果、来源文档等）（避免使用保留字 metadata）
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True)  # 父消息ID（用于关联同一轮次的消息）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 与 Session 的关系
    session = relationship("ChatSession", back_populates="messages")
    
    # 自关联关系（父消息和子消息）
    parent_message = relationship("ChatMessage", remote_side=[id], backref="child_messages")
    
    # 与 ChatHistory 的关系（作为用户消息或助手消息）
    user_history = relationship("ChatHistory", foreign_keys="ChatHistory.user_message_id", back_populates="user_message")
    assistant_history = relationship("ChatHistory", foreign_keys="ChatHistory.assistant_message_id", back_populates="assistant_message")

# ChatHistory 表：存储对话消息的组合记录（一次完整对话轮次）
class ChatHistory(Base):
    __tablename__ = "chat_histories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属会话
    turn_index = Column(Integer, nullable=False)  # 对话轮次序号（从1开始，同一session内递增）
    user_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True)  # 用户消息ID
    assistant_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True)  # AI回复消息ID
    summary = Column(Text, nullable=True)  # 该轮次的摘要
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 与 Session 的关系
    session = relationship("ChatSession", back_populates="histories")
    
    # 与 ChatMessage 的关系
    user_message = relationship("ChatMessage", foreign_keys=[user_message_id], back_populates="user_history")
    assistant_message = relationship("ChatMessage", foreign_keys=[assistant_message_id], back_populates="assistant_history")
    
    # 唯一约束：同一session内turn_index唯一
    __table_args__ = (
        # UniqueConstraint('session_id', 'turn_index', name='uix_chat_history_session_turn'),
    )

