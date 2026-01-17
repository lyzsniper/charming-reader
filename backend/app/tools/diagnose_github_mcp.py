"""
诊断GitHub MCP集成问题的工具脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.manager import skills_manager
from services.mcp_service import get_mcp_service
from tools.mcp_tool_adapter import get_github_mcp_tools
from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)

async def diagnose():
    """诊断GitHub MCP集成问题"""
    print("=" * 80)
    print("GitHub MCP 集成诊断")
    print("=" * 80)
    
    # 1. 检查配置
    print("\n1. 检查配置...")
    print(f"   GITHUB_MCP_URL: {settings.GITHUB_MCP_URL}")
    print(f"   GITHUB_MCP_TOKEN: {'已设置' if settings.GITHUB_MCP_TOKEN else '未设置'}")
    if settings.GITHUB_MCP_TOKEN:
        print(f"   Token前10字符: {settings.GITHUB_MCP_TOKEN[:10]}...")
    
    # 2. 检查GitHub skill是否加载
    print("\n2. 检查GitHub skill是否加载...")
    all_skills = skills_manager.list_all_skills()
    github_skill = None
    for skill in all_skills:
        if skill['name'] == 'github-integration':
            github_skill = skill
            break
    
    if github_skill:
        print(f"   ✓ GitHub skill已加载")
        print(f"   描述: {github_skill.get('description', 'N/A')}")
        print(f"   触发词: {github_skill.get('triggers', [])}")
        print(f"   状态: {github_skill.get('status', 'N/A')}")
    else:
        print("   ✗ GitHub skill未找到！")
        print(f"   已加载的技能: {[s['name'] for s in all_skills]}")
        return
    
    # 3. 测试skill匹配
    print("\n3. 测试skill匹配...")
    test_queries = [
        "给我查找有关transformer的相关开源项目",
        "搜索GitHub上的transformer项目",
        "查找transformer开源项目"
    ]
    
    for query in test_queries:
        matched = skills_manager.auto_activate_for_query(query, max_skills=2)
        print(f"   查询: {query}")
        if matched:
            print(f"   ✓ 匹配到 {len(matched)} 个skill: {[s['name'] for s in matched]}")
        else:
            print(f"   ✗ 未匹配到任何skill")
    
    # 4. 测试MCP服务连接
    print("\n4. 测试MCP服务连接...")
    try:
        mcp_service = get_mcp_service()
        print(f"   MCP服务URL: {mcp_service.base_url}")
        print("   正在获取工具列表...")
        tools = await mcp_service.list_tools()
        if tools:
            print(f"   ✓ 成功获取 {len(tools)} 个工具")
            print(f"   工具列表: {[t.get('name', 'unknown') for t in tools[:5]]}")
        else:
            print("   ✗ 未获取到工具（可能是API格式问题）")
    except Exception as e:
        print(f"   ✗ MCP服务连接失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. 测试工具适配器
    print("\n5. 测试工具适配器...")
    try:
        github_tools = await get_github_mcp_tools()
        if github_tools:
            print(f"   ✓ 成功创建 {len(github_tools)} 个工具适配器")
            for tool in github_tools[:3]:
                print(f"   - {tool.__name__}: {tool.__doc__[:50] if tool.__doc__ else 'N/A'}...")
        else:
            print("   ✗ 未创建任何工具适配器")
    except Exception as e:
        print(f"   ✗ 工具适配器创建失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. 检查激活的skill
    print("\n6. 检查当前激活的skill...")
    active_skills = skills_manager.get_active_skills()
    if active_skills:
        print(f"   当前激活 {len(active_skills)} 个skill:")
        for skill in active_skills:
            print(f"   - {skill['name']}: {skill.get('description', 'N/A')[:50]}")
    else:
        print("   当前没有激活的skill")
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(diagnose())
