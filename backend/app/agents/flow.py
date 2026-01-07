from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part
from tools.definitions import scholar_search, knowledge_retriever
from core.config import settings
import asyncio

# Initialize LiteLLM Model
model = LiteLlm(
    model=settings.DEFAULT_LLM_MODEL
)

# Define the Agent
academic_agent = Agent(
    name="academic_researcher",
    model=model,
    tools=[scholar_search, knowledge_retriever],
    instruction="""You are an academic research assistant. 
    Your goal is to help users find and understand academic papers.
    You have access to a scholar search tool to find real papers and a knowledge retriever to look up information in uploaded documents.
    Always cite your sources when providing information from papers.""",
    generate_content_config={"temperature": 0.7}
)

# Initialize Session Service and Runner
# Note: In a real app, session service should be persistent (e.g. Firestore, Redis)
# InMemorySessionService resets on restart.
session_service = InMemorySessionService()

runner = Runner(
    agent=academic_agent,
    session_service=session_service,
    app_name="paper_agent"
)

async def run_agent(input_text: str) -> str:
    """
    Run the agent with the given input text.
    """
    user_id = "default_user"
    session_id = "default_session"
    
    # Construct input content
    content = Content(parts=[Part(text=input_text)])
    
    # Run the agent asynchronously
    # We iterate over events to ensure the run completes
    final_text = ""
    
    # Using run_async
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content
    ):
        # We could capture streaming tokens here if needed
        # For now, we just wait for completion
        pass
        
    # Retrieve the updated session to get the full response
    # Since session_service might be sync or async, we need to check.
    # InMemorySessionService methods are usually sync.
    session = session_service.get_session(
        app_name="paper_agent",
        user_id=user_id,
        session_id=session_id
    )
    
    if session and session.messages:
        # The last message should be the model response
        last_msg = session.messages[-1]
        # Extract text
        if last_msg.parts:
            text_parts = [p.text for p in last_msg.parts if p.text]
            return "".join(text_parts)
            
    return "No response from agent."
