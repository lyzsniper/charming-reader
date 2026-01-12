"""
Corrective RAG 实现
评估检索文档的质量
如果检索不足，可以：优化查询、额外搜索、网络检索
自我纠错机制
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


class CorrectiveState(TypedDict):
    """纠正式 RAG 状态"""
    question: str  # 原始问题
    optimized_question: str  # 优化后的问题
    context: str  # 检索到的上下文
    answer: str  # 生成的答案
    retrieval_quality: str  # 检索质量：'good', 'poor', 'insufficient'
    correction_needed: bool  # 是否需要纠正
    iterations: int  # 迭代次数


class CorrectiveRAGStrategy(BaseRAGStrategy):
    """Corrective RAG 策略：带自我纠错机制的 RAG"""
    
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
    
    def _retrieve_node(self, state: CorrectiveState) -> Dict[str, Any]:
        """检索节点"""
        question = state.get("optimized_question") or state["question"]
        context = self._local_retriever_tool(question)
        return {
            "context": context,
            "iterations": state.get("iterations", 0) + 1
        }
    
    def _assess_retrieval_node(self, state: CorrectiveState) -> Dict[str, Any]:
        """评估检索质量"""
        context = state["context"]
        question = state["question"]
        llm = self._get_llm()
        
        # 快速检查：上下文是否为空
        if not context or len(context.strip()) < 50:
            return {
                "retrieval_quality": "insufficient",
                "correction_needed": True
            }
        
        # LLM 评估检索质量
        assessment_prompt = f"""Assess the quality of the retrieved context for answering the question.

Question: {question}

Retrieved context (first 1500 chars):
{context[:1500]}

Evaluate the retrieval quality:
1. "good" - The context is highly relevant and sufficient to answer the question
2. "poor" - The context is somewhat relevant but may be incomplete or not directly addressing the question
3. "insufficient" - The context is not relevant or too sparse to answer the question

Respond with only one word: good, poor, or insufficient."""
        
        try:
            response = llm.invoke([HumanMessage(content=assessment_prompt)])
            quality = response.content.lower().strip()
            
            if "good" in quality:
                return {
                    "retrieval_quality": "good",
                    "correction_needed": False
                }
            elif "poor" in quality:
                return {
                    "retrieval_quality": "poor",
                    "correction_needed": True
                }
            else:
                return {
                    "retrieval_quality": "insufficient",
                    "correction_needed": True
                }
        except Exception as e:
            print(f"Assessment error: {e}")
            return {
                "retrieval_quality": "poor",
                "correction_needed": True
            }
    
    def _correct_retrieval_node(self, state: CorrectiveState) -> Dict[str, Any]:
        """纠正检索：优化查询或使用网络搜索"""
        question = state["question"]
        quality = state.get("retrieval_quality", "insufficient")
        llm = self._get_llm()
        
        # 如果质量是 insufficient，尝试网络搜索
        if quality == "insufficient" and self.config.enable_web_search:
            web_context = self._web_search_tool(question)
            if web_context and "disabled" not in web_context.lower():
                return {"context": web_context}
        
        # 否则，优化查询
        optimize_prompt = f"""The initial retrieval was not sufficient. Optimize the query to improve retrieval.

Original question: {question}
Retrieval quality: {quality}

Generate an improved, more specific query that might yield better results. Focus on:
1. Adding relevant keywords
2. Making the query more specific
3. Breaking down complex questions into simpler components

Optimized query:"""
        
        try:
            response = llm.invoke([HumanMessage(content=optimize_prompt)])
            optimized_question = response.content.strip()
            return {"optimized_question": optimized_question}
        except Exception as e:
            print(f"Query optimization error: {e}")
            return {"optimized_question": question}
    
    def _generate_node(self, state: CorrectiveState) -> Dict[str, Any]:
        """生成答案节点"""
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
    
    def _should_correct(self, state: CorrectiveState) -> str:
        """决定是否需要纠正"""
        if state.get("correction_needed", False):
            if state.get("iterations", 0) < self.config.max_iterations:
                return "correct"
            else:
                return "generate"  # 达到最大迭代次数，直接生成
        return "generate"
    
    def _get_graph(self):
        """构建并返回 LangGraph"""
        if self._graph is None:
            workflow = StateGraph(CorrectiveState)
            
            # 添加节点
            workflow.add_node("retrieve", self._retrieve_node)
            workflow.add_node("assess_retrieval", self._assess_retrieval_node)
            workflow.add_node("correct_retrieval", self._correct_retrieval_node)
            workflow.add_node("generate", self._generate_node)
            
            # 设置入口点
            workflow.set_entry_point("retrieve")
            
            # 添加边
            workflow.add_edge("retrieve", "assess_retrieval")
            
            # 条件边：评估检索质量
            workflow.add_conditional_edges(
                "assess_retrieval",
                self._should_correct,
                {
                    "correct": "correct_retrieval",
                    "generate": "generate"
                }
            )
            
            # 纠正后重新检索
            workflow.add_edge("correct_retrieval", "retrieve")
            
            # 生成后结束
            workflow.add_edge("generate", END)
            
            self._graph = workflow.compile()
        
        return self._graph
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 Corrective RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        graph = self._get_graph()
        
        initial_state: CorrectiveState = {
            "question": question,
            "optimized_question": question,
            "context": "",
            "answer": "",
            "retrieval_quality": "unknown",
            "correction_needed": False,
            "iterations": 0
        }
        
        result = graph.invoke(initial_state)
        
        return {
            "answer": result.get("answer", ""),
            "source": "local" if "web" not in result.get("context", "").lower() else "web",
            "context": result.get("context", ""),
            "strategy": "corrective",
            "retrieval_quality": result.get("retrieval_quality", "unknown")
        }
