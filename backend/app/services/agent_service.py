"""
Agent Service 层
实现Agent配置的业务逻辑，包括Skills/Tools关联管理
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from dao.agent_config_dao import (
    AgentTemplateDAO, AgentConfigDAO, AgentSkillDAO, AgentToolDAO
)
from dao.skill_dao import SkillDAO
from dao.tool_dao import ToolDAO
from models.sql import AgentTemplate, AgentConfig, AgentSkill, AgentTool


class AgentService:
    """Agent业务服务"""
    
    async def create_agent_config(
        self,
        db: Session,
        config_data: Dict[str, Any],
        skill_ids: Optional[List[UUID]] = None,
        tool_ids: Optional[List[UUID]] = None
    ) -> AgentConfig:
        """创建Agent配置"""
        # 创建Agent配置
        agent_config = AgentConfigDAO.create(db, config_data)
        
        # 关联Skills
        if skill_ids:
            for priority, skill_id in enumerate(skill_ids):
                AgentSkillDAO.create(db, {
                    "agent_config_id": agent_config.id,
                    "skill_id": skill_id,
                    "priority": len(skill_ids) - priority,  # 逆序优先级
                    "auto_activate": True
                })
        
        # 关联Tools
        if tool_ids:
            for tool_id in tool_ids:
                AgentToolDAO.create(db, {
                    "agent_config_id": agent_config.id,
                    "tool_id": tool_id
                })
        
        return agent_config
    
    async def update_agent_config(
        self,
        db: Session,
        agent_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[AgentConfig]:
        """更新Agent配置"""
        return AgentConfigDAO.update(db, agent_id, updates)
    
    async def delete_agent_config(self, db: Session, agent_id: UUID) -> bool:
        """删除Agent配置"""
        return AgentConfigDAO.delete(db, agent_id)
    
    async def assign_skills(
        self,
        db: Session,
        agent_id: UUID,
        skill_ids: List[UUID],
        auto_activate: bool = True,
        replace: bool = False
    ) -> bool:
        """为Agent分配Skills"""
        # 如果是替换模式，先删除现有关联
        if replace:
            AgentSkillDAO.delete_by_agent(db, agent_id)
        
        # 添加新关联
        for priority, skill_id in enumerate(skill_ids):
            # 检查Skill是否存在
            skill = SkillDAO.get_by_id(db, skill_id)
            if not skill:
                continue
            
            # 检查是否已存在关联
            existing = AgentSkillDAO.get(db, agent_id, skill_id)
            if existing:
                continue
            
            AgentSkillDAO.create(db, {
                "agent_config_id": agent_id,
                "skill_id": skill_id,
                "priority": len(skill_ids) - priority,
                "auto_activate": auto_activate
            })
        
        return True
    
    async def remove_skill(
        self,
        db: Session,
        agent_id: UUID,
        skill_id: UUID
    ) -> bool:
        """移除Agent的Skill"""
        return AgentSkillDAO.delete(db, agent_id, skill_id)
    
    async def assign_tools(
        self,
        db: Session,
        agent_id: UUID,
        tool_ids: List[UUID],
        replace: bool = False
    ) -> bool:
        """为Agent分配Tools"""
        # 如果是替换模式，先删除现有关联
        if replace:
            AgentToolDAO.delete_by_agent(db, agent_id)
        
        # 添加新关联
        for tool_id in tool_ids:
            # 检查Tool是否存在
            tool = ToolDAO.get_by_id(db, tool_id)
            if not tool:
                continue
            
            # 检查是否已存在关联
            existing = AgentToolDAO.get(db, agent_id, tool_id)
            if existing:
                continue
            
            AgentToolDAO.create(db, {
                "agent_config_id": agent_id,
                "tool_id": tool_id
            })
        
        return True
    
    async def remove_tool(
        self,
        db: Session,
        agent_id: UUID,
        tool_id: UUID
    ) -> bool:
        """移除Agent的Tool"""
        return AgentToolDAO.delete(db, agent_id, tool_id)
    
    async def get_agent_config(
        self,
        db: Session,
        agent_id: UUID,
        load_relations: bool = True
    ) -> Optional[AgentConfig]:
        """获取Agent配置（可选加载关联）"""
        return AgentConfigDAO.get_by_id(db, agent_id, load_relations)
    
    async def get_agent_with_dependencies(
        self,
        db: Session,
        agent_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """获取Agent及其关联的Skills和Tools"""
        agent = AgentConfigDAO.get_by_id(db, agent_id, load_relations=True)
        if not agent:
            return None
        
        # 构建返回数据
        skills = []
        for agent_skill in agent.agent_skills:
            skills.append({
                "id": str(agent_skill.skill.id),
                "name": agent_skill.skill.name,
                "display_name": agent_skill.skill.display_name,
                "description": agent_skill.skill.description,
                "priority": agent_skill.priority,
                "auto_activate": agent_skill.auto_activate,
                "is_required": agent_skill.is_required
            })
        
        tools = []
        for agent_tool in agent.agent_tools:
            tools.append({
                "id": str(agent_tool.tool.id),
                "name": agent_tool.tool.name,
                "display_name": agent_tool.tool.display_name,
                "description": agent_tool.tool.description,
                "tool_type": agent_tool.tool.tool_type,
                "is_required": agent_tool.is_required,
                "configuration": agent_tool.configuration
            })
        
        return {
            "id": str(agent.id),
            "name": agent.name,
            "display_name": agent.display_name,
            "instruction": agent.instruction,
            "status": agent.status,
            "is_default": agent.is_default,
            "template_id": str(agent.template_id) if agent.template_id else None,
            "model_config_id": str(agent.model_config_id) if agent.model_config_id else None,
            "skills": skills,
            "tools": tools,
            "agent_metadata": agent.agent_metadata,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
        }
    
    async def list_agent_configs(
        self,
        db: Session,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentConfig]:
        """列出Agent配置"""
        if query:
            return AgentConfigDAO.search(db, query, user_id, status, skip, limit)
        return AgentConfigDAO.list_all(db, user_id, status, skip, limit)

    async def count_agent_configs(
        self,
        db: Session,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """统计Agent配置数量"""
        return AgentConfigDAO.count(db, user_id, status, query)
    
    async def get_default_agent(
        self,
        db: Session,
        user_id: Optional[str] = None
    ) -> Optional[AgentConfig]:
        """获取默认Agent配置"""
        return AgentConfigDAO.get_default(db, user_id)
    
    async def set_default_agent(
        self,
        db: Session,
        agent_id: UUID,
        user_id: Optional[str] = None
    ) -> bool:
        """设置默认Agent配置"""
        return AgentConfigDAO.set_default(db, agent_id, user_id)
    
    async def instantiate_agent(
        self,
        db: Session,
        agent_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """根据配置实例化Agent（准备运行时数据）"""
        agent_data = await self.get_agent_with_dependencies(db, agent_id)
        if not agent_data:
            return None
        
        # 准备Skills内容
        skills_content = []
        for skill_info in agent_data["skills"]:
            from services.skill_service import skill_service
            content = await skill_service.get_skill_content(db, UUID(skill_info["id"]))
            if content:
                skills_content.append({
                    "name": skill_info["name"],
                    "content": content
                })
        
        # 准备Tools配置
        tools_config = []
        for tool_info in agent_data["tools"]:
            tools_config.append({
                "id": tool_info["id"],
                "name": tool_info["name"],
                "tool_type": tool_info["tool_type"],
                "configuration": tool_info.get("configuration", {})
            })
        
        return {
            "agent_config": agent_data,
            "skills_content": skills_content,
            "tools_config": tools_config
        }
    
    # Agent Template 相关方法
    async def create_agent_template(
        self,
        db: Session,
        template_data: Dict[str, Any]
    ) -> AgentTemplate:
        """创建Agent模板"""
        return AgentTemplateDAO.create(db, template_data)
    
    async def list_agent_templates(
        self,
        db: Session,
        category: Optional[str] = None,
        is_builtin: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentTemplate]:
        """列出Agent模板"""
        return AgentTemplateDAO.list_all(db, category, is_builtin, None, skip, limit)
    
    async def get_agent_template(
        self,
        db: Session,
        template_id: UUID
    ) -> Optional[AgentTemplate]:
        """获取Agent模板"""
        return AgentTemplateDAO.get_by_id(db, template_id)


# 创建全局单例
agent_service = AgentService()
