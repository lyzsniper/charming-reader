"""
RAG 策略模块 - 统一的 RAG 处理接口
支持多种 RAG 策略：2-Step、Agentic、Hybrid、Adaptive、Corrective、Self-Reflective
"""
from typing import Dict, Any, Union, Optional
from .base import RAGStrategyFactory, RAGStrategyType, RAGStrategyConfig
from .utils import (
    get_cache_key,
    get_cached_result,
    set_cached_result,
    clear_cache,
    with_cache,
    with_logging,
    with_monitoring,
    format_context,
    validate_question,
    sanitize_result,
    estimate_tokens,
    check_context_quality
)

__all__ = [
    "RAGStrategyFactory",
    "RAGStrategyType",
    "RAGStrategyConfig",
    "query_rag",
    # 工具函数
    "get_cache_key",
    "get_cached_result",
    "set_cached_result",
    "clear_cache",
    "with_cache",
    "with_logging",
    "with_monitoring",
    "format_context",
    "validate_question",
    "sanitize_result",
    "estimate_tokens",
    "check_context_quality"
]


def query_rag(
    question: str,
    strategy_type: Union[RAGStrategyType, str] = RAGStrategyType.ADAPTIVE,
    llm: Optional[Any] = None,
    vector_store: Optional[Any] = None,
    query_engine: Optional[Any] = None,
    reranker: Optional[Any] = None,
    web_search_client: Optional[Any] = None,
    max_iterations: int = 3,
    relevance_threshold: float = 0.7,
    similarity_top_k: int = 10,
    rerank_top_n: int = 3,
    enable_rerank: bool = True,
    enable_web_search: bool = True,
    enable_cache: bool = True,
    cache_ttl: int = 3600,
    enable_logging: bool = True,
    enable_monitoring: bool = True,
    **extra_params
) -> Dict[str, Any]:
    """
    统一的 RAG 查询入口函数
    
    Args:
        question: 用户问题
        strategy_type: RAG 策略类型，可选值：
            - "two_step": 2-Step RAG（简单检索-生成）
            - "agentic": Agentic RAG（智能体驱动）
            - "hybrid": Hybrid RAG（包含质量验证）
            - "adaptive": Adaptive RAG（自适应路由，默认）
            - "corrective": Corrective RAG（自我纠错）
            - "self_reflective": Self-Reflective RAG（自反思）
        llm: LLM 实例（可选，默认使用全局配置）
        vector_store: 向量存储实例（可选，默认使用全局配置）
        query_engine: 查询引擎实例（可选）
        reranker: 重排序器实例（可选）
        web_search_client: 网络搜索客户端（可选）
        max_iterations: 最大迭代次数（用于循环策略）
        relevance_threshold: 相关性阈值
        similarity_top_k: 检索 top-k
        rerank_top_n: 重排序 top-n
        enable_rerank: 是否启用重排序
        enable_web_search: 是否启用网络搜索
        **extra_params: 其他策略特定参数
        
    Returns:
        dict: 包含以下字段的字典：
            - answer: 生成的答案
            - source: 数据来源（"local" 或 "web"）
            - context: 检索到的上下文
            - strategy: 使用的策略名称
            - 其他策略特定的字段
        
    Examples:
        >>> # 使用默认 Adaptive RAG
        >>> result = query_rag("What is machine learning?")
        
        >>> # 使用 2-Step RAG
        >>> result = query_rag(
        ...     "What is machine learning?",
        ...     strategy_type="two_step"
        ... )
        
        >>> # 使用 Agentic RAG 并自定义参数
        >>> result = query_rag(
        ...     "What is machine learning?",
        ...     strategy_type="agentic",
        ...     max_iterations=5
        ... )
        
        >>> # 使用 Self-Reflective RAG
        >>> result = query_rag(
        ...     "Explain quantum computing",
        ...     strategy_type="self_reflective",
        ...     max_iterations=2
        ... )
    """
    # 验证问题
    if not validate_question(question):
        raise ValueError(f"Invalid question: question must be a non-empty string between 3 and 1000 characters")
    
    # 检查缓存
    if enable_cache:
        cache_key = get_cache_key(question, str(strategy_type), **{
            'max_iterations': max_iterations,
            'similarity_top_k': similarity_top_k,
            'enable_rerank': enable_rerank,
            'enable_web_search': enable_web_search
        })
        cached_result = get_cached_result(cache_key, cache_ttl)
        if cached_result is not None:
            return cached_result
    
    # 创建配置
    config = RAGStrategyConfig(
        strategy_type=strategy_type,
        llm=llm,
        vector_store=vector_store,
        query_engine=query_engine,
        reranker=reranker,
        web_search_client=web_search_client,
        max_iterations=max_iterations,
        relevance_threshold=relevance_threshold,
        similarity_top_k=similarity_top_k,
        rerank_top_n=rerank_top_n,
        enable_rerank=enable_rerank,
        enable_web_search=enable_web_search,
        enable_cache=enable_cache,
        cache_ttl=cache_ttl,
        enable_logging=enable_logging,
        enable_monitoring=enable_monitoring,
        extra_params=extra_params
    )
    
    # 创建策略并执行查询
    strategy = RAGStrategyFactory.create_strategy(config)
    result = strategy.query(question)
    
    # 格式化结果
    result = strategy._format_result(result)
    
    # 存入缓存
    if enable_cache:
        set_cached_result(cache_key, result, cache_ttl)
    
    return result
