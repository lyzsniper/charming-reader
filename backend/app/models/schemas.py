from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID

# ===== 知识库相关 Schemas =====

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    documents: List["DocumentSimpleResponse"] = []

# ===== 文档相关 Schemas =====

class DocumentCreate(BaseModel):
    filename: str
    knowledge_base_ids: List[UUID] = []  # 选择的知识库ID列表

class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    knowledge_base_ids: Optional[List[UUID]] = None

class DocumentSimpleResponse(BaseModel):
    id: UUID
    original_filename: str  # 原始文件名
    file_size: Optional[int] = None  # 文件大小
    upload_date: datetime
    is_processed: bool
    
    class Config:
        from_attributes = True
        
    # 兼容性属性
    @property
    def filename(self):
        return self.original_filename

class DocumentResponse(DocumentSimpleResponse):
    storage_object_name: str  # MinIO 对象名称
    storage_path: Optional[str] = None
    file_download_url: Optional[str] = None
    content_type: str  # 文件类型
    content_markdown: Optional[str] = None
    knowledge_bases: List[KnowledgeBaseResponse] = []

# ===== 文档知识库关联相关 Schemas =====

class DocumentKnowledgeBaseCreate(BaseModel):
    document_id: UUID
    knowledge_base_id: UUID

class DocumentKnowledgeBaseResponse(BaseModel):
    id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    added_at: datetime
    
    class Config:
        from_attributes = True

# ===== 模型配置相关 Schemas =====

class ModelConfigurationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    model_name: str = Field(..., min_length=1, max_length=200)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = False

class ModelConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    model_name: Optional[str] = Field(None, min_length=1, max_length=200)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ModelConfigurationResponse(BaseModel):
    id: UUID
    name: str
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ===== Chat 相关 Schemas =====

class VectorizationStep(BaseModel):
    """向量化步骤事件（用于SSE流式输出）"""
    step: str = Field(..., description="步骤名称: uploading, parsing, chunking, embedding, storing, completed")
    message: str = Field(..., description="步骤描述信息")
    progress: Optional[float] = Field(None, ge=0, le=100, description="进度百分比 0-100")
    details: Optional[Dict] = Field(None, description="详细信息（块数量、处理时间等）")

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，不传则自动创建新会话")
    user_id: Optional[str] = Field("default_user", description="用户ID")
    knowledge_base_ids: Optional[List[UUID]] = Field(None, description="知识库ID列表，选择后启用RAG检索")
    use_rag: bool = Field(False, description="是否启用RAG问答（有知识库时自动为True）")
    rag_top_k: int = Field(5, ge=1, le=20, description="RAG检索数量")
    enable_rerank: bool = Field(True, description="是否启用检索重排序")

class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    message: str = Field(..., description="用户消息")
    response: str = Field(..., description="智能体回复")
    sources: Optional[List[Dict]] = Field(None, description="RAG来源（启用RAG时返回）")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="使用的知识库ID列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        from_attributes = True

# ===== 翻译相关 Schemas =====

class TranslationRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., min_length=1, description="要翻译的文本")
    from_language: str = Field("auto", description="源语言代码，'auto' 表示自动检测")
    to_language: str = Field(..., description="目标语言代码（如: 'en', 'zh', 'ja' 等）")
    provider: Optional[str] = Field("google", description="翻译服务提供商（google, baidu, alibaba, youdao, tencent, deepl, bing, sogou）")

class BatchTranslationRequest(BaseModel):
    """批量翻译请求"""
    texts: List[str] = Field(..., min_items=1, description="要翻译的文本列表")
    from_language: str = Field("auto", description="源语言代码，'auto' 表示自动检测")
    to_language: str = Field(..., description="目标语言代码")
    provider: Optional[str] = Field("google", description="翻译服务提供商")

class TranslationResponse(BaseModel):
    """翻译响应"""
    original_text: str = Field(..., description="原始文本")
    translated_text: Optional[str] = Field(None, description="翻译后的文本")
    from_language: str = Field(..., description="源语言")
    to_language: str = Field(..., description="目标语言")
    provider: str = Field(..., description="使用的翻译服务")
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")

class LanguageDetectionRequest(BaseModel):
    """语言检测请求"""
    text: str = Field(..., min_length=1, description="要检测的文本")
    provider: Optional[str] = Field("google", description="翻译服务提供商")

class LanguageDetectionResponse(BaseModel):
    """语言检测响应"""
    text: str = Field(..., description="检测的文本")
    detected_language: Optional[str] = Field(None, description="检测到的语言代码")
    provider: str = Field(..., description="使用的翻译服务")
    success: bool = Field(..., description="是否成功")
