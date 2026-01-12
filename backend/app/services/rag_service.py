"""
RAG 查询服务
支持基于知识库的文档检索和问答
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.postprocessor import LLMRerank, SimilarityPostprocessor
from llama_index.llms.litellm import LiteLLM

from services.vectorization_service import VectorizationService
from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)


class RAGService:
    """RAG 查询服务"""
    
    @staticmethod
    def create_query_engine(
        knowledge_base_ids: Optional[List[UUID]] = None,
        session_id: Optional[str] = None,
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
        logger.info(f"会话过滤: {session_id if session_id else '无'}")
        logger.info(f"检索数量: {similarity_top_k}, 重排序: {enable_rerank}")
        logger.info("=" * 60)
        
        # 获取向量存储
        vector_store = VectorizationService.get_es_vector_store()
        
        # 构建元数据过滤器
        filters = None
        filter_list = []
        
        # 优先使用session_id过滤（临时文件）
        if session_id:
            logger.info(f"应用会话过滤器: session_id={session_id}")
            logger.info(f"  过滤器类型: ExactMatchFilter, key=session_id, value={session_id}")
            
            # 验证 Elasticsearch 中是否有该 session_id 的数据（调试用）
            try:
                vector_store = VectorizationService.get_es_vector_store()
                if hasattr(vector_store, '_client') or hasattr(vector_store, 'client'):
                    es_client = getattr(vector_store, '_client', None) or getattr(vector_store, 'client', None)
                    if es_client and hasattr(es_client, 'search'):
                        index_name = getattr(vector_store, 'index_name', 'paper_index')
                        # 执行一个简单的查询来验证数据
                        verify_query = {
                            "query": {
                                "term": {
                                    "metadata.session_id": session_id
                                }
                            },
                            "size": 0  # 只获取数量，不获取内容
                        }
                        try:
                            verify_result = es_client.search(index=index_name, body=verify_query)
                            total_hits = verify_result.get('hits', {}).get('total', {})
                            if isinstance(total_hits, dict):
                                total_hits = total_hits.get('value', 0)
                            logger.info(f"  ✓ 验证: Elasticsearch 中找到 {total_hits} 个匹配 session_id={session_id} 的文档")
                            if total_hits == 0:
                                logger.warning(f"  ⚠️ 警告: Elasticsearch 中未找到匹配 session_id={session_id} 的文档！")
                        except Exception as verify_e:
                            logger.warning(f"  ⚠️ 验证查询失败: {verify_e}")
            except Exception as e:
                logger.debug(f"  验证查询跳过: {e}")
            
            filter_list.append(
                ExactMatchFilter(
                    key="session_id",
                    value=session_id
                )
            )
        elif knowledge_base_ids:
            # 过滤特定知识库
            logger.info(f"应用知识库过滤器: {[str(kb_id) for kb_id in knowledge_base_ids]}")
            
            # 方案1：使用 ExactMatchFilter（单个知识库）
            if len(knowledge_base_ids) == 1:
                filter_list.append(
                    ExactMatchFilter(
                        key="knowledge_base_ids",
                        value=str(knowledge_base_ids[0])
                    )
                )
            else:
                # 方案2：多个知识库需要特殊处理
                # 这里简化为检索所有，然后在后处理中过滤
                logger.warning("多知识库过滤暂时使用后处理方式")
        
        if filter_list:
            filters = MetadataFilters(filters=filter_list)
        
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
            # 使用 LiteLLM 支持非 OpenAI 模型（如 Qwen）
            rerank_llm = LiteLLM(
                model="openai/" + settings.DEFAULT_LLM_MODEL,
                api_key=settings.QWEN_API_KEY,
                api_base=settings.QWEN_BASE_URL,
                custom_llm_provider="openai"
            )

            node_postprocessors.append(
                LLMRerank(
                    choice_batch_size=5,
                    top_n=rerank_top_n,
                    llm=rerank_llm
                )
            )
        
        # 创建查询引擎
        # 注意：Elasticsearch 的混合检索在 vector store 层面已配置，无需在这里设置
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            node_postprocessors=node_postprocessors,
            filters=filters
        )
        
        logger.info("✓ 查询引擎创建完成")
        return query_engine
    
    @staticmethod
    def query(
        question: str,
        knowledge_base_ids: Optional[List[UUID]] = None,
        session_id: Optional[str] = None,
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
                session_id=session_id,
                **kwargs
            )
            
            # 执行查询
            logger.info("开始执行查询...")
            logger.info(f"  查询问题: {question[:100]}...")
            logger.info(f"  查询参数: session_id={session_id}, knowledge_base_ids={knowledge_base_ids}")
            response = query_engine.query(question)
            
            # 提取来源信息
            sources = []
            if hasattr(response, 'source_nodes'):
                logger.info(f"  查询返回 {len(response.source_nodes)} 个节点")
                if len(response.source_nodes) == 0:
                    logger.warning(f"  ⚠️ 未找到任何节点！可能的原因：")
                    logger.warning(f"    1. session_id={session_id} 不匹配")
                    logger.warning(f"    2. 数据尚未完全索引到 Elasticsearch")
                    logger.warning(f"    3. 查询文本与文档内容不匹配")
                for idx, node in enumerate(response.source_nodes):
                    node_metadata = node.metadata if hasattr(node, 'metadata') else {}
                    logger.info(f"  节点 {idx+1}: session_id={node_metadata.get('session_id')}, document_id={node_metadata.get('document_id')}, score={node.score if hasattr(node, 'score') else 'N/A'}")
                    source_info = {
                        "content": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "score": node.score if hasattr(node, 'score') else None,
                        "metadata": node_metadata
                    }
                    sources.append(source_info)
            else:
                logger.warning("  查询响应没有 source_nodes 属性")
            
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
        session_id: Optional[str] = None,
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
                session_id=session_id,
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
    knowledge_base_ids: Optional[List[UUID]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询知识库（便捷函数）
    """
    return RAGService.query(
        question=question,
        knowledge_base_ids=knowledge_base_ids,
        session_id=session_id
    )


def search_documents(
    query: str,
    knowledge_base_ids: Optional[List[UUID]] = None,
    session_id: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    搜索文档（便捷函数）
    """
    return RAGService.hybrid_search(
        query_text=query,
        knowledge_base_ids=knowledge_base_ids,
        session_id=session_id,
        top_k=top_k
    )

