from google.adk import Runner
from google.adk.sessions import Session
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part
from tools.definitions import scholar_search, knowledge_retriever
from core.config import settings
from core.logger import LoggerFactory
from services.session_service import get_session_service
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import asyncio

logger = LoggerFactory.get_service_logger(__name__)

# Initialize LiteLLM Model
model = LiteLlm(
    model="openai/" + settings.DEFAULT_LLM_MODEL,
    api_base=settings.QWEN_BASE_URL,
    api_key=settings.QWEN_API_KEY,
    # 强制指定提供商为openai-compatible，避免模型映射问题
    custom_llm_provider="openai"

)

# Define the Agent
academic_agent = Agent(
    name="academic_researcher",
    model=model,
    tools=[scholar_search, knowledge_retriever],
    instruction="""You are an academic research assistant. 
    Your goal is to help users find and understand academic papers.
    You have access to a scholar search tool to find real papers and a knowledge retriever to look up information in uploaded documents.
    Always cite your sources when providing information from papers.""",
    generate_content_config={"temperature": 0.7}
)

# Initialize Session Service and Runner
# 使用 PostgreSQL 持久化的 SessionService（根据 ADK 文档 https://adk.wiki/sessions/）
session_service = get_session_service()
logger.info("✓ 使用 PostgreSQL SessionService 进行会话持久化")

runner = Runner(
    agent=academic_agent,
    session_service=session_service,
    app_name="paper_agent"
)


