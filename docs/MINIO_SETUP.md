# MinIO 对象存储集成说明

## 📦 概述

PaperAgent 已集成 **MinIO 对象存储**，用于轻量化、分布式的文件存储管理。

## 🚀 快速启动

### 1. 安装依赖

```bash
cd backend
pip install minio==7.2.14
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 启动服务

使用 Docker Compose 一键启动所有服务（PostgreSQL + Elasticsearch + MinIO）：

```bash
cd C:\App\Coding\PaperAgent
docker-compose up -d
```

### 3. 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

### 4. 访问 MinIO Web 控制台

- **地址**: http://localhost:39001
- **用户名**: `paperagent`
- **密码**: `paperagent123`

在控制台中可以：
- 查看所有上传的文件
- 手动上传/下载文件
- 管理存储桶（Bucket）

## 📊 架构说明

### 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| MinIO API | 39000 | 对象存储 API 端口 |
| MinIO Console | 39001 | Web 管理界面 |
| PostgreSQL | 35432 | 数据库 |
| Elasticsearch | 39200 | 向量搜索 |
| Backend API | 18000 | FastAPI 服务 |

### 存储桶（Bucket）

- **名称**: `paperagent-files`
- **自动创建**: 应用启动时自动创建

### 文件命名规则

- **上传**: 用户上传 `paper.pdf`
- **存储**: MinIO 存储为 `{uuid}.pdf`（如 `a1b2c3d4-...-xyz.pdf`）
- **数据库**: 记录原始文件名和 MinIO 对象名

示例：
```
original_filename: "深度学习论文.pdf"
storage_object_name: "7f3a2b1c-4d5e-6f7g-8h9i-0j1k2l3m4n5o.pdf"
```

## 🔄 文件上传流程

```
用户上传文件
    ↓
存储到 MinIO (UUID命名)
    ↓
创建数据库记录
    ↓
异步处理: 从 MinIO 下载 → 向量化 → 存储到 PG+ES
    ↓
删除临时文件
```

## 💻 代码示例

### 上传文件（API）

```bash
curl -X POST "http://localhost:18000/api/upload" \
  -F "file=@paper.pdf" \
  -F "knowledge_base_ids=kb-uuid-1,kb-uuid-2"
```

### 使用存储服务（代码）

```python
from services.storage_service import get_storage_service

storage = get_storage_service()

# 上传文件
object_name, file_size = storage.upload_file(
    file_data=file_stream,
    original_filename="paper.pdf",
    content_type="application/pdf"
)

# 下载文件
file_data = storage.download_file(object_name)

# 获取预签名 URL（临时访问链接）
url = storage.get_file_url(object_name, expires_in=3600)

# 删除文件
storage.delete_file(object_name)
```

## 🛠️ 配置说明

在 `backend/app/core/config.py` 中配置 MinIO：

```python
# MinIO Object Storage
MINIO_ENDPOINT: str = "localhost:39000"       # MinIO 地址
MINIO_ACCESS_KEY: str = "paperagent"          # 访问密钥
MINIO_SECRET_KEY: str = "paperagent123"       # 私钥
MINIO_BUCKET: str = "paperagent-files"        # 存储桶名称
MINIO_SECURE: bool = False                     # 是否使用 HTTPS
```

环境变量覆盖（可选）：

```bash
export MINIO_ENDPOINT="localhost:39000"
export MINIO_ACCESS_KEY="paperagent"
export MINIO_SECRET_KEY="paperagent123"
export MINIO_BUCKET="paperagent-files"
export MINIO_SECURE="false"
```

## 🔍 数据库表结构变更

### documents 表新增字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `original_filename` | String | 原始文件名（用户上传的文件名） |
| `storage_object_name` | String | MinIO 对象名称（UUID.pdf） |
| `file_size` | Integer | 文件大小（字节） |
| `content_type` | String | 文件 MIME 类型 |

### 兼容性

`filename` 属性现在映射到 `original_filename`，旧代码无需修改。

## 🐛 故障排查

### 1. MinIO 连接失败

```
✗ MinIO 存储桶创建失败: S3 Error
```

**解决方案**：
- 检查 MinIO 服务是否启动：`docker ps | grep minio`
- 检查端口是否被占用：`netstat -ano | findstr 39000`
- 查看 MinIO 日志：`docker logs paperagent-minio`

### 2. 文件上传失败

**解决方案**：
- 确认存储桶已创建：访问 http://localhost:39001
- 检查 API Key 配置
- 查看后端日志

### 3. 向量化处理失败

**解决方案**：
- 检查临时文件目录权限
- 确认 PDF 处理依赖已安装：`pip install markitdown[pdf]`

## 🎯 优势总结

| 对比项 | 本地文件系统 | MinIO 对象存储 |
|--------|-------------|---------------|
| 分布式支持 | ❌ | ✅ |
| 自动备份 | ❌ 手动 | ✅ 可配置 |
| 文件去重 | ❌ | ✅ |
| Web 管理界面 | ❌ | ✅ |
| S3 兼容 | ❌ | ✅ |
| 扩展性 | ⚠️ 有限 | ✅ 优秀 |
| 部署复杂度 | ✅ 简单 | ⚠️ 需 Docker |

## 🔄 迁移到云端 S3（可选）

MinIO 与 AWS S3 完全兼容，后续可无缝迁移：

```python
# 只需修改配置
MINIO_ENDPOINT = "s3.amazonaws.com"
MINIO_ACCESS_KEY = "your-aws-access-key"
MINIO_SECRET_KEY = "your-aws-secret-key"
MINIO_BUCKET = "your-s3-bucket"
MINIO_SECURE = True
```

代码无需修改！

## 📝 注意事项

1. **生产环境**：请修改默认的访问密钥和私钥
2. **数据持久化**：MinIO 数据存储在 Docker Volume `minio_data` 中
3. **备份策略**：定期备份 MinIO 数据和 PostgreSQL 数据库
4. **文件清理**：删除文档时，需要同时删除 MinIO 中的文件（已在代码中实现）

## 🎓 扩展学习

- [MinIO 官方文档](https://min.io/docs/minio/linux/index.html)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [S3 API 兼容性](https://min.io/docs/minio/linux/operations/concepts/s3-compatibility.html)

