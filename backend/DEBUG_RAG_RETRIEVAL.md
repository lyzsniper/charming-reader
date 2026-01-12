# RAG 检索问题调试指南

## 问题描述

上传文档后，模型无法检索到文档内容，返回"抱歉，我无法直接访问或检索您上传的文档内容"。

## 已实施的修复

### 1. **增强的索引刷新**
   - 在存储节点后立即刷新 Elasticsearch 索引
   - 支持多种方式访问 Elasticsearch 客户端
   - 如果客户端刷新失败，自动尝试 HTTP API 刷新

### 2. **增加等待时间**
   - 向量化完成后等待 2 秒（从 1 秒增加）
   - 执行验证查询后，如果未找到节点，再等待 1 秒
   - 在存储函数内部额外等待 0.5 秒

### 3. **验证查询**
   - 在开始对话前，执行一个测试查询验证数据是否可检索
   - 如果验证失败，会记录警告并额外等待

### 4. **详细的调试日志**
   - 记录每个节点的 metadata（包括 session_id 和 document_id）
   - 记录查询时的过滤器信息
   - 记录找到的节点数量和详细信息
   - 如果未找到节点，记录可能的原因

### 5. **Elasticsearch 数据验证**
   - 在应用过滤器前，直接查询 Elasticsearch 验证数据是否存在
   - 记录匹配的文档数量

## 调试步骤

### 1. 查看后端日志

上传文档后，查看后端日志中的以下关键信息：

```
✓ 自动创建新会话: session_id=xxx
✓ Elasticsearch 索引已刷新: paper_index, 节点数: N
  示例节点 metadata: session_id=xxx, document_id=xxx
向量化完成，等待 ES 索引刷新后开始查询，session_id=xxx
✓ 验证查询完成: session_id=xxx, 找到 N 个节点
应用会话过滤器: session_id=xxx
  ✓ 验证: Elasticsearch 中找到 N 个匹配 session_id=xxx 的文档
执行RAG检索（临时文件）: session_id=xxx, top_k=5
  查询返回 N 个节点
```

### 2. 检查关键点

#### 问题 1: 验证查询未找到节点

**日志示例：**
```
⚠️ 警告: 验证查询未找到任何节点，可能数据尚未完全索引
```

**可能原因：**
- Elasticsearch 索引刷新延迟
- session_id 未正确存储到 metadata

**解决方法：**
- 检查日志中是否有 "示例节点 metadata: session_id=xxx"
- 如果 session_id 为 None 或缺失，说明存储时未正确传递

#### 问题 2: Elasticsearch 验证查询失败

**日志示例：**
```
⚠️ 验证: Elasticsearch 中未找到匹配 session_id=xxx 的文档！
```

**可能原因：**
- session_id 在 metadata 中的字段名不匹配
- 数据未正确存储到 Elasticsearch

**解决方法：**
- 检查 Elasticsearch 中的实际数据：
  ```bash
  curl -X GET "http://localhost:39200/paper_index/_search?q=metadata.session_id:xxx"
  ```

#### 问题 3: RAG 查询返回 0 个节点

**日志示例：**
```
⚠️ 未找到任何节点！可能的原因：
  1. session_id=xxx 不匹配
  2. 数据尚未完全索引到 Elasticsearch
  3. 查询文本与文档内容不匹配
```

**解决方法：**
- 检查过滤器是否正确应用
- 检查查询文本是否与文档内容相关
- 尝试使用更通用的查询词（如 "document" 或 "*"）

## 手动验证步骤

### 1. 检查 Elasticsearch 中的数据

```bash
# 查看索引中的所有文档
curl -X GET "http://localhost:39200/paper_index/_search?pretty"

# 按 session_id 查询
curl -X GET "http://localhost:39200/paper_index/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "term": {
      "metadata.session_id": "YOUR_SESSION_ID"
    }
  }
}'
```

### 2. 检查数据库中的文档记录

```sql
-- 查看临时文档
SELECT id, original_filename, is_temporary, session_id 
FROM documents 
WHERE is_temporary = true 
ORDER BY upload_date DESC 
LIMIT 10;
```

### 3. 测试 RAG 查询

使用 Python 脚本直接测试：

```python
from services.rag_service import RAGService

result = RAGService.query(
    question="文档的主要内容是什么？",
    knowledge_base_ids=None,
    session_id="YOUR_SESSION_ID",
    similarity_top_k=5
)

print(f"找到 {len(result.get('sources', []))} 个来源")
for source in result.get('sources', []):
    print(f"  - {source['content'][:100]}...")
    print(f"    session_id: {source['metadata'].get('session_id')}")
```

## 常见问题排查

### Q1: 为什么验证查询找到了节点，但实际查询找不到？

**A:** 可能的原因：
1. 查询文本与文档内容不匹配（相似度太低）
2. 过滤器配置有问题
3. 重排序导致结果被过滤

**解决方法：**
- 尝试使用更通用的查询词
- 检查日志中的相似度分数
- 临时禁用重排序测试

### Q2: session_id 在 metadata 中，但查询时找不到？

**A:** 可能的原因：
1. Elasticsearch 的字段类型不匹配
2. 过滤器语法不正确

**解决方法：**
- 检查 Elasticsearch mapping 中 `metadata.session_id` 的类型
- 尝试使用不同的过滤器类型

### Q3: 数据已存储，但索引刷新后仍查询不到？

**A:** 可能的原因：
1. 索引刷新未成功执行
2. 需要更长的等待时间

**解决方法：**
- 检查日志中是否有索引刷新的成功消息
- 手动刷新索引：
  ```bash
  curl -X POST "http://localhost:39200/paper_index/_refresh"
  ```

## 下一步

如果问题仍然存在，请提供：

1. **后端日志**（从上传文件到查询失败的完整日志）
2. **session_id**（用于验证数据）
3. **Elasticsearch 查询结果**（使用上面的 curl 命令）
4. **数据库查询结果**（文档记录）

这些信息将帮助进一步诊断问题。
