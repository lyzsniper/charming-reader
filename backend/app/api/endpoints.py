from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
import shutil
import os
from sqlalchemy.orm import Session
from core.db import get_db
from core.logger import LoggerFactory
from agents.flow import run_agent
from services.ingestion import process_pdf
from skills.manager import skills_manager
from services import (
    KnowledgeBaseService,
    DocumentService,
    ModelConfigurationService
)
from models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseDetailResponse,
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentSimpleResponse,
    DocumentKnowledgeBaseCreate,
    ModelConfigurationCreate,
    ModelConfigurationUpdate,
    ModelConfigurationResponse
)

# 创建日志记录器
logger = LoggerFactory.get_api_logger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class SkillActivationRequest(BaseModel):
    skill_name: str

@router.post("/chat")
async def chat(request: ChatRequest):
    logger.info(f"收到聊天请求: message={request.message[:50]}...")
    try:
        # Call ADK Agent
        response_text = run_agent(request.message)
        logger.info(f"聊天响应成功: response_length={len(response_text)}")
        return {"response": response_text}
    except Exception as e:
        logger.error(f"聊天请求失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=DocumentResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    knowledge_base_ids: str = "",  # 逗号分隔的知识库ID，如 "1,2,3"
    db: Session = Depends(get_db)
):
    """上传文档到 MinIO 并关联到知识库"""
    logger.info(f"收到文件上传请求: filename={file.filename}, kb_ids={knowledge_base_ids}")
    
    if not file.filename.endswith(".pdf"):
        logger.warning(f"上传文件格式错误: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # 解析知识库 ID（UUID格式）
    kb_ids = []
    if knowledge_base_ids:
        try:
            kb_ids = [UUID(id.strip()) for id in knowledge_base_ids.split(",") if id.strip()]
        except (ValueError, AttributeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid knowledge_base_ids format: {str(e)}")
    
    try:
        # 1. 上传文件到 MinIO
        from services.storage_service import get_storage_service
        storage_service = get_storage_service()
        
        logger.info(f"开始上传文件到 MinIO: {file.filename}")
        object_name, file_size = storage_service.upload_file(
            file_data=file.file,
            original_filename=file.filename,
            content_type=file.content_type or "application/pdf"
        )
        # 获取预签名下载链接和存储路径
        file_download_url = storage_service.get_presigned_url(object_name)
        storage_path = f"{storage_service.bucket_name}/{object_name}"
        
        logger.info(f"✓ 文件上传到 MinIO 成功: object={object_name}, size={file_size}, url={file_download_url}")
        
        # 2. 创建数据库记录
        db_doc = DocumentService.create_document(
            db=db,
            original_filename=file.filename,
            storage_object_name=object_name,
            file_size=file_size,
            content_type=file.content_type or "application/pdf",
            knowledge_base_ids=kb_ids,
            storage_path=storage_path,
            file_download_url=file_download_url
        )
        logger.info(f"✓ 数据库记录创建成功: doc_id={db_doc.id}")
        
        # 3. 触发异步向量化处理（完整流程）
        # 需要从 MinIO 下载文件到临时目录进行处理
        logger.info(f"触发文档向量化任务: doc_id={db_doc.id}, object={object_name}, kb_ids={kb_ids}")
        
        # 导入向量化服务
        from services.vectorization_service import process_uploaded_document_from_minio
        
        # 异步处理：下载 -> 转换 -> 分块 -> 向量化 -> 存储到 PG 和 ES
        background_tasks.add_task(
            process_uploaded_document_from_minio,
            db=db,
            document_id=db_doc.id,
            storage_object_name=object_name,
            knowledge_base_ids=kb_ids
        )
        
        response = DocumentResponse(
            id=db_doc.id,
            original_filename=db_doc.original_filename,
            storage_object_name=db_doc.storage_object_name,
            storage_path=db_doc.storage_path,
            file_download_url=db_doc.file_download_url,
            file_size=db_doc.file_size,
            content_type=db_doc.content_type,
            upload_date=db_doc.upload_date,
            is_processed=db_doc.is_processed,
            content_markdown=db_doc.content_markdown,
            knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in db_doc.knowledge_bases]
        )
        logger.info(f"✅ 文件上传成功: doc_id={db_doc.id}, filename={db_doc.original_filename}")
        return response
        
    except Exception as e:
        logger.error(f"❌ 文件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

# ===== Skills Management Endpoints =====

@router.get("/skills")
async def list_skills():
    """
    List all available skills
    """
    try:
        skills = skills_manager.list_all_skills()
        return {"skills": skills, "count": len(skills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str):
    """
    Get detailed information about a specific skill
    """
    try:
        skill_info = skills_manager.get_skill_info(skill_name)
        if not skill_info:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        return skill_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/{skill_name}/activate")
async def activate_skill_endpoint(skill_name: str):
    """
    Activate a specific skill
    """
    try:
        success = skills_manager.activate_skill(skill_name)
        if success:
            return {"message": f"Skill '{skill_name}' activated successfully", "status": "active"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to activate skill '{skill_name}'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/{skill_name}/deactivate")
async def deactivate_skill_endpoint(skill_name: str):
    """
    Deactivate a specific skill
    """
    try:
        success = skills_manager.deactivate_skill(skill_name)
        if success:
            return {"message": f"Skill '{skill_name}' deactivated successfully", "status": "inactive"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to deactivate skill '{skill_name}'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills/active")
async def get_active_skills():
    """
    Get all currently active skills
    """
    try:
        active_skills = skills_manager.get_active_skills()
        return {"active_skills": active_skills, "count": len(active_skills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skills/suggest")
async def suggest_skills(request: ChatRequest):
    """
    Suggest skills based on user query
    """
    try:
        suggestions = skills_manager.suggest_skills(request.message, top_k=3)
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skills/statistics")
async def get_skills_statistics():
    """
    Get skills system statistics
    """
    try:
        stats = skills_manager.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== 知识库管理 API =====

@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(kb: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """创建知识库"""
    db_kb = KnowledgeBaseService.create_knowledge_base(db, kb)
    response_data = KnowledgeBaseResponse.model_validate(db_kb)
    response_data.document_count = KnowledgeBaseService.get_document_count(db_kb)
    return response_data

@router.get("/knowledge-bases", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取知识库列表"""
    kbs = KnowledgeBaseService.list_knowledge_bases(db, skip=skip, limit=limit)
    return [
        KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=KnowledgeBaseService.get_document_count(kb)
        )
        for kb in kbs
    ]

@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(kb_id: UUID, db: Session = Depends(get_db)):
    """获取单个知识库详情"""
    db_kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
    
    return KnowledgeBaseDetailResponse(
        id=db_kb.id,
        name=db_kb.name,
        description=db_kb.description,
        created_at=db_kb.created_at,
        updated_at=db_kb.updated_at,
        document_count=KnowledgeBaseService.get_document_count(db_kb),
        documents=[DocumentSimpleResponse.model_validate(doc) for doc in db_kb.documents]
    )

@router.put("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(kb_id: UUID, kb_update: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """更新知识库"""
    db_kb = KnowledgeBaseService.update_knowledge_base(db, kb_id, kb_update)
    
    response_data = KnowledgeBaseResponse.model_validate(db_kb)
    response_data.document_count = KnowledgeBaseService.get_document_count(db_kb)
    return response_data

@router.delete("/knowledge-bases/{kb_id}", status_code=204)
async def delete_knowledge_base(kb_id: UUID, db: Session = Depends(get_db)):
    """删除知识库"""
    KnowledgeBaseService.delete_knowledge_base(db, kb_id)
    return None

# ===== 文档管理 API =====

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0, 
    limit: int = 100, 
    knowledge_base_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """获取文档列表，可按知识库筛选"""
    docs = DocumentService.list_documents(db, skip=skip, limit=limit, knowledge_base_id=knowledge_base_id)
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            upload_date=doc.upload_date,
            is_processed=doc.is_processed,
            content_markdown=doc.content_markdown,
            knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in doc.knowledge_bases]
        )
        for doc in docs
    ]

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: UUID, db: Session = Depends(get_db)):
    """获取单个文档详情"""
    db_doc = DocumentService.get_document_by_id(db, doc_id)
    
    return DocumentResponse(
        id=db_doc.id,
        filename=db_doc.filename,
        upload_date=db_doc.upload_date,
        is_processed=db_doc.is_processed,
        content_markdown=db_doc.content_markdown,
        knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in db_doc.knowledge_bases]
    )

@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: UUID, doc_update: DocumentUpdate, db: Session = Depends(get_db)):
    """更新文档"""
    db_doc = DocumentService.update_document(db, doc_id, doc_update)
    
    return DocumentResponse(
        id=db_doc.id,
        filename=db_doc.filename,
        upload_date=db_doc.upload_date,
        is_processed=db_doc.is_processed,
        content_markdown=db_doc.content_markdown,
        knowledge_bases=[KnowledgeBaseResponse.model_validate(kb) for kb in db_doc.knowledge_bases]
    )

@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, db: Session = Depends(get_db)):
    """删除文档"""
    DocumentService.delete_document(db, doc_id)
    return None

# ===== 文档知识库关联 API =====

@router.post("/documents/{doc_id}/knowledge-bases/{kb_id}", status_code=201)
async def add_document_to_knowledge_base(doc_id: UUID, kb_id: UUID, db: Session = Depends(get_db)):
    """将文档添加到知识库"""
    DocumentService.add_to_knowledge_base(db, doc_id, kb_id)
    return {"message": "Document added to knowledge base successfully"}

@router.delete("/documents/{doc_id}/knowledge-bases/{kb_id}", status_code=204)
async def remove_document_from_knowledge_base(doc_id: UUID, kb_id: UUID, db: Session = Depends(get_db)):
    """从知识库移除文档"""
    DocumentService.remove_from_knowledge_base(db, doc_id, kb_id)
    return None

@router.get("/knowledge-bases/{kb_id}/documents", response_model=List[DocumentSimpleResponse])
async def get_knowledge_base_documents(kb_id: UUID, db: Session = Depends(get_db)):
    """获取知识库下的所有文档"""
    # 验证知识库存在
    KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
    
    docs = DocumentService.list_documents(db, knowledge_base_id=kb_id)
    return [DocumentSimpleResponse.model_validate(doc) for doc in docs]

# ===== 模型配置管理 API =====

@router.post("/model-configurations", response_model=ModelConfigurationResponse, status_code=201)
async def create_model_configuration(model_config: ModelConfigurationCreate, db: Session = Depends(get_db)):
    """创建模型配置"""
    db_model = ModelConfigurationService.create_model_configuration(db, model_config)
    return ModelConfigurationResponse.model_validate(db_model)

@router.get("/model-configurations", response_model=List[ModelConfigurationResponse])
async def list_model_configurations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取模型配置列表"""
    models = ModelConfigurationService.list_model_configurations(db, skip=skip, limit=limit)
    return [ModelConfigurationResponse.model_validate(model) for model in models]

@router.get("/model-configurations/active", response_model=ModelConfigurationResponse)
async def get_active_model_configuration(db: Session = Depends(get_db)):
    """获取当前激活的模型配置"""
    db_model = ModelConfigurationService.get_active_model_configuration(db)
    if not db_model:
        raise HTTPException(status_code=404, detail="No active model configuration found")
    
    return ModelConfigurationResponse.model_validate(db_model)

@router.get("/model-configurations/{model_id}", response_model=ModelConfigurationResponse)
async def get_model_configuration(model_id: UUID, db: Session = Depends(get_db)):
    """获取单个模型配置详情"""
    db_model = ModelConfigurationService.get_model_configuration_by_id(db, model_id)
    
    return ModelConfigurationResponse.model_validate(db_model)

@router.put("/model-configurations/{model_id}", response_model=ModelConfigurationResponse)
async def update_model_configuration(model_id: UUID, model_update: ModelConfigurationUpdate, db: Session = Depends(get_db)):
    """更新模型配置"""
    db_model = ModelConfigurationService.update_model_configuration(db, model_id, model_update)
    
    return ModelConfigurationResponse.model_validate(db_model)

@router.delete("/model-configurations/{model_id}", status_code=204)
async def delete_model_configuration(model_id: UUID, db: Session = Depends(get_db)):
    """删除模型配置"""
    ModelConfigurationService.delete_model_configuration(db, model_id)
    return None

@router.post("/model-configurations/{model_id}/activate", response_model=ModelConfigurationResponse)
async def activate_model_configuration(model_id: UUID, db: Session = Depends(get_db)):
    """设置为激活的模型配置"""
    db_model = ModelConfigurationService.activate_model(db, model_id)
    
    return ModelConfigurationResponse.model_validate(db_model)

@router.get("/model-configurations/current/info")
async def get_current_model_info(db: Session = Depends(get_db)):
    """获取当前使用的模型信息（用户配置或默认）"""
    model_info = ModelConfigurationService.get_current_model_info(db)
    return model_info

# ===== RAG 查询 API =====

class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_ids: Optional[List[UUID]] = Field(None, description="知识库 UUID 列表，为空则检索所有知识库")
    top_k: int = Field(5, ge=1, le=20, description="检索数量")
    enable_rerank: bool = Field(True, description="是否启用 LLM 重排序")

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="搜索查询")
    knowledge_base_ids: Optional[List[UUID]] = Field(None, description="知识库 UUID 列表")
    top_k: int = Field(5, ge=1, le=20, description="返回数量")

@router.post("/rag/query")
async def rag_query(request: RAGQueryRequest):
    """
    RAG 查询接口
    支持基于知识库的问答
    """
    logger.info(f"收到 RAG 查询请求: question={request.question[:50]}..., kb_ids={request.knowledge_base_ids}")
    
    try:
        from services.rag_service import query_knowledge_base
        
        result = query_knowledge_base(
            question=request.question,
            knowledge_base_ids=request.knowledge_base_ids
        )
        
        logger.info(f"RAG 查询成功: sources_count={len(result.get('sources', []))}")
        return result
        
    except Exception as e:
        logger.error(f"RAG 查询失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/search")
async def rag_search(request: SearchRequest):
    """
    文档搜索接口
    仅返回检索结果，不生成答案
    """
    logger.info(f"收到搜索请求: query={request.query[:50]}..., kb_ids={request.knowledge_base_ids}")
    
    try:
        from services.rag_service import search_documents
        
        results = search_documents(
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids,
            top_k=request.top_k
        )
        
        logger.info(f"搜索成功: results_count={len(results)}")
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"搜索失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
