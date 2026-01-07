# PaperAgent 项目启动与部署指南

本文档总结了 PaperAgent 项目的开发环境启动方式（前后端分离）以及容器化部署流程。针对后端开发，引入了 `uv` 作为新一代的高性能包管理工具。

## 1. 开发环境启动 (Development)

开发模式下，前端和后端服务需要分别独立启动。

### 1.1 后端服务 (Backend)

后端目前位于 `backend/` 目录，依赖管理推荐从 `pip` 迁移至 `uv` 以获得更快的安装速度和更好的依赖解析体验。

#### 步骤 1: 安装 uv
如果尚未安装 `uv`，请在终端（PowerShell）中执行以下命令进行安装：
```powershell
# Windows 安装
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
*安装完成后，请关闭并重新打开终端以使环境变量生效。*

#### 步骤 2: 创建虚拟环境并安装依赖
进入 `backend` 目录，使用 `uv` 创建虚拟环境并同步依赖。

```bash
cd backend

# 1. 创建虚拟环境 (默认创建在 .venv 目录)
uv venv

# 2. 激活虚拟环境 (Windows PowerShell)
.venv\Scripts\activate

# 3. 安装依赖 (使用 uv pip 接口读取 requirements.txt)
uv pip install -r requirements.txt
```

#### 步骤 3: 启动后端服务
依赖安装完成后，即可启动 FastAPI 服务：

```bash
# 确保虚拟环境已激活
python main.py
```
*注：后端服务通常运行在 `http://localhost:8000` (具体端口视 main.py 配置而定)。*

---

### 1.2 前端服务 (Frontend)

前端位于 `frontend/` 目录，使用 Vite 构建，包管理器为 `pnpm`。

#### 步骤 1: 安装依赖
进入 `frontend` 目录并安装依赖：

```bash
cd frontend
pnpm install
```

#### 步骤 2: 启动开发服务器
```bash
pnpm dev
```
*注：前端服务通常运行在 `http://localhost:5173`，并在控制台显示访问地址。*

---

## 2. 容器化部署 (Deployment)

项目根目录包含 `docker-compose.yml`，可用于一键部署完整的应用栈（包含数据库、后端、前端等所有定义的服务）。

### 启动命令
在项目根目录下执行：

```bash
# 后台启动所有服务
docker-compose up -d

# 查看服务日志
docker-compose logs -f
```

### 停止命令
```bash
# 停止并移除容器
docker-compose down
```

### 手动启动独立服务 (PG, ES, Redis)

如果不需要启动整个编排栈，仅需单独启动基础服务，可使用以下命令。

#### 1. PostgreSQL (pgvector)
*端口: 35432*

**多行格式 (CMD/PowerShell)**:
```bash
docker run -d ^
  --name paperagent-db ^
  -p 35432:5432 ^
  -e POSTGRES_USER=jensenlyz ^
  -e POSTGRES_PASSWORD=1014 ^
  -e POSTGRES_DB=paperagent ^
  -v postgres_data:/var/lib/postgresql/data ^
  pgvector/pgvector:pg16
```

**单行格式 (推荐)**:
```bash
docker run -d --name paperagent-db -p 35432:5432 -e POSTGRES_USER=jensenlyz -e POSTGRES_PASSWORD=1014 -e POSTGRES_DB=paperagent -v postgres_data:/var/lib/postgresql/data pgvector/pgvector:pg16
```

#### 2. Elasticsearch
*端口: 39200*

**多行格式**:
```bash
docker run -d ^
  --name paperagent-es ^
  -p 39200:9200 ^
  -e "discovery.type=single-node" ^
  -e "xpack.security.enabled=false" ^
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" ^
  -v es_data:/usr/share/elasticsearch/data ^
  elasticsearch:8.11.1
```
docker network create paperagent-net
docker run -d --name paperagent-es \
  --net paperagent-net \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.1

docker run -d --name paperagent-kibana \
  --net paperagent-net \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://paperagent-es:9200" \
  kibana:8.11.1


  docker run -d --name paperagent-minio -p 39000:9000 -p 39001:9001 -e MINIO_ROOT_USER=paperagent -e MINIO_ROOT_PASSWORD=paperagent123 -v minio_data:/data --network paperagent-net --health-cmd "curl -f http://localhost:9000/minio/health/live" --health-interval 30s --health-timeout 20s --health-retries 3 minio/minio:latest server /data --console-address ":9001"
**单行格式**:
```bash
docker run -d --name paperagent-es --net paperagent-net -p 39200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" -v es_data:/usr/share/elasticsearch/data elasticsearch:8.11.1

docker run -d --name paperagent-kibana --net paperagent-net -p 35601:5601 -e "ELASTICSEARCH_HOSTS=http://paperagent-es:9200" kibana:8.11.1

```

#### 3. Redis
*端口: 6379*

**多行格式**:
```bash
docker run -d ^
  --name paperagent-redis ^
  -p 16379:6379 ^
  redis:latest
```

**单行格式**:
```bash
docker run -d --name paperagent-redis -p 16379:6379 redis:latest
```

---

## 3. UV 使用指南 (附录)

`uv` 是一个用 Rust 编写的极速 Python 包安装器和解析器。它的主要优势是**速度极快**（通常比 pip 快 10-100 倍）且内置了虚拟环境管理功能。

以下是针对本项目开发场景的常用命令速查：

### 基础操作 (兼容 pip 习惯)

如果你习惯了 `requirements.txt` 的工作流，`uv` 可以作为 `pip` 的直接替代品（Drop-in Replacement）：

| 操作 | 传统 pip 命令 | **推荐 uv 命令** | 说明 |
| :--- | :--- | :--- | :--- |
| **创建虚拟环境** | `python -m venv venv` | **`uv venv`** | 默认创建名为 `.venv` 的环境，速度极快 |
| **安装依赖文件** | `pip install -r requirements.txt` | **`uv pip install -r requirements.txt`** | 极速安装所有依赖 |
| **安装单个包** | `pip install requests` | **`uv pip install requests`** | 安装包到当前环境 |
| **升级包** | `pip install -U requests` | **`uv pip install -U requests`** | 升级指定包 |
| **导出依赖** | `pip freeze > requirements.txt` | **`uv pip freeze > requirements.txt`** | 导出当前环境所有包 |

### 进阶操作 (项目级管理)

`uv` 也支持类似 `npm`/`pnpm` 的项目级管理（通过 `pyproject.toml`），这是更现代的做法。如果想将项目升级为这种管理方式，可以参考以下流程：

1.  **初始化项目**:
    ```bash
    uv init
    ```
    *这会生成 `pyproject.toml` 文件。*

2.  **添加依赖**:
    ```bash
    uv add fastapi uvicorn
    ```
    *这会自动安装包并将依赖写入 `pyproject.toml` 和 `uv.lock`，类似 `pnpm add`。*

3.  **运行脚本**:
    ```bash
    uv run main.py
    ```
    *`uv run` 会自动检测环境，甚至可以在没有手动激活虚拟环境的情况下，自动使用项目环境运行脚本。*

### 常用技巧

*   **清理缓存**: 如果遇到奇怪的安装问题，可以使用 `uv cache clean`。
*   **指定 Python 版本**: `uv venv --python 3.10` 可以快速创建一个指定 Python 版本的虚拟环境（uv 会自动下载需要的 Python 版本，无需系统预装）。

