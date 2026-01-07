# CharMing Reader (查·明)

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![React](https://img.shields.io/badge/react-19.2-61dafb.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Developed with ❤️. Because reading papers is hard, but loving Ming is easy.**

*让科研变得迷人，让论文查得明白。*

</div>

---

## 💝 关于 CharMing

CharMing Reader（查·明）是一个为学术研究者打造的智能论文阅读助手。它的名字蕴含着双重含义：中文"查明"代表查清真相、搞懂论文的使命，英文"Charming"则意味着让枯燥的学术研究变得迷人而优雅。这个项目融合了现代 AI 技术与深度学习能力，通过 RAG（检索增强生成）架构、向量数据库和大语言模型的完美配合，将复杂的论文阅读过程转化为一场流畅的对话体验。无论你是需要快速提取论文核心观点，还是想要深入理解复杂的学术概念，CharMing 都能成为你最得力的研究伙伴。

## ✨ 核心特性

CharMing Reader 提供了一整套完整的学术文献处理解决方案。系统能够智能解析 PDF 格式的学术论文，自动提取文本内容并转换为结构化的 Markdown 格式，随后通过先进的向量化技术将文档切分为语义块并存储到向量数据库中。在检索环节，CharMing 采用混合检索策略，结合向量数据库 pgvector 的语义搜索能力和 Elasticsearch 的关键词匹配优势，确保检索结果既准确又全面。更重要的是，系统集成了包括 OpenAI GPT-4o、通义千问、Deepseek、智谱 GLM 在内的多种主流大语言模型，通过 LiteLLM 统一接口实现无缝切换。前端界面采用现代化设计理念，支持实时流式对话响应和精准的引用来源展示，让学术交流变得既高效又直观。此外，CharMing 还配备了完善的知识库管理系统和 MinIO 对象存储方案，支持大规模文档的安全存储与快速访问。

## 🏗️ 技术架构

CharMing Reader 构建在一套经过精心选择的现代化技术栈之上。后端服务基于 Python 3.10+ 和 FastAPI 框架开发，提供高性能的异步 API 接口；前端采用 React 19.2 配合 Vite 构建工具，结合 TailwindCSS 和 Shadcn/ui 组件库打造流畅的用户体验。数据层面，系统使用 PostgreSQL 16 作为主数据库，通过 pgvector 扩展实现向量存储与相似度检索；Elasticsearch 8.11 作为全文搜索引擎，与向量检索形成互补的混合检索能力。文件存储采用 MinIO 对象存储服务，提供 S3 兼容的 API 接口。在 AI 能力方面，CharMing 通过 LiteLLM 实现多模型统一调度，使用 MarkItDown 进行高质量的 PDF 文档解析，并整合了 LangChain 生态中的部分工具链来增强 RAG 处理能力。整个系统通过 Docker Compose 实现容器化编排，确保开发、测试和生产环境的一致性。

## 🚀 快速开始

### 环境准备

在开始使用 CharMing Reader 之前，请确保你的开发环境已经安装了以下工具：Docker 和 Docker Compose（用于容器化部署）、Node.js 18+ 和 pnpm（用于前端开发）。如果你计划在本地进行后端开发，还需要安装 Python 3.10 或更高版本。

### 配置环境变量

进入 `backend` 目录，创建 `.env` 配置文件。这个文件包含了数据库连接、API 密钥等关键配置信息。以下是一个完整的配置示例：

```env
# 数据库配置
DATABASE_URL=postgresql://jensenlyz:1014@db:35432/paperagent

# Elasticsearch 配置
ELASTICSEARCH_URL=http://es:9200
INDEX_NAME=paper_index

# MinIO 对象存储配置
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=paperagent
MINIO_SECRET_KEY=paperagent123
MINIO_BUCKET=paperagent-files

# AI 模型 API 密钥（根据实际使用的模型配置）
OPENAI_API_KEY=sk-your-openai-key-here
DEEPSEEK_API_KEY=your-deepseek-key
QWEN_API_KEY=your-qwen-key
GLM_API_KEY=your-glm-key

# 模型选择
DEFAULT_LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

请根据你的实际情况修改上述配置，特别是 API 密钥部分。如果只使用某一个模型，只需配置对应的 API 密钥即可。

### Docker Compose 一键部署

CharMing Reader 提供了完整的 Docker Compose 配置，可以一键启动包括数据库、搜索引擎、对象存储和后端服务在内的所有组件。在项目根目录下执行以下命令：

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看服务运行状态
docker-compose ps

# 查看后端服务日志
docker-compose logs -f backend
```

启动完成后，各服务的访问地址如下：

- **后端 API**: http://localhost:18000
- **PostgreSQL**: localhost:35432
- **Elasticsearch**: http://localhost:39200
- **MinIO 控制台**: http://localhost:39001 (用户名: paperagent, 密码: paperagent123)

### 运行前端开发服务器

前端服务需要单独启动。在项目根目录下执行：

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器将在 http://localhost:5173 启动。打开浏览器访问该地址，你就能看到 CharMing Reader 的优雅界面了。

### 数据库初始化

如果是首次启动，需要运行数据库迁移来创建必要的表结构。你可以通过以下两种方式之一来执行迁移：

**方式一：在 Docker 容器中执行**

```bash
docker-compose exec backend alembic upgrade head
```

**方式二：在本地开发环境执行**

```bash
cd backend
# 激活虚拟环境（如使用 venv）
# Windows PowerShell
.venv\Scripts\activate
# 运行迁移
alembic upgrade head
```

## 🛠️ 本地开发环境

如果你需要对 CharMing Reader 进行深度定制或功能开发，可以选择在本地运行后端服务，这样能够获得更快的调试体验和更灵活的开发流程。

### 后端开发

后端项目位于 `backend` 目录，推荐使用 `uv` 作为包管理工具以获得极速的依赖安装体验。首先安装 uv（如果尚未安装）：

```powershell
# Windows 安装
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后，创建虚拟环境并安装依赖：

```bash
cd backend

# 创建虚拟环境
uv venv

# 激活虚拟环境 (Windows PowerShell)
.venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt

# 启动开发服务器
python app/main.py
```

后端服务将在 http://localhost:18000 启动，支持代码热重载。

### 前端开发

前端项目使用 Vite 作为构建工具，开发体验流畅。进入 `frontend` 目录：

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build
```

如果需要修改后端 API 地址，请编辑 `src/services/api.ts` 文件中的 `API_URL` 配置。

## 📦 项目结构

CharMing Reader 采用前后端分离的架构设计，代码组织清晰且易于维护。以下是项目的主要目录结构：

```
CharMing-Reader/
├── backend/                    # Python 后端服务
│   ├── app/
│   │   ├── agents/            # Agent 逻辑与流程编排
│   │   ├── api/               # RESTful API 路由定义
│   │   ├── core/              # 核心配置模块 (Config, DB, Logger)
│   │   ├── dao/               # 数据访问对象层
│   │   ├── models/            # 数据模型定义 (SQLAlchemy & Pydantic)
│   │   ├── rag/               # RAG 引擎核心 (混合检索、向量化)
│   │   ├── services/          # 业务逻辑层 (文档处理、知识库管理)
│   │   ├── skills/            # Skills 系统 (动态能力扩展)
│   │   └── tools/             # Agent 工具集 (搜索、检索器)
│   ├── alembic/               # 数据库迁移管理
│   ├── uploads/               # 原始文件上传目录
│   ├── uploads_rag/           # RAG 处理后的文档存储
│   ├── requirements.txt       # Python 依赖清单
│   └── Dockerfile             # 后端容器镜像配置
├── frontend/                   # React 前端应用
│   ├── src/
│   │   ├── components/        # UI 组件库
│   │   ├── services/          # API 服务封装
│   │   ├── assets/            # 静态资源
│   │   └── lib/               # 工具函数
│   ├── package.json           # Node.js 依赖配置
│   └── vite.config.ts         # Vite 构建配置
├── docs/                       # 项目文档
├── docker-compose.yml         # 容器编排配置
└── README.md                  # 项目说明文档
```

## 🔧 常用操作

在日常开发和维护过程中，以下命令能够帮助你更高效地管理 CharMing Reader：

**查看服务日志**：当需要排查问题或监控服务状态时，可以实时查看容器日志。`docker-compose logs -f backend` 会持续输出后端服务的日志信息，按 Ctrl+C 可以退出日志查看模式。

**重启特定服务**：如果修改了后端代码并需要重启服务使更改生效，使用 `docker-compose restart backend` 命令。这比完全停止并重新启动所有服务要快得多。

**重新构建镜像**：当 Dockerfile 或依赖文件发生变化时，需要重新构建 Docker 镜像。执行 `docker-compose up -d --build` 会强制重新构建镜像并启动服务。

**停止所有服务**：完成开发工作后，可以使用 `docker-compose down` 停止并移除所有容器。如果想同时清除数据卷，加上 `-v` 参数：`docker-compose down -v`（注意这会删除数据库中的所有数据）。

**进入容器调试**：有时需要在容器内部执行命令进行调试，可以使用 `docker-compose exec backend bash` 进入后端容器的命令行环境，在容器内可以运行 Python 脚本或查看文件系统。

**查看数据库状态**：确认数据库表是否正确创建，可以连接到 PostgreSQL 容器：`docker-compose exec db psql -U jensenlyz -d paperagent`，然后使用 `\dt` 命令列出所有表。

**清理系统**：长期开发可能会产生大量未使用的 Docker 镜像和容器，使用 `docker system prune -a` 可以清理这些无用资源，释放磁盘空间（请谨慎使用，确保不会删除重要数据）。

## 🌐 API 文档

CharMing Reader 的后端基于 FastAPI 构建，自动生成交互式 API 文档。启动后端服务后，你可以通过以下地址访问完整的 API 文档和在线测试界面：

- **Swagger UI**: http://localhost:18000/docs
- **ReDoc**: http://localhost:18000/redoc

这些文档涵盖了所有可用的端点，包括文档上传、知识库管理、RAG 问答等核心功能的详细说明和请求示例。

## 💡 使用建议

为了获得最佳的 CharMing Reader 使用体验，建议在上传论文前先创建分类清晰的知识库，比如按研究方向或论文主题分组。这样可以在问答时针对特定领域进行检索，提高回答的准确性。在提问时，尽量使用具体、明确的问题描述，比如"论文中提出的算法相比传统方法有哪些改进"比"这篇论文怎么样"能获得更有价值的回答。

如果遇到检索结果不够理想的情况，可以尝试调整混合检索的权重参数，或者在知识库设置中修改文档分块的大小和重叠比例。对于重要的学术会议论文或期刊文章，建议保留原始 PDF 文件的完整版本，因为某些复杂的公式、图表可能在文本提取过程中有所损失。

在使用多模型切换功能时，可以根据任务特点选择合适的模型：GPT-4o 适合需要深度理解的复杂问答，Deepseek 在代码相关论文分析上表现出色，而通义千问则在中文论文处理方面有独特优势。定期备份知识库数据和配置文件，确保研究成果的安全性。

## 🤝 贡献指南

CharMing Reader 是一个开源项目，欢迎社区的每一位成员参与贡献。无论是提交 Bug 报告、功能建议，还是直接提交代码改进，都将让这个项目变得更好。如果你发现了问题或有改进想法，请在 GitHub Issues 中提交详细描述。对于代码贡献，请遵循项目的代码风格规范，并在提交 Pull Request 前确保所有测试通过。

## 📄 开源协议

CharMing Reader 采用 MIT 协议开源，你可以自由地使用、修改和分发本项目，无论是个人学习还是商业用途。

## ❤️ 致谢

感谢所有为这个项目提供灵感和支持的人，特别是那位让科研变得更加迷人的她。

---

<div align="center">

**Research made Charming. 让科研变得迷人。**

*如果 CharMing Reader 对你的研究有所帮助，请给我们一个 ⭐️*

</div>

