"""
Agent Skills Center API Endpoints
提供Skills、Agent配置、Tools的REST API接口
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from core.db import get_db
from services.skill_service import skill_service
from services.agent_service import agent_service
from services.tool_service import tool_service
from services.runtime_monitor_service import runtime_monitor_service
from skills.manager import skills_manager
from dao.skill_dao import SkillDAO
from dao.tool_dao import ToolDAO
from dao.agent_config_dao import AgentConfigDAO
from models.schemas import (
    SkillCreate, SkillUpdate, SkillResponse, PaginatedSkillsResponse,
    AgentConfigCreate, AgentConfigUpdate, AgentConfigResponse, PaginatedAgentConfigsResponse,
    ToolCreate, ToolUpdate, ToolResponse, PaginatedToolsResponse
)

router = APIRouter()

# ===== Skills API =====

@router.get("/skills", response_model=List[SkillResponse] | PaginatedSkillsResponse)
async def list_skills(
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    include_total: bool = False,
    db: Session = Depends(get_db)
):
    """列出所有Skills"""
    if search:
        skills = await skill_service.search_skills(db, search, category, status, skip, limit)
    else:
        skills = await skill_service.list_skills(db, category, status, skip, limit)
    if include_total:
        total = await skill_service.count_skills(db, category, status, search)
        return {"items": skills, "total": total}
    return skills

@router.get("/skills/popular", response_model=List[SkillResponse])
async def get_popular_skills(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取热门Skills"""
    return await skill_service.get_popular_skills(db, limit)

