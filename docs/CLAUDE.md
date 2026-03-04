# Backend - 后端API服务

[根目录](../../CLAUDE.md) > **backend**

## 模块职责

Backend 模块是 PaperAgent 的核心后端服务，基于 FastAPI 构建，负责处理所有业务逻辑、数据存储、向量检索和LLM集成。该模块采用分层架构设计，确保代码的可维护性和可扩展性。

## 入口与启动

### 主入口文件
- `main.py` - FastAPI应用主入口，包含路由注册和中间件配置
- 启动命令：`python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 18000`

### 关键配置
- 应用配置：`app/core/config.py`
- 数据库配置：`app/core/db.py`
- 日志配置：`app/core/logger.py`

## 对外接口

### REST API 端点
- `app/api/endpoints.py` - 主要API路由定义
- `app/rag/router.py` - RAG相关API路由

#### 核心API接口
```python
# 知识库管理
POST /api/knowledge-bases/          # 创建知识库
GET  /api/knowledge-bases          # 获取知识库列表
PUT  /api/knowledge-bases/{id}     # 更新知识库
DELETE /api/knowledge-bases/{id}    # 删除知识库

# 文档管理
POST /api/documents/upload          # 上传文档
GET  /api/documents                 # 获取文档列表
GET  /api/documents/{id}            # 获取文档详情
DELETE /api/documents/{id}          # 删除文档

# 聊天接口
POST /api/chat                      # 发起对话
GET  /api/chat/sessions             # 获取对话历史
DELETE /api/chat/sessions/{id}      # 删除对话

# 技能管理
GET  /api/skills                    # 获取所有技能
POST /api/skills/{name}/activate   # 激活技能
POST /api/skills/{name}/deactivate  # 停用技能
```

### WebSocket 支持
- 实时对话流式响应
- 文档处理进度推送

## 关键依赖与配置

### 核心依赖
```python
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0

# 数据库
sqlalchemy==2.0.23
alembic==1.12.1
pgvector==0.2.5

# AI/ML
langchain==0.0.340
langchain_litellm==0.0.369
llama-index==0.10.15
litellm==1.35.4

# 向量搜索
elasticsearch==8.11.0

# 文件处理
pypdf==3.17.4
markdown==3.5.1

# 工具库
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 环境变量配置
```env
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/paperagent

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# MinIO对象存储
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET=paperagent-files

# LLM API Keys
OPENAI_API_KEY=your-openai-key
QWEN_API_KEY=your-qwen-key
DEEPSEEK_API_KEY=your-deepseek-key

# GitHub MCP
GITHUB_MCP_TOKEN=your-github-token
```

## 数据模型

### 核心数据表
- `knowledge_bases` - 知识库表
- `documents` - 文档表
- `document_knowledge_base` - 文档-知识库关联表
- `chat_sessions` - 对话会话表
- `model_configurations` - 模型配置表

### 数据模型定义
- `app/models/sql.py` - SQLAlchemy模型定义
- `app/models/schemas.py` - Pydantic模式定义

## 测试与质量

### 测试结构
```
tests/
├── unit/           # 单元测试
├── integration/   # 集成测试
└── api/          # API测试
```

### 代码质量工具
- Black: 代码格式化
- isort: 导入排序
- mypy: 类型检查
- pytest: 测试框架
- flake8: 代码风格检查

## 常见问题 (FAQ)

### Q: 如何添加新的LLM提供商？
A: 在 `app/core/config.py` 中的 `Settings` 类添加新的API密钥和基础URL，然后在 `app/rag/engine.py` 中配置 `setup_litellm_env()` 函数。

### Q: 数据库迁移如何处理？
A: 使用 Alembic 进行数据库版本控制：
```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### Q: 如何自定义RAG策略？
A: 在 `app/rag/strategies/` 目录下创建新的策略类，继承自 `BaseRAGStrategy`，然后在 `app/rag/engine.py` 中注册新策略。

## 相关文件清单

### 核心模块
- `app/main.py` - FastAPI应用入口
- `app/core/config.py` - 配置管理
- `app/core/db.py` - 数据库连接
- `app/core/logger.py` - 日志配置
- `app/core/exceptions.py` - 异常处理

### API模块
- `app/api/endpoints.py` - API端点定义
- `app/rag/router.py` - RAG路由
- `app/models/schemas.py` - API模式定义

### 业务逻辑
- `app/agents/` - 智能体实现
- `app/rag/` - RAG引擎
- `app/services/` - 业务服务
- `app/dao/` - 数据访问层

### 工具和技能
- `app/tools/` - 工具定义
- `app/skills/` - 技能系统
- `app/utils/` - 工具函数

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新API接口文档
- ✅ 完善配置说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*