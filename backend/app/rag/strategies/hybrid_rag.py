"""
Hybrid RAG 实现
包含中间步骤：查询增强、检索验证、答案验证
平衡控制性和灵活性，质量验证机制
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


class HybridState(TypedDict):
    """混合 RAG 状态"""
    question: str  # 原始问题
    enhanced_question: str  # 增强后的问题
    context: str  # 检索到的上下文
    answer: str  # 生成的答案
    retrieval_valid: bool  # 检索是否有效
    answer_valid: bool  # 答案是否有效
    iterations: int  # 迭代次数


class HybridRAGStrategy(BaseRAGStrategy):
    """Hybrid RAG 策略：包含质量验证的混合 RAG"""
    
    def __init__(self, config: RAGStrategyConfig):
        super().__init__(config)
        self._graph = None
        self._llm = None
        self._query_engine = None
    
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
    
    def _enhance_query_node(self, state: HybridState) -> Dict[str, Any]:
        """查询增强节点"""
        question = state["question"]
        llm = self._get_llm()
        
        enhance_prompt = f"""Enhance the following question to improve retrieval quality. 
Generate a more specific and detailed version that captures the user's intent.

Original question: {question}

Enhanced question:"""
        
        response = llm.invoke([HumanMessage(content=enhance_prompt)])
        enhanced_question = response.content.strip()
        
        return {
            "enhanced_question": enhanced_question,
            "iterations": state.get("iterations", 0) + 1
        }
    
    def _retrieve_node(self, state: HybridState) -> Dict[str, Any]:
        """检索节点"""
        question = state.get("enhanced_question") or state["question"]
        query_engine = self._get_query_engine()
        response = query_engine.query(question)
        context = str(response)
        
        return {"context": context}
    
    def _validate_retrieval_node(self, state: HybridState) -> Dict[str, Any]:
        """验证检索结果"""
        context = state["context"]
        question = state["question"]
        llm = self._get_llm()
        
        # 快速检查：上下文是否为空
        if not context or len(context.strip()) < 50:
            return {"retrieval_valid": False}
        
        # LLM 验证
        validation_prompt = f"""Assess whether the retrieved context is relevant and sufficient to answer the question.

Question: {question}

Retrieved context (first 1000 chars):
{context[:1000]}

Is the context relevant and sufficient? Answer 'yes' or 'no'."""
        
        try:
            response = llm.invoke([HumanMessage(content=validation_prompt)])
            is_valid = "yes" in response.content.lower()
            return {"retrieval_valid": is_valid}
        except Exception as e:
            print(f"Validation error: {e}")
            return {"retrieval_valid": True}  # 默认通过
    
    def _generate_node(self, state: HybridState) -> Dict[str, Any]:
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
        
        return {
            "answer": response.content,
            "iterations": state.get("iterations", 0) + 1
        }
    
    def _validate_answer_node(self, state: HybridState) -> Dict[str, Any]:
        """验证答案质量"""
        answer = state["answer"]
        question = state["question"]
        context = state["context"]
        llm = self._get_llm()
        
        validation_prompt = f"""Evaluate the quality of the generated answer.

Question: {question}

Answer:
{answer}

Context used:
{context[:500]}

Evaluate:
1. Is the answer accurate based on the context? (yes/no)
2. Is the answer complete? (yes/no)
3. Does the answer address the question? (yes/no)

Respond with 'valid' if all three are yes, otherwise 'invalid'."""
        
        try:
            response = llm.invoke([HumanMessage(content=validation_prompt)])
            is_valid = "valid" in response.content.lower()
            return {"answer_valid": is_valid}
        except Exception as e:
            print(f"Answer validation error: {e}")
            return {"answer_valid": True}  # 默认通过
    
    def _should_regenerate(self, state: HybridState) -> str:
        """决定是否需要重新生成"""
        current_iterations = state.get("iterations", 0)
        
        if not state.get("retrieval_valid", False):
            if current_iterations < self.config.max_iterations:
                return "enhance_query"  # 重新增强查询并检索
            else:
                return "end"  # 达到最大迭代次数，结束
        
        if not state.get("answer_valid", True):
            if current_iterations < self.config.max_iterations:
                return "regenerate"  # 重新生成答案
            else:
                return "end"  # 达到最大迭代次数，结束
        
        return "end"
    
    def _get_graph(self):
        """构建并返回 LangGraph"""
        if self._graph is None:
            workflow = StateGraph(HybridState)
            
            # 添加节点
            workflow.add_node("enhance_query", self._enhance_query_node)
            workflow.add_node("retrieve", self._retrieve_node)
            workflow.add_node("validate_retrieval", self._validate_retrieval_node)
            workflow.add_node("generate", self._generate_node)
            workflow.add_node("validate_answer", self._validate_answer_node)
            
            # 设置入口点
            workflow.set_entry_point("enhance_query")
            
            # 添加边
            workflow.add_edge("enhance_query", "retrieve")
            workflow.add_edge("retrieve", "validate_retrieval")
            
            # 条件边：验证检索结果
            workflow.add_conditional_edges(
                "validate_retrieval",
                lambda state: "generate" if state.get("retrieval_valid", False) else "enhance_query",
                {
                    "generate": "generate",
                    "enhance_query": "enhance_query"
                }
            )
            
            workflow.add_edge("generate", "validate_answer")
            
            # 条件边：验证答案
            workflow.add_conditional_edges(
                "validate_answer",
                self._should_regenerate,
                {
                    "end": END,
                    "enhance_query": "enhance_query",
                    "regenerate": "generate"
                }
            )
            
            self._graph = workflow.compile()
        
        return self._graph
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 Hybrid RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        graph = self._get_graph()
        
        initial_state: HybridState = {
            "question": question,
            "enhanced_question": "",
            "context": "",
            "answer": "",
            "retrieval_valid": False,
            "answer_valid": False,
            "iterations": 0
        }
        
        result = graph.invoke(initial_state)
        
        return {
            "answer": result.get("answer", ""),
            "source": "local",
            "context": result.get("context", ""),
            "strategy": "hybrid",
            "enhanced_question": result.get("enhanced_question", "")
        }
