"""
A2A协议服务 - 实现智能体间的通信和协作
"""
import asyncio
from contextvars import ContextVar
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4
from core.logger import LoggerFactory
from google.adk import Runner
from google.adk.agents import Agent
from google.genai.types import Content, Part
from services.session_service import get_session_service

logger = LoggerFactory.get_service_logger(__name__)

# 智能体注册表
_agent_registry: Dict[str, Callable] = {}
_agent_runners: Dict[str, Runner] = {}

# 上下文变量：存储当前会话的 session_id、user_id 和 app_name（用于多智能体协作时保持会话一致性）
_current_session_id: ContextVar[Optional[str]] = ContextVar('current_session_id', default=None)
_current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)
_current_app_name: ContextVar[Optional[str]] = ContextVar('current_app_name', default=None)


async def register_agent(
    agent_name: str,
    agent_creator: Callable,
    runner: Optional[Runner] = None
):
    """
    注册智能体到A2A服务
    
    Args:
        agent_name: 智能体名称
        agent_creator: 智能体创建函数（返回Agent实例）
        runner: Runner实例（可选，如果不提供则自动创建）
    """
    _agent_registry[agent_name] = agent_creator
    
    # 如果没有提供runner，创建一个
    # 注意：在多智能体模式下，应该使用主 session 的 app_name，而不是 a2a_{agent_name}
    # 但这里在注册时无法确定，所以先使用默认值，在 call_agent 时会根据上下文变量重新创建
    if runner is None:
        agent = await agent_creator() if asyncio.iscoroutinefunction(agent_creator) else agent_creator()
        # 使用默认 app_name，在 call_agent 时会根据上下文变量调整
        app_name = _current_app_name.get() or "paper_agent"
        runner = Runner(
            agent=agent,
            session_service=get_session_service(),
            app_name=app_name
        )
    
    _agent_runners[agent_name] = runner
    logger.info(f"✓ 智能体 '{agent_name}' 已注册到A2A服务")


def get_registered_agents() -> List[str]:
    """获取已注册的智能体列表"""
    return list(_agent_registry.keys())


def is_agent_registered(agent_name: str) -> bool:
    """检查智能体是否已注册"""
    return agent_name in _agent_registry


