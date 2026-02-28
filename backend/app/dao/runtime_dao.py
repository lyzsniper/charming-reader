"""
运行时监控数据访问层（DAO）
负责记录和查询Agent/Skill的运行时日志
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from models.sql import SkillActivationLog, AgentExecutionLog


class SkillActivationLogDAO:
    """SkillActivationLog数据访问对象"""
    
    @staticmethod
    def create(db: Session, log_data: Dict[str, Any]) -> SkillActivationLog:
        """创建SkillActivationLog记录"""
        log = SkillActivationLog(**log_data)
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_by_id(db: Session, log_id: UUID) -> Optional[SkillActivationLog]:
        """根据ID查询日志"""
        return db.query(SkillActivationLog).filter(SkillActivationLog.id == log_id).first()
    
    @staticmethod
    def list_by_skill(
        db: Session,
        skill_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[SkillActivationLog]:
        """查询指定Skill的激活日志"""
        return db.query(SkillActivationLog).filter(
            SkillActivationLog.skill_id == skill_id
        ).order_by(desc(SkillActivationLog.activated_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def list_by_session(
        db: Session,
        session_id: str,
        active_only: bool = False
    ) -> List[SkillActivationLog]:
        """查询指定Session的激活日志"""
        query = db.query(SkillActivationLog).filter(
            SkillActivationLog.session_id == session_id
        )
        
        if active_only:
            query = query.filter(SkillActivationLog.deactivated_at.is_(None))
        
        return query.order_by(desc(SkillActivationLog.activated_at)).all()
    
    @staticmethod
    def list_by_agent(
        db: Session,
        agent_config_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[SkillActivationLog]:
        """查询指定Agent配置的激活日志"""
        return db.query(SkillActivationLog).filter(
            SkillActivationLog.agent_config_id == agent_config_id
        ).order_by(desc(SkillActivationLog.activated_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_active_skills(db: Session, session_id: Optional[str] = None) -> List[SkillActivationLog]:
        """获取当前激活的Skills"""
        query = db.query(SkillActivationLog).filter(
            SkillActivationLog.deactivated_at.is_(None)
        )
        
        if session_id:
            query = query.filter(SkillActivationLog.session_id == session_id)
        
        return query.order_by(desc(SkillActivationLog.activated_at)).all()
    
    @staticmethod
    def deactivate(db: Session, log_id: UUID) -> bool:
        """标记Skill为已停用"""
        log = db.query(SkillActivationLog).filter(SkillActivationLog.id == log_id).first()
        if not log:
            return False
        
        log.deactivated_at = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def deactivate_by_session(db: Session, session_id: str, skill_id: Optional[UUID] = None) -> int:
        """停用Session中的Skills"""
        query = db.query(SkillActivationLog).filter(
            and_(
                SkillActivationLog.session_id == session_id,
                SkillActivationLog.deactivated_at.is_(None)
            )
        )
        
        if skill_id:
            query = query.filter(SkillActivationLog.skill_id == skill_id)
        
        count = 0
        for log in query.all():
            log.deactivated_at = datetime.utcnow()
            count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def get_skill_stats(
        db: Session,
        skill_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取Skill的统计信息"""
        since = datetime.utcnow() - timedelta(days=days)
        
        total_activations = db.query(func.count(SkillActivationLog.id)).filter(
            and_(
                SkillActivationLog.skill_id == skill_id,
                SkillActivationLog.activated_at >= since
            )
        ).scalar()
        
        unique_sessions = db.query(func.count(func.distinct(SkillActivationLog.session_id))).filter(
            and_(
                SkillActivationLog.skill_id == skill_id,
                SkillActivationLog.activated_at >= since
            )
        ).scalar()
        
        return {
            "total_activations": total_activations,
            "unique_sessions": unique_sessions,
            "time_range_days": days
        }
    
    @staticmethod
    def delete_old_logs(db: Session, days: int = 30) -> int:
        """删除旧日志（数据清理）"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = db.query(SkillActivationLog).filter(
            SkillActivationLog.activated_at < cutoff_date
        ).delete()
        
        db.commit()
        return count


class AgentExecutionLogDAO:
    """AgentExecutionLog数据访问对象"""
    
    @staticmethod
    def create(db: Session, log_data: Dict[str, Any]) -> AgentExecutionLog:
        """创建AgentExecutionLog记录"""
        log = AgentExecutionLog(**log_data)
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_by_id(db: Session, log_id: UUID) -> Optional[AgentExecutionLog]:
        """根据ID查询日志"""
        return db.query(AgentExecutionLog).filter(AgentExecutionLog.id == log_id).first()
    
    @staticmethod
    def list_by_agent(
        db: Session,
        agent_config_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentExecutionLog]:
        """查询指定Agent的执行日志"""
        return db.query(AgentExecutionLog).filter(
            AgentExecutionLog.agent_config_id == agent_config_id
        ).order_by(desc(AgentExecutionLog.executed_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def list_by_session(
        db: Session,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentExecutionLog]:
        """查询指定Session的执行日志"""
        return db.query(AgentExecutionLog).filter(
            AgentExecutionLog.session_id == session_id
        ).order_by(desc(AgentExecutionLog.executed_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_agent_stats(
        db: Session,
        agent_config_id: UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取Agent的统计信息"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # 总执行次数
        total_executions = db.query(func.count(AgentExecutionLog.id)).filter(
            and_(
                AgentExecutionLog.agent_config_id == agent_config_id,
                AgentExecutionLog.executed_at >= since
            )
        ).scalar()
        
        # 成功次数
        successful_executions = db.query(func.count(AgentExecutionLog.id)).filter(
            and_(
                AgentExecutionLog.agent_config_id == agent_config_id,
                AgentExecutionLog.executed_at >= since,
                AgentExecutionLog.status == 'success'
            )
        ).scalar()
        
        # 平均执行时间
        avg_execution_time = db.query(func.avg(AgentExecutionLog.execution_time_ms)).filter(
            and_(
                AgentExecutionLog.agent_config_id == agent_config_id,
                AgentExecutionLog.executed_at >= since,
                AgentExecutionLog.execution_time_ms.isnot(None)
            )
        ).scalar()
        
        # 平均Token数
        avg_token_count = db.query(func.avg(AgentExecutionLog.token_count)).filter(
            and_(
                AgentExecutionLog.agent_config_id == agent_config_id,
                AgentExecutionLog.executed_at >= since,
                AgentExecutionLog.token_count.isnot(None)
            )
        ).scalar()
        
        # 成功率
        success_rate = 0.0
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": total_executions - successful_executions,
            "success_rate": round(success_rate, 2),
            "avg_execution_time_ms": round(avg_execution_time, 2) if avg_execution_time else 0,
            "avg_token_count": round(avg_token_count, 2) if avg_token_count else 0,
            "time_range_days": days
        }
    
    @staticmethod
    def get_recent_errors(
        db: Session,
        agent_config_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[AgentExecutionLog]:
        """获取最近的错误日志"""
        query = db.query(AgentExecutionLog).filter(
            AgentExecutionLog.status != 'success'
        )
        
        if agent_config_id:
            query = query.filter(AgentExecutionLog.agent_config_id == agent_config_id)
        
        return query.order_by(desc(AgentExecutionLog.executed_at)).limit(limit).all()
    
    @staticmethod
    def delete_old_logs(db: Session, days: int = 30) -> int:
        """删除旧日志（数据清理）"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = db.query(AgentExecutionLog).filter(
            AgentExecutionLog.executed_at < cutoff_date
        ).delete()
        
        db.commit()
        return count
