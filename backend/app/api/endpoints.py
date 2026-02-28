from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator, Dict, Any
from uuid import UUID, uuid4
import shutil
import os
import json
import tempfile
import queue
import threading
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from core.db import get_db
from core.logger import LoggerFactory
from agents.flow import run_agent_with_rag, run_agent_with_rag_stream
from agents.education_agent import create_agent as create_education_agent
from agents.research_management_agent import create_agent as create_research_management_agent
from agents.industry_application_agent import create_agent as create_industry_application_agent
from agents.academic_publishing_agent import create_agent as create_academic_publishing_agent
from agents.coordinator_agent import create_coordinator_agent
from agents.a2a_service import (
    initialize_agents,
    get_registered_agents,
    call_agent
)
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
from dao import ModelConfigurationDAO
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
    SkillInfo,
    VectorizationStep,
    TranslationRequest,
    TranslationResponse,
    BatchTranslationRequest,
    LanguageDetectionRequest,
    LanguageDetectionResponse,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatHistoryDetailResponse,
    ChatAttachmentCreate,
    ChatAttachmentResponse
)
from models.sql import Session as DBSessionModel, SessionMessage, ChatSession, ChatMessage, ChatHistory, ChatAttachment
from services.chat_service import ChatService

# 创建日志记录器
logger = LoggerFactory.get_api_logger(__name__)

router = APIRouter()

# ===== 任务管理器：用于跟踪和中断流式任务 =====
class TaskManager:
    """管理正在运行的流式任务，支持中断"""
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}  # {task_id: {task, cancelled, session_id}}
        self._lock = asyncio.Lock()
    
    async def register_task(self, task_id: str, task: asyncio.Task, session_id: Optional[str] = None):
        """注册一个任务"""
        async with self._lock:
            self._tasks[task_id] = {
                "task": task,
                "cancelled": False,
                "session_id": session_id
            }
            logger.info(f"✓ 注册任务: task_id={task_id}, session_id={session_id}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消一个任务"""
        async with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: task_id={task_id}")
                return False
            
            task_info = self._tasks[task_id]
            if task_info["cancelled"]:
                logger.info(f"任务已被取消: task_id={task_id}")
                return True
            
            task_info["cancelled"] = True
            task = task_info["task"]
            
            # 取消任务
            if not task.done():
                task.cancel()
                logger.info(f"✓ 已取消任务: task_id={task_id}")
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"✓ 任务已成功取消: task_id={task_id}")
                except Exception as e:
                    logger.warning(f"取消任务时出现异常: {e}")
            
            return True
    
    async def cancel_by_session(self, session_id: str) -> int:
        """根据 session_id 取消所有相关任务"""
        async with self._lock:
            cancelled_count = 0
            for task_id, task_info in list(self._tasks.items()):
                if task_info["session_id"] == session_id and not task_info["cancelled"]:
                    task_info["cancelled"] = True
                    task = task_info["task"]
                    if not task.done():
                        task.cancel()
                        cancelled_count += 1
                        logger.info(f"✓ 已取消任务: task_id={task_id}, session_id={session_id}")
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.warning(f"取消任务时出现异常: {e}")
            return cancelled_count
    
    async def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已被取消"""
        async with self._lock:
            if task_id not in self._tasks:
                return False
            return self._tasks[task_id]["cancelled"]
    
    async def unregister_task(self, task_id: str):
        """注销一个任务"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"✓ 注销任务: task_id={task_id}")

# 全局任务管理器实例
task_manager = TaskManager()

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

