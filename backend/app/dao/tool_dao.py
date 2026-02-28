"""
Tool 数据访问层（DAO）
负责直接操作数据库，不包含业务逻辑
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from models.sql import Tool


class ToolDAO:
    """Tool数据访问对象"""
    
    @staticmethod
    def create(db: Session, tool_data: Dict[str, Any]) -> Tool:
        """创建Tool记录"""
        tool = Tool(**tool_data)
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool
    
    @staticmethod
    def get_by_id(db: Session, tool_id: UUID) -> Optional[Tool]:
        """根据ID查询Tool"""
        return db.query(Tool).filter(Tool.id == tool_id).first()
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Tool]:
        """根据名称查询Tool"""
        return db.query(Tool).filter(Tool.name == name).first()
    
    @staticmethod
    def list_all(
        db: Session,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tool]:
        """查询Tool列表，支持过滤"""
        query = db.query(Tool)
        
        if tool_type:
            query = query.filter(Tool.tool_type == tool_type)
        if category:
            query = query.filter(Tool.category == category)
        if status:
            query = query.filter(Tool.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def search(
        db: Session,
        query_text: str,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tool]:
        """搜索Tool（按名称、描述）"""
        query = db.query(Tool)
        
        # 构建搜索条件
        search_filter = or_(
            Tool.name.ilike(f"%{query_text}%"),
            Tool.display_name.ilike(f"%{query_text}%"),
            Tool.description.ilike(f"%{query_text}%")
        )
        query = query.filter(search_filter)
        
        if tool_type:
            query = query.filter(Tool.tool_type == tool_type)
        if category:
            query = query.filter(Tool.category == category)
        if status:
            query = query.filter(Tool.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, tool_id: UUID, updates: Dict[str, Any]) -> Optional[Tool]:
        """更新Tool记录"""
        tool = db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            return None
        
        for key, value in updates.items():
            setattr(tool, key, value)
        
        db.commit()
        db.refresh(tool)
        return tool
    
    @staticmethod
    def delete(db: Session, tool_id: UUID) -> bool:
        """删除Tool记录"""
        tool = db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            return False
        
        db.delete(tool)
        db.commit()
        return True
    
    @staticmethod
    def increment_usage_count(db: Session, tool_id: UUID) -> bool:
        """增加使用计数"""
        tool = db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            return False
        
        tool.usage_count += 1
        db.commit()
        return True
    
    @staticmethod
    def get_by_type(db: Session, tool_type: str) -> List[Tool]:
        """获取指定类型的所有Tool"""
        return db.query(Tool).filter(
            and_(Tool.tool_type == tool_type, Tool.status == 'active')
        ).all()
    
    @staticmethod
    def count(
        db: Session,
        tool_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> int:
        """统计Tool数量"""
        query = db.query(func.count(Tool.id))

        if query_text:
            search_filter = or_(
                Tool.name.ilike(f"%{query_text}%"),
                Tool.display_name.ilike(f"%{query_text}%"),
                Tool.description.ilike(f"%{query_text}%")
            )
            query = query.filter(search_filter)
        if tool_type:
            query = query.filter(Tool.tool_type == tool_type)
        if status:
            query = query.filter(Tool.status == status)
        if category:
            query = query.filter(Tool.category == category)
        
        return query.scalar()
