"""
Agent Skills 验证演示 - 主入口
"""
import asyncio
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from agent import run_agent
from skills.manager import skills_manager

def print_separator():
    print("\n" + "="*60 + "\n")

def print_skills_info():
    """打印技能信息"""
    print_separator()
    print("📚 可用技能列表:")
    print_separator()
    
    all_skills = skills_manager.list_all_skills()
    for i, skill in enumerate(all_skills, 1):
        status = "✓ ACTIVE" if skill["status"] == "active" else "○ Available"
        print(f"{i}. {skill['name']} [{status}]")
        print(f"   描述: {skill['description']}")
        print(f"   触发词: {', '.join(skill['triggers'][:5])}")
        print()

async def interactive_demo():
    """交互式演示"""
    print("="*60)
    print("🤖 Agent Skills 验证演示")
    print("="*60)
    
    # 显示技能信息
    print_skills_info()
    
    print("💡 提示: 输入查询来测试技能自动激活功能")
    print("   示例: '帮我分析这篇论文' 或 '格式化引用'")
    print("   输入 'quit' 或 'exit' 退出")
    print_separator()
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            # 显示激活的技能
            active_before = skills_manager.get_active_skills()
            
            print("\n🤔 Agent 正在思考...")
            
            # 运行 Agent
            response = await run_agent(user_input)
            
            # 显示激活的技能（如果有变化）
            active_after = skills_manager.get_active_skills()
            if len(active_after) > len(active_before):
                print_separator()
                print("📌 当前激活的技能:")
                for skill in active_after:
                    print(f"  - {skill['name']}")
            
            print_separator()
            print(f"🤖 Agent: {response}")
            print_separator()
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()

async def test_demo():
    """测试演示 - 运行几个预设查询"""
    print("="*60)
    print("🧪 Agent Skills 测试演示")
    print("="*60)
    
    test_queries = [
        "帮我分析这篇论文的研究方法",
        "格式化这些引用为 APA 格式",
        "生成一个关于深度学习的文献综述"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_queries)}: {query}")
        print('='*60)
        
        response = await run_agent(query)
        
        print(f"\n响应: {response}")
        print("\n" + "-"*60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试模式
        asyncio.run(test_demo())
    else:
        # 交互模式
        asyncio.run(interactive_demo())
