"""
Adaptive RAG 实现
根据问题复杂度动态路由
简单问题可能跳过检索，复杂问题触发向量搜索或网络搜索
这是当前 engine.py 中实现的迁移版本
"""
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .base import BaseRAGStrategy, RAGStrategyConfig
from ..ingestion import get_vector_store
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI
from core.config import settings
from tavily import TavilyClient
import os


class AdaptiveState(TypedDict):
    """自适应 RAG 状态"""
    question: str  # 用户问题
    context: str  # 检索到的上下文
    answer: str  # 最终答案
    source: str  # 来源：'local' 或 'web'


class AdaptiveRAGStrategy(BaseRAGStrategy):
    """Adaptive RAG 策略：根据问题复杂度动态路由"""
    
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
    
    def _retrieve_local_node(self, state: AdaptiveState) -> Dict[str, Any]:
        """节点：从本地索引检索"""
        question = state["question"]
        context = self._local_retriever_tool(question)
        return {"context": context, "source": "local"}
    
    def _web_search_node(self, state: AdaptiveState) -> Dict[str, Any]:
        """节点：网络搜索"""
        question = state["question"]
        context = self._web_search_tool(question)
        return {"context": context, "source": "web"}
    
    def _generate_node(self, state: AdaptiveState) -> Dict[str, Any]:
        """节点：生成答案"""
        question = state["question"]
        context = state["context"]
        llm = self._get_llm()
        
        prompt = f"""You are an academic research assistant. Use the following context to answer the user's question.

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
    
    def _relevance_checker(self, state: AdaptiveState) -> str:
        """
        条件边逻辑：检查检索到的上下文是否相关
        如果本地上下文为空或不相关，切换到网络搜索
        """
        context = state["context"]
        question = state["question"]
        
        # 1. 快速检查：上下文是否为空
        if not context or "Empty Response" in context or len(context.strip()) < 10:
            return "web_search"
        
        # 2. LLM 评分
        llm = self._get_llm()
        grader_prompt = f"""You are a grader assessing relevance of a retrieved document to a user question.

Retrieved document:
{context[:2000]}... (truncated if too long)

User question: 
{question}

Does the document contain keyword(s) or semantic meaning that aligns with the question?
Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
Only answer 'yes' or 'no'."""
        
        try:
            score = llm.invoke([HumanMessage(content=grader_prompt)]).content.lower().strip()
            
            if "yes" in score:
                return "generate"
            else:
                return "web_search"
        except Exception as e:
            print(f"Grader error: {e} -> Fallback to generate")
            return "generate"
    
    def _get_graph(self):
        """构建并返回 LangGraph"""
        if self._graph is None:
            workflow = StateGraph(AdaptiveState)
            
            # 添加节点
            workflow.add_node("retrieve_local", self._retrieve_local_node)
            workflow.add_node("web_search", self._web_search_node)
            workflow.add_node("generate", self._generate_node)
            
            # 设置入口点
            workflow.set_entry_point("retrieve_local")
            
            # 添加条件边
            # retrieve_local -> relevance_checker -> (generate OR web_search)
            workflow.add_conditional_edges(
                "retrieve_local",
                self._relevance_checker,
                {
                    "generate": "generate",
                    "web_search": "web_search"
                }
            )
            
            # web_search -> generate
            workflow.add_edge("web_search", "generate")
            
            # generate -> END
            workflow.add_edge("generate", END)
            
            self._graph = workflow.compile()
        
        return self._graph
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 Adaptive RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        graph = self._get_graph()
        
        initial_state: AdaptiveState = {
            "question": question,
            "context": "",
            "answer": "",
            "source": "local"
        }
        
        result = graph.invoke(initial_state)
        
        return {
            "answer": result.get("answer", ""),
            "source": result.get("source", "local"),
            "context": result.get("context", ""),
            "strategy": "adaptive"
        }