async def run_agent_with_rag(
    input_text: str,
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    knowledge_base_ids: Optional[List[UUID]] = None,
    use_rag: bool = False,
    rag_top_k: int = 5,
    enable_rerank: bool = True,
    session_id_for_temp_files: Optional[str] = None
) -> Tuple[str, str, Optional[List[Dict[str, Any]]]]:
    """
    运行智能体，支持 RAG 检索和 Session 管理
    
    Args:
        input_text: 用户输入文本
        user_id: 用户ID
        session_id: 会话ID（可选，不传则自动创建）
        knowledge_base_ids: 知识库ID列表（可选）
        use_rag: 是否启用RAG检索
        rag_top_k: RAG检索数量
        enable_rerank: 是否启用重排序
    
    Returns:
        Tuple[response_text, actual_session_id, rag_sources]
        - response_text: 智能体回复
        - actual_session_id: 实际使用的会话ID
        - rag_sources: RAG来源列表（如果启用RAG）
    """
    # 如果没有传入 session_id，自动生成一个
    if not session_id:
        session_id = str(uuid4())
        logger.info(f"自动创建新会话: session_id={session_id}")
    else:
        logger.info(f"使用已有会话: session_id={session_id}")
    
    logger.info(f"用户消息: user_id={user_id}, message={input_text[:100]}...")
    
    # 如果传入了知识库ID或临时文件session_id，自动启用RAG
    if knowledge_base_ids or session_id_for_temp_files:
        use_rag = True
        if knowledge_base_ids:
            logger.info(f"检测到知识库选择，自动启用RAG: kb_ids={knowledge_base_ids}")
        if session_id_for_temp_files:
            logger.info(f"检测到临时文件会话，自动启用RAG: session_id={session_id_for_temp_files}")
    
    # RAG检索上下文
    rag_sources = None
    rag_context = ""
    
    if use_rag and (knowledge_base_ids or session_id_for_temp_files):
        # 优先级：临时文件 > 知识库
        if session_id_for_temp_files:
            logger.info(f"执行RAG检索（临时文件）: session_id={session_id_for_temp_files}, top_k={rag_top_k}")
            try:
                from services.rag_service import RAGService
                
                # 执行RAG查询（使用临时文件）
                rag_result = RAGService.query(
                    question=input_text,
                    knowledge_base_ids=None,  # 不使用知识库
                    session_id=session_id_for_temp_files,  # 使用临时文件
                    similarity_top_k=rag_top_k,
                    enable_rerank=enable_rerank,
                    rerank_top_n=min(3, rag_top_k)
                )
                
                rag_sources = rag_result.get("sources", [])
                logger.info(f"✓ RAG检索完成（临时文件）: 找到 {len(rag_sources)} 个相关片段")
                
                # 构建RAG上下文
                if rag_sources:
                    rag_context = "\n\n=== 上传文档检索结果 ===\n"
                    for idx, source in enumerate(rag_sources, 1):
                        rag_context += f"\n[片段 {idx}]\n{source['content']}\n"
                        if source.get('metadata'):
                            rag_context += f"来源: {source['metadata'].get('filename', 'Unknown')}\n"
                    rag_context += "\n=== 请基于以上上传文档内容回答用户问题 ===\n\n"
                
            except Exception as e:
                logger.error(f"✗ RAG检索失败（临时文件）: {type(e).__name__}: {str(e)}")
                # RAG失败不影响对话，继续执行
        elif knowledge_base_ids:
            logger.info(f"执行RAG检索（知识库）: kb_ids={knowledge_base_ids}, top_k={rag_top_k}")
            try:
                from services.rag_service import RAGService
                
                # 执行RAG查询
                rag_result = RAGService.query(
                    question=input_text,
                    knowledge_base_ids=knowledge_base_ids,
                    session_id=None,  # 不使用临时文件
                    similarity_top_k=rag_top_k,
                    enable_rerank=enable_rerank,
                    rerank_top_n=min(3, rag_top_k)
                )
                
                rag_sources = rag_result.get("sources", [])
                logger.info(f"✓ RAG检索完成（知识库）: 找到 {len(rag_sources)} 个相关片段")
                
                # 构建RAG上下文
                if rag_sources:
                    rag_context = "\n\n=== 知识库检索结果 ===\n"
                    for idx, source in enumerate(rag_sources, 1):
                        rag_context += f"\n[片段 {idx}]\n{source['content']}\n"
                        if source.get('metadata'):
                            rag_context += f"来源: {source['metadata'].get('document_id', 'Unknown')}\n"
                    rag_context += "\n=== 请基于以上知识库内容回答用户问题 ===\n\n"
                
            except Exception as e:
                logger.error(f"✗ RAG检索失败（知识库）: {type(e).__name__}: {str(e)}")
                # RAG失败不影响对话，继续执行
    
    # 构建完整的输入（包含RAG上下文）
    full_input = rag_context + input_text if rag_context else input_text
    
    # 构建输入内容
    content = Content(parts=[Part(text=full_input)])
    
    # 检查并确保 Session 存在（ADK Runner 要求 Session 必须预先存在）
    try:
        existing_session = await session_service.get_session(
            app_name="paper_agent",
            user_id=user_id,
            session_id=session_id
        )
        if existing_session:
            logger.info(f"✓ 找到已有会话，继续对话")
        else:
            logger.info(f"✓ 会话不存在，正在创建新会话: session_id={session_id}")
            await session_service.create_session(
                app_name="paper_agent",
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"✓ 新会话创建成功")
    except Exception as e:
        logger.error(f"✗ 检查/创建会话失败: {str(e)}")
        # 如果创建失败，尝试继续，但 Runner 可能会报错
    
    # 运行智能体
    logger.info("开始运行智能体...")
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            # 可以在这里捕获流式事件
            pass
        
        # 获取更新后的 Session
        session = await session_service.get_session(
            app_name="paper_agent",
            user_id=user_id,
            session_id=session_id
        )
        
        # ADK 1.21+：会话里是 events，不再是 messages
        if session and session.events:
            # 优先找“最终回复”事件（且作者不是 user）
            final_events = [
                e
                for e in session.events
                if getattr(e, "author", None) != "user" and e.is_final_response()
            ]
            target_event = final_events[-1] if final_events else session.events[-1]

            content = getattr(target_event, "content", None)
            if content and getattr(content, "parts", None):
                text_parts = [p.text for p in content.parts if getattr(p, "text", None)]
                response_text = "".join(text_parts).strip()
                if response_text:
                    logger.info(f"✓ 智能体回复成功: length={len(response_text)}")
                    return response_text, session_id, rag_sources
        
        logger.warning("未获取到智能体回复")
        return "抱歉，没有收到智能体的回复。", session_id, rag_sources
        
    except Exception as e:
        logger.error(f"✗ 智能体运行失败: {type(e).__name__}: {str(e)}")
        raise


async def run_agent(input_text: str) -> str:
    """
    兼容旧版本的简单接口
    """
    response_text, _, _ = await run_agent_with_rag(input_text)
    return response_text
