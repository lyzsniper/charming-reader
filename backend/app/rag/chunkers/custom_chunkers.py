"""
自定义分块器实现
可以在这里添加自定义的分块逻辑
"""
from typing import List
from .base import BaseChunker, ChunkerConfig


class CustomChunker(BaseChunker):
    """自定义分块器基类"""
    
    def chunk(self, text: str) -> List[str]:
        """
        自定义分块逻辑
        
        子类应该重写此方法来实现自定义分块策略
        
        Args:
            text: 要分块的文本
            
        Returns:
            List[str]: 分块后的文本列表
        """
        # 默认实现：简单的固定大小分块
        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            
            # 移动到下一个分块位置（考虑重叠）
            start = end - chunk_overlap
            if start >= text_length:
                break
        
        return chunks
    
    def get_node_parser(self):
        """自定义分块器不返回 NodeParser"""
        return None


# 可以在这里添加更多自定义分块器类
# 例如：
# class RegexChunker(CustomChunker):
#     """基于正则表达式的分块器"""
#     def chunk(self, text: str) -> List[str]:
#         # 实现正则表达式分块逻辑
#         pass
