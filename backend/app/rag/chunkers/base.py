"""
分块器基础接口和工厂类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Literal, Union
from enum import Enum
from dataclasses import dataclass, field


class ChunkerType(str, Enum):
    """分块器类型枚举"""
    SENTENCE = "sentence"  # 句子分块器
    TOKEN = "token"  # Token 分块器
    CODE = "code"  # 代码分块器
    MARKDOWN = "markdown"  # Markdown 分块器
    SEMANTIC = "semantic"  # 语义分块器
    SENTENCE_WINDOW = "sentence_window"  # 句子窗口分块器
    HIERARCHICAL = "hierarchical"  # 层级分块器
    HTML = "html"  # HTML 分块器
    JSON = "json"  # JSON 分块器
    SIMPLE_FILE = "simple_file"  # 简单文件分块器
    CUSTOM = "custom"  # 自定义分块器


@dataclass
class ChunkerConfig:
    """分块器配置"""
    chunker_type: Union[ChunkerType, str] = ChunkerType.SENTENCE
    chunk_size: int = 1024
    chunk_overlap: int = 100
    separator: str = " "
    paragraph_separator: str = "\n\n"
    secondary_chunking_regex: Optional[str] = None
    
    # 代码分块器参数
    language: Optional[str] = None
    chunk_lines: Optional[int] = None
    chunk_lines_overlap: Optional[int] = None
    max_chars: Optional[int] = None
    
    # 语义分块器参数
    buffer_size: int = 1
    breakpoint_percentile_threshold: float = 95.0
    embed_model: Optional[Any] = None
    
    # 句子窗口分块器参数
    window_size: int = 3
    window_metadata_key: str = "window"
    original_text_metadata_key: str = "original_sentence"
    
    # 层级分块器参数
    chunk_sizes: Optional[List[int]] = None
    
    # HTML 分块器参数
    html_tags: Optional[List[str]] = None
    
    # 其他自定义参数
    extra_params: Dict[str, Any] = field(default_factory=dict)


class BaseChunker(ABC):
    """分块器基类"""
    
    def __init__(self, config: ChunkerConfig):
        self.config = config
    
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """
        分块文本
        
        Args:
            text: 要分块的文本
            
        Returns:
            List[str]: 分块后的文本列表
        """
        pass
    
    @abstractmethod
    def get_node_parser(self):
        """
        获取 LlamaIndex NodeParser 实例（如果适用）
        
        Returns:
            NodeParser 实例或 None
        """
        pass


class ChunkerFactory:
    """分块器工厂类"""
    
    @staticmethod
    def create_chunker(config: ChunkerConfig) -> BaseChunker:
        """
        创建分块器实例
        
        Args:
            config: 分块器配置
            
        Returns:
            BaseChunker: 分块器实例
        """
        chunker_type = config.chunker_type
        if isinstance(chunker_type, str):
            chunker_type = ChunkerType(chunker_type.lower())
        
        if chunker_type == ChunkerType.CUSTOM:
            from .custom_chunkers import CustomChunker
            return CustomChunker(config)
        
        # 其他类型使用 LlamaIndex 分块器
        from .llamaindex_chunkers import LlamaIndexChunker
        return LlamaIndexChunker(config)