async def call_agent(
    agent_name: str,
    message: str,
    user_id: str = "system",
    session_id: Optional[str] = None
) -> str:
    """
    通过A2A协议调用指定智能体
    
    Args:
        agent_name: 智能体名称
        message: 要发送的消息
        user_id: 用户ID
        session_id: 会话ID（可选，如果不提供，将从上下文变量获取，确保多智能体使用同一会话）
    
    Returns:
        智能体的回复内容
    """
    if not is_agent_registered(agent_name):
        error_msg = f"智能体 '{agent_name}' 未注册。可用智能体: {get_registered_agents()}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 如果没有提供 session_id，从上下文变量获取（多智能体协作时使用同一会话）
    if not session_id:
        session_id = _current_session_id.get()
        if not session_id:
            # 如果没有上下文 session_id，说明不是在多智能体模式下，不应该创建新的
            error_msg = f"多智能体模式下必须使用统一的 session_id，但未提供且上下文变量中也不存在"
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info(f"从上下文变量获取 session_id: {session_id}")
    
    # 如果没有提供 user_id，从上下文变量获取
    if not user_id or user_id == "system":
        ctx_user_id = _current_user_id.get()
        if ctx_user_id:
            user_id = ctx_user_id
            logger.debug(f"从上下文变量获取 user_id: {user_id}")
    
    # 从上下文变量获取 app_name（多智能体协作时使用主 session 的 app_name）
    app_name = _current_app_name.get()
    if not app_name:
        # 如果没有上下文 app_name，使用默认值（向后兼容）
        app_name = "paper_agent"
        logger.warning(f"未找到上下文 app_name，使用默认值: {app_name}")
    else:
        logger.debug(f"从上下文变量获取 app_name: {app_name}")
    
    # 获取或创建runner（使用主 session 的 app_name，确保所有智能体共享同一个 session）
    runner = _agent_runners.get(agent_name)
    if not runner:
        # 动态创建runner
        agent_creator = _agent_registry[agent_name]
        agent = await agent_creator() if asyncio.iscoroutinefunction(agent_creator) else agent_creator()
        runner = Runner(
            agent=agent,
            session_service=get_session_service(),
            app_name=app_name  # 使用主 session 的 app_name，而不是 a2a_{agent_name}
        )
        _agent_runners[agent_name] = runner
    else:
        # 如果 runner 已存在，确保它使用正确的 app_name
        # 注意：Runner 的 app_name 在创建时设置，无法动态修改
        # 如果 app_name 不匹配，需要重新创建 runner
        if hasattr(runner, '_app_name') and runner._app_name != app_name:
            logger.warning(f"Runner 的 app_name ({runner._app_name}) 与当前 app_name ({app_name}) 不匹配，重新创建")
            agent_creator = _agent_registry[agent_name]
            agent = await agent_creator() if asyncio.iscoroutinefunction(agent_creator) else agent_creator()
            runner = Runner(
                agent=agent,
                session_service=get_session_service(),
                app_name=app_name
            )
            _agent_runners[agent_name] = runner
    
    logger.info(f"通过A2A调用智能体 '{agent_name}': {message[:100]}...")
    
    # 确保 Session 存在（ADK 要求 Session 必须预先存在）
    # 使用主 session 的 app_name，确保所有智能体共享同一个 session
    session_service = get_session_service()
    
    try:
        existing_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        if not existing_session:
            logger.info(f"Session不存在，正在创建新Session: app_name={app_name}, session_id={session_id}")
            await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"✓ 新Session创建成功")
        else:
            logger.debug(f"✓ 找到已有Session，继续对话")
    except Exception as e:
        logger.error(f"✗ 检查/创建Session失败: {str(e)}")
        raise
    
    # 创建消息内容
    content = Content(parts=[Part(text=message)])
    
    # 调用智能体
    response_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
        
        logger.info(f"✓ 智能体 '{agent_name}' 回复完成，长度: {len(response_text)}")
        return response_text.strip()
    
    except Exception as e:
        logger.error(f"✗ 调用智能体 '{agent_name}' 失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


def create_agent_tool(agent_name: str, description: str) -> Callable:
    """
    将智能体封装为工具函数，以便其他智能体调用
    
    注意：工具函数会自动使用上下文变量中的 session_id 和 user_id，
    确保多智能体协作时所有智能体使用同一个会话。
    
    Args:
        agent_name: 智能体名称
        description: 工具描述
    
    Returns:
        工具函数
    """
    async def agent_tool(query: str) -> str:
        """
        调用智能体工具
        
        Args:
            query: 查询内容
        
        Returns:
            智能体的回复
        
        注意：此函数会自动使用当前上下文的 session_id，确保会话一致性
        """
        try:
            # 从上下文变量获取 session_id 和 user_id（不传参数，让 call_agent 从上下文获取）
            response = await call_agent(agent_name, query)
            return response
        except Exception as e:
            return f"错误: 调用智能体 '{agent_name}' 失败: {str(e)}"
    
    # 设置工具元数据
    agent_tool.__name__ = f"call_{agent_name}_agent"
    agent_tool.__doc__ = f"""{description}

Args:
    query (str): 要发送给智能体的查询内容

Returns:
    str: 智能体的回复内容
"""
    
    return agent_tool


async def initialize_agents():
    """初始化并注册所有可用的智能体"""
    logger.info("开始初始化A2A智能体服务...")
    
    try:
        # 导入所有智能体创建函数
        from agents.experiment_replication_agent import create_experiment_replication_agent
        from agents.paper_writing_agent import create_paper_writing_agent
        from agents.research_trends_agent import create_research_trends_agent
        from agents.cross_domain_agent import create_cross_domain_agent
        from agents.patent_analysis_agent import create_patent_analysis_agent
        from agents.tech_transfer_agent import create_tech_transfer_agent
        from agents.paper_agent.agent import create_agent_with_skills
        
        # 注册智能体
        await register_agent("experiment_replication", create_experiment_replication_agent)
        await register_agent("paper_writing", create_paper_writing_agent)
        await register_agent("research_trends", create_research_trends_agent)
        await register_agent("cross_domain", create_cross_domain_agent)
        await register_agent("patent_analysis", create_patent_analysis_agent)
        await register_agent("tech_transfer", create_tech_transfer_agent)
        await register_agent("paper_agent", create_agent_with_skills)
        
        logger.info(f"✓ A2A智能体服务初始化完成，已注册 {len(_agent_registry)} 个智能体: {list(_agent_registry.keys())}")
        
    except Exception as e:
        logger.error(f"✗ A2A智能体服务初始化失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise
