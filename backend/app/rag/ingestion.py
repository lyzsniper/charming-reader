"""
RAG 底层模块 - 纯粹的文档解析、分块、向量化功能
不包含业务逻辑，供上层 service 调用
"""
import os
from typing import List, Optional, Union
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document as LlamaDocument
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.embeddings.litellm import LiteLLMEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings
from llama_index.core.schema import TextNode
from markitdown import MarkItDown
import litellm
from core.config import settings
from .chunkers import chunk_text as chunk_text_unified, ChunkerConfig, ChunkerType

# Configure Global Settings
# Use LiteLLM for embeddings, which supports multiple providers including OpenAI, Azure, Bedrock, etc.
# We map our EMBEDDING_MODEL to LiteLLM's format.
# Ensure OPENAI_API_KEY or relevant provider keys are set in environment/config.
# Settings.embed_model = LiteLLMEmbedding(
#     model_name=settings.EMBEDDING_MODEL,
#     api_base=settings.QWEN_BASE_URL,
#     api_key=settings.QWEN_API_KEY,
#     embed_batch_size=10, # 降低批量大小以减少请求负载
#     # Qwen API 似乎不支持 encoding_format 参数，LiteLLM 默认会传。
#     # 我们可能需要通过 litellm_kwargs 覆盖或者升级 LiteLLM/LlamaIndex
# )
from llama_index.embeddings.langchain import LangchainEmbedding
from langchain_community.embeddings import DashScopeEmbeddings

Settings.embed_model = LangchainEmbedding(
    DashScopeEmbeddings(
        model="text-embedding-v1", # 注意这里要用短名，不用 openai/ 前缀
        dashscope_api_key=settings.QWEN_API_KEY
    )
)
# We can configure the LLM globally or per query engine, let's keep it flexible.

from llama_index.core.vector_stores.types import VectorStoreQueryMode

# 初始化 MarkItDown 实例
_md_converter = MarkItDown()


def get_vector_store():
    """
    获取 Elasticsearch 向量存储实例
    使用统一索引 + metadata 过滤策略
    """
    return ElasticsearchStore(
        es_url=settings.ELASTICSEARCH_URL,
        index_name=settings.INDEX_NAME,
        vector_store_query_mode=VectorStoreQueryMode.HYBRID,
    )


# ============ 底层工具方法 ============

