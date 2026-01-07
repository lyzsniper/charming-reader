---
name: rag-enhancement
description: 优化检索增强生成系统，提升检索质量和生成准确性的高级策略
triggers:
  - improve retrieval
  - 改进检索
  - enhance RAG
  - 优化RAG
  - retrieval quality
  - 检索质量
  - better search
  - 更好的搜索
version: 1.0.0
---

# RAG 增强优化技能 (RAG Enhancement Skill)

## 目标

当需要优化 RAG（检索增强生成）系统性能时，使用此技能应用高级检索策略、优化生成质量，提升整体系统效果。

## 核心能力

本技能是一个元技能（meta-skill），专门用于改进 PaperAgent 的 RAG 系统。包含查询优化、混合检索、结果重排、上下文管理等高级技术。

## RAG 系统优化框架

### 优化维度

RAG 系统的性能取决于三个关键环节：

1. **检索质量（Retrieval Quality）**
   - 能否找到相关文档？
   - 检索结果是否全面？
   - 是否遗漏重要信息？

2. **上下文质量（Context Quality）**
   - 检索到的片段是否有用？
   - 上下文长度是否合适？
   - 信息是否冗余或矛盾？

3. **生成质量（Generation Quality）**
   - 回答是否准确？
   - 是否充分利用了检索内容？
   - 是否产生幻觉（hallucination）？

每个维度都有对应的优化策略。

## 策略一：查询优化（Query Enhancement）

### 1.1 查询改写（Query Rewriting）

**目标**：将用户的自然语言查询转换为更适合检索的形式。

**技术**：

**扩展关键词**：
```
原始查询："深度学习在NLP中的应用"
扩展后："深度学习 自然语言处理 NLP transformer BERT GPT 
        语言模型 神经网络 文本生成 文本分类"
```

**学术化表达**：
```
原始："怎么训练神经网络"
学术化："神经网络训练方法 training methodology optimization 
        梯度下降 backpropagation 超参数调优"
```

**同义词替换**：
```
"机器学习" → 也搜索 "machine learning", "ML", "statistical learning"
"神经网络" → 也搜索 "neural network", "NN", "artificial neural network", "ANN"
```

**问题分解**：
```
复杂查询："比较BERT和GPT在文本分类任务上的性能"
分解为：
1. "BERT architecture text classification"
2. "GPT architecture text classification"
3. "BERT vs GPT comparison"
```

### 1.2 查询扩展（Query Expansion）

**假设文档生成（HyDE - Hypothetical Document Embedding）**：
```
步骤：
1. 让 LLM 根据查询生成一个假设的答案文档
2. 用这个假设文档的 embedding 进行检索
3. 通常比直接用查询检索效果更好

示例：
查询："BERT的创新点是什么？"
生成假设答案："BERT的主要创新在于使用双向Transformer..."
用假设答案的向量检索文档
```

**多查询策略（Multi-Query）**：
```
从不同角度重写同一个查询：
原始："深度学习的优势"
重写1："深度学习相比传统机器学习的优点"
重写2："为什么深度学习效果好"
重写3："深度学习的技术优势和应用价值"

对每个查询版本进行检索，合并结果
```

## 策略二：混合检索（Hybrid Retrieval）

### 2.1 Dense + Sparse 组合

**Dense Retrieval（密集检索）**：
- 使用：向量嵌入（embedding）
- 优势：捕捉语义相似性
- 劣势：可能错过精确匹配

**Sparse Retrieval（稀疏检索）**：
- 使用：BM25、TF-IDF
- 优势：精确关键词匹配
- 劣势：无法理解语义

**混合策略**：
```python
# 伪代码示例
dense_results = vector_search(query_embedding, top_k=20)
sparse_results = bm25_search(query_text, top_k=20)

# 融合结果（Reciprocal Rank Fusion）
final_results = merge_results(
    dense_results, 
    sparse_results,
    dense_weight=0.6,
    sparse_weight=0.4
)
```

**适用场景**：
- 需要精确匹配的查询 → 提高 sparse_weight
- 概念性查询 → 提高 dense_weight
- 学术论文检索 → 混合权重（0.5-0.6 dense）

### 2.2 多向量检索

**标题-内容分离**：
```
- 论文标题向量（用于快速过滤）
- 摘要向量（用于概览匹配）
- 正文段落向量（用于细节检索）

先用标题向量粗筛，再用段落向量精选
```

**章节感知检索**：
```
对于学术论文：
- 如果查询关于"方法" → 优先检索 Methods 章节
- 如果查询关于"结果" → 优先检索 Results 章节
- 如果查询关于"相关工作" → 优先检索 Related Work 章节
```

