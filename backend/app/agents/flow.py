from google.adk import Runner
from google.adk.sessions import Session
from google.adk.agents import Agent
from google.genai.types import Content, Part
from contextvars import ContextVar
from core.config import settings
from core.logger import LoggerFactory
from services.session_service import get_session_service
from services.chat_service import ChatService
from services.model_config_service import ModelConfigurationService
from agents.paper_agent import create_agent_with_skills
from skills.manager import skills_manager
from tools.mcp_tool_adapter import reset_tool_call_counts
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from uuid import UUID, uuid4
import asyncio
from dataclasses import dataclass
from datetime import datetime

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
    # 如果提供了自定义agent，直接使用；否则创建新的agent
    if custom_agent:
        agent = custom_agent
        logger.info("✓ 使用提供的自定义 Agent")
    else:
        # 获取模型配置（如果提供了model_id和db）
        model_config = None
        if model_id and db:
            try:
                model_config = ModelConfigurationService.get_model_for_agent(db, model_id)
                logger.info(f"使用指定的模型配置: id={model_id}, model={model_config.get('model')}")
            except Exception as e:
                logger.warning(f"获取模型配置失败: {e}，使用默认配置")
        elif db:
            # 如果没有指定model_id，尝试获取激活的模型配置
            try:
                model_config = ModelConfigurationService.get_model_for_agent(db)
            except Exception as e:
                logger.warning(f"获取模型配置失败: {e}，使用默认配置")
        
        # 如果启用多智能体模式，使用协调智能体
        if use_multi_agent:
            logger.info("✓ 启用多智能体协作模式，使用协调智能体")
            from agents.coordinator_agent import create_coordinator_agent
            agent = await create_coordinator_agent(model_config=model_config)
        else:
            agent = await create_agent_with_skills(model_config=model_config)
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


