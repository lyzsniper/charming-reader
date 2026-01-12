"""
RAG 底层模块 - 纯粹的文档解析、分块、向量化功能
不包含业务逻辑，供上层 service 调用
"""
import os
import time
from typing import List, Optional, Union
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document as LlamaDocument
from llama_index.vector_stores.elasticsearch import ElasticsearchStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Settings
from llama_index.core.schema import TextNode
from markitdown import MarkItDown
import litellm
from core.config import settings
from core.logger import LoggerFactory

try:
    # requests 可能不会被直接用到，但 DashScopeEmbeddings 内部会使用 requests/urllib3；
    # 这里用于更精确地判断“可重试”的网络/SSL异常类型。
    from requests.exceptions import SSLError as RequestsSSLError, ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout  # type: ignore
except Exception:  # pragma: no cover
    RequestsSSLError = Exception  # type: ignore
    RequestsConnectionError = Exception  # type: ignore
    RequestsTimeout = Exception  # type: ignore
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

logger = LoggerFactory.get_service_logger(__name__)

# Configure Global Settings
# Use DashScope (Qwen) embeddings via Langchain integration for better flexibility
# Requires: pip install langchain-community dashscope
Settings.embed_model = LangchainEmbedding(
    DashScopeEmbeddings(
        model="text-embedding-v4",  # Qwen embedding v4 (支持 64~2048 维自定义)
        dashscope_api_key=settings.QWEN_API_KEY    )
)

# Configure Global LLM Settings to use Qwen via LiteLLM
# LiteLLM 支持所有 LLM 提供商（OpenAI、Qwen、DeepSeek 等），不会验证模型名称
# This prevents LlamaIndex from defaulting to OpenAI and checking for OPENAI_API_KEY
from llama_index.llms.litellm import LiteLLM

Settings.llm = LiteLLM(
                model="openai/" + settings.DEFAULT_LLM_MODEL,
                api_key=settings.QWEN_API_KEY,
                api_base=settings.QWEN_BASE_URL,
                custom_llm_provider="openai"
            )

from llama_index.core.vector_stores.types import VectorStoreQueryMode

# 初始化 MarkItDown 实例
_md_converter = MarkItDown()

SUPPORTED_MARKDOWN_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".md", ".txt",
    ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
    ".html", ".xml", ".json"
}


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

