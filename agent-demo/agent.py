"""
简化的 Agent 实现 - 使用 Google ADK 和 LiteLLM
"""
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part
import sys
import time
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))
import config
from skills.manager import skills_manager

# 初始化 LiteLLM Model
model = LiteLlm(
    model="openai/"+config.settings.DEFAULT_LLM_MODEL,
    api_key=config.settings.QWEN_API_KEY,
    base_url=config.settings.QWEN_BASE_URL
)

# 基础 instruction
base_instruction = """You are an academic research assistant. 
Your goal is to help users with academic research tasks.
Always cite your sources when providing information."""

# 初始化 Session Service
session_service = InMemorySessionService()

def create_agent_with_skills() -> Agent:
    """
    创建带有激活技能的 Agent
    
    Returns:
        配置好的 Agent 实例
    """
    # 获取激活的技能内容
    skills_prompt = skills_manager.get_skills_prompt_extension()
    
    # 合并 instruction
    full_instruction = base_instruction
    if skills_prompt:
        full_instruction = base_instruction + "\n\n" + skills_prompt
    
    # 创建 Agent（每次创建新的以应用最新的 instruction）
    agent = Agent(
        name="academic_researcher",
        model=model,
        tools=[],  # 简化版本，不包含工具
        instruction=full_instruction,
        generate_content_config={"temperature": 0.7}
    )
    
    return agent

async def run_agent(input_text: str) -> str:
    """
    运行 Agent，自动激活相关技能
    
    Args:
        input_text: 用户输入文本
    
    Returns:
        Agent 的响应文本
    """
    user_id = "demo_user"
    # 使用时间戳创建唯一的 session_id，避免 session 冲突
    session_id = f"session_{int(time.time() * 1000)}"
    
    # 1. 根据查询自动激活技能
    if config.settings.SKILLS_AUTO_ACTIVATION:
        activated = skills_manager.auto_activate_for_query(input_text, max_skills=2)
        if activated:
            print(f"\n[技能激活] 已激活 {len(activated)} 个技能:")
            for skill in activated:
                print(f"  - {skill['name']}: {skill['description']}")
    
    # 2. 创建带有激活技能的 Agent
    agent = create_agent_with_skills()
    active_skills_count = len(skills_manager.get_active_skills())
    if active_skills_count > 0:
        print(f"\n[技能注入] 已将 {active_skills_count} 个技能注入 Agent 上下文")
    
    # 3. 创建 Runner（每次创建新的以使用最新的 Agent）
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="agent_demo"
    )
    
    # 4. 先创建 session（重要：必须在运行前创建）
    try:
        await session_service.create_session(
            app_name="agent_demo",
            user_id=user_id,
            session_id=session_id
        )
    except Exception as e:
        # 如果 session 已存在，忽略错误
        pass
    
    # 5. 构造输入内容
    content = Content(parts=[Part(text=input_text)])
    
    # 6. 运行 Agent 并从事件中收集响应
    import warnings
    # 抑制 Pydantic 序列化警告
    warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
    
    try:
        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            # 从事件中提取文本响应（根据 Google ADK 文档）
            try:
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text
                    elif isinstance(event.content, str):
                        response_text += event.content
                elif hasattr(event, 'text') and event.text:
                    response_text += event.text
            except Exception:
                # 忽略单个事件处理错误，继续处理下一个事件
                pass
        
        # 如果从事件中获取到了响应，直接返回
        if response_text:
            return response_text.strip()
    except Exception as e:
        print(f"\n❌ Agent 运行错误: {e}")
        import traceback
        traceback.print_exc()
        return f"错误: {str(e)}"
    
    # 7. 如果事件中没有响应，尝试从 session 获取（同步方法）
    try:
        # InMemorySessionService 的 get_session 是同步的（根据 backend 代码）
        session = session_service.get_session(
            app_name="agent_demo",
            user_id=user_id,
            session_id=session_id
        )
        
        # 检查 session 对象的属性
        if session:
            # 尝试不同的属性名
            if hasattr(session, 'messages') and session.messages:
                last_msg = session.messages[-1]
                if hasattr(last_msg, 'parts') and last_msg.parts:
                    text_parts = [p.text for p in last_msg.parts if p.text]
                    return "".join(text_parts)
            elif hasattr(session, 'history') and session.history:
                # 尝试 history 属性
                last_msg = session.history[-1] if session.history else None
                if last_msg and hasattr(last_msg, 'parts') and last_msg.parts:
                    text_parts = [p.text for p in last_msg.parts if p.text]
                    return "".join(text_parts)
    except Exception as e:
        print(f"\n❌ 获取响应错误: {e}")
        import traceback
        traceback.print_exc()
        # 不返回错误，继续尝试其他方法
    
    return "No response from agent."
