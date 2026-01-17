# RAG - 检索增强生成引擎

[根目录](../../../CLAUDE.md) > [backend](../../CLAUDE.md) > **rag**

## 模块职责

RAG (Retrieval-Augmented Generation) 模块是 PaperAgent 的核心检索系统，负责从知识库中检索相关信息并生成高质量的回答。该模块采用 LangGraph 构建工作流，支持多种检索策略和重排序算法。

## 入口与启动

### 主要入口文件
- `engine.py` - RAG引擎核心实现
- `ingestion.py` - 文档处理和向量化
- `router.py` - RAG API路由

### 工作流启动
```python
# 流式执行
result = await run_agent_with_rag_stream(question, context)

# 非流式执行
result = await run_agent_with_rag(question, context)
```

## 对外接口

### 核心接口
```python
# 引擎配置
class AgentState(TypedDict):
    question: str      # 用户问题
    context: str       # 检索到的上下文
    answer: str        # 最终答案
    source: str        # 来源标识

# 检索策略
from rag.strategies import (
    AdaptiveRAG,
    AgenticRAG,
    CorrectiveRAG,
    HybridRAG,
    SelfReflectiveRAG,
    TwoStepRAG
)

# 分块策略
from rag.chunkers import (
    CustomChunkers,
    LlamaIndexChunkers
)
```

### API接口
```python
# RAG相关API (在 router.py 中)
POST /api/rag/query          # RAG查询
POST /api/rag/stream         # 流式RAG查询
GET  /api/rag/strategies     # 获取可用策略
```

## 关键依赖与配置

### 依赖项
```python
from langgraph.graph import StateGraph, END
from langchain_litellm import ChatLiteLLM
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import LLMRerank
from rag.ingestion import get_vector_store
from tavily import TavilyClient
```

### 模型配置
```python
# LLM配置
llm = LiteLLM(
    model="openai/" + settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL,
    custom_llm_provider="openai"
)

# 重排序模型
rerank_llm = LiteLLM(
    model="openai/" + settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL,
    custom_llm_provider="openai"
)
```

### 环境变量设置
```python
def setup_litellm_env():
    if settings.DEEPSEEK_API_KEY:
        os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY
    if settings.QWEN_API_KEY:
        os.environ["DASHSCOPE_API_KEY"] = settings.QWEN_API_KEY
    if settings.GLM_API_KEY:
        os.environ["ZHIPUAI_API_KEY"] = settings.GLM_API_KEY
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
```

## 数据模型

### 检索状态
```python
class AgentState(TypedDict):
    question: str      # 原始问题
    context: str       # 检索到的上下文
    answer: str        # 生成的答案
    source: str        # 来源（'local' 或 'web'）
```

### 向量存储
- 使用 PostgreSQL + pgvector 存储文档向量
- 支持余弦相似度计算
- 支持批量向量化

## 测试与质量

### 测试策略
- 单元测试：各个检索策略
- 集成测试：完整的RAG流程
- 性能测试：检索速度和准确性

### 质量指标
- 检索准确率 (Precision@K)
- 召回率 (Recall@K)
- MRR (Mean Reciprocal Rank)
- 答案相关性评分

## 常见问题 (FAQ)

### Q: 如何添加新的检索策略？
A:
1. 在 `strategies/` 目录下创建新策略类
2. 继承 `BaseRAGStrategy` 基类
3. 实现 `retrieve` 方法
4. 在 `engine.py` 中注册新策略

### Q: 如何优化检索效果？
A:
1. 调整文档分块策略
2. 优化嵌入模型选择
3. 使用重排序模型提升相关性
4. 调整检索参数（top_k, score_threshold）

### Q: 支持哪些文档格式？
A: 目前支持：
- PDF (.pdf)
- Markdown (.md)
- 文本文件 (.txt)
- Word文档 (.docx - 需要额外配置)

### Q: 如何处理长文档？
A: 系统提供多种分块策略：
- 固定大小分块
- 语义感知分块
- 层次化分块
- 自定义分块器

## 相关文件清单

### 核心模块
- `engine.py` - RAG引擎核心
- `ingestion.py` - 文档处理
- `router.py` - API路由

### 策略模块
- `strategies/` - 检索策略实现
  - `adaptive_rag.py` - 自适应RAG
  - `agentic_rag.py` - 智能体RAG
  - `corrective_rag.py` - 纠正式RAG
  - `hybrid_rag.py` - 混合RAG
  - `self_reflective_rag.py` - 自反思RAG
  - `two_step_rag.py` - 两步RAG

### 分块模块
- `chunkers/` - 文档分块策略
  - `base.py` - 基础分块器
  - `custom_chunkers.py` - 自定义分块器
  - `llamaindex_chunkers.py` - LlamaIndex分块器

### 工具和配置
- `../../core/config.py` - 配置管理
- `../../services/ingestion.py` - 文档处理服务

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新RAG引擎接口文档
- ✅ 完善检索策略说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*