def convert_file_to_markdown(file_path: str) -> str:
    """
    将多种办公/文本格式转换为 Markdown 文本
    
    Args:
        file_path: 文件路径（支持 pdf/doc/docx/md/txt/xls/xlsx/ppt/pptx/csv/html/xml/json）
        
    Returns:
        str: Markdown 格式的文本内容
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext and ext not in SUPPORTED_MARKDOWN_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")

    result = _md_converter.convert(file_path)
    return result.text_content


# 兼容旧接口命名
convert_pdf_to_markdown = convert_file_to_markdown


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
    model: str = "text-embedding-v4",  # 默认使用 v2 (1536 dimensions)
    batch_size: int = 10
) -> List[List[float]]:
    """
    生成向量嵌入（批量处理）
    使用 LangChain DashScope 集成，避免 LiteLLM 的 encoding_format 问题
    
    Args:
        texts: 文本列表
        model: 向量模型名称
        batch_size: 批次大小
        
    Returns:
        List[List[float]]: 向量列表
    """
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except Exception:
            return default

    def _env_float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return default

    def _is_retryable_error(e: Exception) -> bool:
        # DashScopeEmbeddings 内部一般会抛 requests/urllib3 相关异常；
        # 这里用“类型 + 文本”双保险判断。
        if isinstance(e, (RequestsSSLError, RequestsConnectionError, RequestsTimeout)):
            return True
        name = type(e).__name__
        msg = str(e)
        retry_markers = (
            "SSLError",
            "SSLEOFError",
            "UNEXPECTED_EOF_WHILE_READING",
            "Max retries exceeded",
            "Connection aborted",
            "Connection reset",
            "Read timed out",
            "ConnectTimeout",
            "ReadTimeout",
        )
        return (name in retry_markers) or any(m in msg for m in retry_markers)

    def _embed_batch_with_retries(batch_texts: List[str], model_name: str) -> List[List[float]]:
        max_retries = max(1, _env_int("QWEN_EMBEDDING_MAX_RETRIES", 4))
        backoff = max(0.1, _env_float("QWEN_EMBEDDING_RETRY_BACKOFF_S", 0.8))

        embeddings_client = DashScopeEmbeddings(
            model=model_name,
            dashscope_api_key=settings.QWEN_API_KEY,
        )

        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                return embeddings_client.embed_documents(batch_texts)
            except Exception as e:
                last_err = e
                if (attempt >= max_retries) or (not _is_retryable_error(e)):
                    raise
                sleep_s = backoff * (2 ** (attempt - 1))
                logger.warning(
                    f"⚠️ DashScope embedding 失败（可重试），第 {attempt}/{max_retries} 次: {type(e).__name__}: {e}；{sleep_s:.1f}s 后重试"
                )
                time.sleep(sleep_s)

        # 理论上走不到这里（上面 attempt>=max_retries 已 raise），兜底：
        raise last_err or RuntimeError("DashScope embedding failed with unknown error")

    def _embed_batch_via_litellm(batch_texts: List[str], model_name: str) -> List[List[float]]:
        # 备用通道：走 Qwen OpenAI-compatible base_url（与 DashScope 官方 embedding API 不同路径）
        # 这通常可以绕开某些 SDK/参数兼容性问题，并且失败时也更容易定位。
        resp = litellm.embedding(
            model=model_name,
            input=batch_texts,
            api_key=settings.QWEN_API_KEY,
            api_base=settings.QWEN_BASE_URL,
        )
        return [d["embedding"] for d in resp["data"]]

    all_embeddings: List[List[float]] = []

    # 强制使用配置里的正确模型名（去掉 openai/ 前缀）
    model_name = settings.EMBEDDING_MODEL.replace("openai/", "")
    if "text-embedding" not in model_name:
        model_name = "text-embedding-v1"  # fallback

    # 分批处理
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]

        try:
            batch_embeddings = _embed_batch_with_retries(batch_texts, model_name=model_name)
        except Exception as dashscope_err:
            # 只有在 DashScope/网络类问题时才切 fallback（避免掩盖真实参数错误）
            if not _is_retryable_error(dashscope_err):
                raise

            logger.warning(
                f"⚠️ DashScope embedding 多次失败（将尝试 fallback: litellm + compatible-mode）: {type(dashscope_err).__name__}: {dashscope_err}"
            )
            try:
                batch_embeddings = _embed_batch_via_litellm(batch_texts, model_name=model_name)
            except Exception as litellm_err:
                raise RuntimeError(
                    "DashScope embeddings 请求失败（SSL/网络异常），且 fallback（litellm + compatible-mode）也失败。"
                    "建议检查：网络代理/防火墙/SSL中间人、是否需要配置 HTTPS_PROXY/HTTP_PROXY，或证书链（REQUESTS_CA_BUNDLE/SSL_CERT_FILE）。"
                ) from litellm_err

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
    
    # 刷新 Elasticsearch 索引，确保数据立即可查询
    try:
        index_name = getattr(vector_store, 'index_name', settings.INDEX_NAME)
        es_client = None

        # 尝试多种方式访问 Elasticsearch 客户端
        if hasattr(vector_store, '_client'):
            es_client = vector_store._client
        elif hasattr(vector_store, 'client'):
            es_client = vector_store.client
        elif hasattr(vector_store, '_elasticsearch_client'):
            es_client = vector_store._elasticsearch_client

        if es_client and hasattr(es_client, 'indices'):
            es_client.indices.refresh(index=index_name)
            logger.info(f"✓ Elasticsearch 索引已刷新: {index_name}, 节点数: {len(nodes)}")
        else:
            # 如果无法通过客户端刷新，尝试使用 HTTP API
            logger.warning(f"⚠ 无法通过客户端刷新索引，尝试使用 HTTP API")
            try:
                import requests
                es_url = settings.ELASTICSEARCH_URL.rstrip('/')
                refresh_url = f"{es_url}/{index_name}/_refresh"
                response = requests.post(refresh_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✓ 通过 HTTP API 刷新索引成功: {index_name}")
                else:
                    logger.warning(f"⚠ HTTP API 刷新索引返回状态码: {response.status_code}")
            except Exception as http_e:
                logger.warning(f"⚠ HTTP API 刷新索引失败: {http_e}")
    except Exception as e:
        logger.warning(f"⚠ 刷新 Elasticsearch 索引失败（不影响数据存储）: {e}")

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
    markdown_text = convert_file_to_markdown(file_path)
    
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
