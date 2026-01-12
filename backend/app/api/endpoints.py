from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator
from uuid import UUID, uuid4
import shutil
import os
import json
import tempfile
import queue
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from core.db import get_db
from core.logger import LoggerFactory
from agents.flow import run_agent_with_rag
from services.ingestion import process_pdf
from services.vectorization_service import VectorizationService
from services.storage_service import get_storage_service
from skills.manager import skills_manager
from rag.ingestion import SUPPORTED_MARKDOWN_EXTENSIONS
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
    ModelConfigurationResponse,
    ChatRequest,
    ChatResponse,
    VectorizationStep,
    TranslationRequest,
    TranslationResponse,
    BatchTranslationRequest,
    LanguageDetectionRequest,
    LanguageDetectionResponse
)
from models.sql import Session as DBSessionModel, SessionMessage

# 创建日志记录器
logger = LoggerFactory.get_api_logger(__name__)

router = APIRouter()

# 简单的扩展名到 MIME 映射（用于缺省 content_type）
EXTENSION_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".csv": "text/csv",
    ".html": "text/html",
    ".xml": "application/xml",
    ".json": "application/json",
}

class SkillActivationRequest(BaseModel):
    skill_name: str

def _format_sse_event(event_type: str, data: dict) -> str:
    """格式化SSE事件"""
    data_json = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data_json}\n\n"