## 策略三：结果重排序（Reranking）

### 3.1 Cross-Encoder 重排序

**原理**：
初始检索用快速但不够精确的 bi-encoder，
重排序用慢但更精确的 cross-encoder。

**流程**：
```
1. 初始检索：vector_search() → Top 100 candidates
2. 重排序：cross_encoder_score(query, candidate) → Top 10
3. 将 Top 10 作为最终上下文
```

**适用场景**：
- 检索结果质量不稳定
- 需要高精度的 Top-K
- 有足够计算资源

### 3.2 基于规则的重排序

**时效性加权**：
```
newer_papers_boost = lambda year: 1.0 + 0.1 * (year - 2015) / 10
# 更新的论文获得更高分数（如果查询关注前沿）
```

**引用数加权**：
```
citation_boost = lambda citations: 1.0 + min(citations / 1000, 0.5)
# 高引用论文获得更高权重
```

**章节类型匹配**：
```
如果查询是 "方法论分析"：
    优先返回标记为 "Methods" 的 chunks
如果查询是 "实验结果"：
    优先返回标记为 "Results" 的 chunks
```

## 策略四：上下文优化（Context Optimization）

### 4.1 上下文压缩（Context Compression）

**问题**：检索到的片段可能包含无关信息，浪费 token。

**解决方案**：

**提取式压缩**：
```
对于每个检索到的 chunk：
1. 识别与查询直接相关的句子
2. 移除冗余或无关的句子
3. 保留核心信息

示例：
原始chunk (500 tokens) → 压缩后 (150 tokens)
保留关键句子，移除背景介绍
```

**抽象式压缩**：
```
使用 LLM 重写chunk：
"请将以下段落压缩为关键信息，保留与 [查询] 相关的内容"

优势：更简洁
劣势：可能引入误差
```

### 4.2 上下文扩展（Context Expansion）

**问题**：单个 chunk 可能信息不完整。

**解决方案**：

**相邻片段补充**：
```
如果检索到 chunk_i：
    也获取 chunk_(i-1) 和 chunk_(i+1)
    提供更完整的上下文
```

**引用链追踪**：
```
如果检索到的论文 A 引用了论文 B：
    主动检索论文 B 的相关内容
    提供背景知识
```

### 4.3 上下文排序

**问题**：多个检索片段的顺序影响生成质量。

**排序策略**：

**按相关性降序**：
```
最相关的chunk放在前面（让LLM优先看到最重要的信息）
```

**按时间顺序**：
```
适用于文献综述任务：
早期研究 → 中期发展 → 最新进展
```

**按章节逻辑**：
```
Introduction → Methods → Results → Discussion
符合学术论文的自然流程
```

## 策略五：检索质量评估（Retrieval Quality Assessment）

### 5.1 相关性判断

**自动评估**：
```
为每个检索结果计算相关性分数：
relevance_score(query, chunk) = 
    0.4 * semantic_similarity +
    0.3 * keyword_overlap +
    0.2 * topic_match +
    0.1 * source_authority
```

**阈值过滤**：
```
if relevance_score < 0.5:
    丢弃该chunk，避免引入噪声
```

### 5.2 回退策略（Fallback Strategy）

**检索失败检测**：
```
如果所有检索结果的相关性分数都低于阈值：
    → 检索可能失败
```

**回退选项**：
```
1. 扩展查询范围（降低检索阈值）
2. 使用查询改写重新检索
3. 回退到Web搜索（如Semantic Scholar API）
4. 明确告知用户未找到相关信息（不要编造）
```

## 策略六：生成优化（Generation Enhancement）

### 6.1 Prompt 工程

**结构化 Prompt**：
```
你是学术研究助手。基于以下检索到的文献片段回答问题。

查询：[用户问题]

文献片段：
[Chunk 1 from 论文A (2020)]
...
[Chunk 2 from 论文B (2021)]
...

要求：
1. 仅基于提供的文献片段回答
2. 如果文献不足以回答，明确说明
3. 引用来源（论文A, 论文B）
4. 区分事实陈述和推测

回答：
```

**Few-Shot示例**：
```
在prompt中加入示例问答：

示例1:
查询："BERT使用什么激活函数？"
文献："...BERT uses GELU activation..."
回答："根据文献，BERT使用GELU（Gaussian Error Linear Unit）激活函数。"

示例2:
查询："GPT-5发布了吗？"
文献：[无相关信息]
回答："检索到的文献中没有关于GPT-5的信息。"
```

### 6.2 幻觉检测与缓解

