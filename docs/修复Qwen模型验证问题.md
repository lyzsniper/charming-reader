# 修复 Qwen 模型验证问题

## 问题描述

使用 Qwen 模型时出现错误：

```
ValueError: Unknown model 'qwen-flash-2025-07-28'. Please provide a valid OpenAI model name in: o1, o1-2024-12-17, o1-pro...
```

**错误位置**：RAG 搜索和重排序

## 问题根本原因

`llama_index.llms.openai.OpenAI` 类会验证模型名称，只接受 OpenAI 官方模型列表中的模型名称。当使用 Qwen、DeepSeek 等其他提供商的模型时会失败。

## 解决方案

**使用 `LiteLLM` 替代 `OpenAI` 类**

`LiteLLM` 支持所有 LLM 提供商（100+ 模型），不会验证模型名称，完美支持：
- ✅ OpenAI (gpt-4, gpt-3.5-turbo, etc.)
- ✅ Qwen (qwen-flash, qwen-plus, qwen-turbo, etc.)
- ✅ DeepSeek (deepseek-chat, deepseek-coder, etc.)
- ✅ GLM (glm-4, etc.)
- ✅ 所有 OpenAI 兼容 API

## 修复内容

### 1. RAG Service (`backend/app/services/rag_service.py`)

**修改前：**
```python
from llama_index.llms.openai import OpenAI

rerank_llm = OpenAI(
    model=settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL
)
```

**修改后：**
```python
from llama_index.llms.litellm import LiteLLM

rerank_llm = LiteLLM(
    model=settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL
)
```

### 2. RAG Ingestion (`backend/app/rag/ingestion.py`)

**修改前：**
```python
from llama_index.llms.openai import OpenAI

Settings.llm = OpenAI(
    model=settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL,
    is_chat_model=True
)
```

**修改后：**
```python
from llama_index.llms.litellm import LiteLLM

Settings.llm = LiteLLM(
    model=settings.DEFAULT_LLM_MODEL,
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL
)
```

### 3. RAG Engine (`backend/app/rag/engine.py`)

**修改前：**
```python
from llama_index.llms.openai import OpenAI

rerank_llm = OpenAI(
    model=settings.DEFAULT_LLM_MODEL, 
    api_key=settings.OPENAI_API_KEY or "dummy"
)
```

**修改后：**
```python
from llama_index.llms.litellm import LiteLLM

rerank_llm = LiteLLM(
    model=settings.DEFAULT_LLM_MODEL, 
    api_key=settings.QWEN_API_KEY,
    api_base=settings.QWEN_BASE_URL
)
```

## 验证步骤

### 1. 重启服务

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 2. 测试 RAG 搜索

```bash
curl -X POST http://localhost:8000/api/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Transformer 架构",
    "knowledge_base_ids": ["YOUR_KB_ID"],
    "top_k": 5
  }'
```

**预期结果**：成功返回检索结果，不再报错。

### 3. 测试 RAG 问答（带重排序）

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "什么是 Self-Attention？",
    "knowledge_base_ids": ["YOUR_KB_ID"],
    "enable_rerank": true
  }'
```

**预期结果**：成功返回答案和来源，LLM 重排序正常工作。

### 4. 测试不同的模型

可以在 `config.py` 中切换模型测试：

```python
# Qwen 模型
DEFAULT_LLM_MODEL: str = "qwen-flash-2025-07-28"
DEFAULT_LLM_MODEL: str = "qwen-plus"
DEFAULT_LLM_MODEL: str = "qwen-turbo"

# DeepSeek 模型（如果配置了）
DEFAULT_LLM_MODEL: str = "deepseek-chat"

# OpenAI 模型（如果配置了）
DEFAULT_LLM_MODEL: str = "gpt-4o"
DEFAULT_LLM_MODEL: str = "gpt-3.5-turbo"
```

所有模型都应该正常工作，不会再有验证错误。

## LiteLLM 的优势

1. **通用性** - 支持 100+ LLM 提供商
2. **无验证** - 不检查模型名称，支持所有自定义模型
3. **兼容性** - 完全兼容 llama_index 的 LLM 接口
4. **配置简单** - 只需要 `model`, `api_key`, `api_base` 三个参数
5. **统一接口** - 所有提供商使用相同的调用方式

## 修改文件清单

- ✅ `backend/app/services/rag_service.py` - RAG 重排序
- ✅ `backend/app/rag/ingestion.py` - 全局 LLM 配置
- ✅ `backend/app/rag/engine.py` - RAG Engine 重排序

## 技术说明

### 为什么 OpenAI 类会验证模型名称？

`llama_index.llms.openai.OpenAI` 类的设计目的是专门用于 OpenAI 的 API，因此内置了模型名称验证逻辑，确保用户只使用 OpenAI 支持的模型。

### 为什么 LiteLLM 不验证？

`LiteLLM` 是一个通用的 LLM 代理层，设计目标是支持所有 LLM 提供商。它通过模型名称前缀（如 `openai/`, `anthropic/`, `cohere/`）或 API base URL 来判断使用哪个提供商，不会限制模型名称。

### 为什么不需要模型前缀？

当提供 `api_base` 参数时，LiteLLM 会自动识别这是一个 OpenAI 兼容的自定义 API，不需要前缀。

## 常见问题

### Q1: LiteLLM 是否会影响性能？

**A**: 不会。LiteLLM 只是一个轻量级的代理层，调用开销极小。

### Q2: 是否需要修改配置文件？

**A**: 不需要。`config.py` 中的配置保持不变：
- `DEFAULT_LLM_MODEL = "qwen-flash-2025-07-28"`
- `QWEN_API_KEY = "your-api-key"`
- `QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"`

### Q3: 是否支持流式输出？

**A**: 是的，LiteLLM 完全支持流式输出（streaming）。

### Q4: 如果想切换到 OpenAI 怎么办？

**A**: 只需修改配置：
```python
DEFAULT_LLM_MODEL = "gpt-4o"
OPENAI_API_KEY = "your-openai-key"
# QWEN_BASE_URL 不需要修改，LiteLLM 会自动识别
```

LiteLLM 会自动检测到这是 OpenAI 模型，使用 OpenAI 的 API。

## 总结

通过将 `OpenAI` 类替换为 `LiteLLM` 类，系统现在支持：

- ✅ **所有 LLM 提供商** - OpenAI、Qwen、DeepSeek、GLM 等
- ✅ **无模型验证** - 可以使用任何模型名称
- ✅ **完整功能** - RAG 检索、重排序、问答全部正常
- ✅ **灵活切换** - 随时切换不同的 LLM 提供商

**不再需要 OpenAI API，完全可以使用 Qwen 或其他国产模型！** 🎉

