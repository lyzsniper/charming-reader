from google.adk.sessions import InMemorySessionService
import inspect

svc = InMemorySessionService()
print(inspect.signature(svc.get_session))

