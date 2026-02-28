"""
Runtime Monitor Service 层
实现运行时监控和日志记录功能
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from dao.runtime_dao import SkillActivationLogDAO, AgentExecutionLogDAO
from models.sql import SkillActivationLog, AgentExecutionLog


class RuntimeMonitorService:
    """运行时监控服务"""
    
    # ===== Skill Activation 相关 =====
    
    async def record_skill_activation(
        self,
        db: Session,
        skill_id: UUID,
        session_id: str,
        agent_config_id: Optional[UUID] = None,
        activation_reason: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> SkillActivationLog:
        """记录Skill激活"""
        log_data = {
            "skill_id": skill_id,
            "agent_config_id": agent_config_id,
            "session_id": session_id,
            "activation_reason": activation_reason,
            "query_text": query_text,
            "activated_at": datetime.utcnow()
        }
        
        # 同时更新Skill的activation_count
        from dao.skill_dao import SkillDAO
        SkillDAO.increment_activation_count(db, skill_id)
        
        return SkillActivationLogDAO.create(db, log_data)
    
    async def record_skill_deactivation(
        self,
        db: Session,
        log_id: UUID
    ) -> bool:
        """记录Skill停用"""
        return SkillActivationLogDAO.deactivate(db, log_id)
    
    async def deactivate_session_skills(
        self,
        db: Session,
        session_id: str,
        skill_id: Optional[UUID] = None
    ) -> int:
        """停用Session中的Skills"""
        return SkillActivationLogDAO.deactivate_by_session(db, session_id, skill_id)
    
    async def get_active_skills(
        self,
        db: Session,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取当前激活的Skills"""
        logs = SkillActivationLogDAO.get_active_skills(db, session_id)
        
        result = []
        for log in logs:
            result.append({
                "log_id": str(log.id),
                "skill_id": str(log.skill_id),
                "skill_name": log.skill.name if log.skill else None,
                "skill_display_name": log.skill.display_name if log.skill else None,
                "session_id": log.session_id,
                "activated_at": log.activated_at.isoformat() if log.activated_at else None,
                "activation_reason": log.activation_reason,
                "query_text": log.query_text
            })
        
        return result
    
    async def get_skill_activation_logs(
        self,
        db: Session,
        skill_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[SkillActivationLog]:
        """获取Skill的激活日志"""
        return SkillActivationLogDAO.list_by_skill(db, skill_id, skip, limit)
    
    async def get_session_activation_logs(
        self,
        db: Session,
        session_id: str,
        active_only: bool = False
    ) -> List[SkillActivationLog]:
        """获取Session的激活日志"""
        return SkillActivationLogDAO.list_by_session(db, session_id, active_only)
    
    async def get_skill_stats(
        self,
        db: Session,
        skill_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取Skill的统计信息"""
        return SkillActivationLogDAO.get_skill_stats(db, skill_id, days)
    
    # ===== Agent Execution 相关 =====
    
    async def record_agent_execution(
        self,
        db: Session,
        agent_config_id: UUID,
        session_id: str,
        input_text: str,
        output_text: str,
        execution_time_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        activated_skills: Optional[List[str]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AgentExecutionLog:
        """记录Agent执行"""
        log_data = {
            "agent_config_id": agent_config_id,
            "session_id": session_id,
            "input_text": input_text,
            "output_text": output_text,
            "execution_time_ms": execution_time_ms,
            "token_count": token_count,
            "tool_calls": tool_calls,
            "activated_skills": activated_skills,
            "status": status,
            "error_message": error_message,
            "executed_at": datetime.utcnow()
        }
        
        return AgentExecutionLogDAO.create(db, log_data)
    
    async def get_agent_execution_logs(
        self,
        db: Session,
        agent_config_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[AgentExecutionLog]:
        """获取Agent的执行日志"""
        return AgentExecutionLogDAO.list_by_agent(db, agent_config_id, skip, limit)
    
    async def get_session_execution_logs(
        self,
        db: Session,
        session_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[AgentExecutionLog]:
        """获取Session的执行日志"""
        return AgentExecutionLogDAO.list_by_session(db, session_id, skip, limit)
    
    async def get_agent_stats(
        self,
        db: Session,
        agent_config_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取Agent的统计信息"""
        return AgentExecutionLogDAO.get_agent_stats(db, agent_config_id, days)
    
    async def get_recent_errors(
        self,
        db: Session,
        agent_config_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[AgentExecutionLog]:
        """获取最近的错误日志"""
        return AgentExecutionLogDAO.get_recent_errors(db, agent_config_id, limit)
    
    # ===== 数据清理 =====
    
    async def cleanup_old_logs(
        self,
        db: Session,
        days: int = 30
    ) -> Dict[str, int]:
        """清理旧日志"""
        skill_logs_deleted = SkillActivationLogDAO.delete_old_logs(db, days)
        agent_logs_deleted = AgentExecutionLogDAO.delete_old_logs(db, days)
        
        return {
            "skill_activation_logs_deleted": skill_logs_deleted,
            "agent_execution_logs_deleted": agent_logs_deleted,
            "total_deleted": skill_logs_deleted + agent_logs_deleted
        }


# 创建全局单例
runtime_monitor_service = RuntimeMonitorService()
