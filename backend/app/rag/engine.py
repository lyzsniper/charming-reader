from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_litellm import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI
from rag.ingestion import get_vector_store
from core.config import settings
from tavily import TavilyClient
import os

# --- 1. Define Graph State ---
class AgentState(TypedDict):
    question: str           # User question
    context: str            # Retrieved context
    answer: str             # Final answer
    source: str             # Source: 'local' (or 'web' in future)

# --- 2. Initialize LLM with LiteLLM ---
# Helper to configure environment variables for LiteLLM based on selected provider
def setup_litellm_env():
    if settings.DEEPSEEK_API_KEY:
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
    if settings.QWEN_API_KEY:
        os.environ["DASHSCOPE_API_KEY"] = settings.QWEN_API_KEY
    if settings.GLM_API_KEY:
        os.environ["ZHIPUAI_API_KEY"] = settings.GLM_API_KEY
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

setup_litellm_env()

# Map common model names to LiteLLM format if needed, or user passes full string
# e.g., "glm-4", "qwen-turbo", "deepseek-chat"
# ChatLiteLLM handles the routing based on the model name and set env vars.
llm = ChatLiteLLM(
    model=settings.DEFAULT_LLM_MODEL,
    temperature=0,
    max_tokens=None
)

# Use LlamaIndex LLM wrapper for Reranker (needs to be compatible)
# We use OpenAI class but point it to compatible APIs if needed, or just use GPT-4o for reranking quality
rerank_llm = OpenAI(
    model=settings.DEFAULT_LLM_MODEL, 
    api_key=settings.OPENAI_API_KEY or "dummy" # LlamaIndex OpenAI wrapper might need explicit key
)

# Initialize Tavily Client
tavily_client = None
if settings.TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

# --- 3. Define Tools/Helpers ---
def get_query_engine():
    """
    Get the LlamaIndex query engine backed by Elasticsearch with Hybrid Search and Re-ranking.
    """
    vector_store = get_vector_store()
    # We load the index from the vector store
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    
    # Configure Re-ranker
    # using LLM Reranker for simplicity as we have LLM access
    reranker = LLMRerank(choice_batch_size=5, top_n=3, llm=rerank_llm)
    
    # Configure retriever
    # Hybrid search is enabled in get_vector_store configuration
    return index.as_query_engine(
        similarity_top_k=10, # Retrieve more for reranking
        node_postprocessors=[reranker],
        vector_store_query_mode="hybrid",
        alpha=0.5 # Balance between keyword and vector search
    )

def local_retriever_tool(query: str) -> str:
    query_engine = get_query_engine()
    response = query_engine.query(query)
    return str(response)

def web_search_tool(query: str) -> str:
    """
    Web Search Tool using Tavily.
    """
    if not tavily_client:
        return "Web search is disabled (TAVILY_API_KEY not found)."
        
    try:
        # Search with advanced depth for better RAG context
        response = tavily_client.search(query=query, search_depth="advanced")
        # Extract content from results
        context = []
        for result in response.get("results", []):
            context.append(f"Source: {result['title']} ({result['url']})\nContent: {result['content']}")
        
        return "\n\n".join(context)
    except Exception as e:
        return f"Error during web search: {str(e)}"

# --- 4. Define Nodes ---

def retrieve_local_node(state: AgentState):
    """Node: Retrieve from local paper index."""
    print("---RETRIEVE: LOCAL PAPERS---")
    question = state["question"]
    context = local_retriever_tool(question)
    return {"context": context, "source": "local"}

def web_search_node(state: AgentState):
    """Node: Retrieve from Web."""
    print("---RETRIEVE: WEB SEARCH---")
    question = state["question"]
    context = web_search_tool(question)
    return {"context": context, "source": "web"}

def generate_node(state: AgentState):
    """Node: Generate answer using context."""
    print("---GENERATE ANSWER---")
    question = state["question"]
    context = state["context"]
    
    prompt = f"""
    You are an academic research assistant. Use the following context to answer the user's question.
    
    Guidelines:
    1. If the context contains specific paper details, you MUST cite them using the format [Source: Document Name/URL, Page X].
    2. If the answer is not in the context, say so, do not hallucinate.
    3. Keep the answer concise and professional.
    
    Context:
    {context}
    
    Question: 
    {question}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"answer": response.content}

def relevance_checker(state: AgentState):
    """
    Conditional Edge Logic: Check if retrieved context is relevant using LLM grading.
    If local context is empty or irrelevant, switch to web search.
    """
    context = state["context"]
    question = state["question"]
    
    # 1. Quick check for empty context
    if not context or "Empty Response" in context or len(context.strip()) < 10:
        print("---DECISION: CONTEXT EMPTY -> WEB SEARCH---")
        return "web_search"
        
    # 2. LLM Grading
    print("---CHECKING RELEVANCE---")
    
    grader_prompt = f"""
    You are a grader assessing relevance of a retrieved document to a user question.
    
    Retrieved document:
    {context[:2000]}... (truncated if too long)
    
    User question: 
    {question}
    
    Does the document contain keyword(s) or semantic meaning that aligns with the question?
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
    Only answer 'yes' or 'no'.
    """
    
    try:
        score = llm.invoke([HumanMessage(content=grader_prompt)]).content.lower().strip()
        print(f"---GRADER SCORE: {score}---")
        
        if "yes" in score:
            return "generate"
        else:
            print("---DECISION: CONTEXT IRRELEVANT -> WEB SEARCH---")
            return "web_search"
            
    except Exception as e:
        print(f"---GRADER ERROR: {e} -> FALLBACK TO GENERATE---")
        # Fail safe to generate if grader fails
        return "generate"

# --- 5. Build Graph ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("retrieve_local", retrieve_local_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)

# Set entry point
workflow.set_entry_point("retrieve_local")

# Add edges
# retrieve_local -> relevance_checker -> (generate OR web_search)
workflow.add_conditional_edges(
    "retrieve_local",
    relevance_checker,
    {
        "generate": "generate",
        "web_search": "web_search"
    }
)

# web_search -> generate
workflow.add_edge("web_search", "generate")

# generate -> END
workflow.add_edge("generate", END)

# Compile graph
rag_app = workflow.compile()

def get_rag_engine():
    return rag_app
