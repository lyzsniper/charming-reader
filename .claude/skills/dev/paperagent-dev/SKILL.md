---
name: paperagent-dev
description: PaperAgent项目开发指南，包含架构、编码规范和常用命令
triggers:
  - paperagent development
  - project structure
  - 项目架构
  - 开发指南
version: 1.0.0
---

# PaperAgent 开发指南

## 项目概述

PaperAgent 是一个基于 RAG 的学术研究助手，结合了 Google ADK、LlamaIndex 和 LangGraph 构建智能论文分析系统。

## 技术栈

**后端**：
- FastAPI - Web 框架
- Google ADK - Agent 框架
- LiteLLM - 多模型统一接口
- LlamaIndex - 文档处理和索引
- LangGraph - 工作流编排
- PostgreSQL + pgvector - 向量数据库
- Elasticsearch - 全文检索

**前端**：
- React + TypeScript
- Vite构建工具
- TailwindCSS + shadcn/ui

## 项目结构

```
PaperAgent/
├── backend/
│   ├── app/
│   │   ├── agents/          # Agent 定义
│   │   │   └── flow.py      # 学术研究 Agent
│   │   ├── api/             # API 端点
│   │   │   └── endpoints.py
│   │   ├── core/            # 核心配置
│   │   │   ├── config.py
│   │   │   └── db.py
│   │   ├── models/          # 数据模型
│   │   │   └── sql.py
│   │   ├── services/        # 业务逻辑
│   │   │   └── ingestion.py
│   │   ├── skills/          # 技能系统
│   │   │   ├── loader.py
│   │   │   ├── registry.py
│   │   │   ├── activator.py
│   │   │   └── manager.py
│   │   ├── tools/           # Agent 工具
│   │   │   └── definitions.py
│   │   └── main.py          # FastAPI 应用
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── App.tsx
│   └── package.json
├── .claude/skills/          # Agent Skills
│   ├── paper-analysis/
│   ├── literature-review/
│   ├── citation-management/
│   ├── rag-enhancement/
│   ├── data-extraction/
│   └── dev/
└── docs/                    # 文档
```

## 开发环境设置

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑 .env 填入API密钥
```

### 前端

```bash
cd frontend
pnpm install
```

### Docker

```bash
docker-compose up -d
```

## 常用命令

### 后端开发

```bash
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "description"

# 运行测试
pytest backend/tests/
```

### 前端开发

```bash
# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build
```

### Skills 管理

```bash
# 同步技能到 AGENTS.md
npm run skills:sync

# 列出所有技能
npm run skills:list
```

## 编码规范

### Python (Backend)

- 使用 type hints
- 遵循 PEP 8
- 函数命名：snake_case
- 类命名：PascalCase
- 常量：UPPER_CASE

示例：
```python
from typing import Optional

def process_document(file_path: str, chunk_size: int = 1000) -> Optional[str]:
    """
    Process a document and return content.
    
    Args:
        file_path: Path to the document
        chunk_size: Size of text chunks
    
    Returns:
        Processed content or None if failed
    """
    pass
```

### TypeScript (Frontend)

- 使用 TypeScript严格模式
- 组件命名：PascalCase
- 函数/变量：camelCase
- 接口前缀：I (可选)

示例：
```typescript
interface Skill {
  name: string;
  description: string;
  status: 'active' | 'inactive';
}

function activateSkill(skillName: string): Promise<void> {
  // implementation
}
```

## Agent 开发指南

### 添加新工具

1. 在 `backend/app/tools/definitions.py` 定义工具函数
2. 在 `backend/app/agents/flow.py` 注册到 Agent 的 tools 列表

```python
def my_new_tool(param: str) -> str:
    """
    Tool description for the agent.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
    """
    # implementation
    return result
```

### 修改 Agent 指令

编辑 `backend/app/agents/flow.py` 中的 `BASE_INSTRUCTION`：

```python
BASE_INSTRUCTION = """
Your instruction here...
"""
```

## Skills 开发指南

### 创建新技能

1. 在 `.claude/skills/` 创建新目录
2. 添加 `SKILL.md` 文件：

```markdown
---
name: skill-name
description: One-line description
triggers:
  - trigger word 1
  - trigger word 2
version: 1.0.0
---

# Skill Title

## 目标
...

## 核心能力
...
```

3. 重启后端或调用 reload API

### 技能最佳实践

- 明确的触发词
- 清晰的使用指南
- 结构化的输出格式
- 实用的示例
- 适当的参考资源

## API 设计

### RESTful 规范

- GET: 获取资源
- POST: 创建资源
- PUT/PATCH: 更新资源
- DELETE: 删除资源

### 响应格式

成功：
```json
{
  "data": {...},
  "message": "Success"
}
```

失败：
```json
{
  "detail": "Error message"
}
```

## 数据库

### 模型定义

使用 SQLAlchemy ORM：

```python
from sqlalchemy import Column, Integer, String
from core.db import Base

class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

### 迁移

```bash
alembic revision --autogenerate -m "Add my_table"
alembic upgrade head
```

## 测试

### 单元测试

```python
import pytest

def test_my_function():
    result = my_function("input")
    assert result == "expected"
```

### API 测试

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_endpoint():
    response = client.get("/api/test")
    assert response.status_code == 200
```

## 部署

### Docker

```bash
docker-compose build
docker-compose up -d
```

### 环境变量

重要环境变量：
- `DATABASE_URL`: PostgreSQL连接
- `ELASTICSEARCH_URL`: ES连接
- `DEFAULT_LLM_MODEL`: 默认模型
- `*_API_KEY`: 各种API密钥

## 调试技巧

### 后端调试

```python
# 添加日志
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Debug info: {variable}")
```

### Agent 调试

在 `run_agent()` 中添加打印：

```python
print(f"Query: {input_text}")
print(f"Active skills: {skills_manager.get_active_skills()}")
```

### Skills 调试

检查加载情况：

```python
from skills.manager import skills_manager
stats = skills_manager.get_statistics()
print(stats)
```

## 常见问题

**Q: Agent 没有激活技能？**
A: 检查 `SKILLS_AUTO_ACTIVATION` 配置，确保触发词匹配

**Q: 数据库迁移失败？**
A: 检查数据库连接，查看 `alembic/versions/` 中的迁移脚本

**Q: API 调用慢？**
A: 检查 LLM API 响应时间，考虑使用缓存

**Q: 前端连接后端失败？**
A: 检查 CORS 配置，确保前端配置了正确的 API URL

## 资源链接

- [Google ADK文档](https://github.com/google/generative-ai-docs)
- [LlamaIndex文档](https://docs.llamaindex.ai/)
- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Agent Skills规范](https://github.com/agentskills/agentskills)

---

需要帮助？查看 `docs/` 目录下的详细文档或询问开发团队。

