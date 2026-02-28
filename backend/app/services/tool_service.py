"""
Tool Service 层
实现Tool的业务逻辑，包括MCP工具发现和注册
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from dao.tool_dao import ToolDAO
from models.sql import Tool


class ToolService:
    """Tool业务服务"""
    
    async def create_tool(self, db: Session, tool_data: Dict[str, Any]) -> Tool:
        """创建Tool"""
        tool_data["status"] = tool_data.get("status", "active")
        return ToolDAO.create(db, tool_data)
    
    async def update_tool(
        self,
        db: Session,
        tool_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[Tool]:
        """更新Tool"""
        return ToolDAO.update(db, tool_id, updates)
    
    async def delete_tool(self, db: Session, tool_id: UUID) -> bool:
        """删除Tool"""
        return ToolDAO.delete(db, tool_id)
    
    async def get_tool(self, db: Session, tool_id: UUID) -> Optional[Tool]:
        """根据ID获取Tool"""
        return ToolDAO.get_by_id(db, tool_id)
    
    async def get_tool_by_name(self, db: Session, name: str) -> Optional[Tool]:
        """根据名称获取Tool"""
        return ToolDAO.get_by_name(db, name)
    
    async def list_tools(
        self,
        db: Session,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tool]:
        """列出Tools"""
        if query:
            return ToolDAO.search(db, query, tool_type, category, status, skip, limit)
        return ToolDAO.list_all(db, tool_type, category, status, skip, limit)
    
    async def search_tools(
        self,
        db: Session,
        query: str,
        tool_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tool]:
        """搜索Tools"""
        return ToolDAO.search(db, query, tool_type, category, status, skip, limit)
    
    async def discover_mcp_tools(self, db: Session) -> Dict[str, Any]:
        """发现MCP工具并注册到数据库"""
        discovered_count = 0
        skipped_count = 0
        error_count = 0
        
        try:
            # TODO: 实际集成MCP工具发现逻辑
            # 这里需要扫描MCP服务器配置，获取可用工具
            # 从 tools/mcp_tool_adapter.py 或 MCP 配置中获取工具列表
            
            # 示例：假设我们有一个函数获取MCP工具列表
            # mcp_tools = await get_mcp_tools_list()
            
            # for mcp_tool in mcp_tools:
            #     # 检查是否已存在
            #     existing_tool = ToolDAO.get_by_name(db, mcp_tool["name"])
            #     if existing_tool:
            #         skipped_count += 1
            #         continue
            #     
            #     # 创建工具记录
            #     tool_data = {
            #         "name": mcp_tool["name"],
            #         "display_name": mcp_tool.get("display_name", mcp_tool["name"]),
            #         "description": mcp_tool.get("description", ""),
            #         "tool_type": "mcp",
            #         "category": mcp_tool.get("category", "general"),
            #         "source_config": mcp_tool.get("source_config", {}),
            #         "schema_config": mcp_tool.get("schema", {}),
            #         "status": "active"
            #     }
            #     
            #     ToolDAO.create(db, tool_data)
            #     discovered_count += 1
            
            return {
                "discovered": discovered_count,
                "skipped": skipped_count,
                "errors": error_count,
                "message": f"Discovered {discovered_count} MCP tools"
            }
            
        except Exception as e:
            return {
                "discovered": 0,
                "skipped": 0,
                "errors": 1,
                "message": f"Error discovering MCP tools: {str(e)}"
            }
    
    async def register_python_function(
        self,
        db: Session,
        function_name: str,
        module_path: str,
        description: str = "",
        schema: Optional[Dict[str, Any]] = None
    ) -> Tool:
        """注册Python函数工具"""
        tool_data = {
            "name": function_name,
            "display_name": function_name,
            "description": description,
            "tool_type": "python",
            "category": "python_function",
            "source_config": {
                "module_path": module_path,
                "function_name": function_name
            },
            "schema_config": schema or {},
            "status": "active"
        }
        
        return ToolDAO.create(db, tool_data)
    
    async def increment_usage(self, db: Session, tool_id: UUID) -> bool:
        """增加工具使用计数"""
        return ToolDAO.increment_usage_count(db, tool_id)
    
    async def count_tools(
        self,
        db: Session,
        tool_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None
    ) -> int:
        """统计Tool数量"""
        return ToolDAO.count(db, tool_type, status, category, query)


# 创建全局单例
tool_service = ToolService()
