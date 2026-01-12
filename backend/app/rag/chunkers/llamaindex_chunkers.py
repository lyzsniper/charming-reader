"""
LlamaIndex 分块器实现
"""
from typing import List, Optional, Any
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
    CodeSplitter,
    MarkdownNodeParser,
    SentenceWindowNodeParser,
    SemanticSplitterNodeParser,
    HierarchicalNodeParser,
    HTMLNodeParser,
    JSONNodeParser,
    SimpleFileNodeParser,
)
from llama_index.core import Settings
from .base import BaseChunker, ChunkerConfig, ChunkerType


class LlamaIndexChunker(BaseChunker):
    """LlamaIndex 分块器包装类"""
    
    def __init__(self, config: ChunkerConfig):
        super().__init__(config)
        self._node_parser = None
        self._chunker_type = config.chunker_type
        if isinstance(self._chunker_type, str):
            self._chunker_type = ChunkerType(self._chunker_type.lower())
    
    def _create_node_parser(self):
        """创建 NodeParser 实例"""
        config = self.config
        
        if self._chunker_type == ChunkerType.SENTENCE:
            return SentenceSplitter(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                separator=config.separator,
                paragraph_separator=config.paragraph_separator or "\n\n",
                secondary_chunking_regex=config.secondary_chunking_regex or "[^,.;。？！]+[,.;。？！]?|[,.;。？！]"
            )
        
        elif self._chunker_type == ChunkerType.TOKEN:
            return TokenTextSplitter(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                separator=config.separator
            )
        
        elif self._chunker_type == ChunkerType.CODE:
            if not config.language:
                raise ValueError("代码分块器需要指定 language 参数")
            return CodeSplitter(
                language=config.language,
                chunk_lines=config.chunk_lines or 40,
                chunk_lines_overlap=config.chunk_lines_overlap or 15,
                max_chars=config.max_chars or 1500
            )
        
        elif self._chunker_type == ChunkerType.MARKDOWN:
            return MarkdownNodeParser()
        
        elif self._chunker_type == ChunkerType.SEMANTIC:
            embed_model = config.embed_model or Settings.embed_model
            if embed_model is None:
                raise ValueError("语义分块器需要 embed_model 参数或全局 Settings.embed_model")
            return SemanticSplitterNodeParser(
                buffer_size=config.buffer_size,
                breakpoint_percentile_threshold=config.breakpoint_percentile_threshold,
                embed_model=embed_model
            )
        
        elif self._chunker_type == ChunkerType.SENTENCE_WINDOW:
            return SentenceWindowNodeParser.from_defaults(
                window_size=config.window_size,
                window_metadata_key=config.window_metadata_key,
                original_text_metadata_key=config.original_text_metadata_key
            )
        
        elif self._chunker_type == ChunkerType.HIERARCHICAL:
            chunk_sizes = config.chunk_sizes or [2048, 512, 128]
            return HierarchicalNodeParser.from_defaults(
                chunk_sizes=chunk_sizes
            )
        
        elif self._chunker_type == ChunkerType.HTML:
            tags = config.html_tags or ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section"]
            return HTMLNodeParser(tags=tags)
        
        elif self._chunker_type == ChunkerType.JSON:
            return JSONNodeParser()
        
        elif self._chunker_type == ChunkerType.SIMPLE_FILE:
            return SimpleFileNodeParser()
        
        else:
            raise ValueError(f"不支持的分块器类型: {self._chunker_type}")
    
    def get_node_parser(self):
        """获取 NodeParser 实例"""
        if self._node_parser is None:
            self._node_parser = self._create_node_parser()
        return self._node_parser
    
    def chunk(self, text: str) -> List[str]:
        """
        分块文本
        
        Args:
            text: 要分块的文本
            
        Returns:
            List[str]: 分块后的文本列表
        """
        from llama_index.core.schema import Document
        
        node_parser = self.get_node_parser()
        
        # 创建 Document 对象
        document = Document(text=text)
        
        # 使用 NodeParser 解析文档
        nodes = node_parser.get_nodes_from_documents([document])
        
        # 提取文本内容
        chunks = []
        for node in nodes:
            # 对于句子窗口分块器，可能需要特殊处理
            if self._chunker_type == ChunkerType.SENTENCE_WINDOW:
                # 句子窗口分块器返回的是单个句子，窗口在 metadata 中
                chunk_text = node.text
                chunks.append(chunk_text)
            else:
                chunks.append(node.text)
        
        return chunks
