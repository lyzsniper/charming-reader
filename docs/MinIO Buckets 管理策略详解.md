## 📦 MinIO Buckets 管理策略详解

### **1. Buckets 是什么？有什么作用？**

**Bucket（存储桶）** 是 MinIO/S3 中的顶层存储容器，可以理解为：

```
MinIO 实例
  ├─ Bucket 1 (paperagent-files)     ← 顶层容器
  │   ├─ a1b2c3d4-...-xyz.pdf        ← 对象（文件）
  │   ├─ e5f6g7h8-...-abc.pdf
  │   └─ ...
  ├─ Bucket 2 (user-avatars)
  │   └─ ...
  └─ Bucket 3 (backups)
      └─ ...
```

**作用：**
- 🗂️ **数据组织**：按业务逻辑分类存储（如：文档、图片、备份）
- 🔒 **权限隔离**：不同 Bucket 可以设置不同的访问策略
- 📊 **资源管理**：可以为不同 Bucket 设置存储配额、生命周期规则
- 🌍 **地域管理**：可以指定 Bucket 存储在不同的地域（多数据中心）

---

### **2. MinIO 有默认 Buckets 吗？**

❌ **没有！** MinIO 刚部署时是**空的**，没有任何 Bucket。

**这意味着：**
- 第一次使用前必须先创建 Bucket
- 如果尝试上传文件到不存在的 Bucket，会报错：`NoSuchBucket`

---

### **3. 我们的代码如何处理？**

在 `backend/app/services/storage_service.py` 中，我已经实现了**自动创建 Bucket** 的逻辑：

```python
def __init__(self):
    """初始化 MinIO 客户端"""
    self.client = Minio(...)
    self.bucket_name = settings.MINIO_BUCKET  # "paperagent-files"
    self._ensure_bucket_exists()  # ← 自动创建 Bucket
    
def _ensure_bucket_exists(self):
    """确保存储桶存在"""
    if not self.client.bucket_exists(self.bucket_name):
        self.client.make_bucket(self.bucket_name)
        logger.info(f"✓ MinIO 存储桶已创建: {self.bucket_name}")
    else:
        logger.info(f"✓ MinIO 存储桶已存在: {self.bucket_name}")
```

**触发时机：**
- 第一次调用 `get_storage_service()` 时
- 通常是在**第一次上传文件**时

---

### **4. 刚部署的 MinIO，文件传到哪里了？**

#### **场景 A：使用我们的 PaperAgent 上传接口**

```bash
curl -X POST "http://localhost:18000/api/upload" -F "file=@paper.pdf"
```

**流程：**
```
1. 调用 upload_pdf() API
2. 触发 get_storage_service()
3. 检测到 Bucket 不存在
4. 自动创建 "paperagent-files" Bucket  ← 这里！
5. 上传文件到该 Bucket
```

**结果：** 文件存储在 `paperagent-files` bucket 中

---

#### **场景 B：直接使用 MinIO API（未通过我们的代码）**

如果你直接使用 MinIO Python SDK 或 Web 控制台上传文件到**不存在的 Bucket**：

```python
from minio import Minio
client = Minio("localhost:39000", ...)
client.put_object("non-existent-bucket", "file.pdf", data)  # ❌ 报错！
```

**错误：**
```
S3Error: Code: NoSuchBucket, Message: The specified bucket does not exist
```

**解决方案：** 先手动创建 Bucket

---

### **5. 如何查看和管理 Buckets？**

#### **方法 1：Web 控制台（推荐）**

访问 http://localhost:39001

- 用户名：`paperagent`
- 密码：`paperagent123`

在控制台中你可以：
- ✅ 查看所有 Buckets
- ✅ 创建/删除 Buckets
- ✅ 设置访问策略（Public/Private）
- ✅ 查看 Bucket 中的所有文件
- ✅ 手动上传/下载文件

#### **方法 2：使用 MinIO Client (mc)**

```bash
# 安装 mc
# Windows: scoop install minio-client
# Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc

# 配置别名
mc alias set local http://localhost:39000 paperagent paperagent123

# 列出所有 Buckets
mc ls local

# 创建 Bucket
mc mb local/new-bucket

# 列出 Bucket 中的文件
mc ls local/paperagent-files
```

#### **方法 3：Python 代码**

```python
from services.storage_service import get_storage_service

storage = get_storage_service()

# 列出所有 Buckets
buckets = storage.client.list_buckets()
for bucket in buckets:
    print(f"Bucket: {bucket.name}, Created: {bucket.creation_date}")

# 列出 Bucket 中的对象
objects = storage.client.list_objects(storage.bucket_name)
for obj in objects:
    print(f"File: {obj.object_name}, Size: {obj.size}")
```

---

### **6. Bucket 管理最佳实践**

#### **策略 A：单一 Bucket（我们当前的方案）** ⭐

```
paperagent-files/
  ├─ uuid1.pdf
  ├─ uuid2.pdf
  └─ uuid3.pdf
```

**优点：**
- ✅ 简单直观
- ✅ 便于管理
- ✅ 适合小型项目

**适用场景：** 文件量 < 100万，单一业务场景

---

#### **策略 B：按知识库分 Bucket**

```
kb-{uuid1}/
  ├─ doc1.pdf
  └─ doc2.pdf
kb-{uuid2}/
  ├─ doc3.pdf
  └─ doc4.pdf
```

**优点：**
- ✅ 逻辑隔离清晰
- ✅ 可以为不同知识库设置不同权限
- ✅ 便于按知识库删除所有文件

**缺点：**
- ❌ Bucket 数量有限制（推荐 < 1000）
- ❌ 管理复杂度增加

---

#### **策略 C：按时间分区（前缀）**

```
paperagent-files/
  ├─ 2026/01/uuid1.pdf
  ├─ 2026/01/uuid2.pdf
  └─ 2026/02/uuid3.pdf
```

**优点：**
- ✅ 便于按时间查询和清理
- ✅ 符合数据归档需求

**实现：** 修改 `storage_service.py` 中的 `upload_file()`：

```python
from datetime import datetime

object_name = f"{datetime.now().strftime('%Y/%m')}/{uuid.uuid4()}.{file_extension}"
```

---

### **7. 你当前的配置**

根据我们的代码：

**配置文件：** `backend/app/core/config.py`
```python
MINIO_BUCKET: str = "paperagent-files"
```

**结果：**
- 所有上传的文件都存储在 `paperagent-files` bucket
- 第一次上传时自动创建
- 文件命名格式：`{uuid}.pdf`

**验证方式：**
1. 启动服务后上传一个文件
2. 访问 http://localhost:39001
3. 登录后在左侧菜单点击 "Buckets"
4. 你会看到 `paperagent-files` bucket
5. 点击进入可以看到所有上传的文件（以 UUID 命名）

---

### **8. 常见问题**

**Q: 可以改 Bucket 名称吗？**
A: 可以！修改 `config.py` 中的 `MINIO_BUCKET` 即可，但已有数据需要迁移。

**Q: 一个文件可以存在多个 Buckets 吗？**
A: 可以，但需要上传多次。我们的架构是：一个文件对应一个 MinIO 对象。

**Q: 删除 Bucket 会怎样？**
A: Bucket 中的所有文件都会被删除（如果 Bucket 为空才能删除）。

**Q: Bucket 数量有限制吗？**
A: MinIO 理论上无限制，但推荐 < 10,000 个。

需要我帮你实现其他 Bucket 管理策略吗（如按知识库分 Bucket）？