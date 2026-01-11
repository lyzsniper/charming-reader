"""
2-Step RAG 实现
最简单的 RAG 模式：检索 -> 生成
固定流程，无决策逻辑，低延迟
"""
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from .base import BaseRAGStrategy, RAGStrategyConfig
from ..ingestion import get_vector_store
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank
from llama_index.llms.openai import OpenAI
from core.config import settings


class TwoStepRAGStrategy(BaseRAGStrategy):
    """2-Step RAG 策略：最简单的检索-生成模式"""
    
    def __init__(self, config: RAGStrategyConfig):
        super().__init__(config)
        self._query_engine = None
        self._llm = None
    
    def _get_query_engine(self):
        """获取查询引擎"""
        if self._query_engine is None:
            vector_store = self.config.vector_store or get_vector_store()
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            
            # 配置重排序器（如果启用）
            node_postprocessors = []
            if self.config.enable_rerank:
                rerank_llm = self.config.reranker or OpenAI(
                    model=settings.DEFAULT_LLM_MODEL,
                    api_key=settings.OPENAI_API_KEY or "dummy"
                )
                reranker = LLMRerank(
                    choice_batch_size=5,
                    top_n=self.config.rerank_top_n,
                    llm=rerank_llm
                )
                node_postprocessors.append(reranker)
            
            self._query_engine = index.as_query_engine(
                similarity_top_k=self.config.similarity_top_k,
                node_postprocessors=node_postprocessors if node_postprocessors else None,
                vector_store_query_mode="hybrid",
                alpha=0.5
            )
        return self._query_engine
    
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
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 2-Step RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 的字典
        """
        # 验证问题
        if not self._validate_question(question):
            raise ValueError("Invalid question: question must be a non-empty string between 3 and 1000 characters")
        
        try:
            # Step 1: 检索
            query_engine = self._get_query_engine()
            response = query_engine.query(question)
            context = str(response)
            
            # Step 2: 生成答案
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
            llm_response = llm.invoke([HumanMessage(content=prompt)])
            
            result = {
                "answer": llm_response.content,
                "source": "local",
                "context": context
            }
            
            # 格式化结果
            result = self._format_result(result)
            
            # 记录日志
            self._log_query(question, result)
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error in 2-Step RAG query: {str(e)}", exc_info=True)
            raise
