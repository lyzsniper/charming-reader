"""
ChatService for Chat Tables
实现基于 chat_session、chat_message、chat_history 表的对话持久化存储
区别于 ADK 表，用于业务展示和管理
"""
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_, func
from core.db import SessionLocal
from models.sql import ChatSession, ChatMessage, ChatHistory
from core.logger import LoggerFactory
from google.adk.sessions import Session as ADKSession
from google.adk.events.event import Event
from google.genai.types import Content

logger = LoggerFactory.get_service_logger(__name__)


class ChatService:
    """
    Chat 对话服务
    管理 chat_session、chat_message、chat_history 表的存储
    """
    
    @staticmethod
    def _get_db() -> DBSession:
        """获取数据库会话"""
        return SessionLocal()
    
    @staticmethod
    async def create_or_get_chat_session(
        session_id: str,
        user_id: str,
        session_title: Optional[str] = None
    ) -> ChatSession:
        """
        创建或获取对话会话
        
        Args:
            session_id: 会话唯一标识符（String类型）
            user_id: 用户ID
            session_title: 会话标题（可选）
        
        Returns:
            ChatSession 对象
        """
        db = ChatService._get_db()
        try:
            # 查找是否已存在（使用session_id作为唯一标识）
            chat_session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if chat_session:
                logger.debug(f"找到已有Chat会话: session_id={session_id}, db_id={chat_session.id}")
                # 如果user_id不同，更新user_id（可能是同一个session但不同用户访问）
                if chat_session.user_id != user_id:
                    chat_session.user_id = user_id
                    db.commit()
                    db.refresh(chat_session)
                return chat_session
            
            # 再次检查（防止并发创建）
            chat_session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            if chat_session:
                logger.debug(f"并发检查：找到已有Chat会话: session_id={session_id}")
                return chat_session
            
            # 创建新会话
            chat_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                session_title=session_title
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
            
            logger.info(f"✓ 创建Chat会话成功: session_id={session_id}, db_id={chat_session.id}")
            return chat_session
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 创建/获取Chat会话失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    async def save_message(
        session_id: str,
        role: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_message_id: Optional[UUID] = None,
        user_id: Optional[str] = None,
        skip_duplicate_check: bool = False
    ) -> ChatMessage:
        """
        保存消息到 chat_message 表
        
        Args:
            session_id: 会话ID（String类型）
            role: 角色类型（user, assistant, tool, system）
            message_type: 消息类型（user_message, ai_response, tool_result, system_assembled）
            content: 消息内容
            metadata: 额外信息（工具调用详情、RAG检索结果等）
            parent_message_id: 父消息ID（用于关联同一轮次的消息）
            user_id: 用户ID（可选，如果提供则用于创建会话）
            skip_duplicate_check: 是否跳过重复检查（用于工具调用等可能重复的消息）
        
        Returns:
            ChatMessage 对象
        """
        db = ChatService._get_db()
        try:
            # 获取会话（确保存在）
            # 如果提供了user_id，使用它；否则尝试从现有会话获取
            if user_id:
                chat_session = await ChatService.create_or_get_chat_session(
                    session_id=session_id,
                    user_id=user_id
                )
            else:
                # 尝试从数据库获取现有会话以获取user_id
                existing_session = db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                if existing_session:
                    chat_session = existing_session
                else:
                    # 如果不存在且没有提供user_id，使用默认值
                    chat_session = await ChatService.create_or_get_chat_session(
                        session_id=session_id,
                        user_id="default_user"
                    )
            
            # 对于用户消息，检查是否已存在相同的消息（防止重复保存）
            if not skip_duplicate_check and role == "user" and message_type == "user_message":
                # 检查最近1分钟内是否有相同内容的用户消息
                from datetime import datetime, timedelta
                recent_time = datetime.now() - timedelta(seconds=5)  # 5秒内的重复消息视为重复
                existing_msg = db.query(ChatMessage).filter(
                    ChatMessage.session_id == chat_session.id,
                    ChatMessage.role == role,
                    ChatMessage.message_type == message_type,
                    ChatMessage.content == content,
                    ChatMessage.created_at >= recent_time
                ).first()
                
                if existing_msg:
                    logger.warning(f"⚠ 检测到重复的用户消息，跳过保存: session_id={session_id}, content={content[:50]}...")
                    return existing_msg
            
            # 创建消息
            chat_message = ChatMessage(
                session_id=chat_session.id,
                role=role,
                message_type=message_type,
                content=content,
                message_metadata=metadata,
                parent_message_id=parent_message_id
            )
            db.add(chat_message)
            db.commit()
            db.refresh(chat_message)
            
            logger.debug(f"✓ 保存Chat消息成功: role={role}, type={message_type}, id={chat_message.id}")
            return chat_message
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 保存Chat消息失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    async def create_chat_history_turn(
        session_id: str,
        user_message_id: UUID,
        assistant_message_id: UUID,
        summary: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ChatHistory:
        """
        创建对话轮次记录
        
        Args:
            session_id: 会话ID（String类型）
            user_message_id: 用户消息ID
            assistant_message_id: AI回复消息ID
            summary: 该轮次的摘要（可选）
            user_id: 用户ID（可选，用于创建会话）
        
        Returns:
            ChatHistory 对象
        """
        db = ChatService._get_db()
        try:
            # 获取会话
            if user_id:
                chat_session = await ChatService.create_or_get_chat_session(
                    session_id=session_id,
                    user_id=user_id
                )
            else:
                # 尝试从数据库获取现有会话
                existing_session = db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                if existing_session:
                    chat_session = existing_session
                else:
                    chat_session = await ChatService.create_or_get_chat_session(
                        session_id=session_id,
                        user_id="default_user"
                    )
            
            # 获取当前会话的最大 turn_index
            max_turn = db.query(func.max(ChatHistory.turn_index)).filter(
                ChatHistory.session_id == chat_session.id
            ).scalar()
            
            next_turn_index = (max_turn or 0) + 1
            
            # 创建历史记录
            chat_history = ChatHistory(
                session_id=chat_session.id,
                turn_index=next_turn_index,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
                summary=summary
            )
            db.add(chat_history)
            db.commit()
            db.refresh(chat_history)
            
            logger.info(f"✓ 创建Chat历史记录成功: session_id={session_id}, turn_index={next_turn_index}")
            return chat_history
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 创建Chat历史记录失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    async def sync_from_adk_session(
        adk_session: ADKSession,
        chat_session_id: str,
        user_id: str
    ) -> None:
        """
        从 ADK Session 同步消息到 Chat 表
        用于在对话完成后统一处理
        
        Args:
            adk_session: ADK Session 对象
            chat_session_id: Chat 会话ID（String类型）
            user_id: 用户ID
        """
        try:
            # 确保 Chat 会话存在
            chat_session = await ChatService.create_or_get_chat_session(
                session_id=chat_session_id,
                user_id=user_id
            )
            
            # 遍历 ADK events，转换为 chat_message
            user_message_id = None
            assistant_message_id = None
            
            for event in adk_session.events:
                if event.partial:
                    continue
                
                # 提取消息内容
                content_text = ""
                if event.content and hasattr(event.content, "parts"):
                    text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                    content_text = "".join(text_parts).strip()
                
                # 根据事件类型确定 role 和 message_type
                role = event.author if hasattr(event, "author") else "user"
                message_type = "user_message"
                metadata = {}
                
                # 判断消息类型
                if role == "user":
                    message_type = "user_message"
                elif role == "model" or role == "assistant":
                    message_type = "ai_response"
                    # 检查是否有工具调用
                    if event.content and hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                metadata["function_call"] = {
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args) if part.function_call.args else {}
                                }
                elif role == "tool":
                    message_type = "tool_result"
                    # 提取工具调用结果
                    if event.content and hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "function_response") and part.function_response:
                                metadata["function_response"] = {
                                    "name": part.function_response.name,
                                    "response": dict(part.function_response.response) if part.function_response.response else {}
                                }
                
                # 保存消息
                if content_text:
                    chat_msg = await ChatService.save_message(
                        session_id=chat_session_id,
                        role=role,
                        message_type=message_type,
                        content=content_text,
                        metadata=metadata if metadata else None,
                        user_id=user_id
                    )
                    
                    # 记录用户消息和AI回复的ID
                    if message_type == "user_message":
                        user_message_id = chat_msg.id
                    elif message_type == "ai_response":
                        assistant_message_id = chat_msg.id
            
            # 如果同时有用户消息和AI回复，创建历史记录
            if user_message_id and assistant_message_id:
                await ChatService.create_chat_history_turn(
                    session_id=chat_session_id,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id
                )
            
            logger.info(f"✓ 从ADK Session同步消息完成: session_id={chat_session_id}, events={len(adk_session.events)}")
            
        except Exception as e:
            logger.error(f"✗ 从ADK Session同步消息失败: {type(e).__name__}: {str(e)}", exc_info=True)
            # 不抛出异常，避免影响主流程
    
    @staticmethod
    def get_chat_history(
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ChatHistory]:
        """
        获取对话历史记录
        
        Args:
            session_id: 会话ID（String类型）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            ChatHistory 列表
        """
        db = ChatService._get_db()
        try:
            chat_session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not chat_session:
                return []
            
            query = db.query(ChatHistory).filter(
                ChatHistory.session_id == chat_session.id
            ).order_by(ChatHistory.turn_index.desc())
            
            if offset > 0:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"✗ 获取Chat历史记录失败: {type(e).__name__}: {str(e)}")
            return []
        finally:
            db.close()


# 单例实例
_chat_service = None


def get_chat_service() -> ChatService:
    """
    获取 ChatService 单例
    
    Returns:
        ChatService 实例
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
        logger.info("✓ ChatService 初始化完成")
    return _chat_service