async def _chat_stream(
    message: str,
    session_id: Optional[str],
    user_id: str,
    db: Session,
    agent_config_id: Optional[UUID] = None,
    knowledge_base_ids: Optional[List[UUID]] = None,
    use_rag: bool = False,
    rag_top_k: int = 5,
    enable_rerank: bool = True,
    model_id: Optional[UUID] = None,
    use_multi_agent: bool = False
) -> AsyncGenerator[str, None]:
    """处理无文件的聊天请求（流式响应）"""
    # 生成任务ID
    task_id = str(uuid4())
    event_queue = asyncio.Queue()
    done = asyncio.Event()
    error_occurred = None
    final_result = None
    cancelled = False
    
    async def yield_event(event_type: str, event_data: Dict[str, Any]):
        """事件回调函数"""
        # 检查是否已取消
        if await task_manager.is_cancelled(task_id):
            return
        await event_queue.put((event_type, event_data))
    
    async def run_agent_task():
        """在后台任务中运行agent"""
        nonlocal error_occurred, final_result, cancelled
        try:
            # 检查是否已取消
            if await task_manager.is_cancelled(task_id):
                cancelled = True
                logger.info(f"任务在启动前已被取消: task_id={task_id}")
                return
            
            result = await run_agent_with_rag_stream(
                input_text=message,
                user_id=user_id,
                session_id=session_id,
                agent_config_id=agent_config_id,
                knowledge_base_ids=knowledge_base_ids,
                use_rag=use_rag,
                rag_top_k=rag_top_k,
                enable_rerank=enable_rerank,
                yield_event=yield_event,
                model_id=model_id,
                db=db,
                use_multi_agent=use_multi_agent,
                cancellation_flag=lambda: task_manager.is_cancelled(task_id)
            )
            final_result = result
        except asyncio.CancelledError:
            cancelled = True
            logger.info(f"✓ 任务已被取消: task_id={task_id}")
            raise
        except Exception as e:
            if not cancelled:
                error_occurred = e
        finally:
            done.set()
    
    try:
        # 启动agent任务
        agent_task = asyncio.create_task(run_agent_task())
        
        # 注册任务到管理器
        await task_manager.register_task(task_id, agent_task, session_id)
        
        # 流式发送事件
        while True:
            # 检查是否已取消
            if await task_manager.is_cancelled(task_id):
                cancelled = True
                logger.info(f"检测到任务已取消，停止流式输出: task_id={task_id}")
                # 取消任务
                if not agent_task.done():
                    agent_task.cancel()
                yield _format_sse_event("cancelled", {
                    "message": "对话已中断",
                    "task_id": task_id
                })
                break
            
            # 优先处理队列中的事件
            try:
                # 使用 get_nowait 非阻塞获取事件
                while True:
                    try:
                        event_type, event_data = event_queue.get_nowait()
                        yield _format_sse_event(event_type, event_data)
                    except asyncio.QueueEmpty:
                        break
            except Exception as e:
                logger.warning(f"处理事件队列时出错: {e}")
            
            # 检查任务是否完成
            if done.is_set():
                # 任务完成，再处理一次队列中剩余的事件
                try:
                    while True:
                        try:
                            event_type, event_data = event_queue.get_nowait()
                            yield _format_sse_event(event_type, event_data)
                        except asyncio.QueueEmpty:
                            break
                except Exception as e:
                    logger.warning(f"处理剩余事件时出错: {e}")
                break
            
            # 等待一小段时间，避免CPU占用过高
            await asyncio.sleep(0.01)
        
        # 等待agent任务完成（如果还没完成）
        if not agent_task.done():
            try:
                await agent_task
            except asyncio.CancelledError:
                cancelled = True
                logger.info(f"✓ 任务已成功取消: task_id={task_id}")
        
        # 检查是否有错误（且不是取消错误）
        if error_occurred and not cancelled:
            raise error_occurred
        
        # 发送完成事件（如果没有被取消）
        if final_result and not cancelled:
            response_text, actual_session_id, rag_sources, activated_skills, skills_prompt = final_result
            yield _format_sse_event("agent_complete", {
                "session_id": actual_session_id,
                "user_id": user_id,
                "message": message,
                "response": response_text,
                "sources": rag_sources,
                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else None,
                "activated_skills": activated_skills,
                "skills_prompt": skills_prompt,
                "created_at": datetime.now().isoformat()
            })
        
    except asyncio.CancelledError:
        cancelled = True
        logger.info(f"✓ 流式响应已取消: task_id={task_id}")
        yield _format_sse_event("cancelled", {
            "message": "对话已中断",
            "task_id": task_id
        })
    except Exception as e:
        if not cancelled:
            logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
            yield _format_sse_event("error", {
                "error": f"处理失败: {str(e)}"
            })
    finally:
        # 注销任务
        await task_manager.unregister_task(task_id)

