# Chat API 重构说明

## 重构概述

根据 [ADK 官方文档 Session 概念](https://adk.wiki/sessions/)，本次重构实现了以下核心功能：

### 核心改进

1. **自动创建 Session**：用户不传 `session_id` 时，使用 UUID 自动创建新会话
2. **多知识库选择**：支持选择多个知识库进行 RAG 检索
3. **RAG 问答集成**：选择知识库后自动进行向量检索，基于知识库内容回答
4. **会话持久化存储**：基于 PostgreSQL 的 Session 持久化（替代 InMemorySessionService）

### ADK Session 架构

根据 ADK 文档，Session 管理包含三个核心概念：

- **Session**：当前对话线程，包含消息历史和事件序列
- **State**：当前对话中的临时数据（`session.state`）
- **Memory**：跨 Session 的长期知识存储

## 数据库变更

### 新增表结构

#### 1. `adk_sessions` - Session 主表

```sql
CREATE TABLE adk_sessions (
    id UUID PRIMARY KEY,
    session_id VARCHAR NOT NULL,           -- ADK session_id
    user_id VARCHAR NOT NULL,              -- ADK user_id
    app_name VARCHAR NOT NULL DEFAULT 'paper_agent',  -- ADK app_name
    state JSON,                            -- Session.state 数据
    metadata JSON,                         -- 额外元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_adk_sessions_session_id ON adk_sessions(session_id);
CREATE INDEX ix_adk_sessions_user_id ON adk_sessions(user_id);
CREATE INDEX ix_adk_sessions_app_name ON adk_sessions(app_name);
```

#### 2. `adk_session_messages` - 会话消息表

```sql
CREATE TABLE adk_session_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES adk_sessions(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL,                 -- 'user' or 'model'
    content JSON NOT NULL,                 -- Content 对象的 JSON 表示
    metadata JSON,                         -- 额外元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_adk_session_messages_session_id ON adk_session_messages(session_id);
```

## 新增组件

### 1. PostgreSQLSessionService

位置：`backend/app/services/session_service.py`

实现了 ADK `SessionService` 接口，提供：

- `create_session()` - 创建新会话
- `get_session()` - 获取会话
- `update_session()` - 更新会话（保存消息和状态）
- `delete_session()` - 删除会话
- `list_sessions()` - 列出用户所有会话

核心特性：

- Content 对象序列化/反序列化（支持 text、function_call、function_response）
- 自动管理消息历史
- State 数据持久化
- 级联删除保护

### 2. 更新的 Schema

位置：`backend/app/models/schemas.py`

新增：

```python
class ChatRequest(BaseModel):
    message: str                                    # 用户消息
    session_id: Optional[str] = None                # 会话ID（可选，自动创建）
    user_id: Optional[str] = "default_user"         # 用户ID
    knowledge_base_ids: Optional[List[UUID]] = None # 知识库ID列表（多选）
    use_rag: bool = False                           # 是否启用RAG
    rag_top_k: int = 5                              # RAG检索数量
    enable_rerank: bool = True                      # 是否启用重排序

class ChatResponse(BaseModel):
    session_id: str                                 # 实际使用的会话ID
    user_id: str                                    # 用户ID
    message: str                                    # 用户消息
    response: str                                   # 智能体回复
    sources: Optional[List[Dict]] = None            # RAG来源
    knowledge_base_ids: Optional[List[str]] = None  # 使用的知识库
    created_at: datetime                            # 创建时间
```

## API 使用示例

### 场景 1：简单对话（不带知识库）

```bash
POST /api/chat
{
  "message": "什么是 Transformer？"
}
```

响应：

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "default_user",
  "message": "什么是 Transformer？",
  "response": "Transformer 是一种基于注意力机制的深度学习模型...",
  "sources": null,
  "knowledge_base_ids": null,
  "created_at": "2026-01-07T12:00:00Z"
}
```

### 场景 2：继续对话（使用已有 session_id）

```bash
POST /api/chat
{
  "message": "能详细解释一下吗？",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 场景 3：带知识库的 RAG 问答（单个知识库）

```bash
POST /api/chat
{
  "message": "Attention Is All You Need 这篇论文的主要贡献是什么？",
  "knowledge_base_ids": ["123e4567-e89b-12d3-a456-426614174000"]
}
```

响应：

```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "default_user",
  "message": "Attention Is All You Need 这篇论文的主要贡献是什么？",
  "response": "根据论文内容，主要贡献包括...",
  "sources": [
    {
      "content": "We propose a new simple network architecture...",
      "score": 0.92,
      "metadata": {
        "document_id": "789e4567-e89b-12d3-a456-426614174000",
        "chunk_index": 5
      }
    }
  ],
  "knowledge_base_ids": ["123e4567-e89b-12d3-a456-426614174000"],
  "created_at": "2026-01-07T12:00:00Z"
}
```

### 场景 4：多知识库 RAG 问答

```bash
POST /api/chat
{
  "message": "对比 Transformer 和 BERT 的区别",
  "knowledge_base_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "223e4567-e89b-12d3-a456-426614174001"
  ],
  "rag_top_k": 10,
  "enable_rerank": true
}
```

### 场景 5：指定用户和会话

```bash
POST /api/chat
{
  "message": "继续之前的讨论",
  "user_id": "user_123",
  "session_id": "my-custom-session-id"
}
```

## 部署步骤

### 1. 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

这将创建 `adk_sessions` 和 `adk_session_messages` 表。

### 2. 重启后端服务

```bash
# 如果使用 Docker
docker-compose restart backend

# 或者直接运行
cd backend
python -m uvicorn app.main:app --reload
```

### 3. 验证功能

测试基本对话：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?"
  }'
