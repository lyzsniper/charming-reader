"""
Agentic RAG 实现
LLM 驱动的智能体决定何时检索
动态决策，高灵活性，可以使用工具进行多步检索
"""
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .base import BaseRAGStrategy, RAGStrategyConfig
from ..ingestion import get_vector_store
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI
from core.config import settings
from tavily import TavilyClient
import os


class AgenticState(TypedDict):
    """智能体状态"""
    messages: List[Any]  # 消息历史
    question: str  # 用户问题
    context: str  # 检索到的上下文
    answer: str  # 最终答案
    iterations: int  # 迭代次数
    tools_used: List[str]  # 使用的工具列表


class AgenticRAGStrategy(BaseRAGStrategy):
    """Agentic RAG 策略：智能体驱动的 RAG"""
    
    def __init__(self, config: RAGStrategyConfig):
        super().__init__(config)
        self._graph = None
        self._llm = None
        self._query_engine = None
        self._tavily_client = None
    
    def _get_llm(self):
        """获取 LLM 实例"""
        if self._llm is None:
            if self.config.llm:
                self._llm = self.config.llm
            else:
                from langchain_litellm import ChatLiteLLM
                self._llm = ChatLiteLLM(
                    model=settings.DEFAULT_LLM_MODEL,
                    temperature=0,
                    max_tokens=None
                )
        return self._llm
    
    def _get_query_engine(self):
        """获取查询引擎"""
        if self._query_engine is None:
            vector_store = self.config.vector_store or get_vector_store()
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            
            if self.config.enable_rerank:
                rerank_llm = self.config.reranker or OpenAI(
                    model=settings.DEFAULT_LLM_MODEL,
                    api_key=settings.OPENAI_API_KEY or "dummy"
                )
                reranker = LLMRerank(choice_batch_size=5, top_n=self.config.rerank_top_n, llm=rerank_llm)
                self._query_engine = index.as_query_engine(
                    similarity_top_k=self.config.similarity_top_k,
                    node_postprocessors=[reranker],
                    vector_store_query_mode="hybrid",
                    alpha=0.5
                )
            else:
                self._query_engine = index.as_query_engine(
                    similarity_top_k=self.config.similarity_top_k,
                    vector_store_query_mode="hybrid",
                    alpha=0.5
                )
        return self._query_engine
    
    def _local_retriever_tool(self, query: str) -> str:
        """本地检索工具"""
        query_engine = self._get_query_engine()
        response = query_engine.query(query)
        return str(response)
    
    def _web_search_tool(self, query: str) -> str:
        """网络搜索工具"""
        if not self.config.enable_web_search:
            return "Web search is disabled."
        
        if self._tavily_client is None:
            if self.config.web_search_client:
                self._tavily_client = self.config.web_search_client
            elif settings.TAVILY_API_KEY:
                self._tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            else:
                return "Web search is disabled (TAVILY_API_KEY not found)."
        
        try:
            response = self._tavily_client.search(query=query, search_depth="advanced")
            context = []
            for result in response.get("results", []):
                context.append(f"Source: {result['title']} ({result['url']})\nContent: {result['content']}")
            return "\n\n".join(context)
        except Exception as e:
            return f"Error during web search: {str(e)}"
    
    def _should_continue(self, state: AgenticState) -> str:
        """决定下一步操作"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 检查是否应该结束
        if state["iterations"] >= self.config.max_iterations:
            return "end"
        
        # 分析最后一条消息，决定下一步
        llm = self._get_llm()
        decision_prompt = f"""Based on the conversation history, decide what to do next.

Conversation:
{chr(10).join([str(msg) for msg in messages[-3:]])}

Options:
1. "retrieve" - Need to retrieve more information from local knowledge base
2. "web_search" - Need to search the web for additional information
3. "generate" - Have enough information, can generate final answer
4. "end" - Can answer directly without retrieval

