"""
Self-Reflective RAG 实现
生成初始答案后自我评估
如果答案不足，可以重新生成或添加约束
迭代改进机制
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


class ReflectiveState(TypedDict):
    """自反思 RAG 状态"""
    question: str  # 用户问题
    context: str  # 检索到的上下文
    answer: str  # 生成的答案
    reflection: str  # 自我反思结果
    answer_quality: str  # 答案质量：'good', 'needs_improvement', 'poor'
    improvement_needed: bool  # 是否需要改进
    iterations: int  # 迭代次数
    constraints: str  # 改进约束


class SelfReflectiveRAGStrategy(BaseRAGStrategy):
    """Self-Reflective RAG 策略：自反思 RAG"""
    
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
    
    def _retrieve_node(self, state: ReflectiveState) -> Dict[str, Any]:
        """检索节点"""
        question = state["question"]
        query_engine = self._get_query_engine()
        response = query_engine.query(question)
        context = str(response)
        return {"context": context}
    
    def _generate_node(self, state: ReflectiveState) -> Dict[str, Any]:
        """生成答案节点"""
        question = state["question"]
        context = state["context"]
        constraints = state.get("constraints", "")
        llm = self._get_llm()
        
        prompt = f"""You are an academic research assistant. Use the following context to answer the user's question.

Guidelines:
1. If the context contains specific paper details, you MUST cite them using the format [Source: Document Name/URL, Page X].
2. If the answer is not in the context, say so, do not hallucinate.
3. Keep the answer concise and professional.
{chr(10) + constraints if constraints else ""}

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
    
    def _reflect_node(self, state: ReflectiveState) -> Dict[str, Any]:
        """自我反思节点"""
        question = state["question"]
        answer = state["answer"]
        context = state["context"]
        llm = self._get_llm()
        
        reflection_prompt = f"""You are evaluating the quality of an answer you just generated.

Question: {question}

Generated Answer:
{answer}

Context Used:
{context[:1000]}

Evaluate the answer on the following criteria:
1. **Accuracy**: Is the answer factually correct based on the context?
2. **Completeness**: Does the answer fully address all aspects of the question?
3. **Relevance**: Is the answer directly relevant to the question?
4. **Clarity**: Is the answer clear and well-structured?

Provide:
1. A quality assessment: "good", "needs_improvement", or "poor"
2. Specific feedback on what could be improved (if any)
3. Suggestions for improvement (if needed)

Format your response as:
Quality: [good/needs_improvement/poor]
Feedback: [your feedback]
Suggestions: [your suggestions]"""
        
        try:
            response = llm.invoke([HumanMessage(content=reflection_prompt)])
            reflection_text = response.content
            
            # 解析质量评估
            quality = "good"
            if "needs_improvement" in reflection_text.lower():
                quality = "needs_improvement"
            elif "poor" in reflection_text.lower():
                quality = "poor"
            
            return {
                "reflection": reflection_text,
                "answer_quality": quality,
                "improvement_needed": quality != "good"
            }
        except Exception as e:
            print(f"Reflection error: {e}")
            return {
                "reflection": "Reflection failed",
                "answer_quality": "good",
                "improvement_needed": False
            }
    
    def _improve_node(self, state: ReflectiveState) -> Dict[str, Any]:
        """改进节点：生成改进约束"""
        reflection = state.get("reflection", "")
        llm = self._get_llm()
        
        improve_prompt = f"""Based on the self-reflection, generate specific constraints and guidelines for improving the answer.

Reflection:
{reflection}

Generate improvement constraints that should be applied when regenerating the answer. These should be specific, actionable guidelines."""
        
        try:
            response = llm.invoke([HumanMessage(content=improve_prompt)])
            constraints = response.content.strip()
            return {"constraints": constraints}
        except Exception as e:
            print(f"Improvement generation error: {e}")
            return {"constraints": "Focus on accuracy and completeness."}
    
    def _should_improve(self, state: ReflectiveState) -> str:
        """决定是否需要改进"""
        if state.get("improvement_needed", False):
            if state.get("iterations", 0) < self.config.max_iterations:
                return "improve"
            else:
                return "end"  # 达到最大迭代次数，结束
        return "end"
    
    def _get_graph(self):
        """构建并返回 LangGraph"""
        if self._graph is None:
            workflow = StateGraph(ReflectiveState)
            
            # 添加节点
            workflow.add_node("retrieve", self._retrieve_node)
            workflow.add_node("generate", self._generate_node)
            workflow.add_node("reflect", self._reflect_node)
            workflow.add_node("improve", self._improve_node)
            
            # 设置入口点
            workflow.set_entry_point("retrieve")
            
            # 添加边
            workflow.add_edge("retrieve", "generate")
            workflow.add_edge("generate", "reflect")
            
            # 条件边：反思后决定是否改进
            workflow.add_conditional_edges(
                "reflect",
                self._should_improve,
                {
                    "improve": "improve",
                    "end": END
                }
            )
            
            # 改进后重新生成
            workflow.add_edge("improve", "generate")
            
            self._graph = workflow.compile()
        
        return self._graph
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 Self-Reflective RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        graph = self._get_graph()
        
        initial_state: ReflectiveState = {
            "question": question,
            "context": "",
            "answer": "",
            "reflection": "",
            "answer_quality": "unknown",
            "improvement_needed": False,
            "iterations": 0,
            "constraints": ""
        }
        
        result = graph.invoke(initial_state)
        
        return {
            "answer": result.get("answer", ""),
            "source": "local",
            "context": result.get("context", ""),
            "strategy": "self_reflective",
            "reflection": result.get("reflection", ""),
            "answer_quality": result.get("answer_quality", "unknown")
        }
