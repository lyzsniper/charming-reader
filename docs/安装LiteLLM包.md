# 安装 LiteLLM 包

## 问题

```
ModuleNotFoundError: No module named 'llama_index.llms.litellm'
```

## 解决方案

安装 `llama-index-llms-litellm` 包。

## 安装步骤

### 方法 1: 使用 requirements.txt（推荐）

```bash
cd backend
pip install -r requirements.txt
```

这会安装所有缺失的依赖，包括：
- `llama-index-llms-litellm==0.4.1`

### 方法 2: 单独安装

```bash
cd backend
pip install llama-index-llms-litellm==0.4.1
```

## 验证安装

安装完成后，测试导入：

```bash
cd backend
python -c "from llama_index.llms.litellm import LiteLLM; print('✓ LiteLLM 安装成功')"
```

预期输出：
```
✓ LiteLLM 安装成功
```

## 启动服务

```bash
cd backend
python -m uvicorn app.main:app --reload
```

预期输出：
```
INFO:     Will watch for changes in these directories: ['C:\\App\\Coding\\PaperAgent\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 已更新的文件

- ✅ `backend/requirements.txt` - 添加了 `llama-index-llms-litellm==0.4.1`

## 完整的 LiteLLM 相关包

项目中使用的 LiteLLM 相关包：

```
litellm==1.80.11                      # LiteLLM 核心库
llama-index-llms-litellm==0.4.1       # LlamaIndex LiteLLM 集成 (新增)
llama-index-embeddings-litellm==0.4.1 # LlamaIndex LiteLLM Embeddings
langchain-litellm==0.3.5              # LangChain LiteLLM 集成
```

## 常见问题

### Q1: pip install 很慢怎么办？

**A**: 使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: 安装失败怎么办？

**A**: 尝试升级 pip：

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Q3: 虚拟环境问题

**A**: 确保在正确的虚拟环境中：

```bash
# Windows
cd backend
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## 总结

安装 `llama-index-llms-litellm` 包后：

- ✅ 支持所有 LLM 提供商（OpenAI、Qwen、DeepSeek 等）
- ✅ RAG 重排序功能正常工作
- ✅ 不再有模型验证错误
- ✅ 完整的 RAG 功能

现在可以愉快地使用 Qwen 模型了！🎉

