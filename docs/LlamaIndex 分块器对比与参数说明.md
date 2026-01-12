## LlamaIndex 分块器对比与参数说明

### 1. **SentenceSplitter**（句子分块器）
**特点**：按句子边界分块，保持语义完整性

**可控制参数**：
- `chunk_size` (int): 每个分块的 token 数量，默认 `1024`
- `chunk_overlap` (int): 分块之间的重叠 token 数，默认 `200`
- `separator` (str): 用于分割单词的字符，默认 `' '`
- `paragraph_separator` (str): 段落分隔符，默认 `'\n\n\n'`
- `secondary_chunking_regex` (str): 备用正则表达式，用于句子分割，默认 `'[^,.;。？！]+[,.;。？！]?|[,.;。？！]'`

**适用场景**：通用文本、需要保持句子完整性的文档

---

### 2. **TokenTextSplitter**（Token 分块器）
**特点**：按 token 数量分块，块大小一致

**可控制参数**：
- `chunk_size` (int): 每个分块的 token 数量
- `chunk_overlap` (int): 分块之间的重叠 token 数
- `separator` (str): 用于分割的字符，默认 `' '`

**适用场景**：需要精确控制 token 数量、有 token 限制的模型

---

### 3. **CodeSplitter**（代码分块器）
**特点**：按编程语言语法分块，保持代码结构

**可控制参数**：
- `language` (str): 编程语言（如 `'python'`, `'javascript'`, `'java'` 等）
- `chunk_lines` (int): 每个分块的行数
- `chunk_lines_overlap` (int): 分块之间重叠的行数
- `max_chars` (int): 每个分块的最大字符数

**适用场景**：代码文档、技术文档、源代码分析

---

### 4. **MarkdownNodeParser**（Markdown 分块器）
**特点**：按 Markdown 结构（标题、段落等）分块，保留格式

**可控制参数**：
- 无需特殊参数，自动识别 Markdown 结构

**适用场景**：Markdown 文档、技术文档、README 文件

---

### 5. **SemanticSplitterNodeParser**（语义分块器）
**特点**：基于嵌入相似度自适应分块，确保语义连贯

**可控制参数**：
- `buffer_size` (int): 评估语义相似度时分组句子数量
- `breakpoint_percentile_threshold` (float): 确定分块断点的百分位阈值（如 `95`）
- `embed_model` (BaseEmbedding): 用于相似度计算的嵌入模型（必需）
- `sentence_splitter` (Optional[Callable]): 将文本分割为句子的函数（可选）
- `include_metadata` (bool): 是否在节点中包含元数据
- `include_prev_next_rel` (bool): 是否包含前后关系

**适用场景**：需要语义连贯性、复杂文档、学术论文

---

### 6. **SentenceWindowNodeParser**（句子窗口分块器）
**特点**：将文档分割为单个句子，并在元数据中包含周围句子上下文

**可控制参数**：
- `window_size` (int): 每侧捕获的句子数量（如 `3` 表示前后各 3 句）
- `window_metadata_key` (str): 存储周围句子的元数据键，默认 `"window"`
- `original_text_metadata_key` (str): 存储原始句子的元数据键，默认 `"original_sentence"`
- `sentence_splitter` (Optional[Callable]): 句子分割函数（可选）
- `include_metadata` (bool): 是否包含元数据
- `include_prev_next_rel` (bool): 是否包含前后关系

**适用场景**：需要精确句子级检索、问答系统、需要上下文窗口的场景

---

### 7. **HierarchicalNodeParser**（层级分块器）
**特点**：创建层级结构，支持父子关系，适用于多粒度检索

**可控制参数**：
- `chunk_sizes` (List[int]): 不同层级的分块大小列表（如 `[2048, 512, 128]`）

**适用场景**：需要多粒度检索、长文档、复杂文档结构

---

### 8. **HTMLNodeParser**（HTML 分块器）
**特点**：解析 HTML，提取指定标签的文本

**可控制参数**：
- `tags` (List[str]): 要提取文本的 HTML 标签列表，默认 `["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section"]`

**适用场景**：网页内容、HTML 文档

---

### 9. **JSONNodeParser**（JSON 分块器）
**特点**：解析 JSON 内容

**可控制参数**：
- 无需特殊参数

**适用场景**：JSON 数据、API 响应、结构化数据

---

### 10. **SimpleFileNodeParser**（简单文件分块器）
**特点**：根据文件类型自动选择合适的分块器

**可控制参数**：
- 无需特殊参数，自动识别文件类型

**适用场景**：混合文件类型、自动化处理

---

## 选择建议

| 文档类型 | 推荐分块器 | 原因 |
|---------|-----------|------|
| 通用文本 | `SentenceSplitter` | 平衡语义与性能 |
| 代码文档 | `CodeSplitter` | 保持代码结构 |
| Markdown | `MarkdownNodeParser` | 保留格式结构 |
| 学术论文 | `SemanticSplitterNodeParser` | 语义连贯性 |
| 精确问答 | `SentenceWindowNodeParser` | 句子级检索 |
| 长文档 | `HierarchicalNodeParser` | 多粒度检索 |
| HTML 网页 | `HTMLNodeParser` | 提取结构化内容 |
