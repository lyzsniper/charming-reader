"""
检查 ADK SessionService 的接口和实现
"""
from google.adk.sessions import InMemorySessionService, Session
from google.genai.types import Content, Part
import inspect

# 创建 InMemorySessionService 实例
svc = InMemorySessionService()

print("=" * 80)
print("InMemorySessionService 的所有方法:")
print("=" * 80)

# 获取所有公共方法
methods = [method for method in dir(svc) if not method.startswith('_') and callable(getattr(svc, method))]

for method_name in methods:
    method = getattr(svc, method_name)
    sig = inspect.signature(method)
    print(f"\n{method_name}{sig}")
    
    # 获取方法的文档字符串
    if method.__doc__:
        print(f"  文档: {method.__doc__.strip()[:100]}...")

print("\n" + "=" * 80)
print("Session 对象的属性:")
print("=" * 80)

# 创建一个测试 session
test_session = Session(
    session_id="test",
    messages=[Content(parts=[Part(text="hello")])],
    state={}
)

print(f"\nSession 对象类型: {type(test_session)}")
print(f"Session 属性: {dir(test_session)}")

# 测试 session 的关键属性
print(f"\nsession_id: {test_session.session_id if hasattr(test_session, 'session_id') else 'N/A'}")
print(f"messages: {test_session.messages if hasattr(test_session, 'messages') else 'N/A'}")
print(f"state: {test_session.state if hasattr(test_session, 'state') else 'N/A'}")

print("\n" + "=" * 80)

