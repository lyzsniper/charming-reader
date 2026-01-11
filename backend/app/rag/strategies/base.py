"""
RAG 策略基础接口和工厂类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class RAGStrategyType(str, Enum):
    """RAG 策略类型枚举"""
    TWO_STEP = "two_step"  # 2-Step RAG
    AGENTIC = "agentic"  # Agentic RAG
    HYBRID = "hybrid"  # Hybrid RAG
    ADAPTIVE = "adaptive"  # Adaptive RAG
    CORRECTIVE = "corrective"  # Corrective RAG
    SELF_REFLECTIVE = "self_reflective"  # Self-Reflective RAG


@dataclass
class RAGStrategyConfig:
    """RAG 策略配置"""
    strategy_type: Union[RAGStrategyType, str] = RAGStrategyType.ADAPTIVE
    llm: Optional[Any] = None  # LLM 实例
    vector_store: Optional[Any] = None  # 向量存储
    query_engine: Optional[Any] = None  # 查询引擎（可选）
    reranker: Optional[Any] = None  # 重排序器（可选）
    web_search_client: Optional[Any] = None  # 网络搜索客户端（可选）
    max_iterations: int = 3  # 最大迭代次数（用于循环策略）
    relevance_threshold: float = 0.7  # 相关性阈值
    similarity_top_k: int = 10  # 检索 top-k
    rerank_top_n: int = 3  # 重排序 top-n
    enable_rerank: bool = True  # 是否启用重排序
    enable_web_search: bool = True  # 是否启用网络搜索
    
    # 缓存配置
    enable_cache: bool = True  # 是否启用缓存
    cache_ttl: int = 3600  # 缓存有效期（秒）
    
    # 日志和监控
    enable_logging: bool = True  # 是否启用日志
    enable_monitoring: bool = True  # 是否启用监控
    log_level: int = logging.INFO  # 日志级别
    
    # 其他自定义参数
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """配置验证"""
        if self.max_iterations < 1:
            logger.warning(f"max_iterations should be >= 1, got {self.max_iterations}, setting to 1")
            self.max_iterations = 1
        
        if self.max_iterations > 10:
            logger.warning(f"max_iterations is very high ({self.max_iterations}), this may cause high latency")
        
        if not 0 <= self.relevance_threshold <= 1:
            logger.warning(f"relevance_threshold should be between 0 and 1, got {self.relevance_threshold}")
            self.relevance_threshold = max(0, min(1, self.relevance_threshold))


class BaseRAGStrategy(ABC):
    """RAG 策略基类"""
    
    def __init__(self, config: RAGStrategyConfig):
        self.config = config
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def query(self, question: str) -> dict:
        """
        执行 RAG 查询
        
        Args:
            question: 用户问题
            
        Returns:
            dict: 包含 answer, source, context 等字段的字典
        """
        pass
    
    def get_graph(self):
        """
        获取 LangGraph 实例（如果适用）
        
        Returns:
            Graph 实例或 None
        """
        return None
    
    def _validate_question(self, question: str) -> bool:
        """
        验证问题是否有效
        
        Args:
            question: 用户问题
            
        Returns:
            bool: 是否有效
        """
        from .utils import validate_question
        return validate_question(question)
    
    def _format_result(self, result: dict) -> dict:
        """
        格式化结果，添加元数据
        
        Args:
            result: 原始结果
            
        Returns:
            dict: 格式化后的结果
        """
        from .utils import sanitize_result
        formatted = sanitize_result(result)
        
        # 添加策略元数据
        formatted['strategy'] = self.config.strategy_type.value if isinstance(self.config.strategy_type, RAGStrategyType) else str(self.config.strategy_type)
        formatted['config'] = {
            'max_iterations': self.config.max_iterations,
            'similarity_top_k': self.config.similarity_top_k,
            'enable_rerank': self.config.enable_rerank,
            'enable_web_search': self.config.enable_web_search
        }
        
        return formatted
    
    def _log_query(self, question: str, result: dict):
        """
        记录查询日志
        
        Args:
            question: 用户问题
            result: 查询结果
        """
        if self.config.enable_logging:
            self._logger.info(
                f"Query: {question[:50]}... | "
                f"Strategy: {self.config.strategy_type} | "
                f"Source: {result.get('source', 'unknown')} | "
                f"Answer length: {len(result.get('answer', ''))}"
            )


class RAGStrategyFactory:
    """RAG 策略工厂类"""
    
    @staticmethod
    def create_strategy(config: RAGStrategyConfig) -> BaseRAGStrategy:
        """
        创建 RAG 策略实例
        
        Args:
            config: RAG 策略配置
            
        Returns:
            BaseRAGStrategy: RAG 策略实例
        """
        strategy_type = config.strategy_type
        if isinstance(strategy_type, str):
            strategy_type = RAGStrategyType(strategy_type.lower())
        
        if strategy_type == RAGStrategyType.TWO_STEP:
            from .two_step_rag import TwoStepRAGStrategy
            return TwoStepRAGStrategy(config)
        
        elif strategy_type == RAGStrategyType.AGENTIC:
            from .agentic_rag import AgenticRAGStrategy
            return AgenticRAGStrategy(config)
        
        elif strategy_type == RAGStrategyType.HYBRID:
            from .hybrid_rag import HybridRAGStrategy
            return HybridRAGStrategy(config)
        
        elif strategy_type == RAGStrategyType.ADAPTIVE:
            from .adaptive_rag import AdaptiveRAGStrategy
            return AdaptiveRAGStrategy(config)
        
        elif strategy_type == RAGStrategyType.CORRECTIVE:
            from .corrective_rag import CorrectiveRAGStrategy
            return CorrectiveRAGStrategy(config)
        
        elif strategy_type == RAGStrategyType.SELF_REFLECTIVE:
            from .self_reflective_rag import SelfReflectiveRAGStrategy
            return SelfReflectiveRAGStrategy(config)
        
        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