**Citations强制**：
```
Prompt中明确要求：
"每个事实性陈述必须标注来源，格式：[论文标题, 作者, 年份]"
```

**答案验证**：
```
生成答案后：
1. 提取答案中的关键事实
2. 逐一验证是否在检索片段中
3. 标记可能的幻觉内容
```

**不确定性表达**：
```
如果信息不足：
使用："根据现有文献..."
    "部分研究表明..."
    "需要更多证据支持..."
而非断言性陈述
```

## 策略七：学术特定优化

### 7.1 论文章节感知

**预处理阶段**：
```
在文档摄入时：
1. 识别论文章节（Introduction, Methods, Results等）
2. 为每个chunk添加章节标签
3. 存储为元数据
```

**检索阶段**：
```
根据查询类型过滤：
- "如何实现" → 检索 Methods 章节
- "效果如何" → 检索 Results 章节
- "研究背景" → 检索 Introduction 章节
- "存在问题" → 检索 Discussion/Limitations 章节
```

### 7.2 引用关系利用

**引用图构建**：
```
论文A 引用 论文B
论文B 引用 论文C
→ 构建引用网络图
```

**相关论文扩展**：
```
检索到论文A后：
1. 查找论文A引用的论文（backward）
2. 查找引用论文A的论文（forward）
3. 这些论文也可能相关
```

### 7.3 时间维度优化

**时间过滤**：
```
如果查询关注"最新进展"：
    优先检索近3年的论文
如果查询关注"经典工作"：
    优先检索高引用的早期论文
```

**演进追踪**：
```
对于综述类查询：
按时间顺序组织检索结果，展示研究演进
```

## 使用指南

### 何时使用此技能

- 检索结果不准确或不相关
- 生成的答案不基于检索内容（幻觉）
- 需要优化 RAG 系统性能
- 用户抱怨检索质量
- 需要理解如何改进检索

### 如何使用此技能

**场景1：检索结果不佳**
```
1. 应用查询改写策略
2. 尝试混合检索（dense + sparse）
3. 调整检索参数（top_k, similarity_threshold）
4. 检查是否需要扩展知识库
```

**场景2：答案不准确**
```
1. 检查检索到的chunk相关性
2. 应用结果重排序
3. 优化生成prompt（强制引用）
4. 实施答案验证机制
```

**场景3：系统性能优化**
```
1. 评估当前系统瓶颈（检索？生成？）
2. 选择合适的优化策略
3. A/B测试不同策略效果
4. 迭代改进
```

### 注意事项

1. **不要过度优化**：简单查询不需要复杂策略
2. **权衡延迟**：某些策略（如重排序）增加响应时间
3. **保持透明**：向用户展示检索来源
4. **渐进式应用**：从简单策略开始，逐步增加复杂度

## 效果评估

### 评估指标

**检索质量**：
- Recall@K：Top-K中包含相关文档的比例
- Precision@K：Top-K中相关文档的比例
- MRR (Mean Reciprocal Rank)：第一个相关结果的位置

**生成质量**：
- Faithfulness：答案与检索内容的一致性
- Answer Relevance：答案对查询的相关性
- Context Relevance：检索内容对查询的相关性

**用户满意度**：
- 用户是否点赞/点踩
- 用户是否进一步追问
- 用户是否采纳答案

### 优化效果示例

**优化前**：
```
查询："BERT的训练方法"
检索：返回10个chunk，只有2个相关
生成：答案混入无关信息，未标注来源
```

**优化后**：
```
查询改写："BERT training methodology pre-training fine-tuning"
混合检索：dense (0.6) + sparse (0.4)
重排序：cross-encoder 筛选 Top 5
生成：结构化答案，明确引用来源

检索：10个chunk中8个相关
生成：准确答案，完整引用
```

## 技能协作

- 与 `paper-analysis` 技能配合：理解论文结构指导章节检索
- 与 `literature-review` 技能配合：优化多文档综合检索
- 与 `data-extraction` 技能配合：优化表格和数据检索

## 参考资源

详细的检索策略：
- `references/retrieval-strategies.md` - 学术界最新检索方法论

## 实施清单

优化 RAG 系统时，按顺序检查：
- [ ] 查询是否需要改写或扩展？
- [ ] 是否应该使用混合检索？
- [ ] 是否需要结果重排序？
- [ ] 上下文长度是否合适？
- [ ] 上下文是否包含足够信息？
- [ ] 生成prompt是否强制引用？
- [ ] 是否有幻觉检测机制？
- [ ] 是否利用了论文章节信息？
- [ ] 是否需要回退策略？
- [ ] 如何评估优化效果？

