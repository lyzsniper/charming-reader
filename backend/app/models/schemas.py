from pydantic import BaseModel, Field
from typing import Optional, List
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