Respond with only one word: retrieve, web_search, generate, or end."""
        
        try:
            response = llm.invoke([HumanMessage(content=decision_prompt)])
            decision = response.content.lower().strip()
            
            if "retrieve" in decision:
                return "retrieve"
            elif "web" in decision or "search" in decision:
                return "web_search"
            elif "generate" in decision or "answer" in decision:
                return "generate"
            else:
                return "end"
        except Exception as e:
            print(f"Decision error: {e}")
            return "generate"
    
    def _agent_node(self, state: AgenticState) -> Dict[str, Any]:
        """智能体节点：决定下一步操作"""
        messages = state["messages"]
        question = state["question"]
        
        llm = self._get_llm()
        
        # 构建系统提示
        system_prompt = """You are an intelligent research assistant. You can:
1. Retrieve information from local knowledge base
2. Search the web for additional information
3. Generate answers based on available context

Analyze the user's question and decide what action to take. If you need more information, indicate which tool to use."""
        
        # 如果还没有开始，先分析问题
        if len(messages) == 0:
            analysis_prompt = f"""User question: {question}

What information do you need to answer this question? Do you need to:
- Retrieve from local knowledge base?
- Search the web?
- Or can you answer directly?

Respond with your decision."""
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ])
            messages.append(response)
        
        return {"messages": messages}
    
    def _retrieve_node(self, state: AgenticState) -> Dict[str, Any]:
        """检索节点"""
        question = state["question"]
        context = self._local_retriever_tool(question)
        
        llm = self._get_llm()
        summary_prompt = f"""Retrieved context:
{context[:2000]}

Summarize the key information relevant to the question: {question}"""
        
        summary = llm.invoke([HumanMessage(content=summary_prompt)])
        
        return {
            "context": context,
            "messages": state["messages"] + [HumanMessage(content=f"Retrieved: {summary.content}")],
            "tools_used": state.get("tools_used", []) + ["local_retrieve"],
            "iterations": state.get("iterations", 0) + 1
        }
    
    def _web_search_node(self, state: AgenticState) -> Dict[str, Any]:
        """网络搜索节点"""
        question = state["question"]
        context = self._web_search_tool(question)
        
        return {
            "context": context,
            "messages": state["messages"] + [HumanMessage(content=f"Web search results: {context[:500]}...")],
            "tools_used": state.get("tools_used", []) + ["web_search"],
            "iterations": state.get("iterations", 0) + 1
        }
    
    def _generate_node(self, state: AgenticState) -> Dict[str, Any]:
        """生成答案节点"""
        question = state["question"]
        context = state.get("context", "")
        messages = state["messages"]
        
        llm = self._get_llm()
        
        prompt = f"""You are an academic research assistant. Use the following context to answer the user's question.

Guidelines:
1. If the context contains specific paper details, you MUST cite them.
2. If the answer is not in the context, say so, do not hallucinate.
3. Keep the answer concise and professional.

Context:
{context}

Question: 
{question}
"""
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {
            "answer": response.content,
            "messages": messages + [AIMessage(content=response.content)]
        }
    
    def _get_graph(self):
        """构建并返回 LangGraph"""
        if self._graph is None:
            workflow = StateGraph(AgenticState)
            
            # 添加节点
            workflow.add_node("agent", self._agent_node)
            workflow.add_node("retrieve", self._retrieve_node)
            workflow.add_node("web_search", self._web_search_node)
            workflow.add_node("generate", self._generate_node)
            
            # 设置入口点
            workflow.set_entry_point("agent")
            
            # 添加条件边
            workflow.add_conditional_edges(
                "agent",
                self._should_continue,
                {
                    "retrieve": "retrieve",
                    "web_search": "web_search",
                    "generate": "generate",
                    "end": "generate"
                }
            )
            
            # 检索后返回智能体
            workflow.add_edge("retrieve", "agent")
            workflow.add_edge("web_search", "agent")
            
            # 生成后结束
            workflow.add_edge("generate", END)
            
            self._graph = workflow.compile()
        
        return self._graph
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 Agentic RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        graph = self._get_graph()
        
        initial_state: AgenticState = {
            "messages": [],
            "question": question,
            "context": "",
            "answer": "",
            "iterations": 0,
            "tools_used": []
        }
        
        result = graph.invoke(initial_state)
        
        return {
            "answer": result.get("answer", ""),
            "source": "local" if "local_retrieve" in result.get("tools_used", []) else "web",
            "context": result.get("context", ""),
            "strategy": "agentic",
            "tools_used": result.get("tools_used", [])
        }
