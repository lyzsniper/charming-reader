"""
PostgreSQL SessionService for ADK
实现基于 PostgreSQL 的 ADK Session 持久化存储
根据 ADK 文档（https://adk.wiki/sessions/）实现 SessionService 接口
"""
from typing import Optional, List, Dict, Any
import time
import uuid

from google.adk.sessions import BaseSessionService
from google.adk.sessions import Session as ADKSession
from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.base_session_service import ListSessionsResponse
from google.adk.events.event import Event
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.genai.types import Content, Part
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_
from core.db import get_db, SessionLocal
from models.sql import Session as DBSessionModel, SessionMessage
from core.logger import LoggerFactory
import json

logger = LoggerFactory.get_service_logger(__name__)


class PostgreSQLSessionService(BaseSessionService):
    """
    基于 PostgreSQL 的 SessionService 实现
    根据 ADK 官方文档 (https://adk.wiki/sessions/) 的 Session 概念实现
    """
    
    def __init__(self):
        """初始化 PostgreSQL Session Service"""
        logger.info("初始化 PostgreSQL SessionService")
    
    def _get_db(self) -> DBSession:
        """获取数据库会话"""
        return SessionLocal()
    
    def _serialize_content(self, content: Content) -> Dict[str, Any]:
        """
        将 ADK Content 对象序列化为 JSON
        
        Args:
            content: ADK Content 对象
        
        Returns:
            JSON 可序列化的字典
        """
        if not content:
            return {}
        
        parts_data = []
        if content.parts:
            for part in content.parts:
                part_dict = {}
                if part.text:
                    part_dict["text"] = part.text
                if hasattr(part, "function_call") and part.function_call:
                    part_dict["function_call"] = {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {}
                    }
                if hasattr(part, "function_response") and part.function_response:
                    part_dict["function_response"] = {
                        "name": part.function_response.name,
                        "response": dict(part.function_response.response) if part.function_response.response else {}
                    }
                parts_data.append(part_dict)
        
        return {
            "role": content.role if hasattr(content, "role") else "user",
            "parts": parts_data
        }
    
    def _deserialize_content(self, content_dict: Dict[str, Any]) -> Content:
        """
        将 JSON 反序列化为 ADK Content 对象
        
        Args:
            content_dict: JSON 字典
        
        Returns:
            ADK Content 对象
        """
        if not content_dict:
            return Content(parts=[])
        
        parts = []
        for part_dict in content_dict.get("parts", []):
            if "text" in part_dict:
                parts.append(Part(text=part_dict["text"]))
            # 可以添加对 function_call 和 function_response 的支持
        
        return Content(
            role=content_dict.get("role", "user"),
            parts=parts
        )
    
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> ADKSession:
        """
        创建新的 Session
        
        Args:
            app_name: 应用名称
            user_id: 用户ID
            state: 初始状态数据
            session_id: 会话ID（可选，不传则自动生成）
        
        Returns:
            ADK Session 对象
        """
        if session_id:
            session_id = session_id.strip()
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"创建新会话: app={app_name}, user={user_id}, session={session_id}")
        
        db = self._get_db()
        try:
            # 检查是否已存在
            existing = db.query(DBSessionModel).filter(
                and_(
                    DBSessionModel.app_name == app_name,
                    DBSessionModel.user_id == user_id,
                    DBSessionModel.session_id == session_id
                )
            ).first()
            
            if existing:
                raise AlreadyExistsError(f"Session with id {session_id} already exists.")
            
            # 创建新会话
            db_session = DBSessionModel(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state=state or {},
                custom_metadata={}
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            logger.info(f"✓ 会话创建成功: db_id={db_session.id}")
            
            return self._db_to_adk_session(db_session)
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 创建会话失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()
    
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[ADKSession]:
        """
        获取 Session
        
        Args:
            app_name: 应用名称
            user_id: 用户ID
            session_id: 会话ID
            config: 获取配置（可选，限制最近事件/按时间过滤）
        
        Returns:
            ADK Session 对象，如果不存在返回 None
        """
        logger.debug(f"获取会话: app={app_name}, user={user_id}, session={session_id}")
        
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                and_(
                    DBSessionModel.app_name == app_name,
                    DBSessionModel.user_id == user_id,
                    DBSessionModel.session_id == session_id
                )
            ).first()
            
            if not db_session:
                logger.debug(f"会话不存在")
                return None

            return self._db_to_adk_session(db_session, config=config)
            
        finally:
            db.close()
    
    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        """
        列出会话（ADK 规范：返回 Session 列表，但不包含 events 的内容）
        """
        db = self._get_db()
        try:
            q = db.query(DBSessionModel).filter(DBSessionModel.app_name == app_name)
            if user_id:
                q = q.filter(DBSessionModel.user_id == user_id)
            rows = q.order_by(DBSessionModel.updated_at.desc()).all()

            sessions: List[ADKSession] = []
            for row in rows:
                last_update_time = 0.0
                if getattr(row, "updated_at", None) is not None:
                    try:
                        last_update_time = float(row.updated_at.timestamp())
                    except Exception:
                        last_update_time = 0.0

                sessions.append(
                    ADKSession(
                        id=row.session_id,
                        app_name=row.app_name,
                        user_id=row.user_id,
                        state=row.state or {},
                        events=[],
                        last_update_time=last_update_time,
                    )
                )

            return ListSessionsResponse(sessions=sessions)
        finally:
            db.close()
    
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """
        删除 Session
        
        Args:
            app_name: 应用名称
            user_id: 用户ID
            session_id: 会话ID
        """
        logger.info(f"删除会话: app={app_name}, user={user_id}, session={session_id}")
        
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                and_(
                    DBSessionModel.app_name == app_name,
                    DBSessionModel.user_id == user_id,
                    DBSessionModel.session_id == session_id
                )
            ).first()
            
            if db_session:
                db.delete(db_session)
                db.commit()
                logger.info(f"✓ 会话删除成功")
            else:
                logger.warning(f"会话不存在，无需删除")
                
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 删除会话失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()
    
    async def append_event(self, session: ADKSession, event: Event) -> Event:
        """
        追加事件到会话：持久化到 PostgreSQL，并同步更新 session.state / session.events
        """
        if event.partial:
            return event

        # 持久化（先落库，避免内存状态与存储不一致）
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                and_(
                    DBSessionModel.app_name == session.app_name,
                    DBSessionModel.user_id == session.user_id,
                    DBSessionModel.session_id == session.id,
                )
            ).first()
            if not db_session:
                raise ValueError(f"Session {session.id} not found.")

            # 更新 state（仅处理非 TEMP 前缀的 state_delta；TEMP 由 BaseSessionService 过滤）
            if event.actions and event.actions.state_delta:
                # 直接做浅合并（ADK 更复杂的 app/user/session 前缀拆分这里先不做）
                current_state = dict(db_session.state or {})
                for k, v in event.actions.state_delta.items():
                    # TEMP 前缀交给 BaseSessionService._trim_temp_delta_state 再处理，这里也防御一下
                    if isinstance(k, str) and k.startswith("temp:"):
                        continue
                    current_state[k] = v
                db_session.state = current_state

            db_message = SessionMessage(
                session_id=db_session.id,
                role=event.author,
                content=event.model_dump(mode="json", exclude_none=True),
                custom_metadata={},
            )
            db.add(db_message)
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"✗ 追加事件失败: {type(e).__name__}: {str(e)}")
            raise
        finally:
            db.close()

        # 让 ADK 基类负责：裁剪 TEMP state_delta + 更新内存 session.state + 追加到 session.events
        return await super().append_event(session=session, event=event)
    
    def _db_to_adk_session(
        self, db_session: DBSessionModel, config: Optional[GetSessionConfig] = None
    ) -> ADKSession:
        """
        将数据库 Session 转换为 ADK Session 对象
        
        Args:
            db_session: 数据库 Session 模型
        
        Returns:
            ADK Session 对象
        """
        # 构建事件列表（兼容旧数据：content 是 Content JSON 时，转成 Event）
        events: List[Event] = []
        if db_session.messages:
            for db_msg in db_session.messages:
                raw = db_msg.content or {}
                try:
                    # 新格式：存的是 Event 的 dict
                    if isinstance(raw, dict) and "author" in raw and "timestamp" in raw:
                        ev = Event.model_validate(raw)
                    else:
                        # 旧格式：存的是 Content dict（role/parts）
                        content = self._deserialize_content(raw if isinstance(raw, dict) else {})
                        ev = Event(author=db_msg.role or "user", content=content)
                    events.append(ev)
                except Exception as e:
                    logger.warning(f"跳过无法解析的事件记录: {type(e).__name__}: {str(e)}")

        # 按 config 过滤
        if config:
            if config.after_timestamp is not None:
                events = [e for e in events if e.timestamp >= config.after_timestamp]
            if config.num_recent_events is not None:
                # ADK 语义：最近 N 条（但返回仍应按时间正序）
                events = events[-config.num_recent_events :]

        last_update_time = 0.0
        if events:
            try:
                last_update_time = float(events[-1].timestamp)
            except Exception:
                last_update_time = 0.0
        else:
            if getattr(db_session, "updated_at", None) is not None:
                try:
                    last_update_time = float(db_session.updated_at.timestamp())
                except Exception:
                    last_update_time = 0.0

        return ADKSession(
            id=db_session.session_id,
            app_name=db_session.app_name,
            user_id=db_session.user_id,
            state=db_session.state or {},
            events=events,
            last_update_time=last_update_time,
        )


# 单例实例
_session_service = None


def get_session_service() -> PostgreSQLSessionService:
    """
    获取 SessionService 单例
    
    Returns:
        PostgreSQLSessionService 实例
    """
    global _session_service
    if _session_service is None:
        _session_service = PostgreSQLSessionService()
        logger.info("✓ PostgreSQL SessionService 初始化完成")
    return _session_service