async def _chat_with_file_stream(
    file: UploadFile,
    message: str,
    session_id: Optional[str],
    user_id: str,
    db: Session
) -> AsyncGenerator[str, None]:
    """处理带文件上传的聊天请求（流式响应）"""
    temp_file_path = None
    document_id = None
    
    try:
        # 1. 自动创建 session_id（如果未提供）
        if not session_id:
            session_id = str(uuid4())
            logger.info(f"✓ 自动创建新会话: session_id={session_id}")
        
        # 2. 校验文件格式
        _, ext = os.path.splitext(file.filename or "")
        ext = ext.lower()
        if not ext or ext not in SUPPORTED_MARKDOWN_EXTENSIONS:
            allowed_exts = ", ".join(sorted(SUPPORTED_MARKDOWN_EXTENSIONS))
            yield _format_sse_event("error", {
                "error": f"不支持的文件格式。允许的格式: {allowed_exts}"
            })
            return
        
        content_type = file.content_type or EXTENSION_CONTENT_TYPE.get(ext, "application/octet-stream")
        
        # 3. 保存文件到临时目录
        yield _format_sse_event("vectorization_step", {
            "step": "uploading",
            "message": "正在上传文件...",
            "progress": 5
        })
        
        suffix = ext if ext else ""
        with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            file_size = len(content)
        
        yield _format_sse_event("vectorization_step", {
            "step": "uploading",
            "message": f"文件上传完成，大小: {file_size} 字节",
            "progress": 10
        })
        
        # 4. 上传到MinIO
        storage_service = get_storage_service()
        with open(temp_file_path, 'rb') as file_data:
            object_name, _ = storage_service.upload_file(
                file_data=file_data,
                original_filename=file.filename,
                content_type=content_type
            )
        file_download_url = storage_service.get_presigned_url(object_name)
        storage_path = f"{storage_service.bucket_name}/{object_name}"
        
        # 5. 创建文档记录（临时文件）
        db_doc = DocumentService.create_document(
            db=db,
            original_filename=file.filename,
            storage_object_name=object_name,
            file_size=file_size,
            content_type=content_type,
            knowledge_base_ids=[],  # 临时文件不关联知识库
            storage_path=storage_path,
            file_download_url=file_download_url,
            is_temporary=True,
            session_id=session_id
        )
        document_id = db_doc.id
        
        # 6. 向量化处理（流式输出）
        import asyncio
        step_queue = queue.Queue()  # 线程安全的队列
        vectorization_done = threading.Event()
        vectorization_error = None
        
        def step_callback(step: str, msg: str, progress: Optional[float] = None, details: Optional[dict] = None):
            """向量化步骤回调（在同步上下文中调用）"""
            step_queue.put((step, msg, progress, details))
        
        # 在后台线程中处理向量化（同步操作）
        def process_vectorization_sync():
            try:
                result = VectorizationService.process_document_full_streaming(
                    db=db,
                    document_id=document_id,
                    file_path=temp_file_path,
                    knowledge_base_ids=[],
                    yield_step=step_callback,
                    session_id=session_id
                )
                step_queue.put(("completed", "向量化处理完成", 100, result))
            except Exception as e:
                nonlocal vectorization_error
                vectorization_error = str(e)
                step_queue.put(("error", f"向量化失败: {str(e)}", None, {"error": str(e)}))
            finally:
                vectorization_done.set()
        
        # 启动向量化线程
        vectorization_thread = threading.Thread(target=process_vectorization_sync, daemon=True)
        vectorization_thread.start()
        
        # 流式发送向量化步骤
        while not vectorization_done.is_set() or not step_queue.empty():
            try:
                # 从队列中获取事件（非阻塞）
                step, msg, progress, details = step_queue.get(timeout=0.5)
                yield _format_sse_event("vectorization_step", {
                    "step": step,
                    "message": msg,
                    "progress": progress,
                    "details": details
                })
            except queue.Empty:
                # 队列为空，继续等待
                await asyncio.sleep(0.1)
                continue
        
        # 等待向量化线程完成
        vectorization_thread.join(timeout=60)  # 增加超时时间到60秒
        
        # 检查是否有错误
        if vectorization_error:
            raise Exception(f"向量化失败: {vectorization_error}")
        
        # 等待更长时间，确保 Elasticsearch 索引已刷新并可查询
        logger.info(f"向量化完成，等待 ES 索引刷新后开始查询，session_id={session_id}, document_id={document_id}")
        await asyncio.sleep(2)  # 增加到2秒
        
        # 验证数据是否已存储（可选，用于调试）
        try:
            from services.rag_service import RAGService
            # 尝试查询一个简单的测试，验证数据是否可检索
            test_result = RAGService.query(
                question="test",  # 简单的测试查询
                knowledge_base_ids=None,
                session_id=session_id,
                similarity_top_k=1,
                enable_rerank=False
            )
            found_nodes = len(test_result.get("sources", []))
            logger.info(f"✓ 验证查询完成: session_id={session_id}, 找到 {found_nodes} 个节点")
            if found_nodes == 0:
                logger.warning(f"⚠️ 警告: 验证查询未找到任何节点，可能数据尚未完全索引")
                # 再等待1秒
                await asyncio.sleep(1)
        except Exception as verify_e:
            logger.warning(f"⚠️ 验证查询失败（不影响主流程）: {verify_e}")
        
        # 7. 执行对话（使用临时文件进行RAG）
        yield _format_sse_event("chat_start", {
            "message": "开始生成回答..."
        })
        
        response_text, actual_session_id, rag_sources = await run_agent_with_rag(
            input_text=message,
            user_id=user_id,
            session_id=session_id,
            knowledge_base_ids=None,  # 不使用知识库
            use_rag=True,  # 启用RAG，使用临时文件
            rag_top_k=5,
            enable_rerank=True,
            session_id_for_temp_files=session_id  # 指定使用临时文件
        )
        
        # 8. 发送最终响应
        yield _format_sse_event("chat_response", {
            "session_id": actual_session_id,
            "user_id": user_id,
            "message": message,
            "response": response_text,
            "sources": rag_sources,
            "knowledge_base_ids": None,
            "created_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
        yield _format_sse_event("error", {
            "error": f"处理失败: {str(e)}"
        })
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """
    智能对话接口（支持 JSON 和 form-data 两种格式）
    
    功能特性：
    - 自动创建 Session：如果不传 session_id，自动使用 UUID 创建新会话
    - 多知识库选择：支持选择多个知识库进行 RAG 检索
    - RAG 问答：选择知识库后自动启用 RAG 检索，从向量数据库检索相关内容
    - 会话持久化：基于 PostgreSQL 的 Session 存储（符合 ADK 官方文档规范）
    
    参考文档：https://adk.wiki/sessions/
    """
    content_type = request_obj.headers.get("content-type", "")
    
    # 解析请求参数
    if "application/json" in content_type:
        # JSON 格式
        try:
            body = await request_obj.json()
            req = ChatRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    elif "multipart/form-data" in content_type:
        # Form-data 格式
        try:
            form = await request_obj.form()
            message = form.get("message")
            if not message:
                raise HTTPException(status_code=400, detail="Missing required field: message")
            
            # 检查是否有文件上传（使用 /chat/form 接口）
            if "file" in form:
                file_item = form["file"]
                if file_item and hasattr(file_item, 'filename') and file_item.filename:
                    raise HTTPException(
                        status_code=400, 
                        detail="File upload detected. Please use /chat/form endpoint for file uploads."
                    )
            
            # 解析知识库ID
            kb_ids = None
            kb_ids_str = form.get("knowledge_base_ids")
            if kb_ids_str:
                try:
                    kb_ids = [UUID(id.strip()) for id in str(kb_ids_str).split(",") if id.strip()]
                except (ValueError, AttributeError):
                    kb_ids = None
            
            # 解析布尔值
            use_rag_val = form.get("use_rag", "false")
            if isinstance(use_rag_val, str):
                use_rag_val = use_rag_val.lower() == "true"
            
            enable_rerank_val = form.get("enable_rerank", "true")
            if isinstance(enable_rerank_val, str):
                enable_rerank_val = enable_rerank_val.lower() == "true"
            
            req = ChatRequest(
                message=str(message),
                session_id=form.get("session_id"),
                user_id=form.get("user_id", "default_user"),
                knowledge_base_ids=kb_ids,
                use_rag=use_rag_val,
                rag_top_k=int(form.get("rag_top_k", 5)),
                enable_rerank=enable_rerank_val
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Form-data parsing error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid form-data format: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type. Use application/json or multipart/form-data")
    
    logger.info("=" * 80)
    logger.info(f"收到聊天请求: message={req.message[:100]}...")
    logger.info(f"参数: session_id={req.session_id}, user_id={req.user_id}")
    logger.info(f"知识库: kb_ids={req.knowledge_base_ids}, use_rag={req.use_rag}")
    logger.info("=" * 80)
    
    try:
        # 1. 自动创建 session_id（如果未提供）
        session_id = req.session_id
        if not session_id:
            session_id = str(uuid4())
            logger.info(f"✓ 自动创建新会话: session_id={session_id}")
        else:
            logger.info(f"✓ 使用已有会话: session_id={session_id}")
        
        user_id = req.user_id or "default_user"
        
        # 2. 验证知识库（如果提供了）
        if req.knowledge_base_ids:
            for kb_id in req.knowledge_base_ids:
                kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
                if not kb:
                    logger.warning(f"知识库不存在: {kb_id}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"知识库不存在: {kb_id}"
                    )
            logger.info(f"✓ 知识库验证通过: {len(req.knowledge_base_ids)} 个知识库")
        
        # 3. 调用智能体（支持 RAG）
        logger.info("开始调用智能体...")
        response_text, actual_session_id, rag_sources = await run_agent_with_rag(
            input_text=req.message,
            user_id=user_id,
            session_id=session_id,
            knowledge_base_ids=req.knowledge_base_ids,
            use_rag=req.use_rag,
            rag_top_k=req.rag_top_k,
            enable_rerank=req.enable_rerank
        )
        
        logger.info(f"✓ 智能体响应成功: length={len(response_text)}")
        if rag_sources:
            logger.info(f"✓ RAG 来源: {len(rag_sources)} 个片段")
        
        # 4. 构建响应
        response = ChatResponse(
            session_id=actual_session_id,
            user_id=user_id,
            message=req.message,
            response=response_text,
            sources=rag_sources,
            knowledge_base_ids=[str(kb_id) for kb_id in req.knowledge_base_ids] if req.knowledge_base_ids else None,
            created_at=datetime.now()
        )
        
        logger.info("=" * 80)
        logger.info("✅ 聊天请求处理完成")
        logger.info("=" * 80)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # 确保错误消息是 UTF-8 编码的字符串
        try:
            if isinstance(error_msg, bytes):
                error_msg = error_msg.decode('utf-8', errors='replace')
            else:
                error_msg = str(error_msg).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            error_msg = "An error occurred while processing the request"
        
        logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {error_msg}")


@router.post("/chat/form", response_model=ChatResponse)
async def chat_form(
    file: Optional[UploadFile] = File(None),
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    user_id: str = Form("default_user"),
    knowledge_base_ids: Optional[str] = Form(None),  # JSON字符串
    use_rag: bool = Form(False),
    rag_top_k: int = Form(5),
    enable_rerank: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    智能对话接口（支持文件上传和SSE流式响应）
    
    功能特性：
    - 支持文件上传：上传文件后自动向量化并用于RAG检索
    - SSE流式输出：实时显示向量化步骤和对话结果
    - 临时文件：上传的文件绑定到会话，不关联知识库
    - 自动创建 Session：如果不传 session_id，自动使用 UUID 创建新会话
    - 多知识库选择：支持选择多个知识库进行 RAG 检索
    - RAG 问答：选择知识库后自动启用 RAG 检索，从向量数据库检索相关内容
    - 会话持久化：基于 PostgreSQL 的 Session 存储（符合 ADK 官方文档规范）
    
    参考文档：https://adk.wiki/sessions/
    """
    logger.info("=" * 80)
    logger.info(f"收到聊天请求: message={message[:100]}...")
    logger.info(f"参数: session_id={session_id}, user_id={user_id}, has_file={file is not None}")
    logger.info("=" * 80)
    
    # 如果有文件上传，使用流式响应
    if file:
        return StreamingResponse(
            _chat_with_file_stream(file, message, session_id, user_id, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # 否则使用传统JSON响应（兼容旧接口）
    try:
        # 解析知识库ID
        kb_ids = None
        if knowledge_base_ids:
            try:
                kb_ids = [UUID(id.strip()) for id in knowledge_base_ids.split(",") if id.strip()]
            except:
                pass
        
        # 1. 自动创建 session_id（如果未提供）
        if not session_id:
            session_id = str(uuid4())
            logger.info(f"✓ 自动创建新会话: session_id={session_id}")
        
        # 2. 验证知识库（如果提供了）
        if kb_ids:
            for kb_id in kb_ids:
                kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
                if not kb:
                    raise HTTPException(
                        status_code=404,
                        detail=f"知识库不存在: {kb_id}"
                    )
        
        # 3. 调用智能体（支持 RAG）
        response_text, actual_session_id, rag_sources = await run_agent_with_rag(
            input_text=message,
            user_id=user_id,
            session_id=session_id,
            knowledge_base_ids=kb_ids,
            use_rag=use_rag,
            rag_top_k=rag_top_k,
            enable_rerank=enable_rerank
        )
        
        # 4. 构建响应
        response = ChatResponse(
            session_id=actual_session_id,
            user_id=user_id,
            message=message,
            response=response_text,
            sources=rag_sources,
            knowledge_base_ids=[str(kb_id) for kb_id in kb_ids] if kb_ids else None,
            created_at=datetime.now()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {str(e)}")

@router.post("/upload", response_model=DocumentResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    knowledge_base_ids: str = Query("", description="逗号分隔的知识库ID，如 'id1,id2,id3'"),
    db: Session = Depends(get_db)
):
    """上传文档到 MinIO 并关联到知识库"""
    logger.info(f"收到文件上传请求: filename={file.filename}, content_type={file.content_type}, kb_ids={knowledge_base_ids}")
    
    # 验证文件名
    if not file.filename:
        logger.error("上传文件名为空")
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    # 校验文件扩展名（支持 rag.ingestion 中声明的全部格式）
    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    
    logger.debug(f"文件扩展名: {ext}, 支持列表: {SUPPORTED_MARKDOWN_EXTENSIONS}")
    
    if not ext or ext not in SUPPORTED_MARKDOWN_EXTENSIONS:
        logger.warning(f"上传文件格式不支持: {file.filename}, 扩展名: {ext}")
        allowed_exts = ", ".join(sorted(SUPPORTED_MARKDOWN_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext or '(无扩展名)'}。允许的格式: {allowed_exts}"
        )
    
    # content_type 兜底，避免默认写成 application/pdf
    content_type = file.content_type or EXTENSION_CONTENT_TYPE.get(ext, "application/octet-stream")
    logger.debug(f"最终 content_type: {content_type}")
    
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
            content_type=content_type
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
            content_type=content_type,
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
        
        # 构建响应，确保所有必需字段都存在
        response_data = {
            "id": db_doc.id,
            "original_filename": db_doc.original_filename,
            "storage_object_name": db_doc.storage_object_name,
            "storage_path": db_doc.storage_path,
            "file_download_url": db_doc.file_download_url,
            "file_size": db_doc.file_size,
            "content_type": db_doc.content_type,
            "upload_date": db_doc.upload_date,
            "is_processed": db_doc.is_processed,
            "content_markdown": db_doc.content_markdown,
            "knowledge_bases": [KnowledgeBaseResponse.model_validate(kb) for kb in db_doc.knowledge_bases] if db_doc.knowledge_bases else []
        }
        
        logger.debug(f"响应数据: {response_data}")
        response = DocumentResponse(**response_data)
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
    response_data.document_count = KnowledgeBaseService.get_document_count(db_kb, db)
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
            document_count=KnowledgeBaseService.get_document_count(kb, db)
        )
        for kb in kbs
    ]

@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(kb_id: UUID, db: Session = Depends(get_db)):
    """获取单个知识库详情"""
    db_kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
    
    # 使用 DAO 方法查询文档，避免访问关系属性（兼容迁移前的数据库结构）
    from dao import DocumentDAO
    docs = DocumentDAO.list_by_knowledge_base(db, kb_id)
    
    return KnowledgeBaseDetailResponse(
        id=db_kb.id,
        name=db_kb.name,
        description=db_kb.description,
        created_at=db_kb.created_at,
        updated_at=db_kb.updated_at,
        document_count=KnowledgeBaseService.get_document_count(db_kb, db),
        documents=[DocumentSimpleResponse.model_validate(doc) for doc in docs]
    )

@router.put("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(kb_id: UUID, kb_update: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """更新知识库"""
    db_kb = KnowledgeBaseService.update_knowledge_base(db, kb_id, kb_update)
    
    response_data = KnowledgeBaseResponse.model_validate(db_kb)
    response_data.document_count = KnowledgeBaseService.get_document_count(db_kb, db)
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
            original_filename=doc.original_filename,
            storage_object_name=doc.storage_object_name,
            storage_path=doc.storage_path,
            file_download_url=doc.file_download_url,
            file_size=doc.file_size,
            content_type=doc.content_type,
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

@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: UUID, doc_update: DocumentUpdate, db: Session = Depends(get_db)):
    """更新文档"""
    db_doc = DocumentService.update_document(db, doc_id, doc_update)
    
    return DocumentResponse(
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
    session_id: Optional[str] = Field(None, description="会话 ID（用于临时文件）")
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
    logger.info(f"收到搜索请求: query={request.query[:50]}..., kb_ids={request.knowledge_base_ids}, session_id={request.session_id}")
    
    try:
        from services.rag_service import search_documents
        
        results = search_documents(
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids,
            session_id=request.session_id,
            top_k=request.top_k
        )
        
        logger.info(f"搜索成功: results_count={len(results)}")
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"搜索失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== 会话历史 API =====

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    获取会话消息列表（简化版，仅返回角色和文本）
    """
    try:
        # 查找会话
        db_session = db.query(DBSessionModel).filter(
            DBSessionModel.session_id == session_id,
            DBSessionModel.user_id == user_id
        ).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = []
        logger.info(f"开始提取会话消息: session_id={session_id}, 消息数量={len(db_session.messages)}")
        
        for idx, msg in enumerate(db_session.messages):
            try:
                content_data = msg.content if isinstance(msg.content, dict) else \
                    json.loads(msg.content) if isinstance(msg.content, str) else {}
                
                text = ""
                
                # 检查是否是 Event 格式（新格式：包含 author, content, timestamp 等）
                if isinstance(content_data, dict) and "content" in content_data:
                    # 新格式：Event 对象，content 字段包含 Content 对象
                    event_content = content_data.get("content", {})
                    if isinstance(event_content, dict):
                        parts = event_content.get("parts", [])
                        if parts and isinstance(parts, list):
                            # 提取所有文本部分
                            text_parts = []
                            for part in parts:
                                if isinstance(part, dict):
                                    part_text = part.get("text", "")
                                    if part_text:
                                        text_parts.append(part_text)
                                elif hasattr(part, "text"):
                                    text_parts.append(part.text)
                            text = "".join(text_parts)
                            logger.debug(f"  消息 {idx+1}: 从 Event.content.parts 提取文本，长度={len(text)}")
                # 检查是否是 Content 格式（旧格式：直接包含 parts）
                elif isinstance(content_data, dict) and "parts" in content_data:
                    # 旧格式：直接是 Content 对象
                    parts = content_data.get("parts", [])
                    if parts and isinstance(parts, list):
                        text_parts = []
                        for part in parts:
                            if isinstance(part, dict):
                                part_text = part.get("text", "")
                                if part_text:
                                    text_parts.append(part_text)
                            elif hasattr(part, "text"):
                                text_parts.append(part.text)
                        text = "".join(text_parts)
                        logger.debug(f"  消息 {idx+1}: 从 Content.parts 提取文本，长度={len(text)}")
                else:
                    # 尝试其他可能的格式
                    if isinstance(content_data, dict):
                        # 尝试直接获取 text 字段
                        text = content_data.get("text", "")
                        if not text and "data" in content_data:
                            # 尝试从 data 中获取
                            data = content_data.get("data", {})
                            if isinstance(data, dict):
                                text = data.get("text", "")
                        logger.debug(f"  消息 {idx+1}: 尝试其他格式提取文本，长度={len(text)}")
                
                # 如果仍然没有文本，记录详细信息用于调试
                if not text:
                    logger.warning(f"  消息 {idx+1} 无法提取文本: role={msg.role}, content_keys={list(content_data.keys()) if isinstance(content_data, dict) else 'N/A'}, content_sample={str(content_data)[:200] if isinstance(content_data, dict) else str(content_data)[:200]}")
                
                # 标准化 role：'model' -> 'agent'（前端期望的格式）
                role = msg.role
                if role == "model":
                    role = "agent"
                elif role not in ["user", "agent"]:
                    # 如果 role 不是标准值，尝试从 event 中获取
                    if isinstance(content_data, dict) and "author" in content_data:
                        role = content_data.get("author", role)
                        if role == "model":
                            role = "agent"
                
                messages.append({
                    "role": role,
                    "text": text,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
            except Exception as e:
                logger.error(f"  消息 {idx+1} 处理失败: {type(e).__name__}: {str(e)}", exc_info=True)
                # 即使处理失败，也添加一条空消息，避免索引错乱
                messages.append({
                    "role": msg.role or "user",
                    "text": f"[消息解析失败: {str(e)[:50]}]",
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
        
        text_count = sum(1 for m in messages if m['text'] and len(m['text'].strip()) > 0)
        logger.info(f"✓ 成功提取 {len(messages)} 条消息，其中 {text_count} 条有文本内容")
        return {"session_id": session_id, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== 会话历史 API =====

@router.get("/sessions")
async def list_sessions(
    user_id: str = "default_user",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取用户会话列表"""
    try:
        from services.session_service import get_session_service
        from models.sql import Session as DBSessionModel
        
        session_service = get_session_service()
        
        result = await session_service.list_sessions(
            app_name="paper_agent",
            user_id=user_id
        )
        
        # 转换为前端需要的格式
        sessions = []
        for session in result.sessions[skip:skip+limit]:
            # 获取第一条用户消息作为标题
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session.id
            ).first()
            
            title = "新对话"
            last_message_time = session.last_update_time
            
            if db_session and db_session.messages:
                # 查找第一条用户消息
                user_message = next(
                    (msg for msg in db_session.messages if msg.role == "user"),
                    None
                )
                if user_message and user_message.content:
                    content_data = user_message.content if isinstance(user_message.content, dict) else json.loads(user_message.content) if isinstance(user_message.content, str) else {}
                    
                    text = ""
                    # 检查是否是 Event 格式
                    if isinstance(content_data, dict) and "content" in content_data:
                        event_content = content_data.get("content", {})
                        if isinstance(event_content, dict):
                            parts = event_content.get("parts", [])
                            if parts and len(parts) > 0:
                                first_part = parts[0]
                                if isinstance(first_part, dict):
                                    text = first_part.get("text", "")
                    # 检查是否是 Content 格式
                    elif isinstance(content_data, dict) and "parts" in content_data:
                        parts = content_data.get("parts", [])
                        if parts and len(parts) > 0:
                            first_part = parts[0]
                            if isinstance(first_part, dict):
                                text = first_part.get("text", "")
                    
                    if text:
                        title = text[:50] + "..." if len(text) > 50 else text
                
                # 获取最后一条消息的时间
                last_msg = db_session.messages[-1] if db_session.messages else None
                if last_msg:
                    last_message_time = last_msg.created_at.timestamp() if hasattr(last_msg.created_at, 'timestamp') else session.last_update_time
            
            sessions.append({
                "session_id": session.id,
                "title": title,
                "last_message_time": last_message_time,
                "created_at": db_session.created_at.isoformat() if db_session and db_session.created_at else None,
                "updated_at": db_session.updated_at.isoformat() if db_session and db_session.updated_at else None,
            })
        
        return {
            "sessions": sessions,
            "total": len(result.sessions)
        }
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/download-url")
async def get_document_download_url(doc_id: UUID, db: Session = Depends(get_db)):
    """获取文档的下载URL（重新生成预签名URL）"""
    try:
        db_doc = DocumentService.get_document_by_id(db, doc_id)
        if not db_doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 重新生成预签名URL
        storage_service = get_storage_service()
        new_url = storage_service.get_presigned_url(db_doc.storage_object_name)
        
        # 更新数据库中的URL
        db_doc.file_download_url = new_url
        db.commit()
        
        return {
            "file_download_url": new_url,
            "storage_object_name": db_doc.storage_object_name
        }
    except Exception as e:
        logger.error(f"获取文档下载URL失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== 翻译 API =====

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    翻译文本
    
    支持多种翻译服务提供商：
    - google: Google Translate（默认）
    - baidu: 百度翻译
    - alibaba: 阿里翻译
    - youdao: 有道翻译
    - tencent: 腾讯翻译
    - deepl: DeepL（需要 API key）
    - bing: Bing Translator
    - sogou: 搜狗翻译
    """
    logger.info(f"收到翻译请求: from={request.from_language}, to={request.to_language}, provider={request.provider}, text_length={len(request.text)}")
    
    try:
        from services.translation_service import TranslationService
        
        if not TranslationService.is_available():
            raise HTTPException(
                status_code=503,
                detail="翻译服务不可用，请确保已安装 translators 库: pip install translators"
            )
        
        result = TranslationService.translate(
            text=request.text,
            from_language=request.from_language,
            to_language=request.to_language,
            provider=request.provider or "google"
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"翻译失败: {result.get('error', '未知错误')}"
            )
        
        logger.info(f"翻译成功: provider={result['provider']}, result_length={len(result['translated_text'])}")
        return TranslationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"翻译请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"翻译请求失败: {str(e)}")


@router.post("/translate/batch", response_model=List[TranslationResponse])
async def batch_translate_texts(request: BatchTranslationRequest):
    """
    批量翻译文本
    
    支持一次翻译多个文本，使用相同的语言设置
    """
    logger.info(f"收到批量翻译请求: count={len(request.texts)}, from={request.from_language}, to={request.to_language}, provider={request.provider}")
    
    try:
        from services.translation_service import TranslationService
        
        if not TranslationService.is_available():
            raise HTTPException(
                status_code=503,
                detail="翻译服务不可用，请确保已安装 translators 库: pip install translators"
            )
        
        results = TranslationService.batch_translate(
            texts=request.texts,
            from_language=request.from_language,
            to_language=request.to_language,
            provider=request.provider or "google"
        )
        
        logger.info(f"批量翻译完成: success_count={sum(1 for r in results if r['success'])}/{len(results)}")
        return [TranslationResponse(**result) for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量翻译请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量翻译请求失败: {str(e)}")


@router.post("/translate/detect", response_model=LanguageDetectionResponse)
async def detect_language(request: LanguageDetectionRequest):
    """
    检测文本语言
    
    自动检测文本的语言代码
    """
    logger.info(f"收到语言检测请求: text_length={len(request.text)}, provider={request.provider}")
    
    try:
        from services.translation_service import TranslationService
        
        if not TranslationService.is_available():
            raise HTTPException(
                status_code=503,
                detail="翻译服务不可用，请确保已安装 translators 库: pip install translators"
            )
        
        detected = TranslationService.detect_language(
            text=request.text,
            provider=request.provider or "google"
        )
        
        success = detected is not None
        logger.info(f"语言检测完成: detected={detected}, success={success}")
        
        return LanguageDetectionResponse(
            text=request.text,
            detected_language=detected,
            provider=request.provider or "google",
            success=success,
            error=None if success else "无法检测语言"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语言检测请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语言检测请求失败: {str(e)}")


@router.get("/translate/providers")
async def get_translation_providers():
    """
    获取支持的翻译服务提供商列表
    """
    try:
        from services.translation_service import TranslationService
        
        return {
            "available": TranslationService.is_available(),
            "providers": TranslationService.SUPPORTED_PROVIDERS,
            "default": "google"
        }
    except Exception as e:
        logger.error(f"获取翻译提供商列表失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate/document")
async def translate_document(
    file: UploadFile = File(...),
    from_language: str = Form("auto"),
    to_language: str = Form(...),
    provider: str = Form("google"),
    db: Session = Depends(get_db)
):
    """
    翻译文档（支持 PDF、DOCX、TXT 等格式）
    
    流程：
    1. 提取文档文本内容
    2. 翻译文本
    3. 返回翻译后的文本内容（Markdown 格式）
    """
    logger.info(f"收到文档翻译请求: filename={file.filename}, from={from_language}, to={to_language}, provider={provider}")
    
    try:
        from services.translation_service import TranslationService
        from rag.ingestion import convert_file_to_markdown
        import tempfile
        import os
        
        if not TranslationService.is_available():
            raise HTTPException(
                status_code=503,
                detail="翻译服务不可用，请确保已安装 translators 库: pip install translators"
            )
        
        # 1. 保存上传的文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            # 2. 提取文档文本内容（转换为 Markdown）
            logger.info("开始提取文档文本...")
            markdown_text = convert_file_to_markdown(tmp_file_path)
            logger.info(f"文档文本提取完成，长度: {len(markdown_text)}")
            
            if not markdown_text or len(markdown_text.strip()) == 0:
                raise HTTPException(status_code=400, detail="文档内容为空，无法翻译")
            
            # 3. 将文本分块（避免单次翻译文本过长）
            from rag.ingestion import chunk_text
            chunks = chunk_text(markdown_text, chunk_size=2000, chunk_overlap=200)
            logger.info(f"文档分块完成，共 {len(chunks)} 个块")
            
            # 4. 批量翻译所有块
            logger.info("开始翻译文档...")
            translated_chunks = []
            failed_count = 0
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"翻译块 {i}/{len(chunks)} (长度: {len(chunk)})...")
                result = TranslationService.translate(
                    text=chunk,
                    from_language=from_language,
                    to_language=to_language,
                    provider=provider
                )
                
                if result["success"] and result["translated_text"]:
                    translated_text = result["translated_text"]
                    # 检查翻译结果是否与原文相同（可能是翻译失败）
                    if translated_text.strip() == chunk.strip() and len(chunk.strip()) > 10:
                        logger.warning(f"块 {i} 翻译结果与原文相同，可能翻译失败")
                        failed_count += 1
                    translated_chunks.append(translated_text)
                else:
                    error_msg = result.get('error', '未知错误')
                    logger.warning(f"块 {i} 翻译失败: {error_msg}")
                    failed_count += 1
                    # 如果翻译失败，保留原文
                    translated_chunks.append(chunk)
            
            if failed_count > 0:
                logger.warning(f"翻译完成，但有 {failed_count}/{len(chunks)} 个块翻译失败或结果异常")
            
            # 5. 合并翻译后的文本
            translated_text = "\n\n".join(translated_chunks)
            logger.info(f"文档翻译完成，翻译后长度: {len(translated_text)}")
            
            return {
                "original_text": markdown_text,
                "translated_text": translated_text,
                "from_language": from_language,
                "to_language": to_language,
                "provider": provider,
                "original_filename": file.filename,
                "chunks_count": len(chunks),
                "success": True
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                logger.debug(f"已删除临时文件: {tmp_file_path}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档翻译失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档翻译失败: {str(e)}")