async def run_agent_with_rag_stream(
    input_text: str,
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    knowledge_base_ids: Optional[List[UUID]] = None,
    use_rag: bool = False,
    rag_top_k: int = 5,
    enable_rerank: bool = True,
    session_id_for_temp_files: Optional[str] = None,
    yield_event: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    model_id: Optional[UUID] = None,
    db: Optional[Any] = None,
    custom_agent: Optional[Agent] = None,
    use_multi_agent: bool = False,
    cancellation_flag: Optional[Callable[[], Awaitable[bool]]] = None
) -> Tuple[str, str, Optional[List[Dict[str, Any]]], Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    运行智能体（流式版本），支持 RAG 检索和 Session 管理，支持通过回调函数发送流式事件
    
    Args:
        input_text: 用户输入文本
        user_id: 用户ID
        session_id: 会话ID（可选，不传则自动创建）
        knowledge_base_ids: 知识库ID列表（可选）
        use_rag: 是否启用RAG检索
        rag_top_k: RAG检索数量
        enable_rerank: 是否启用重排序
        session_id_for_temp_files: 临时文件会话ID
        yield_event: 事件回调函数 (event_type, event_data) -> None
        model_id: 模型配置ID（可选）
        db: 数据库会话（可选）
        custom_agent: 自定义Agent实例（可选，如果提供则直接使用）
        use_multi_agent: 是否启用多智能体协作模式（使用协调智能体）
        cancellation_flag: 取消标志检查函数，返回 True 表示已取消
    
    Returns:
        Tuple[response_text, actual_session_id, rag_sources, activated_skills, skills_prompt]
    """
    async def _check_cancelled():
        """检查是否已取消"""
        if cancellation_flag:
            return await cancellation_flag()
        return False
    
    async def _yield(event_type: str, event_data: Dict[str, Any]):
        """内部辅助函数，发送事件"""
        # 检查是否已取消
        if await _check_cancelled():
            raise asyncio.CancelledError("任务已被取消")
        if yield_event:
            await yield_event(event_type, event_data)
    
    # 如果没有传入 session_id，自动生成一个
    if not session_id:
        session_id = str(uuid4())
        logger.info(f"自动创建新会话: session_id={session_id}")
        # 新会话时重置工具调用计数器
        reset_tool_call_counts()
    else:
        logger.info(f"使用已有会话: session_id={session_id}")
    
    logger.info(f"用户消息: user_id={user_id}, message={input_text[:100]}...")
    
    # ===== 步骤 1: 检查并确保 Session 存在 =====
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
            # 新会话时重置工具调用计数器
            reset_tool_call_counts()
            await session_service.create_session(
                app_name="paper_agent",
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"✓ 新会话创建成功")
    except Exception as e:
        logger.error(f"✗ 检查/创建会话失败: {str(e)}")
        raise
    
    # ===== 步骤 1.5: 创建/获取 ChatSession =====
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
    
    # ===== 步骤 2: 根据查询自动激活技能（如果启用） =====
    activated_skills = None
    skills_prompt = None
    
    if settings.SKILLS_AUTO_ACTIVATION:
        logger.info(f"开始自动激活技能...")
        logger.info(f"用户查询: {input_text}")
        
        # 调试：列出所有可用技能
        all_skills = skills_manager.list_all_skills()
        logger.info(f"可用技能列表 ({len(all_skills)} 个): {[s['name'] for s in all_skills]}")
        
        # 调试：检查GitHub skill是否存在
        github_skill = None
        for skill in all_skills:
            if skill['name'] == 'github-integration':
                github_skill = skill
                logger.info(f"✓ 找到GitHub skill: {github_skill}")
                logger.info(f"  触发词: {github_skill.get('triggers', [])}")
                break
        
        if not github_skill:
            logger.warning("⚠ GitHub skill未找到！可能需要重新加载技能")
        
        await _yield("skill_loading", {
            "step": "matching",
            "message": "正在匹配相关技能...",
            "skill_name": None
        })
        logger.debug(f"✓ 已发送 skill_loading 事件")
        
        # 调试：测试匹配逻辑
        matched_skills = skills_manager.registry.find_skills_by_query(input_text)
        logger.info(f"匹配到的技能 ({len(matched_skills)} 个): {[s.name for s in matched_skills]}")
        for skill in matched_skills:
            logger.info(f"  - {skill.name}: 触发词={skill.triggers}")
        
        activated = skills_manager.auto_activate_for_query(input_text, max_skills=2)
        logger.info(f"激活结果: {len(activated)} 个技能被激活")
        if activated:
            logger.info(f"✓ 技能自动激活: 已激活 {len(activated)} 个技能")
            for skill_dict in activated:
                logger.info(f"  - {skill_dict['name']}: {skill_dict['description']}")
                
                # 发送技能激活事件
                skill_event_data = {
                    "skill_name": skill_dict['name'],
                    "description": skill_dict.get('description', ''),
                    "version": skill_dict.get('version')
                }
                await _yield("skill_activated", skill_event_data)
                logger.debug(f"✓ 已发送 skill_activated 事件: {skill_event_data}")
                
                # 发送技能内容事件
                active_skill = skills_manager.registry.get_skill(skill_dict['name'])
                if active_skill and active_skill.content:
                    skill_content_data = {
                        "skill_name": skill_dict['name'],
                        "content_length": len(active_skill.content)
                    }
                    await _yield("skill_content", skill_content_data)
                    logger.debug(f"✓ 已发送 skill_content 事件: {skill_content_data}")
                    logger.debug(f"  - 技能内容已加载: {skill_dict['name']} ({len(active_skill.content)} 字符)")
            
            activated_skills = activated
        else:
            logger.debug(f"未激活任何技能")
    
    # ===== 步骤 3: 创建 Agent 和 Runner =====
    logger.info("正在创建Agent...")
    await _yield("agent_thinking", {"message": "正在初始化Agent..."})
    
    # 如果提供了自定义agent，直接使用；否则创建新的agent
    if custom_agent:
        agent = custom_agent
        logger.info("✓ 使用提供的自定义 Agent")
        active_skills = []
        skills_prompt = None
    else:
        # 获取模型配置（如果提供了model_id和db）
        model_config = None
        if model_id and db:
            try:
                model_config = ModelConfigurationService.get_model_for_agent(db, model_id)
                logger.info(f"使用指定的模型配置: id={model_id}, model={model_config.get('model')}")
            except Exception as e:
                logger.warning(f"获取模型配置失败: {e}，使用默认配置")
        elif db:
            # 如果没有指定model_id，尝试获取激活的模型配置
            try:
                model_config = ModelConfigurationService.get_model_for_agent(db)
            except Exception as e:
                logger.warning(f"获取模型配置失败: {e}，使用默认配置")
        
        # 如果启用多智能体模式，使用协调智能体
        if use_multi_agent:
            logger.info("✓ 启用多智能体协作模式，使用协调智能体")
            await _yield("agent_thinking", {
                "message": "正在初始化多智能体协作系统..."
            })
            from agents.coordinator_agent import create_coordinator_agent
            agent = await create_coordinator_agent(model_config=model_config)
            await _yield("agent_thinking", {
                "message": "✓ 协调智能体已就绪，可调用多个专业智能体"
            })
            active_skills = []
            skills_prompt = None
        else:
            agent = await create_agent_with_skills(model_config=model_config)
            active_skills = skills_manager.get_active_skills()
            active_skills_count = len(active_skills)
            if active_skills_count > 0:
                logger.info(f"✓ 技能注入: 已将 {active_skills_count} 个技能注入 Agent 上下文")
                skills_prompt = skills_manager.get_skills_prompt_extension()
                if skills_prompt:
                    logger.debug(f"技能提示词长度: {len(skills_prompt)} 字符")
                
                if not activated_skills:
                    activated_skills = active_skills
                
                await _yield("agent_thinking", {
                    "message": f"已注入 {active_skills_count} 个技能到Agent上下文"
                })
            else:
                skills_prompt = None
    
    # 创建 Runner
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="paper_agent"
    )
    
    # ===== 步骤 3.6: 设置上下文变量（用于多智能体协作时保持会话一致性）=====
    if use_multi_agent:
        from agents.a2a_service import _current_session_id, _current_user_id, _current_app_name
        _current_session_id.set(session_id)
        _current_user_id.set(user_id)
        _current_app_name.set("paper_agent")  # 主 session 的 app_name
        logger.info(f"✓ 已设置上下文变量: session_id={session_id}, user_id={user_id}, app_name=paper_agent（多智能体模式）")
    
    # ===== 步骤 3.5: RAG 检索 =====
    if knowledge_base_ids or session_id_for_temp_files:
        use_rag = True
        if knowledge_base_ids:
            logger.info(f"检测到知识库选择，自动启用RAG: kb_ids={knowledge_base_ids}")
        if session_id_for_temp_files:
            logger.info(f"检测到临时文件会话，自动启用RAG: session_id={session_id_for_temp_files}")
    
    rag_sources = None
    rag_context = ""
    
    if use_rag and (knowledge_base_ids or session_id_for_temp_files):
        # 检查是否已取消
        if await _check_cancelled():
            raise asyncio.CancelledError("任务已被取消")
        
        # 优先级：临时文件 > 知识库
        if session_id_for_temp_files:
            logger.info(f"执行RAG检索（临时文件）: session_id={session_id_for_temp_files}, top_k={rag_top_k}")
            await _yield("rag_retrieval", {
                "step": "start",
                "message": "正在从上传文档中检索相关内容...",
                "type": "temp_file"
            })
            # 再次检查是否已取消
            if await _check_cancelled():
                raise asyncio.CancelledError("任务已被取消")
            try:
                from services.rag_service import RAGService
                
                rag_result = RAGService.query(
                    question=input_text,
                    knowledge_base_ids=None,
                    session_id=session_id_for_temp_files,
                    similarity_top_k=rag_top_k,
                    enable_rerank=enable_rerank,
                    rerank_top_n=min(3, rag_top_k)
                )
                
                rag_sources = rag_result.get("sources", [])
                logger.info(f"✓ RAG检索完成（临时文件）: 找到 {len(rag_sources)} 个相关片段")
                
                await _yield("rag_retrieval", {
                    "step": "completed",
                    "message": f"从上传文档中找到 {len(rag_sources)} 个相关片段",
                    "type": "temp_file",
                    "count": len(rag_sources)
                })
                
                if rag_sources:
                    rag_context = "\n\n=== 上传文档检索结果 ===\n"
                    for idx, source in enumerate(rag_sources, 1):
                        rag_context += f"\n[片段 {idx}]\n{source['content']}\n"
                        if source.get('metadata'):
                            rag_context += f"来源: {source['metadata'].get('filename', 'Unknown')}\n"
                    rag_context += "\n=== 请基于以上上传文档内容回答用户问题 ===\n\n"
                    
                    # 发送RAG检索结果事件
                    await _yield("rag_sources", {
                        "sources": rag_sources,
                        "type": "temp_file"
                    })
                    
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
                await _yield("rag_retrieval", {
                    "step": "error",
                    "message": f"RAG检索失败: {str(e)}",
                    "type": "temp_file"
                })
        elif knowledge_base_ids:
            logger.info(f"执行RAG检索（知识库）: kb_ids={knowledge_base_ids}, top_k={rag_top_k}")
            await _yield("rag_retrieval", {
                "step": "start",
                "message": "正在从知识库中检索相关内容...",
                "type": "knowledge_base",
                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids]
            })
            # 检查是否已取消
            if await _check_cancelled():
                raise asyncio.CancelledError("任务已被取消")
            try:
                from services.rag_service import RAGService
                
                rag_result = RAGService.query(
                    question=input_text,
                    knowledge_base_ids=knowledge_base_ids,
                    session_id=None,
                    similarity_top_k=rag_top_k,
                    enable_rerank=enable_rerank,
                    rerank_top_n=min(3, rag_top_k)
                )
                
                rag_sources = rag_result.get("sources", [])
                logger.info(f"✓ RAG检索完成（知识库）: 找到 {len(rag_sources)} 个相关片段")
                
                await _yield("rag_retrieval", {
                    "step": "completed",
                    "message": f"从知识库中找到 {len(rag_sources)} 个相关片段",
                    "type": "knowledge_base",
                    "count": len(rag_sources)
                })
                
                if rag_sources:
                    rag_context = "\n\n=== 知识库检索结果 ===\n"
                    for idx, source in enumerate(rag_sources, 1):
                        rag_context += f"\n[片段 {idx}]\n{source['content']}\n"
                        if source.get('metadata'):
                            rag_context += f"来源: {source['metadata'].get('document_id', 'Unknown')}\n"
                    rag_context += "\n=== 请基于以上知识库内容回答用户问题 ===\n\n"
                    
                    # 发送RAG检索结果事件
                    await _yield("rag_sources", {
                        "sources": rag_sources,
                        "type": "knowledge_base"
                    })
                    
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
                await _yield("rag_retrieval", {
                    "step": "error",
                    "message": f"RAG检索失败: {str(e)}",
                    "type": "knowledge_base"
                })
    
    # ===== 步骤 4: 构建完整的输入 =====
    full_input = rag_context + input_text if rag_context else input_text
    logger.info(f"构建完整的输入（包含RAG上下文）")
    content = Content(parts=[Part(text=full_input)])
    
    # ===== 步骤 5: 运行智能体（流式处理） =====
    logger.info("开始运行智能体...")
    await _yield("agent_thinking", {"message": "开始生成回答..."})
    
    response_text = ""
    last_content_length = 0
    has_sent_content = False  # 跟踪是否已发送过流式内容
    try:
        event_count = 0
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            # 检查是否已取消
            if await _check_cancelled():
                logger.info("检测到取消请求，停止处理事件")
                raise asyncio.CancelledError("任务已被取消")
            
            event_count += 1
            # 从事件中提取增量文本内容
            try:
                # 打印事件信息用于调试
                author = getattr(event, 'author', None)
                is_partial = hasattr(event, 'partial') and event.partial
                event_type = type(event).__name__
                logger.info(f"[事件 #{event_count}] author={author}, partial={is_partial}, type={event_type}")
                
                # 打印事件的所有属性
                event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
                logger.debug(f"事件属性: {event_attrs[:10]}...")  # 只打印前10个属性
                
                # 跳过用户消息
                if author == 'user':
                    logger.debug(f"跳过用户消息")
                    continue
                
                # 处理工具调用事件（可能在model/assistant事件中的function_call，或在tool事件中）
                tool_call_detected = False
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            # 检测函数调用（工具调用开始）- 在model/assistant事件中
                            if hasattr(part, 'function_call') and part.function_call:
                                try:
                                    tool_name = getattr(part.function_call, 'name', None)
                                    tool_arguments = {}
                                    if hasattr(part.function_call, 'args'):
                                        tool_arguments = dict(part.function_call.args) if part.function_call.args else {}
                                    
                                    # 发送工具调用开始事件
                                    if tool_name:
                                        await _yield("tool_call", {
                                            "tool_name": tool_name,
                                            "arguments": tool_arguments,
                                            "status": "start",
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        logger.info(f"✓ 发送工具调用开始事件: {tool_name}")
                                        tool_call_detected = True
                                except Exception as e:
                                    logger.warning(f"处理function_call事件时出错: {type(e).__name__}: {e}")
                            
                            # 检测函数响应（工具调用结果）- 在tool事件中
                            if hasattr(part, 'function_response') and part.function_response:
                                try:
                                    tool_name = getattr(part.function_response, 'name', None)
                                    tool_result = {}
                                    if hasattr(part.function_response, 'response'):
                                        tool_result = dict(part.function_response.response) if part.function_response.response else {}
                                    
                                    # 发送工具调用结果事件
                                    if tool_name:
                                        await _yield("tool_result", {
                                            "tool_name": tool_name,
                                            "result": tool_result,
                                            "success": True,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        logger.info(f"✓ 发送工具调用结果事件: {tool_name}")
                                        tool_call_detected = True
                                except Exception as e:
                                    logger.warning(f"处理function_response事件时出错: {type(e).__name__}: {e}")
                
                # 如果是tool事件，处理工具返回的文本内容
                if author == 'tool':
                    try:
                        tool_content = ""
                        if hasattr(event, 'content') and event.content:
                            if hasattr(event.content, 'parts') and event.content.parts:
                                for part in event.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        tool_content += part.text
                        
                        if tool_content:
                            # 尝试从之前的工具调用中获取工具名称，如果没有则使用unknown
                            tool_name = "unknown"
                            await _yield("tool_result", {
                                "tool_name": tool_name,
                                "result": {"content": tool_content},
                                "success": True,
                                "timestamp": datetime.now().isoformat()
                            })
                            logger.info(f"✓ 发送工具文本结果事件: {tool_name}")
                    except Exception as e:
                        logger.warning(f"处理tool事件时出错: {type(e).__name__}: {e}")
                    # tool事件处理完后继续，不跳过
                
                # 处理所有非用户事件，不仅仅是 model/assistant
                # 因为可能有些事件没有 author 属性或 author 值不同
                if author and author not in ('model', 'assistant', None, 'tool'):
                    logger.debug(f"跳过非model/assistant/tool事件: author={author}")
                    # 不直接 continue，先检查是否有内容
                
                # 检查是否是最终响应
                is_final = False
                if hasattr(event, 'is_final_response') and callable(event.is_final_response):
                    is_final = event.is_final_response()
                
                # 提取事件内容 - 尝试多种方式
                event_text = ""
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            # 只提取文本内容，跳过函数调用等其他类型
                            if hasattr(part, 'text') and part.text:
                                part_text = part.text
                                event_text += part_text
                                logger.info(f"从part提取文本: {len(part_text)} 字符, 预览: {part_text[:30]}...")
                    elif isinstance(event.content, str):
                        event_text += event.content
                        logger.info(f"从content提取文本: {len(event.content)} 字符")
                elif hasattr(event, 'text') and event.text:
                    event_text += event.text
                    logger.info(f"从text提取文本: {len(event.text)} 字符")
                
                # 如果没有提取到文本，记录警告
                if not event_text:
                    logger.debug(f"未提取到文本内容，事件可能不包含文本")
                else:
                    logger.info(f"提取的事件文本长度: {len(event_text)}, 当前累积长度: {len(response_text)}")
                
                # 处理流式内容
                if event_text:
                    # ADK 的流式事件处理：
                    # - partial=True 的事件：每次返回从开始到当前的所有累积内容
                    # - partial=False 的事件：返回完整内容
                    # 我们需要比较新内容和已累积的内容，找出增量部分
                    current_length = len(response_text)
                    new_length = len(event_text)
                    
                    # 如果新内容比已累积的内容长，说明有新增内容
                    if new_length > current_length:
                        # 提取增量部分（从已累积内容的末尾到新内容的末尾）
                        incremental_text = event_text[current_length:]
                        response_text = event_text  # 更新累积内容
                        
                        # 发送增量内容事件
                        if incremental_text:
                            has_sent_content = True
                            
                            # 如果增量内容太大（超过100字符），分块发送以模拟流式效果
                            # 这样可以确保即使ADK返回完整内容，也能实现打字机效果
                            chunk_size = 30  # 每块30个字符
                            if len(incremental_text) > chunk_size:
                                # 分块发送
                                for i in range(0, len(incremental_text), chunk_size):
                                    chunk = incremental_text[i:i+chunk_size]
                                    is_last_chunk = (i + chunk_size >= len(incremental_text))
                                    await _yield("agent_content", {
                                        "content": chunk,
                                        "is_complete": (is_final and not is_partial) and is_last_chunk
                                    })
                                    logger.info(f"✓ 发送流式增量内容块: {len(chunk)} 字符 (块 {i//chunk_size + 1}/{(len(incremental_text)-1)//chunk_size + 1})")
                                    # 添加小延迟，模拟打字效果
                                    if not is_last_chunk:
                                        await asyncio.sleep(0.02)  # 20ms延迟
                            else:
                                # 小块内容直接发送
                                await _yield("agent_content", {
                                    "content": incremental_text,
                                    "is_complete": is_final and not is_partial
                                })
                                logger.info(f"✓ 发送流式增量内容: +{len(incremental_text)} 字符, 总计={len(response_text)}, is_partial={is_partial}, is_final={is_final}")
                                logger.debug(f"增量内容预览: {incremental_text[:50]}...")
                    elif new_length == current_length:
                        # 内容长度相同
                        if event_text != response_text:
                            # 内容不同，可能是内容被替换了（少见情况）
                            # 发送完整内容作为增量
                            incremental_text = event_text
                            response_text = event_text
                            await _yield("agent_content", {
                                "content": incremental_text,
                                "is_complete": is_final and not is_partial
                            })
                            logger.debug(f"✓ 发送替换内容: {len(incremental_text)} 字符, is_partial={is_partial}, is_final={is_final}")
                        elif is_final and not is_partial:
                            # 内容相同且是最终事件，发送完成标记
                            await _yield("agent_content", {
                                "content": "",
                                "is_complete": True
                            })
                            logger.debug(f"✓ 发送完成标记: is_final={is_final}")
                    elif new_length < current_length:
                        # 新内容更短，可能是重置或错误，记录警告但继续处理
                        logger.warning(f"⚠ 事件内容变短: 当前={current_length}, 新={new_length}, 可能是重置")
                        if is_final:
                            # 如果是最终事件，使用新内容
                            incremental_text = event_text
                            response_text = event_text
                            await _yield("agent_content", {
                                "content": incremental_text,
                                "is_complete": True
                            })
                            logger.debug(f"✓ 发送重置内容: {len(incremental_text)} 字符")
                    # 如果新内容更短且不是最终事件，可能是重复或错误事件，忽略
                    
            except Exception as e:
                logger.error(f"处理流式事件时出错: {type(e).__name__}: {str(e)}, event_type={type(event).__name__}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")
                # 即使出错也继续处理，不要中断流式输出
        
        # 获取更新后的 Session（用于保存完整回复）
        session = await session_service.get_session(
            app_name="paper_agent",
            user_id=user_id,
            session_id=session_id
        )
        
        # 记录流式处理结果
        logger.info(f"流式处理完成: 处理了 {event_count} 个事件, 累积内容长度={len(response_text)}, 是否从事件获取={bool(response_text)}")
        
        # 如果没有从流式事件中获取到完整回复，尝试从session获取
        if not response_text and session and session.events:
            final_events = [
                e for e in session.events
                if getattr(e, "author", None) != "user" and e.is_final_response()
            ]
            target_event = final_events[-1] if final_events else session.events[-1]
            content = getattr(target_event, "content", None)
            if content and hasattr(content, "parts"):
                text_parts = [p.text for p in content.parts if hasattr(p, "text") and p.text]
                response_text = "".join(text_parts).strip()
        
        if response_text:
            response_text = response_text.strip()
            logger.info(f"✓ 智能体回复成功: length={len(response_text)}")
            
            # 如果之前没有发送过流式内容，现在发送完整内容作为流式输出
            # 这样可以确保前端至少能看到内容（即使不是真正的流式）
            if not has_sent_content:
                logger.warning(f"⚠ 没有收到流式事件，将完整内容分块发送以模拟流式输出")
                # 将完整内容分块发送，模拟流式输出
                chunk_size = 30  # 每次发送30个字符，与上面的chunk_size保持一致
                total_chunks = (len(response_text) + chunk_size - 1) // chunk_size
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i+chunk_size]
                    is_last_chunk = (i + chunk_size >= len(response_text))
                    await _yield("agent_content", {
                        "content": chunk,
                        "is_complete": is_last_chunk
                    })
                    logger.info(f"✓ 发送备用流式内容块: {len(chunk)} 字符 (块 {i//chunk_size + 1}/{total_chunks})")
                    # 添加延迟，模拟打字效果
                    if not is_last_chunk:
                        await asyncio.sleep(0.02)  # 20ms延迟
                
                logger.info(f"✓ 已发送完整内容作为流式输出: {len(response_text)} 字符，分 {total_chunks} 块")
            
            # 如果之前没有发送过最终事件，发送完成事件
            # （注意：如果流式事件已经发送了 is_complete=True，这里就不需要再发送了）
            
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
                        "skills_prompt": skills_prompt,
                        "sources": rag_sources  # 保存 RAG 检索结果
                    },
                    user_id=user_id
                )
                assistant_msg_id = assistant_msg.id
                logger.debug(f"✓ AI回复已保存到Chat表: message_id={assistant_msg_id}")
                
                # 处理工具调用
                if session and session.events:
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
        
    except ValueError as e:
        error_msg = str(e)
        # 检查是否是工具调用相关的错误（工具不存在等）
        if "tool" in error_msg.lower() and ("not found" in error_msg.lower() or "available" in error_msg.lower()):
            logger.warning(f"⚠ 工具调用错误（已记录，不影响流程）: {error_msg}")
            # 不返回错误消息给前端，不阻塞流程
            # 让 agent 自然处理这种情况，如果已经有响应文本就返回，否则返回默认消息
            if response_text:
                return response_text, session_id, rag_sources, activated_skills, skills_prompt
            else:
                # 如果没有响应文本，返回一个友好的消息，但不暴露内部错误
                friendly_msg = "我正在处理您的请求，但遇到了一个小问题。让我尝试其他方法。"
                return friendly_msg, session_id, rag_sources, activated_skills, skills_prompt
        else:
            # 其他 ValueError 继续抛出
            logger.error(f"✗ 智能体运行失败: {type(e).__name__}: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"✗ 智能体运行失败: {type(e).__name__}: {str(e)}")
        raise


async def run_agent(input_text: str) -> str:
    """
    兼容旧版本的简单接口
    """
    response_text, _, _, _, _ = await run_agent_with_rag(input_text)
    return response_text