def convert_pdf_to_markdown(file_path: str) -> str:
    """
    将 PDF 转换为 Markdown 文本
    
    Args:
        file_path: PDF 文件路径
        
    Returns:
        str: Markdown 格式的文本内容
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    result = _md_converter.convert(file_path)
    return result.text_content


def chunk_text(
    text: str, 
    chunk_size: int = 1024, 
    chunk_overlap: int = 100,
    chunker_type: Union[ChunkerType, str] = ChunkerType.SENTENCE,
    **chunker_kwargs
) -> List[str]:
    """
    智能分块，支持多种分块策略
    
    Args:
        text: 要分块的文本
        chunk_size: 分块大小（token 或字符数，取决于分块器）
        chunk_overlap: 重叠大小
        chunker_type: 分块器类型，可选值：
            - "sentence": 句子分块器（默认）
            - "token": Token 分块器
            - "code": 代码分块器（需要 language 参数）
            - "markdown": Markdown 分块器
            - "semantic": 语义分块器（需要 embed_model 或使用全局 Settings.embed_model）
            - "sentence_window": 句子窗口分块器
            - "hierarchical": 层级分块器
            - "html": HTML 分块器
            - "json": JSON 分块器
            - "simple_file": 简单文件分块器
            - "custom": 自定义分块器
        **chunker_kwargs: 其他分块器特定参数，例如：
            - language: 代码分块器的编程语言
            - buffer_size: 语义分块器的缓冲区大小
            - window_size: 句子窗口分块器的窗口大小
            - chunk_sizes: 层级分块器的分块大小列表
            - html_tags: HTML 分块器的标签列表
        
    Returns:
        List[str]: 分块后的文本列表
        
    Examples:
        >>> # 使用默认句子分块器
        >>> chunks = chunk_text(text, chunk_size=1024, chunk_overlap=100)
        
        >>> # 使用代码分块器
        >>> chunks = chunk_text(text, chunker_type="code", language="python")
        
        >>> # 使用语义分块器
        >>> chunks = chunk_text(text, chunker_type="semantic", buffer_size=1)
    """
    return chunk_text_unified(
        text=text,
        chunker_type=chunker_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **chunker_kwargs
    )


def generate_embeddings(
    texts: List[str], 
    model: str = "text-embedding-v3",
    batch_size: int = 10
) -> List[List[float]]:
    """
    生成向量嵌入（批量处理）
    使用 LiteLLM 支持多个提供商
    
    Args:
        texts: 文本列表
        model: 向量模型名称
        batch_size: 批次大小
        
    Returns:
        List[List[float]]: 向量列表
    """
    all_embeddings = []
    
    # 配置 API key
    if "qwen" in model.lower() or "dashscope" in model.lower():
        os.environ["DASHSCOPE_API_KEY"] = settings.QWEN_API_KEY
    
    # 分批处理
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        
        response = litellm.embedding(
            model=model,
            input=batch_texts,
            api_base=settings.QWEN_BASE_URL if "qwen" in model.lower() else None
        )
        
        batch_embeddings = [d['embedding'] for d in response['data']]
        all_embeddings.extend(batch_embeddings)
    
    return all_embeddings


def create_text_nodes(
    chunks: List[str],
    embeddings: List[List[float]],
    metadata_list: Optional[List[dict]] = None
) -> List[TextNode]:
    """
    创建 LlamaIndex TextNode 列表
    
    Args:
        chunks: 文本分块列表
        embeddings: 对应的向量列表
        metadata_list: 每个 chunk 的 metadata（可选）
        
    Returns:
        List[TextNode]: TextNode 列表
    """
    nodes = []
    
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = metadata_list[idx] if metadata_list else {}
        
        node = TextNode(
            text=chunk_text,
            embedding=embedding,
            metadata=metadata
        )
        nodes.append(node)
    
    return nodes


def store_nodes_to_es(nodes: List[TextNode]) -> int:
    """
    存储 TextNode 列表到 Elasticsearch
    
    Args:
        nodes: TextNode 列表
        
    Returns:
        int: 存储的节点数量
    """
    vector_store = get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 创建索引并插入
    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True
    )
    
    return len(nodes)


# ============ 完整流程方法（无业务逻辑）============

def ingest_file(
    file_path: str,
    chunker_type: Union[ChunkerType, str] = ChunkerType.SENTENCE,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
    **chunker_kwargs
):
    """
    完整的文件摄取流程（无业务逻辑版本）
    适用于纯 RAG 场景：读取文件 -> 分块 -> 向量化 -> 存储到 ES
    
    Args:
        file_path: 文件路径
        chunker_type: 分块器类型，默认为 "sentence"
        chunk_size: 分块大小
        chunk_overlap: 重叠大小
        **chunker_kwargs: 其他分块器特定参数
        
    Returns:
        str: 处理结果消息
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Load Data
    # SimpleDirectoryReader can accept a list of files.
    # It supports .pdf, .docx, .md, etc. automatically via file extension detection.
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

    # 2. Setup Vector Store (Elasticsearch)
    vector_store = get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 3. Parse and Index
    # 创建分块器配置并获取 NodeParser
    from .chunkers import ChunkerFactory, ChunkerConfig
    
    config = ChunkerConfig(
        chunker_type=chunker_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **chunker_kwargs
    )
    chunker = ChunkerFactory.create_chunker(config)
    splitter = chunker.get_node_parser()
    
    if splitter is None:
        raise ValueError(f"分块器类型 {chunker_type} 不支持 NodeParser，请使用其他方法")
    
    # from_documents handles parsing (using splitter in transformations if provided, 
    # but here we can pass it globally or in the call)
    # Note: VectorStoreIndex.from_documents will insert into the vector store.
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[splitter],
        show_progress=True
    )
    
    return f"Successfully indexed {len(documents)} documents from {file_path}"


def process_file_to_chunks_and_embeddings(
    file_path: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
    embedding_model: str = "text-embedding-v3",
    chunker_type: Union[ChunkerType, str] = ChunkerType.SENTENCE,
    **chunker_kwargs
) -> tuple[str, List[str], List[List[float]]]:
    """
    完整的文件处理流程（返回中间结果，不存储）
    适用于需要自定义存储逻辑的场景
    
    Args:
        file_path: 文件路径
        chunk_size: 分块大小
        chunk_overlap: 重叠大小
        embedding_model: 向量模型
        chunker_type: 分块器类型，默认为 "sentence"
        **chunker_kwargs: 其他分块器特定参数
        
    Returns:
        tuple: (markdown_text, chunks, embeddings)
    """
    # 1. 转换为 Markdown
    markdown_text = convert_pdf_to_markdown(file_path)
    
    # 2. 分块
    chunks = chunk_text(
        markdown_text, 
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        chunker_type=chunker_type,
        **chunker_kwargs
    )
    
    # 3. 生成向量
    embeddings = generate_embeddings(chunks, model=embedding_model)
    
    return markdown_text, chunks, embeddings
