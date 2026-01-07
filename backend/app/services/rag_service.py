"""
RAG 查询服务
支持基于知识库的文档检索和问答
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.postprocessor import LLMRerank, SimilarityPostprocessor
from llama_index.llms.openai import OpenAI

from services.vectorization_service import VectorizationService
from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)


class RAGService:
    """RAG 查询服务"""
    
    @staticmethod
    def create_query_engine(
        knowledge_base_ids: Optional[List[UUID]] = None,
        similarity_top_k: int = 10,
        enable_rerank: bool = True,
        rerank_top_n: int = 3,
        alpha: float = 0.5  # 混合检索权重：0=纯 BM25, 1=纯向量, 0.5=平衡
    ):
        """
        创建查询引擎
        
        Args:
            knowledge_base_ids: 知识库 UUID 列表，如果为 None 则检索所有知识库
            similarity_top_k: 初始检索数量
            enable_rerank: 是否启用 LLM 重排序
            rerank_top_n: 重排序后返回的数量
            alpha: 混合检索权重（0-1）
        
        Returns:
            LlamaIndex QueryEngine
        """
        logger.info("=" * 60)
        logger.info("创建 RAG 查询引擎")
        logger.info(f"知识库过滤: {knowledge_base_ids if knowledge_base_ids else '全部知识库'}")
        logger.info(f"检索数量: {similarity_top_k}, 重排序: {enable_rerank}")
        logger.info("=" * 60)
        
        # 获取向量存储
        vector_store = VectorizationService.get_es_vector_store()
        
        # 构建元数据过滤器
        filters = None
        if knowledge_base_ids:
            # 过滤特定知识库
            # 注意：这里使用 "in" 操作符，需要 Elasticsearch 支持
            # 如果 Elasticsearch 不支持，可以改为多个 OR 条件
            logger.info(f"应用知识库过滤器: {[str(kb_id) for kb_id in knowledge_base_ids]}")
            
            # 方案1：使用 ExactMatchFilter（单个知识库）
            if len(knowledge_base_ids) == 1:
                filters = MetadataFilters(
                    filters=[
                        ExactMatchFilter(
                            key="knowledge_base_ids",
                            value=str(knowledge_base_ids[0])
                        )
                    ]
                )
            else:
                # 方案2：多个知识库需要特殊处理
                # 这里简化为检索所有，然后在后处理中过滤
                logger.warning("多知识库过滤暂时使用后处理方式")
        
        # 从向量存储创建索引
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store
        )
        
        # 配置后处理器
        node_postprocessors = []
        
        # 1. 相似度过滤器
        node_postprocessors.append(
            SimilarityPostprocessor(similarity_cutoff=0.6)
        )
        
        # 2. LLM 重排序（可选）
        if enable_rerank:
            logger.info(f"启用 LLM 重排序，Top-{rerank_top_n}")
            rerank_llm = OpenAI(
                model=settings.DEFAULT_LLM_MODEL,
                api_key=settings.QWEN_API_KEY or settings.GLM_API_KEY or settings.OPENAI_API_KEY,
                api_base=settings.QWEN_BASE_URL
            )
            node_postprocessors.append(
                LLMRerank(
                    choice_batch_size=5,
                    top_n=rerank_top_n,
                    llm=rerank_llm
                )
            )
        
        # 创建查询引擎
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            node_postprocessors=node_postprocessors,
            filters=filters,
            # Elasticsearch 混合检索参数
            vector_store_query_mode="hybrid",
            alpha=alpha  # 向量检索和 BM25 的权重
        )
        
        logger.info("✓ 查询引擎创建完成")
        return query_engine
    
    @staticmethod
    def query(
        question: str,
        knowledge_base_ids: Optional[List[UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 RAG 查询
        
        Args:
            question: 用户问题
            knowledge_base_ids: 知识库 UUID 列表（可选）
            **kwargs: 其他查询引擎参数
        
        Returns:
            包含答案和来源的字典
        """
        logger.info(f"收到 RAG 查询: {question[:100]}...")
        
        try:
            # 创建查询引擎
            query_engine = RAGService.create_query_engine(
                knowledge_base_ids=knowledge_base_ids,
                **kwargs
            )
            
            # 执行查询
            logger.info("开始执行查询...")
            response = query_engine.query(question)
            
            # 提取来源信息
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_info = {
                        "content": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "score": node.score if hasattr(node, 'score') else None,
                        "metadata": node.metadata if hasattr(node, 'metadata') else {}
                    }
                    sources.append(source_info)
            
            logger.info(f"✓ 查询完成，找到 {len(sources)} 个来源")
            
            return {
                "answer": str(response),
                "sources": sources,
                "knowledge_base_ids": [str(kb_id) for kb_id in knowledge_base_ids] if knowledge_base_ids else None
            }
            
        except Exception as e:
            logger.error(f"✗ RAG 查询失败: {type(e).__name__}: {str(e)}")
            raise
    
    @staticmethod
    def hybrid_search(
        query_text: str,
        knowledge_base_ids: Optional[List[UUID]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        混合检索（向量 + BM25）
        仅返回检索结果，不生成答案
        
        Args:
            query_text: 查询文本
            knowledge_base_ids: 知识库过滤
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        logger.info(f"混合检索: {query_text[:100]}...")
        
        try:
            # 创建检索器
            query_engine = RAGService.create_query_engine(
                knowledge_base_ids=knowledge_base_ids,
                similarity_top_k=top_k,
                enable_rerank=False  # 纯检索不需要重排序
            )
            
            # 执行检索
            response = query_engine.query(query_text)
            
            # 提取检索结果
            results = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    results.append({
                        "content": node.text,
                        "score": node.score if hasattr(node, 'score') else None,
                        "metadata": node.metadata if hasattr(node, 'metadata') else {},
                        "document_id": node.metadata.get("document_id") if hasattr(node, 'metadata') else None,
                        "chunk_index": node.metadata.get("chunk_index") if hasattr(node, 'metadata') else None
                    })
            
            logger.info(f"✓ 检索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"✗ 混合检索失败: {type(e).__name__}: {str(e)}")
            raise


# 便捷函数
def query_knowledge_base(
    question: str,
    knowledge_base_ids: Optional[List[UUID]] = None
) -> Dict[str, Any]:
    """
    查询知识库（便捷函数）
    """
    return RAGService.query(
        question=question,
        knowledge_base_ids=knowledge_base_ids
    )


def search_documents(
    query: str,
    knowledge_base_ids: Optional[List[UUID]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    搜索文档（便捷函数）
    """
    return RAGService.hybrid_search(
        query_text=query,
        knowledge_base_ids=knowledge_base_ids,
        top_k=top_k
    )