async def _chat_with_file_stream(
    file: UploadFile,
    message: str,
    session_id: Optional[str],
    user_id: str,
    db: Session,
    agent_config_id: Optional[UUID] = None,
    knowledge_base_ids: Optional[List[UUID]] = None,
    use_rag: bool = False
) -> AsyncGenerator[str, None]:
    """处理带文件上传的聊天请求（流式响应）"""
    # 生成任务ID
    task_id = str(uuid4())
    temp_file_path = None
    document_id = None
    cancelled = False
    
    try:
        # 1. 自动创建 session_id（如果未提供）
        if not session_id:
            session_id = str(uuid4())
            logger.info(f"✓ 自动创建新会话: session_id={session_id}")
        
        # 2. 获取文件信息（不限制文件类型，允许所有文件上传到对话）
        _, ext = os.path.splitext(file.filename or "")
        ext = ext.lower() if ext else ""
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
        
        # 7. 执行对话（使用临时文件进行RAG，流式输出）
        # 如果提供了知识库，使用知识库进行 RAG；否则使用临时文件进行 RAG
        use_rag_final = use_rag or knowledge_base_ids is not None
        kb_ids_final = knowledge_base_ids if knowledge_base_ids else None
        
        # 使用流式函数
        event_queue = asyncio.Queue()
        done = asyncio.Event()
        error_occurred = None
        final_result = None
        
        async def yield_event(event_type: str, event_data: Dict[str, Any]):
            """事件回调函数"""
            # 检查是否已取消
            if await task_manager.is_cancelled(task_id):
                return
            await event_queue.put((event_type, event_data))
        
        async def run_agent_task():
            """在后台任务中运行agent"""
            nonlocal error_occurred, final_result, cancelled
            try:
                # 检查是否已取消
                if await task_manager.is_cancelled(task_id):
                    cancelled = True
                    logger.info(f"任务在启动前已被取消: task_id={task_id}")
                    return
                
                result = await run_agent_with_rag_stream(
                    input_text=message,
                    user_id=user_id,
                    session_id=session_id,
                    agent_config_id=agent_config_id,
                    knowledge_base_ids=kb_ids_final,
                    use_rag=use_rag_final,
                    rag_top_k=5,
                    enable_rerank=True,
                    session_id_for_temp_files=session_id if not kb_ids_final else None,
                    yield_event=yield_event,
                    cancellation_flag=lambda: task_manager.is_cancelled(task_id)
                )
                final_result = result
            except asyncio.CancelledError:
                cancelled = True
                logger.info(f"✓ 任务已被取消: task_id={task_id}")
                raise
            except Exception as e:
                if not cancelled:
                    error_occurred = e
            finally:
                done.set()
        
        # 启动agent任务
        agent_task = asyncio.create_task(run_agent_task())
        
        # 注册任务到管理器
        await task_manager.register_task(task_id, agent_task, session_id)
        
        # 流式发送事件
        while True:
            # 检查是否已取消
            if await task_manager.is_cancelled(task_id):
                cancelled = True
                logger.info(f"检测到任务已取消，停止流式输出: task_id={task_id}")
                # 取消任务
                if not agent_task.done():
                    agent_task.cancel()
                yield _format_sse_event("cancelled", {
                    "message": "对话已中断",
                    "task_id": task_id
                })
                break
            # 优先处理队列中的事件
            try:
                # 使用 get_nowait 非阻塞获取事件
                while True:
                    try:
                        event_type, event_data = event_queue.get_nowait()
                        yield _format_sse_event(event_type, event_data)
                    except asyncio.QueueEmpty:
                        break
            except Exception as e:
                logger.warning(f"处理事件队列时出错: {e}")
            
            # 检查任务是否完成
            if done.is_set():
                # 任务完成，再处理一次队列中剩余的事件
                try:
                    while True:
                        try:
                            event_type, event_data = event_queue.get_nowait()
                            yield _format_sse_event(event_type, event_data)
                        except asyncio.QueueEmpty:
                            break
                except Exception as e:
                    logger.warning(f"处理剩余事件时出错: {e}")
                break
            
            # 等待一小段时间，避免CPU占用过高
            await asyncio.sleep(0.01)
        
        # 等待agent任务完成（如果还没完成）
        if not agent_task.done():
            try:
                await agent_task
            except asyncio.CancelledError:
                cancelled = True
                logger.info(f"✓ 任务已成功取消: task_id={task_id}")
        
        # 检查是否有错误（且不是取消错误）
        if error_occurred and not cancelled:
            raise error_occurred
        
        # 发送完成事件（如果没有被取消）
        if final_result and not cancelled:
            response_text, actual_session_id, rag_sources, activated_skills, skills_prompt = final_result
            yield _format_sse_event("agent_complete", {
                "session_id": actual_session_id,
                "user_id": user_id,
                "message": message,
                "response": response_text,
                "sources": rag_sources,
                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else None,
                "activated_skills": activated_skills,
                "skills_prompt": skills_prompt,
                "created_at": datetime.now().isoformat()
            })
        
    except asyncio.CancelledError:
        cancelled = True
        logger.info(f"✓ 流式响应已取消: task_id={task_id}")
        yield _format_sse_event("cancelled", {
            "message": "对话已中断",
            "task_id": task_id
        })
    except Exception as e:
        if not cancelled:
            logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {str(e)}", exc_info=True)
            yield _format_sse_event("error", {
                "error": f"处理失败: {str(e)}"
            })
    finally:
        # 注销任务
        await task_manager.unregister_task(task_id)
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

@router.post("/chat")
async def chat(
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """
    智能对话接口（支持 JSON 格式，SSE流式响应）
    
    功能特性：
    - 自动创建 Session：如果不传 session_id，自动使用 UUID 创建新会话
    - 多知识库选择：支持选择多个知识库进行 RAG 检索
    - RAG 问答：选择知识库后自动启用 RAG 检索，从向量数据库检索相关内容
    - 会话持久化：基于 PostgreSQL 的 Session 存储（符合 ADK 官方文档规范）
    - SSE流式输出：实时显示Skills加载、RAG检索和Agent回复
    
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
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type. Use application/json")
    
    logger.info("=" * 80)
    logger.info(f"收到聊天请求: message={req.message[:100]}...")
    logger.info(f"参数: session_id={req.session_id}, user_id={req.user_id}")
    logger.info(f"知识库: kb_ids={req.knowledge_base_ids}, use_rag={req.use_rag}")
    logger.info(f"Agent配置: agent_config_id={req.agent_config_id}")
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
        # 注意：req.knowledge_base_ids 已经是 List[UUID] 类型（Pydantic已转换），不需要再次转换
        kb_ids = None
        if req.knowledge_base_ids:
            kb_ids = req.knowledge_base_ids
            for kb_id in kb_ids:
                kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
                if not kb:
                    logger.warning(f"知识库不存在: {kb_id}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"知识库不存在: {kb_id}"
                    )
            logger.info(f"✓ 知识库验证通过: {len(kb_ids)} 个知识库")
        
        # 3. 使用流式响应
        return StreamingResponse(
            _chat_stream(
                message=req.message,
                session_id=session_id,
                user_id=user_id,
                db=db,
                agent_config_id=req.agent_config_id,
                knowledge_base_ids=kb_ids,
                use_rag=req.use_rag,
                rag_top_k=req.rag_top_k,
                enable_rerank=req.enable_rerank,
                model_id=req.model_id,
                use_multi_agent=req.use_multi_agent or False
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        try:
            if isinstance(error_msg, bytes):
                error_msg = error_msg.decode('utf-8', errors='replace')
            else:
                error_msg = str(error_msg).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            error_msg = "An error occurred while processing the request"
        
        logger.error(f"❌ 聊天请求失败: {type(e).__name__}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {error_msg}")

@router.post("/chat/cancel")
async def cancel_chat(
    session_id: Optional[str] = Query(None, description="会话ID，用于取消该会话的所有任务"),
    db: Session = Depends(get_db)
):
    """
    中断正在进行的对话任务
    
    功能特性:
    - 如果提供 session_id，将取消该会话的所有正在运行的任务
    - 彻底断开流式响应和后端处理
    """
    try:
        if session_id:
            cancelled_count = await task_manager.cancel_by_session(session_id)
            logger.info(f"✓ 已取消会话 {session_id} 的 {cancelled_count} 个任务")
            return {
                "success": True,
                "message": f"已取消 {cancelled_count} 个任务",
                "session_id": session_id,
                "cancelled_count": cancelled_count
            }
        else:
            raise HTTPException(status_code=400, detail="必须提供 session_id")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.post("/chat/form", response_model=ChatResponse)
async def chat_form(
    file: Optional[UploadFile] = File(None),
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    user_id: str = Form("default_user"),
    agent_config_id: Optional[str] = Form(None),
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
    logger.info(f"Agent配置: agent_config_id={agent_config_id}")
    logger.info("=" * 80)
    
    # 如果有文件上传，使用流式响应
    if file:
        # 解析知识库ID
        kb_ids_for_stream = None
        if knowledge_base_ids:
            try:
                kb_ids_for_stream = [UUID(id.strip()) for id in knowledge_base_ids.split(",") if id.strip()]
                # 验证知识库
                for kb_id in kb_ids_for_stream:
                    kb = KnowledgeBaseService.get_knowledge_base_by_id(db, kb_id)
                    if not kb:
                        raise HTTPException(
                            status_code=404,
                            detail=f"知识库不存在: {kb_id}"
                        )
                use_rag_for_stream = True
            except (ValueError, AttributeError):
                kb_ids_for_stream = None
                use_rag_for_stream = use_rag
        else:
            use_rag_for_stream = use_rag
        
        parsed_agent_config_id = None
        if agent_config_id:
            try:
                parsed_agent_config_id = UUID(agent_config_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="agent_config_id 格式无效")

        return StreamingResponse(
            _chat_with_file_stream(
                file,
                message,
                session_id,
                user_id,
                db,
                parsed_agent_config_id,
                kb_ids_for_stream,
                use_rag_for_stream
            ),
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
        
        parsed_agent_config_id = None
        if agent_config_id:
            try:
                parsed_agent_config_id = UUID(agent_config_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="agent_config_id 格式无效")

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
        response_text, actual_session_id, rag_sources, activated_skills, skills_prompt = await run_agent_with_rag(
            input_text=message,
            user_id=user_id,
            session_id=session_id,
            agent_config_id=parsed_agent_config_id,
            knowledge_base_ids=kb_ids,
            use_rag=use_rag,
            rag_top_k=rag_top_k,
            enable_rerank=enable_rerank,
            db=db
        )
        
        # 转换技能信息格式
        skill_info_list = None
        if activated_skills:
            skill_info_list = [
                SkillInfo(
                    name=skill.get("name", ""),
                    description=skill.get("description", ""),
                    version=skill.get("version")
                )
                for skill in activated_skills
            ]
        
        # 4. 构建响应
        response = ChatResponse(
            session_id=actual_session_id,
            user_id=user_id,
            message=message,
            response=response_text,
            sources=rag_sources,
            knowledge_base_ids=[str(kb_id) for kb_id in kb_ids] if kb_ids else None,
            activated_skills=skill_info_list,
            skills_prompt=skills_prompt,
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

@router.post("/skills/reload")
async def reload_skills():
    """
    重新加载所有技能（用于修复编码问题或更新技能）
    """
    try:
        skills_manager.reload_skills()
        skills = skills_manager.list_all_skills()
        return {
            "message": "Skills reloaded successfully",
            "count": len(skills),
            "skills": [s["name"] for s in skills]
        }
    except Exception as e:
        logger.error(f"重新加载技能失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新加载技能失败: {str(e)}")

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

@router.post("/model-configurations/sync-from-config")
async def sync_models_from_config(db: Session = Depends(get_db)):
    """从配置文件同步模型到数据库（作为备份）"""
    from core.config import settings
    
    # 从配置文件创建默认模型配置
    default_config = {
        "name": "default_qwen",
        "model_name": settings.DEFAULT_LLM_MODEL,
        "api_key": settings.QWEN_API_KEY,
        "base_url": settings.QWEN_BASE_URL,
        "provider": "openai",
        "description": "从配置文件同步的默认模型配置",
        "is_active": False,  # 默认不激活，避免覆盖用户设置
        "temperature": 0.7,
        "max_tokens": None,
        "top_p": None,
        "frequency_penalty": None,
        "presence_penalty": None
    }
    
    # 检查是否已存在同名配置
    existing = ModelConfigurationDAO.get_by_name(db, default_config["name"])
    if existing:
        # 更新现有配置（但不改变is_active状态）
        existing.model_name = default_config["model_name"]
        existing.api_key = default_config["api_key"]
        existing.base_url = default_config["base_url"]
        existing.provider = default_config["provider"]
        existing.description = default_config["description"]
        existing.temperature = default_config["temperature"]
        existing.max_tokens = default_config["max_tokens"]
        existing.top_p = default_config["top_p"]
        existing.frequency_penalty = default_config["frequency_penalty"]
        existing.presence_penalty = default_config["presence_penalty"]
        db.commit()
        db.refresh(existing)
        return {
            "message": "模型配置已更新",
            "model": ModelConfigurationResponse.model_validate(existing)
        }
    else:
        # 创建新配置
        from models.schemas import ModelConfigurationCreate
        config_create = ModelConfigurationCreate(**default_config)
        db_model = ModelConfigurationService.create_model_configuration(db, config_create)
        return {
            "message": "模型配置已创建",
            "model": ModelConfigurationResponse.model_validate(db_model)
        }

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
    获取会话消息列表（使用Chat表，仅返回用户和助手消息，简化格式）
    """
    try:
        # 使用Chat表查询
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 只获取用户消息和助手回复（过滤掉system和tool消息）
        chat_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_session.id,
            ChatMessage.role.in_(["user", "assistant"])
        ).order_by(ChatMessage.created_at.asc()).all()
        
        messages = []
        for msg in chat_messages:
            # 标准化 role：'assistant' -> 'agent'（前端期望的格式）
            role = "agent" if msg.role == "assistant" else msg.role
            
            messages.append({
                "role": role,
                "text": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        logger.info(f"✓ 从Chat表获取消息: session_id={session_id}, 消息数量={len(messages)}")
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
    """获取用户会话列表（使用Chat表）"""
    try:
        # 使用Chat表查询会话列表
        chat_sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
        
        sessions = []
        for chat_session in chat_sessions:
            # 获取第一条用户消息作为标题
            first_user_message = db.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id,
                ChatMessage.role == "user"
            ).order_by(ChatMessage.created_at.asc()).first()
            
            title = chat_session.session_title or "新对话"
            if not title or title == "新对话":
                if first_user_message:
                    # 使用用户消息的前50个字符作为标题
                    title = first_user_message.content[:50] if first_user_message.content else "新对话"
            
            # 获取最后一条消息的时间
            last_message = db.query(ChatMessage).filter(
                ChatMessage.session_id == chat_session.id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            last_message_time = 0.0
            if last_message and last_message.created_at:
                try:
                    last_message_time = float(last_message.created_at.timestamp())
                except Exception:
                    last_message_time = 0.0
            elif chat_session.updated_at:
                try:
                    last_message_time = float(chat_session.updated_at.timestamp())
                except Exception:
                    last_message_time = 0.0
            
            sessions.append({
                "session_id": chat_session.session_id,
                "title": title,
                "last_message_time": last_message_time,
                "created_at": chat_session.created_at.isoformat() if chat_session.created_at else None,
                "updated_at": chat_session.updated_at.isoformat() if chat_session.updated_at else None,
            })
        
        return {
            "sessions": sessions,
            "total": len(sessions)
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

# ===== Chat 对话表 API（区别于ADK表） =====

@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    user_id: str = Query("default_user", description="用户ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取用户的Chat会话列表
    """
    try:
        db_sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
        
        return [ChatSessionResponse.model_validate(session) for session in db_sessions]
    except Exception as e:
        logger.error(f"获取Chat会话列表失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取Chat会话详情
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return ChatSessionResponse.model_validate(chat_session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Chat会话详情失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    update_data: ChatSessionUpdate,
    db: Session = Depends(get_db)
):
    """
    更新Chat会话（如修改标题）
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 更新字段
        if update_data.session_title is not None:
            chat_session.session_title = update_data.session_title
        if update_data.custom_metadata is not None:
            chat_session.custom_metadata = update_data.custom_metadata
        
        db.commit()
        db.refresh(chat_session)
        
        return ChatSessionResponse.model_validate(chat_session)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新Chat会话失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    删除Chat会话（级联删除消息和历史记录）
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        db.delete(chat_session)
        db.commit()
        
        return {"success": True, "message": "会话已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除Chat会话失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    role: Optional[str] = Query(None, description="过滤角色：user, assistant, tool, system"),
    message_type: Optional[str] = Query(None, description="过滤消息类型"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取Chat会话的消息列表
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        query = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_session.id
        )
        
        if role:
            query = query.filter(ChatMessage.role == role)
        if message_type:
            query = query.filter(ChatMessage.message_type == message_type)
        
        messages = query.order_by(ChatMessage.created_at.asc()).offset(skip).limit(limit).all()
        
        return [ChatMessageResponse.model_validate(msg) for msg in messages]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Chat消息列表失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== 一键总结为方案 API =====

@router.post("/chat/sessions/{session_id}/generate-summary")
async def generate_summary_plan(
    session_id: str,
    top_k: int = Query(20, ge=1, le=100, description="选择前 K 条重要消息用于总结"),
    max_messages: Optional[int] = Query(None, ge=1, description="最大消息数限制（None 表示不限制）"),
    db: Session = Depends(get_db)
):
    """
    一键总结为方案：从当前会话读取对话历史，生成 MD 方案并上传到 OSS
    
    Args:
        session_id: 会话ID
        top_k: 选择前 K 条重要消息用于总结
        max_messages: 最大消息数限制
    
    Returns:
        Dict[str, Any]: {
            "success": bool,
            "object_name": str,  # MinIO 对象名称
            "download_url": str,  # 下载链接
            "plan_content": str,  # 方案内容预览
            "messages_used": int,  # 使用的消息数量
            "total_messages": int,  # 总消息数量
            "error": str  # 错误信息（如果失败）
        }
    """
    try:
        # 验证会话是否存在
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 导入总结智能体
        from agents.summary_agent import generate_summary_plan
        
        # 调用总结智能体生成方案
        result = await generate_summary_plan(
            session_id=session_id,
            top_k=top_k,
            max_messages=max_messages
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "生成方案失败")
            )
        
        # 保存附件记录到数据库
        try:
            attachment = ChatAttachment(
                session_id=chat_session.id,
                message_id=None,  # 稍后可以通过消息ID关联
                attachment_type="summary",
                file_name=result.get("file_name", ""),
                file_type="markdown",
                file_size=len(result.get("plan_content_full", "").encode('utf-8')),
                storage_object_name=result.get("object_name"),
                download_url=result.get("download_url"),
                preview_url=None,
                description=f"从 {result.get('total_messages', 0)} 条消息中筛选出 {result.get('messages_used', 0)} 条重要消息生成的方案总结",
                attachment_metadata={
                    "messages_used": result.get("messages_used", 0),
                    "total_messages": result.get("total_messages", 0),
                    "plan_content_preview": result.get("plan_content", "")[:500]  # 保存预览内容
                }
            )
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            logger.info(f"✓ 保存附件记录: attachment_id={attachment.id}, file_name={attachment.file_name}")
        except Exception as e:
            logger.error(f"✗ 保存附件记录失败: {type(e).__name__}: {str(e)}", exc_info=True)
            # 不抛出异常，避免影响主流程
        
        return {
            "success": True,
            "data": {
                "object_name": result.get("object_name"),
                "download_url": result.get("download_url"),
                "plan_content": result.get("plan_content", ""),
                "plan_content_full": result.get("plan_content_full", ""),  # 完整内容（用于预览）
                "file_name": result.get("file_name", ""),  # 文件名
                "file_type": "markdown",  # 文件类型
                "messages_used": result.get("messages_used", 0),
                "total_messages": result.get("total_messages", 0),
                "attachment_id": str(attachment.id) if 'attachment' in locals() else None  # 附件ID
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成方案总结失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

from enum import Enum

class AgentType(str, Enum):
    PAPER = "paper"  # 原有的论文智能体
    EDUCATION = "education"  # 教育领域智能体
    RESEARCH_MANAGEMENT = "research_management"  # 科研管理智能体
    INDUSTRY_APPLICATION = "industry_application"  # 产业应用智能体
    ACADEMIC_PUBLISHING = "academic_publishing"  # 学术出版智能体

@router.post("/agents/{agent_type}/chat")
async def chat_with_agent(
    agent_type: AgentType,
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """
    使用指定智能体进行对话

    Args:
        agent_type: 智能体类型
        request_obj: 请求数据
        db: 数据库会话
    """
    content_type = request_obj.headers.get("content-type", "")

    # 解析请求参数
    if "application/json" in content_type:
        try:
            body = await request_obj.json()
            req = ChatRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type. Use application/json")

    logger.info(f"收到{agent_type.value}智能体聊天请求: message={req.message[:100]}...")

    try:
        # 根据智能体类型创建相应的Agent
        if agent_type == AgentType.EDUCATION:
            agent = await create_education_agent()
        elif agent_type == AgentType.RESEARCH_MANAGEMENT:
            agent = await create_research_management_agent()
        elif agent_type == AgentType.INDUSTRY_APPLICATION:
            agent = await create_industry_application_agent()
        elif agent_type == AgentType.ACADEMIC_PUBLISHING:
            agent = await create_academic_publishing_agent()
        else:
            # 默认使用论文智能体
            agent = await create_agent_with_skills()

        # TODO: 实现不同智能体的对话逻辑
        # 这里需要根据不同智能体的特点调整对话处理方式
        response_text, actual_session_id, rag_sources, activated_skills, skills_prompt = await run_agent_with_rag(
            input_text=req.message,
            user_id=req.user_id or "default_user",
            session_id=req.session_id,
            agent_config_id=getattr(req, "agent_config_id", None),
            knowledge_base_ids=req.knowledge_base_ids,
            use_rag=req.use_rag if hasattr(req, 'use_rag') else False,
            rag_top_k=5,
            enable_rerank=True,
            db=db
        )

        return ChatResponse(
            response=response_text,
            session_id=actual_session_id,
            rag_sources=rag_sources,
            activated_skills=activated_skills
        )

    except Exception as e:
        logger.error(f"{agent_type.value}智能体对话失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/sessions/{session_id}/history", response_model=List[ChatHistoryDetailResponse])
async def get_chat_history(
    session_id: str,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取Chat会话的历史记录（包含关联的消息对象）
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        histories = db.query(ChatHistory).filter(
            ChatHistory.session_id == chat_session.id
        ).order_by(ChatHistory.turn_index.desc()).offset(skip).limit(limit).all()
        
        result = []
        for history in histories:
            history_dict = ChatHistoryResponse.model_validate(history).model_dump()
            
            # 加载关联的消息对象
            if history.user_message_id:
                user_msg = db.query(ChatMessage).filter(
                    ChatMessage.id == history.user_message_id
                ).first()
                if user_msg:
                    history_dict["user_message"] = ChatMessageResponse.model_validate(user_msg).model_dump()
            
            if history.assistant_message_id:
                assistant_msg = db.query(ChatMessage).filter(
                    ChatMessage.id == history.assistant_message_id
                ).first()
                if assistant_msg:
                    history_dict["assistant_message"] = ChatMessageResponse.model_validate(assistant_msg).model_dump()
            
            # 加载该轮次相关的附件（通过消息ID关联）
            message_ids = []
            if history.user_message_id:
                message_ids.append(history.user_message_id)
            if history.assistant_message_id:
                message_ids.append(history.assistant_message_id)
            
            attachments = []
            if message_ids:
                attachments = db.query(ChatAttachment).filter(
                    ChatAttachment.session_id == chat_session.id,
                    ChatAttachment.message_id.in_(message_ids)
                ).all()
            
            # 如果没有通过消息ID找到附件，尝试查找该会话的所有附件（按时间排序，取最近的）
            if not attachments:
                # 查找该会话的所有附件，按创建时间排序
                all_attachments = db.query(ChatAttachment).filter(
                    ChatAttachment.session_id == chat_session.id
                ).order_by(ChatAttachment.created_at.desc()).all()
                
                # 如果附件创建时间在该轮次之后，认为是相关的
                if all_attachments and history.created_at:
                    for att in all_attachments:
                        if att.created_at and att.created_at >= history.created_at:
                            attachments.append(att)
                            break  # 只取最近的一个
            
            history_dict["attachments"] = [ChatAttachmentResponse.model_validate(att).model_dump() for att in attachments] if attachments else None
            
            result.append(ChatHistoryDetailResponse.model_validate(history_dict))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Chat历史记录失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/sessions/{session_id}/attachments", response_model=List[ChatAttachmentResponse])
async def get_chat_attachments(
    session_id: str,
    attachment_type: Optional[str] = Query(None, description="过滤附件类型：'upload'、'generated'、'summary' 等"),
    db: Session = Depends(get_db)
):
    """
    获取Chat会话的附件列表
    """
    try:
        chat_session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        query = db.query(ChatAttachment).filter(
            ChatAttachment.session_id == chat_session.id
        )
        
        if attachment_type:
            query = query.filter(ChatAttachment.attachment_type == attachment_type)
        
        attachments = query.order_by(ChatAttachment.created_at.desc()).all()
        
        return [ChatAttachmentResponse.model_validate(att) for att in attachments]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Chat附件列表失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/list")
async def list_agents():
    """
    列出所有可用的智能体
    """
    try:
        # 确保智能体已初始化
        await initialize_agents()
        
        agents = get_registered_agents()
        agent_descriptions = {
            "experiment_replication": "实验复现助手：从论文中提取实验配置并生成可执行代码",
            "paper_writing": "论文写作助手：辅助撰写学术论文，包括大纲生成、段落润色、审稿意见响应",
            "research_trends": "研究趋势分析：分析领域最新动态和发展趋势，预测未来研究方向",
            "cross_domain": "跨领域知识关联：发现不同领域间的知识联系，促进跨领域创新",
            "patent_analysis": "专利分析：评估学术成果的专利转化潜力，协助专利相关任务",
            "tech_transfer": "技术转移助手：将学术研究转化为产业应用，制定商业化路径",
            "paper_agent": "论文智能体：通用学术研究助手，用于论文分析和知识检索"
        }
        
        agent_list = [
            {
                "name": agent_name,
                "description": agent_descriptions.get(agent_name, f"{agent_name} 智能体")
            }
            for agent_name in agents
        ]
        
        return {
            "success": True,
            "agents": agent_list,
            "count": len(agent_list)
        }
    except Exception as e:
        logger.error(f"获取智能体列表失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/coordinator")
async def chat_with_coordinator(
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """
    使用协调智能体进行多智能体协作对话
    
    功能特性：
    - 自动任务分解：复杂任务自动分解为多个子任务
    - 智能体选择：自动选择最合适的智能体执行任务
    - 结果合成：整合多个智能体的输出
    - SSE流式响应：实时显示任务执行状态
    """
    content_type = request_obj.headers.get("content-type", "")
    
    # 解析请求参数
    if "application/json" in content_type:
        try:
            body = await request_obj.json()
            req = ChatRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type. Use application/json")
    
    logger.info("=" * 80)
    logger.info(f"收到协调智能体请求: message={req.message[:100]}...")
    logger.info(f"参数: session_id={req.session_id}, user_id={req.user_id}")
    logger.info("=" * 80)
    
    try:
        # 自动创建 session_id（如果未提供）
        session_id = req.session_id or str(uuid4())
        user_id = req.user_id or "default_user"
        
        # 创建协调智能体
        coordinator_agent = await create_coordinator_agent()
        
        # 使用现有的流式响应逻辑（暂时使用默认的paper_agent流程，后续可以优化为直接使用coordinator_agent）
        # 注意：由于_chat_stream和run_agent_with_rag_stream的架构，暂时通过message来触发协调智能体的逻辑
        # 更好的方案是修改flow.py以支持传入自定义agent
        return StreamingResponse(
            _chat_stream(
                message=f"[COORDINATOR_MODE] {req.message}",  # 添加标记以标识使用协调模式
                session_id=session_id,
                user_id=user_id,
                db=db,
                knowledge_base_ids=req.knowledge_base_ids,
                use_rag=req.use_rag,
                rag_top_k=req.rag_top_k or 5,
                enable_rerank=req.enable_rerank if req.enable_rerank is not None else True,
                model_id=req.model_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        try:
            if isinstance(error_msg, bytes):
                error_msg = error_msg.decode('utf-8', errors='replace')
            else:
                error_msg = str(error_msg).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            error_msg = "An error occurred while processing the request"
        
        logger.error(f"❌ 协调智能体请求失败: {type(e).__name__}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"协调智能体请求失败: {error_msg}")


@router.post("/agents/{agent_name}")
async def call_specific_agent(
    agent_name: str,
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """
    直接调用指定的智能体
    
    Args:
        agent_name: 智能体名称（experiment_replication, paper_writing, research_trends, cross_domain, patent_analysis, tech_transfer, paper_agent）
    """
    content_type = request_obj.headers.get("content-type", "")
    
    # 解析请求参数
    if "application/json" in content_type:
        try:
            body = await request_obj.json()
            req = ChatRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported Content-Type. Use application/json")
    
    logger.info(f"收到直接调用智能体请求: agent_name={agent_name}, message={req.message[:100]}...")
    
    try:
        # 确保智能体已初始化
        await initialize_agents()
        
        # 检查智能体是否存在
        registered_agents = get_registered_agents()
        if agent_name not in registered_agents:
            raise HTTPException(
                status_code=404,
                detail=f"智能体 '{agent_name}' 不存在。可用智能体: {registered_agents}"
            )
        
        # 调用指定智能体
        session_id = req.session_id or f"{agent_name}_{uuid4()}"
        user_id = req.user_id or "default_user"
        
        response = await call_agent(
            agent_name=agent_name,
            message=req.message,
            user_id=user_id,
            session_id=session_id
        )
        
        # 保存对话记录（如果提供了session_id）
        if req.session_id:
            try:
                from services.chat_service import ChatService
                await ChatService.create_or_get_chat_session(
                    session_id=req.session_id,
                    user_id=user_id
                )
                
                await ChatService.save_message(
                    session_id=req.session_id,
                    role="user",
                    message_type="user_message",
                    content=req.message,
                    user_id=user_id
                )
                
                await ChatService.save_message(
                    session_id=req.session_id,
                    role="assistant",
                    message_type="assistant_message",
                    content=response,
                    user_id=user_id
                )
            except Exception as e:
                logger.warning(f"保存对话记录失败（不影响主流程）: {e}")
        
        return ChatResponse(
            message=response,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 调用智能体失败: {type(e).__name__}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"调用智能体失败: {error_msg}")