```

测试 RAG 问答：

```bash
# 首先获取知识库列表
curl http://localhost:8000/api/knowledge-bases

# 使用知识库进行对话
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "这篇论文的主要内容是什么？",
    "knowledge_base_ids": ["YOUR_KB_ID"]
  }'
```

## 技术细节

### Session 持久化流程

1. **创建/获取 Session**
   - 用户首次对话 → 自动创建 UUID Session
   - 用户传入 session_id → 获取已有 Session 或创建新 Session

2. **消息存储**
   - 用户消息和智能体回复作为 `Content` 对象存储
   - JSON 序列化支持 text、function_call、function_response

3. **RAG 集成**
   - 选择知识库 → 触发向量检索
   - 检索结果注入到 prompt
   - 智能体基于检索内容回答

4. **State 管理**
   - `session.state` 存储为 JSON
   - 可用于存储对话中的临时变量

### RAG 工作流程

```
用户消息
  ↓
选择知识库？
  ↓ 是
向量检索 (Elasticsearch + PostgreSQL)
  ↓
LLM 重排序 (可选)
  ↓
构建 RAG 上下文
  ↓
注入到智能体 Prompt
  ↓
ADK Agent 处理
  ↓
返回答案 + 来源
```

## 相关文档

- [ADK Session 官方文档](https://adk.wiki/sessions/)
- [RAG 系统架构说明](./RAG_系统架构说明.md)
- [项目启动指南](./PROJECT_STARTUP.md)

## 注意事项

1. **Session 清理**：建议定期清理过期 Session（可以添加定时任务）
2. **State 大小**：避免在 `session.state` 中存储过大的数据
3. **知识库验证**：API 会自动验证知识库是否存在
4. **RAG 性能**：可以通过 `rag_top_k` 和 `enable_rerank` 调整检索性能

## 后续优化建议

1. **添加 Session 过期机制**（TTL）
2. **实现 Memory 服务**（跨 Session 的长期知识）
3. **添加 Session 列表和管理 API**
4. **支持 Session 回滚**（ADK rollback 功能）
5. **添加流式响应支持**（SSE/WebSocket）

