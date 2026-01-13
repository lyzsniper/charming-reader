from google.adk import Runner
from google.adk.sessions import Session
from google.genai.types import Content, Part
from core.config import settings
from core.logger import LoggerFactory
from services.session_service import get_session_service
from services.chat_service import ChatService
from agents.paper_agent import create_agent_with_skills
from skills.manager import skills_manager
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import asyncio
from dataclasses import dataclass

logger = LoggerFactory.get_service_logger(__name__)

# Initialize Session Service
# 使用 PostgreSQL 持久化的 SessionService（根据 ADK 文档 https://adk.wiki/sessions/）
session_service = get_session_service()
logger.info("✓ 使用 PostgreSQL SessionService 进行会话持久化")


@dataclass
class AgentExecutionResult:
    """Agent 执行结果"""
    response_text: str
    session_id: str
    rag_sources: Optional[List[Dict[str, Any]]] = None
    activated_skills: Optional[List[Dict[str, Any]]] = None
    skills_prompt: Optional[str] = None


async def run_agent_with_rag(
    input_text: str,
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    knowledge_base_ids: Optional[List[UUID]] = None,
    use_rag: bool = False,
    rag_top_k: int = 5,
    enable_rerank: bool = True,
    session_id_for_temp_files: Optional[str] = None
) -> Tuple[str, str, Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]], Optional[str]]:
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
        Tuple[response_text, actual_session_id, rag_sources, activated_skills, skills_prompt]
        - response_text: 智能体回复
        - actual_session_id: 实际使用的会话ID
        - rag_sources: RAG来源列表（如果启用RAG）
        - activated_skills: 激活的技能列表
        - skills_prompt: 注入到Agent的技能提示词内容
    """
    # 如果没有传入 session_id，自动生成一个
    if not session_id:
        session_id = str(uuid4())
        logger.info(f"自动创建新会话: session_id={session_id}")
    else:
        logger.info(f"使用已有会话: session_id={session_id}")
    
    logger.info(f"用户消息: user_id={user_id}, message={input_text[:100]}...")
    
    # ===== 步骤 1: 检查并确保 Session 存在（必须在最前面，ADK Runner 要求 Session 必须预先存在） =====
    try:
        existing_session = await session_service.get_session(
            app_name="paper_agent",
            user_id=user_id,
            session_id=session_id
        )
        if existing_session:
            logger.info(f"✓ 找到已有会话，继续对话")
        else:
            logger.info(f"会话不存在，正在创建新会话: session_id={session_id}")
            await session_service.create_session(
                app_name="paper_agent",
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"✓ 新会话创建成功")
    except Exception as e:
        logger.error(f"✗ 检查/创建会话失败: {str(e)}")
        raise  # Session 创建失败必须抛出异常，不能继续
    
    # ===== 步骤 1.5: 创建/获取 ChatSession（用于业务展示） =====
    user_msg_id = None
    try:
        await ChatService.create_or_get_chat_session(
            session_id=session_id,
            user_id=user_id
        )
        logger.debug(f"✓ Chat会话准备完成: session_id={session_id}")
        
        # 保存用户消息
        user_msg = await ChatService.save_message(
            session_id=session_id,
            role="user",
            message_type="user_message",
            content=input_text,
            user_id=user_id
        )
        user_msg_id = user_msg.id
        logger.debug(f"✓ 用户消息已保存到Chat表: message_id={user_msg_id}")
    except Exception as e:
        logger.warning(f"⚠ Chat表存储失败（不影响主流程）: {type(e).__name__}: {str(e)}")
        # Chat表存储失败不影响主流程，继续执行
    
    # ===== 步骤 2: 根据查询自动激活技能（如果启用） =====
    activated_skills = None
    skills_prompt = None
    if settings.SKILLS_AUTO_ACTIVATION:
        activated = skills_manager.auto_activate_for_query(input_text, max_skills=2)
        if activated:
            logger.info(f"✓ 技能自动激活: 已激活 {len(activated)} 个技能")
            for skill in activated:
                logger.info(f"  - {skill['name']}: {skill['description']}")
            activated_skills = activated
    
    # ===== 步骤 3: 创建 Agent 和 Runner =====
    agent = create_agent_with_skills()
    active_skills = skills_manager.get_active_skills()
    active_skills_count = len(active_skills)
    if active_skills_count > 0:
        logger.info(f"✓ 技能注入: 已将 {active_skills_count} 个技能注入 Agent 上下文")
        # 获取技能提示词内容
        skills_prompt = skills_manager.get_skills_prompt_extension()
        # 如果没有激活的技能列表，使用当前激活的技能
        if not activated_skills:
            activated_skills = active_skills
    
    # 创建 Runner（每次创建新的以使用最新的 Agent 和技能）
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="paper_agent"
    )
    
    # ===== 步骤 3.5: RAG 检索（在 Session 创建之后） =====
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
                    
                    # 保存RAG检索结果到Chat表
                    try:
                        await ChatService.save_message(
                            session_id=session_id,
                            role="system",
                            message_type="system_assembled",
                            content=rag_context,
                            metadata={
                                "sources": rag_sources,
                                "session_id_for_temp_files": session_id_for_temp_files,
                                "rag_top_k": rag_top_k,
                                "enable_rerank": enable_rerank
                            },
                            user_id=user_id
                        )
                        logger.debug(f"✓ RAG检索结果已保存到Chat表（临时文件）")
                    except Exception as e:
                        logger.warning(f"⚠ 保存RAG结果到Chat表失败: {type(e).__name__}: {str(e)}")
                
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
                    
                    # 保存RAG检索结果到Chat表
                    try:
                        await ChatService.save_message(
                            session_id=session_id,
                            role="system",
                            message_type="system_assembled",
                            content=rag_context,
                            metadata={
                                "sources": rag_sources,
                                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else None,
                                "rag_top_k": rag_top_k,
                                "enable_rerank": enable_rerank
                            },
                            user_id=user_id
                        )
                        logger.debug(f"✓ RAG检索结果已保存到Chat表（知识库）")
                    except Exception as e:
                        logger.warning(f"⚠ 保存RAG结果到Chat表失败: {type(e).__name__}: {str(e)}")
                
            except Exception as e:
                logger.error(f"✗ RAG检索失败（知识库）: {type(e).__name__}: {str(e)}")
                # RAG失败不影响对话，继续执行
    
    # ===== 步骤 4: 构建完整的输入（包含RAG上下文） =====
    full_input = rag_context + input_text if rag_context else input_text
    logger.info(f"构建完整的输入（包含RAG上下文）: {full_input}")
    # 构建输入内容
    content = Content(parts=[Part(text=full_input)])
    
    # ===== 步骤 5: 运行智能体 =====
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
                    
                    # 保存AI回复到Chat表
                    assistant_msg_id = None
                    try:
                        assistant_msg = await ChatService.save_message(
                            session_id=session_id,
                            role="assistant",
                            message_type="ai_response",
                            content=response_text,
                            metadata={
                                "activated_skills": activated_skills,
                                "skills_prompt": skills_prompt
                            },
                            user_id=user_id
                        )
                        assistant_msg_id = assistant_msg.id
                        logger.debug(f"✓ AI回复已保存到Chat表: message_id={assistant_msg_id}")
                        
                        # 处理工具调用：从session.events中提取工具调用结果
                        tool_events = [
                            e for e in session.events
                            if getattr(e, "author", None) == "tool" and not e.partial
                        ]
                        for tool_event in tool_events:
                            try:
                                tool_content = ""
                                tool_metadata = {}
                                if tool_event.content and hasattr(tool_event.content, "parts"):
                                    for part in tool_event.content.parts:
                                        if hasattr(part, "text") and part.text:
                                            tool_content += part.text
                                        if hasattr(part, "function_response") and part.function_response:
                                            tool_metadata["function_response"] = {
                                                "name": part.function_response.name,
                                                "response": dict(part.function_response.response) if part.function_response.response else {}
                                            }
                                
                                if tool_content or tool_metadata:
                                    await ChatService.save_message(
                                        session_id=session_id,
                                        role="tool",
                                        message_type="tool_result",
                                        content=tool_content or str(tool_metadata),
                                        metadata=tool_metadata if tool_metadata else None,
                                        parent_message_id=assistant_msg_id,
                                        user_id=user_id
                                    )
                                    logger.debug(f"✓ 工具调用结果已保存到Chat表")
                            except Exception as e:
                                logger.warning(f"⚠ 保存工具调用结果失败: {type(e).__name__}: {str(e)}")
                        
                        # 创建对话轮次记录
                        if user_msg_id and assistant_msg_id:
                            try:
                                await ChatService.create_chat_history_turn(
                                    session_id=session_id,
                                    user_message_id=user_msg_id,
                                    assistant_message_id=assistant_msg_id,
                                    user_id=user_id
                                )
                                logger.debug(f"✓ 对话轮次记录已创建")
                            except Exception as e:
                                logger.warning(f"⚠ 创建对话轮次记录失败: {type(e).__name__}: {str(e)}")
                    except Exception as e:
                        logger.warning(f"⚠ 保存AI回复到Chat表失败: {type(e).__name__}: {str(e)}")
                    
                    return response_text, session_id, rag_sources, activated_skills, skills_prompt
        
        logger.warning("未获取到智能体回复")
        return "抱歉，没有收到智能体的回复。", session_id, rag_sources, activated_skills, skills_prompt
        
    except Exception as e:
        logger.error(f"✗ 智能体运行失败: {type(e).__name__}: {str(e)}")
        raise


async def run_agent(input_text: str) -> str:
    """
    兼容旧版本的简单接口
    """
    response_text, _, _, _, _ = await run_agent_with_rag(input_text)
    return response_text