@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: UUID, db: Session = Depends(get_db)):
    """获取Skill详情"""
    skill = await skill_service.get_skill_by_id(db, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill

@router.post("/skills", response_model=SkillResponse, status_code=201)
async def create_skill(skill: SkillCreate, db: Session = Depends(get_db)):
    """创建新Skill"""
    return await skill_service.create_skill(db, skill.dict())

@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    updates: SkillUpdate,
    db: Session = Depends(get_db)
):
    """更新Skill"""
    updated = await skill_service.update_skill(db, skill_id, updates.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Skill not found")
    return updated

@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID, db: Session = Depends(get_db)):
    """删除Skill"""
    success = await skill_service.delete_skill(db, skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")

@router.post("/skills/sync")
async def sync_skills_from_filesystem(db: Session = Depends(get_db)):
    """从文件系统同步Skills到数据库"""
    result = await skills_manager.sync_with_database(db)
    return result

# ===== Agent Config API =====

@router.get("/agent-configs", response_model=List[AgentConfigResponse] | PaginatedAgentConfigsResponse)
async def list_agent_configs(
    user_id: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    include_total: bool = False,
    db: Session = Depends(get_db)
):
    """列出Agent配置"""
    agents = await agent_service.list_agent_configs(db, user_id, search, status, skip, limit)
    if include_total:
        total = await agent_service.count_agent_configs(db, user_id, search, status)
        return {"items": agents, "total": total}
    return agents

@router.get("/agent-configs/{agent_id}")
async def get_agent_config(agent_id: UUID, db: Session = Depends(get_db)):
    """获取Agent配置详情"""
    agent = await agent_service.get_agent_with_dependencies(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return agent

@router.post("/agent-configs", response_model=AgentConfigResponse, status_code=201)
async def create_agent_config(config: AgentConfigCreate, db: Session = Depends(get_db)):
    """创建Agent配置"""
    skill_ids = config.skill_ids or []
    tool_ids = config.tool_ids or []
    config_dict = config.dict(exclude={"skill_ids", "tool_ids"})
    
    agent = await agent_service.create_agent_config(
        db, config_dict, skill_ids, tool_ids
    )
    return agent

@router.put("/agent-configs/{agent_id}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_id: UUID,
    updates: AgentConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新Agent配置"""
    updated = await agent_service.update_agent_config(
        db, agent_id, updates.dict(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return updated

@router.delete("/agent-configs/{agent_id}", status_code=204)
async def delete_agent_config(agent_id: UUID, db: Session = Depends(get_db)):
    """删除Agent配置"""
    success = await agent_service.delete_agent_config(db, agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent config not found")

@router.post("/agent-configs/{agent_id}/skills")
async def assign_skills_to_agent(
    agent_id: UUID,
    skill_ids: List[UUID],
    replace: bool = False,
    db: Session = Depends(get_db)
):
    """为Agent分配Skills"""
    success = await agent_service.assign_skills(db, agent_id, skill_ids, replace=replace)
    return {"success": success}

@router.delete("/agent-configs/{agent_id}/skills/{skill_id}", status_code=204)
async def remove_skill_from_agent(
    agent_id: UUID,
    skill_id: UUID,
    db: Session = Depends(get_db)
):
    """移除Agent的Skill"""
    success = await agent_service.remove_skill(db, agent_id, skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Association not found")

@router.post("/agent-configs/{agent_id}/tools")
async def assign_tools_to_agent(
    agent_id: UUID,
    tool_ids: List[UUID],
    replace: bool = False,
    db: Session = Depends(get_db)
):
    """为Agent分配Tools"""
    success = await agent_service.assign_tools(db, agent_id, tool_ids, replace=replace)
    return {"success": success}

# ===== Tools API =====

@router.get("/tools", response_model=List[ToolResponse] | PaginatedToolsResponse)
async def list_tools(
    tool_type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    include_total: bool = False,
    db: Session = Depends(get_db)
):
    """列出Tools"""
    tools = await tool_service.list_tools(db, tool_type, category, status, search, skip, limit)
    if include_total:
        total = await tool_service.count_tools(db, tool_type, status, category, search)
        return {"items": tools, "total": total}
    return tools

@router.get("/tools/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: UUID, db: Session = Depends(get_db)):
    """获取Tool详情"""
    tool = await tool_service.get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@router.post("/tools", response_model=ToolResponse, status_code=201)
async def create_tool(tool: ToolCreate, db: Session = Depends(get_db)):
    """创建Tool"""
    return await tool_service.create_tool(db, tool.dict())

@router.put("/tools/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    updates: ToolUpdate,
    db: Session = Depends(get_db)
):
    """更新Tool"""
    updated = await tool_service.update_tool(db, tool_id, updates.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Tool not found")
    return updated

@router.delete("/tools/{tool_id}", status_code=204)
async def delete_tool(tool_id: UUID, db: Session = Depends(get_db)):
    """删除Tool"""
    success = await tool_service.delete_tool(db, tool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tool not found")

@router.post("/tools/discover")
async def discover_mcp_tools(db: Session = Depends(get_db)):
    """发现MCP工具"""
    result = await tool_service.discover_mcp_tools(db)
    return result

# ===== Demo Seed API =====

@router.post("/dev/seed-demo")
async def seed_demo_data(db: Session = Depends(get_db)):
    """插入演示用Skills、Tools和Agent配置"""
    created = {"skills": [], "tools": [], "agents": []}
    skipped = {"skills": [], "tools": [], "agents": []}

    demo_skills = [
        {
            "name": "paper-summary",
            "display_name": "论文摘要助手",
            "description": "生成论文的结构化摘要与亮点概述",
            "version": "1.0.0",
            "content": "你是论文摘要助手，输出结构化摘要：背景、方法、结果、贡献。",
            "category": "academic",
            "tags": ["summary", "academic"],
            "triggers": ["摘要", "总结", "overview"],
            "author": "system",
        },
        {
            "name": "literature-review",
            "display_name": "文献综述生成",
            "description": "综合多篇论文生成综述与趋势",
            "version": "1.0.0",
            "content": "你是文献综述助手，输出研究趋势、差距和建议。",
            "category": "academic",
            "tags": ["review", "trend"],
            "triggers": ["综述", "literature", "related work"],
            "author": "system",
        },
        {
            "name": "citation-format",
            "display_name": "引文格式化",
            "description": "将引用信息格式化为常见引用样式",
            "version": "1.0.0",
            "content": "你是引文格式化助手，支持 APA/IEEE/MLA。",
            "category": "academic",
            "tags": ["citation", "format"],
            "triggers": ["引用", "citation"],
            "author": "system",
        },
        {
            "name": "experiment-planner",
            "display_name": "实验设计助手",
            "description": "帮助制定实验设计、变量控制与评估指标",
            "version": "1.0.0",
            "content": "你是实验设计助手，输出实验目标、变量控制、评估指标与风险点。",
            "category": "research",
            "tags": ["experiment", "design"],
            "triggers": ["实验设计", "对照组", "ablation"],
            "author": "system",
        },
    ]

    demo_tools = [
        {
            "name": "health-check",
            "display_name": "服务健康检查",
            "description": "调用后端根路径检查服务状态",
            "tool_type": "api",
            "category": "utils",
            "source_config": {"url": "http://localhost:18000/"},
            "schema_config": {"type": "object", "properties": {}},
        },
        {
            "name": "echo-text",
            "display_name": "文本回显",
            "description": "回显输入文本，便于快速验证工具调用链路",
            "tool_type": "python",
            "category": "utils",
            "source_config": {"module_path": "tools.local_tools", "function_name": "echo_text"},
            "schema_config": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            },
        },
        {
            "name": "crossref-search",
            "display_name": "Crossref 文献检索",
            "description": "基于关键词检索文献元数据（Crossref API）",
            "tool_type": "api",
            "category": "academic",
            "source_config": {
                "url": "https://api.crossref.org/works",
                "method": "GET"
            },
            "schema_config": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                    "rows": {"type": "integer", "description": "返回条数"}
                },
                "required": ["query"]
            },
        },
    ]

    for skill in demo_skills:
        existing = SkillDAO.get_by_name(db, skill["name"])
        if existing:
            skipped["skills"].append(skill["name"])
            continue
        created_skill = await skill_service.create_skill(db, skill)
        created["skills"].append(str(created_skill.id))

    for tool in demo_tools:
        existing = ToolDAO.get_by_name(db, tool["name"])
        if existing:
            skipped["tools"].append(tool["name"])
            continue
        created_tool = await tool_service.create_tool(db, tool)
        created["tools"].append(str(created_tool.id))

    demo_agent_name = "paper-research-agent"
    existing_agent = AgentConfigDAO.get_by_name(db, demo_agent_name)
    if existing_agent:
        skipped["agents"].append(demo_agent_name)
    else:
        skill_ids = [UUID(sid) for sid in created["skills"]]
        tool_ids = [UUID(tid) for tid in created["tools"]]
        agent = await agent_service.create_agent_config(
            db,
            {
                "name": demo_agent_name,
                "display_name": "论文研究助手",
                "instruction": "你是论文研究助手，擅长检索、摘要与综述生成。",
                "status": "active",
            },
            skill_ids,
            tool_ids,
        )
        created["agents"].append(str(agent.id))

    demo_agent_name = "experiment-analysis-agent"
    existing_agent = AgentConfigDAO.get_by_name(db, demo_agent_name)
    if existing_agent:
        skipped["agents"].append(demo_agent_name)
    else:
        skill_records = []
        tool_records = []
        for skill_name in ["experiment-planner", "paper-summary"]:
            skill_record = SkillDAO.get_by_name(db, skill_name)
            if skill_record:
                skill_records.append(skill_record)
        for tool_name in ["crossref-search", "echo-text"]:
            tool_record = ToolDAO.get_by_name(db, tool_name)
            if tool_record:
                tool_records.append(tool_record)
        skill_ids = [record.id for record in skill_records]
        tool_ids = [record.id for record in tool_records]
        agent = await agent_service.create_agent_config(
            db,
            {
                "name": demo_agent_name,
                "display_name": "实验分析助手",
                "instruction": "你是实验分析助手，擅长实验设计、消融分析与文献检索。",
                "status": "active",
            },
            skill_ids,
            tool_ids,
        )
        created["agents"].append(str(agent.id))

    return {"created": created, "skipped": skipped}

# ===== Runtime Monitor API =====

@router.get("/runtime/skills/active")
async def get_active_skills(
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取当前激活的Skills"""
    return await runtime_monitor_service.get_active_skills(db, session_id)

@router.get("/runtime/agents/{agent_id}/stats")
async def get_agent_stats(
    agent_id: UUID,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """获取Agent统计信息"""
    return await runtime_monitor_service.get_agent_stats(db, agent_id, days)

@router.get("/runtime/skills/{skill_id}/logs")
async def get_skill_activation_logs(
    skill_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取Skill激活日志"""
    logs = await runtime_monitor_service.get_skill_activation_logs(db, skill_id, skip, limit)
    return [
        {
            "id": str(log.id),
            "skill_id": str(log.skill_id),
            "session_id": log.session_id,
            "activated_at": log.activated_at.isoformat() if log.activated_at else None,
            "deactivated_at": log.deactivated_at.isoformat() if log.deactivated_at else None,
            "activation_reason": log.activation_reason,
            "query_text": log.query_text
        }
        for log in logs
    ]
