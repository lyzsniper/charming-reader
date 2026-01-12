"""
分块器模块 - 统一的文本分块接口
支持多种分块策略：LlamaIndex 分块器、自定义分块器等
"""
from typing import List, Optional, Dict, Any, Literal, Union
from .base import ChunkerFactory, ChunkerType, ChunkerConfig

__all__ = [
    "ChunkerFactory",
    "ChunkerType", 
    "ChunkerConfig",
    "chunk_text",
]

# 导出统一的 chunk_text 函数
def chunk_text(
    text: str,
    chunker_type: Union[ChunkerType, str] = ChunkerType.SENTENCE,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
    **kwargs
) -> List[str]:
    """
    统一的文本分块入口函数
    
    Args:
        text: 要分块的文本
        chunker_type: 分块器类型
        chunk_size: 分块大小（token 或字符数，取决于分块器）
        chunk_overlap: 重叠大小
        **kwargs: 其他分块器特定参数
        
    Returns:
        List[str]: 分块后的文本列表
        
    Examples:
        >>> # 使用句子分块器
        >>> chunks = chunk_text(text, chunker_type="sentence", chunk_size=1024)
        
        >>> # 使用语义分块器
        >>> chunks = chunk_text(text, chunker_type="semantic", buffer_size=1)
        
        >>> # 使用代码分块器
        >>> chunks = chunk_text(text, chunker_type="code", language="python")
    """
    config = ChunkerConfig(
        chunker_type=chunker_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    chunker = ChunkerFactory.create_chunker(config)
    return chunker.chunk(text)
