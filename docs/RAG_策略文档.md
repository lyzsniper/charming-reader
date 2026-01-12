# RAG 策略文档

## 概述

本文档介绍了项目中实现的 6 种 RAG（检索增强生成）策略。这些策略采用工厂模式+策略模式设计，提供了统一的接口，可以根据不同场景选择最适合的 RAG 处理方式。

### 架构设计

```
rag/strategies/
├── __init__.py              # 统一入口，导出 query_rag() 函数
├── base.py                   # 基础架构：枚举、配置类、工厂类
├── two_step_rag.py           # 2-Step RAG 实现
├── agentic_rag.py            # Agentic RAG 实现
├── hybrid_rag.py             # Hybrid RAG 实现
├── adaptive_rag.py           # Adaptive RAG 实现
├── corrective_rag.py         # Corrective RAG 实现
├── self_reflective_rag.py    # Self-Reflective RAG 实现
└── utils.py                  # 工具函数：缓存、日志、监控等
```

### 核心特性

- **统一接口**：所有策略实现 `BaseRAGStrategy` 接口
- **工厂模式**：通过 `RAGStrategyFactory` 创建策略实例
- **配置驱动**：通过 `RAGStrategyConfig` 配置参数
- **可扩展性**：易于添加新的 RAG 策略
- **向后兼容**：不影响现有代码
- **性能优化**：内置缓存、日志、监控等机制

---

## RAG 原理与设计思想

### RAG 基础原理

**检索增强生成（Retrieval-Augmented Generation, RAG）** 是一种结合信息检索和生成式 AI 的技术范式。其核心思想是：

1. **知识外化**：将大型语言模型（LLM）的知识库与外部知识源分离
2. **动态检索**：根据用户查询从外部知识库中检索相关信息
3. **上下文注入**：将检索到的信息作为上下文注入到 LLM 的提示中
4. **增强生成**：LLM 基于检索到的上下文生成更准确、更相关的答案

**RAG 的优势**：
- **减少幻觉**：基于真实文档生成答案，减少模型编造信息
- **知识更新**：无需重新训练模型即可更新知识库
- **可追溯性**：可以追踪答案的来源文档
- **领域适应**：可以针对特定领域构建知识库

### 设计模式：策略模式 + 工厂模式

本项目采用**策略模式（Strategy Pattern）**和**工厂模式（Factory Pattern）**的组合：

**策略模式**：
- 定义一系列算法（RAG 策略），将它们封装成独立的类
- 使算法可以互相替换，而不影响使用算法的客户端
- 每个策略类实现 `BaseRAGStrategy` 接口，提供统一的 `query()` 方法

**工厂模式**：
- 通过 `RAGStrategyFactory` 统一创建策略实例
- 客户端无需知道具体策略类的实现细节
- 便于添加新策略，符合开闭原则

**优势**：
- **解耦**：策略选择与策略实现分离
- **扩展**：新增策略只需实现接口并注册到工厂
- **测试**：每个策略可以独立测试
- **配置**：通过配置对象统一管理参数

### 工作流编排：LangGraph

大部分策略使用 **LangGraph** 进行工作流编排：

**LangGraph 的优势**：
- **状态管理**：通过 TypedDict 定义状态结构，类型安全
- **条件路由**：支持基于状态的动态路由决策
- **循环控制**：支持迭代和循环逻辑
- **可视化**：可以可视化工作流图
- **可观测性**：内置日志和追踪功能

**状态传递机制**：
```python
class AgentState(TypedDict):
    question: str      # 用户问题
    context: str       # 检索到的上下文
    answer: str        # 生成的答案
    # ... 其他状态字段
```

状态在节点间自动传递，每个节点可以读取和更新状态。

---

## 各策略原理详解

### 1. 2-Step RAG 原理

**设计思想**：
最简单的 RAG 实现，遵循"检索-生成"的线性流程。这是 RAG 的基础范式，所有其他策略都是在此基础上扩展。

**工作原理**：
1. **检索阶段**：使用向量相似度搜索从知识库中检索最相关的文档片段
2. **生成阶段**：将检索到的文档作为上下文，与用户问题一起构建提示，让 LLM 生成答案

**数学表示**：
```
给定查询 q，检索函数 R，生成函数 G：
1. D = R(q)  # 检索相关文档
2. a = G(q, D)  # 基于查询和文档生成答案
```

**适用场景**：
- 查询与文档有明确的语义对应关系
- 不需要复杂的决策逻辑
- 对延迟要求严格

**局限性**：
- 无法处理需要多步推理的复杂查询
- 无法动态调整检索策略
- 无法验证检索和生成的质量

---

### 2. Agentic RAG 原理

**设计思想**：
引入 LLM 驱动的智能体，让系统能够自主决定何时检索、如何检索、何时停止。这是将 RAG 与 Agent 范式结合的产物。

**工作原理**：
1. **智能体决策**：LLM 分析用户问题，决定需要执行的操作（检索、搜索、生成等）
2. **工具调用**：智能体可以调用多个工具（本地检索、网络搜索等）
3. **迭代优化**：根据中间结果决定是否需要继续检索或直接生成答案

**决策机制**：
```
智能体状态机：
- 分析问题 → 决定操作类型
- 执行操作 → 评估结果
- 如果满足条件 → 生成答案
- 否则 → 继续检索/搜索
```

**优势**：
- **灵活性高**：可以根据问题动态调整策略
- **多工具协作**：可以组合使用多个检索工具
- **智能路由**：自动选择最合适的检索方式

**挑战**：
- **延迟较高**：需要多次 LLM 调用
- **成本较高**：每次决策都需要调用 LLM
- **不确定性**：智能体的决策可能不稳定

---

### 3. Hybrid RAG 原理

**设计思想**：
在检索和生成之间加入质量验证环节，通过反馈循环优化查询和答案质量。这是质量控制导向的 RAG 实现。

**工作原理**：
1. **查询增强**：使用 LLM 将用户问题转换为更精确的检索查询
2. **检索验证**：评估检索结果是否足够相关和充分
3. **答案生成**：基于验证通过的检索结果生成答案
4. **答案验证**：评估生成答案的质量，必要时重新生成

**质量评估机制**：
```
质量评估器（LLM-based Grader）：
- 输入：检索结果/生成答案 + 原始问题
- 输出：质量评分（good/poor/insufficient）
- 决策：基于评分决定是否继续优化
```

**反馈循环**：
```
查询增强 → 检索 → 验证检索质量
    ↓ (质量不足)
重新增强查询 → 重新检索
    ↓ (质量足够)
生成答案 → 验证答案质量
    ↓ (质量不足)
重新生成答案
```

**优势**：
- **质量保证**：多层次的验证机制
- **自动优化**：通过反馈循环自动改进
- **可控性强**：可以设置质量阈值

**适用场景**：
- 对答案准确性要求高的应用
- 领域特定的问答系统
- 需要质量保证的生产环境

---

### 4. Adaptive RAG 原理

**设计思想**：
根据问题的复杂度动态选择处理策略。简单问题可能不需要检索，复杂问题需要深度检索甚至网络搜索。这是效率与质量平衡的体现。

**工作原理**：
1. **问题分类**：评估问题的复杂度（简单/复杂）
2. **路由决策**：根据复杂度选择处理路径
   - 简单问题：可能直接回答或简单检索
   - 复杂问题：深度检索或网络搜索
3. **相关性检查**：验证检索结果的相关性
4. **动态切换**：如果本地检索不足，切换到网络搜索

**路由机制**：
```
问题复杂度评估：
- 简单：常见问题、定义性问题 → 直接检索或生成
- 复杂：需要推理、多步骤 → 深度检索
- 未知：本地无相关信息 → 网络搜索
```

**相关性评估**：
使用 LLM 作为相关性评分器：
```
相关性评分器：
- 输入：检索结果 + 用户问题
- 输出：相关/不相关
- 阈值：如果相关则生成，否则切换策略
```

**优势**：
- **效率优化**：简单问题快速处理
- **质量保证**：复杂问题深度检索
- **资源平衡**：合理分配计算资源

**适用场景**：
- 通用问答系统
- 混合知识源场景
- 需要智能路由的应用

---

### 5. Corrective RAG 原理

**设计思想**：
引入自我纠错机制，当检索质量不足时，系统能够自动纠正检索策略。这是"失败-学习-改进"循环的体现。

**工作原理**：
1. **初始检索**：使用原始查询进行检索
2. **质量评估**：评估检索结果的质量（good/poor/insufficient）
3. **错误诊断**：分析检索失败的原因
4. **策略纠正**：
   - 查询优化：重新构造更精确的查询
   - 检索扩展：使用网络搜索补充信息
   - 参数调整：调整检索参数（top-k、相似度阈值等）
5. **重新检索**：使用纠正后的策略重新检索

**纠正策略**：
```
质量评估结果 → 纠正策略：
- insufficient → 网络搜索或大幅优化查询
- poor → 优化查询或调整检索参数
- good → 直接生成答案
```

**错误诊断**：
```
LLM 分析检索失败原因：
- 查询不够精确 → 优化查询
- 知识库覆盖不足 → 网络搜索
- 检索参数不当 → 调整参数
```

**优势**：
- **自适应**：自动适应不同的查询类型
- **鲁棒性**：对检索失败有容错机制
- **持续改进**：通过迭代优化检索质量

**适用场景**：
- 检索质量不稳定的场景
- 复杂查询处理
- 需要自动优化的应用

---

### 6. Self-Reflective RAG 原理

**设计思想**：
在生成答案后，系统对答案进行自我评估，如果质量不足则重新生成。这是"生成-评估-改进"的反思循环。

**工作原理**：
1. **检索与生成**：检索相关文档并生成初始答案
2. **自我反思**：LLM 评估自己生成的答案质量
3. **质量分析**：从多个维度评估答案（准确性、完整性、相关性、清晰度）
4. **改进生成**：如果质量不足，生成改进约束并重新生成答案

**反思机制**：
```
自我反思器（Self-Reflector）：
- 输入：生成的答案 + 原始问题 + 检索上下文
- 评估维度：
  * 准确性：答案是否基于上下文事实正确
  * 完整性：是否回答了问题的所有方面
  * 相关性：是否直接相关于问题
  * 清晰度：是否清晰且结构良好
- 输出：质量评分 + 改进建议
```

**改进约束生成**：
```
基于反思结果生成改进约束：
- 如果准确性不足 → 强调基于上下文事实
- 如果完整性不足 → 要求覆盖所有方面
- 如果相关性不足 → 强调直接回答问题
- 如果清晰度不足 → 要求结构化表达
```

**迭代改进**：
```
生成答案 → 自我反思 → 质量评估
    ↓ (质量不足)
生成改进约束 → 重新生成答案
    ↓ (质量足够)
返回最终答案
```

**优势**：
- **质量极高**：通过自我验证确保答案质量
- **自我纠错**：能够识别并纠正自己的错误
- **多维度评估**：从多个角度评估答案

**适用场景**：
- 关键应用（医疗、法律、金融等）
- 对答案准确性要求极高的场景
- 需要可解释性的应用

**局限性**：
- **延迟高**：需要多次生成和评估
- **成本高**：多次 LLM 调用
- **可能过度优化**：在某些场景下可能不必要

---

## 技术实现细节

### 向量检索原理

**嵌入模型（Embedding Model）**：
- 将文本转换为高维向量（通常 768 或 1536 维）
- 语义相似的文本在向量空间中距离较近
- 使用余弦相似度计算文本相似度

**检索过程**：
```
1. 查询嵌入：query_vector = embed(query)
2. 相似度计算：similarity = cosine(query_vector, doc_vector)
3. Top-K 检索：返回相似度最高的 K 个文档
```

**混合检索（Hybrid Search）**：
- **向量检索**：基于语义相似度
- **关键词检索**：基于 BM25 算法
- **融合策略**：alpha * vector_score + (1-alpha) * keyword_score

### 重排序（Reranking）原理

**目的**：对初始检索结果进行精细化排序，提高相关性。

**方法**：
- **LLM Reranker**：使用 LLM 评估文档与查询的相关性
- **Cross-Encoder**：使用专门的排序模型
- **多阶段排序**：粗排 + 精排

**LLM Reranker 工作流程**：
```
1. 批量评估：将查询与多个文档一起输入 LLM
2. 相关性评分：LLM 输出每个文档的相关性分数
3. 重新排序：按分数重新排序文档
4. Top-N 选择：选择前 N 个最相关的文档
```

### 提示工程（Prompt Engineering）

**提示模板结构**：
```
System Message: 定义角色和任务
Context: 检索到的文档
Question: 用户问题
Guidelines: 回答指导原则
```

**关键原则**：
- **明确指令**：清晰说明任务要求
- **上下文注入**：将检索文档作为上下文
- **格式约束**：指定输出格式（如引用格式）
- **幻觉预防**：明确要求基于上下文回答

---

## 性能优化原理

### 缓存机制

**查询缓存**：
- 对相同查询缓存结果
- 使用查询的哈希值作为缓存键
- 减少重复的检索和生成成本

**检索缓存**：
- 缓存向量检索结果
- 相同查询的检索结果可以复用

### 批量处理

**批量检索**：
- 将多个查询合并批量检索
- 减少向量数据库的查询次数

**批量生成**：
- 使用 LLM 的批量 API
- 提高吞吐量

### 异步处理

**异步检索**：
- 使用异步 I/O 进行向量检索
- 不阻塞主线程

**并发生成**：
- 多个查询并发处理
- 提高系统吞吐量

---

## 快速开始

### 基本使用

```python
from app.rag.strategies import query_rag, RAGStrategyType

# 使用默认 Adaptive RAG
result = query_rag("What is machine learning?")
print(result["answer"])

# 指定策略类型
result = query_rag(
    "What is machine learning?",
    strategy_type=RAGStrategyType.TWO_STEP
)
```

### 自定义配置

```python
from app.rag.strategies import query_rag, RAGStrategyConfig, RAGStrategyFactory

# 方式一：通过 query_rag 函数传参
result = query_rag(
    "Explain quantum computing",
    strategy_type="self_reflective",
    max_iterations=2,
    similarity_top_k=15,
    enable_rerank=True
)

# 方式二：使用配置对象
config = RAGStrategyConfig(
    strategy_type=RAGStrategyType.AGENTIC,
    max_iterations=5,
    enable_web_search=True
)
strategy = RAGStrategyFactory.create_strategy(config)
result = strategy.query("What is machine learning?")
```

---

## RAG 策略详解

### 1. 2-Step RAG（两步 RAG）

**文件**：`two_step_rag.py`

**特点**：
- 最简单的 RAG 模式
- 固定流程：检索 → 生成
- 无决策逻辑，低延迟
- 适合简单、直接的问答场景

**工作流程**：
```
用户问题 → 检索文档 → 生成答案 → 返回结果
```

**适用场景**：
- FAQ 系统
- 文档机器人
- 简单问答系统
- 对延迟敏感的场景

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "What is the main contribution of this paper?",
    strategy_type=RAGStrategyType.TWO_STEP,
    chunk_size=1024,
    similarity_top_k=5
)

print(f"Answer: {result['answer']}")
print(f"Source: {result['source']}")
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local",
    "context": "检索到的上下文",
    "strategy": "two_step"
}
```

---

### 2. Agentic RAG（智能体 RAG）

**文件**：`agentic_rag.py`

**特点**：
- LLM 驱动的智能体决定何时检索
- 动态决策，高灵活性
- 可以使用工具进行多步检索
- 支持本地检索和网络搜索

**工作流程**：
```
用户问题 → 智能体分析 → 决定操作
    ├─→ 本地检索 → 智能体评估 → 继续/生成
    ├─→ 网络搜索 → 智能体评估 → 继续/生成
    └─→ 直接生成 → 返回结果
```

**适用场景**：
- 研究助手
- 需要多工具协作的场景
- 复杂查询需要多步检索
- 需要动态决策的场景

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "Compare machine learning and deep learning, and find recent developments",
    strategy_type=RAGStrategyType.AGENTIC,
    max_iterations=5,
    enable_web_search=True
)

print(f"Answer: {result['answer']}")
print(f"Tools used: {result.get('tools_used', [])}")
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local" or "web",
    "context": "检索到的上下文",
    "strategy": "agentic",
    "tools_used": ["local_retrieve", "web_search"]
}
```

**关键参数**：
- `max_iterations`: 最大迭代次数（默认 3）
- `enable_web_search`: 是否启用网络搜索（默认 True）

---

### 3. Hybrid RAG（混合 RAG）

**文件**：`hybrid_rag.py`

**特点**：
- 包含中间步骤：查询增强、检索验证、答案验证
- 平衡控制性和灵活性
- 质量验证机制
- 自动优化查询和答案

**工作流程**：
```
用户问题 → 查询增强 → 检索 → 验证检索质量
    ├─→ 质量不足 → 重新增强查询 → 重新检索
    └─→ 质量足够 → 生成答案 → 验证答案质量
        ├─→ 质量不足 → 重新生成
        └─→ 质量足够 → 返回结果
```

**适用场景**：
- 领域特定问答系统
- 需要质量保证的场景
- 对答案准确性要求高的应用
- 复杂查询需要多次优化

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "Explain the transformer architecture in detail",
    strategy_type=RAGStrategyType.HYBRID,
    max_iterations=3,
    enable_rerank=True
)

print(f"Answer: {result['answer']}")
print(f"Enhanced question: {result.get('enhanced_question', '')}")
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local",
    "context": "检索到的上下文",
    "strategy": "hybrid",
    "enhanced_question": "增强后的问题"
}
```

**关键参数**：
- `max_iterations`: 最大迭代次数（默认 3）
- `enable_rerank`: 是否启用重排序（默认 True）

---

### 4. Adaptive RAG（自适应 RAG）

**文件**：`adaptive_rag.py`

**特点**：
- 根据问题复杂度动态路由
- 简单问题可能跳过检索
- 复杂问题触发向量搜索或网络搜索
- 自动评估检索相关性

**工作流程**：
```
用户问题 → 本地检索 → 相关性检查
    ├─→ 相关 → 生成答案
    └─→ 不相关 → 网络搜索 → 生成答案
```

**适用场景**：
- 通用问答系统
- 需要智能路由的场景
- 混合本地和网络知识的场景
- 当前项目的默认策略

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "What are the latest developments in AI?",
    strategy_type=RAGStrategyType.ADAPTIVE,
    enable_web_search=True
)

print(f"Answer: {result['answer']}")
print(f"Source: {result['source']}")  # 'local' or 'web'
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local" or "web",
    "context": "检索到的上下文",
    "strategy": "adaptive"
}
```

**关键参数**：
- `enable_web_search`: 是否启用网络搜索（默认 True）
- `relevance_threshold`: 相关性阈值（默认 0.7）

---

### 5. Corrective RAG（纠正式 RAG）

**文件**：`corrective_rag.py`

**特点**：
- 评估检索文档的质量
- 如果检索不足，自动纠正：优化查询或网络检索
- 自我纠错机制
- 迭代优化检索结果

**工作流程**：
```
用户问题 → 检索 → 评估检索质量
    ├─→ 质量不足 → 纠正（优化查询/网络搜索）→ 重新检索
    └─→ 质量足够 → 生成答案 → 返回结果
```

**适用场景**：
- 需要高质量检索的场景
- 复杂查询
- 检索结果不稳定的场景
- 需要自动优化的应用

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "What are the key differences between supervised and unsupervised learning?",
    strategy_type=RAGStrategyType.CORRECTIVE,
    max_iterations=3,
    enable_web_search=True
)

print(f"Answer: {result['answer']}")
print(f"Retrieval quality: {result.get('retrieval_quality', 'unknown')}")
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local" or "web",
    "context": "检索到的上下文",
    "strategy": "corrective",
    "retrieval_quality": "good" or "poor" or "insufficient"
}
```

**关键参数**：
- `max_iterations`: 最大迭代次数（默认 3）
- `enable_web_search`: 是否启用网络搜索（默认 True）

**检索质量评估**：
- `good`: 检索结果高度相关且充分
- `poor`: 检索结果部分相关但不完整
- `insufficient`: 检索结果不相关或过于稀疏

---

### 6. Self-Reflective RAG（自反思 RAG）

**文件**：`self_reflective_rag.py`

**特点**：
- 生成初始答案后自我评估
- 如果答案不足，可以重新生成或添加约束
- 迭代改进机制
- 多维度质量评估

**工作流程**：
```
用户问题 → 检索 → 生成答案 → 自我反思
    ├─→ 质量不足 → 生成改进约束 → 重新生成
    └─→ 质量足够 → 返回结果
```

**适用场景**：
- 需要高质量答案的场景
- 关键应用（医疗、法律等）
- 对答案准确性要求极高的场景
- 需要自我验证的系统

**使用示例**：
```python
from app.rag.strategies import query_rag, RAGStrategyType

result = query_rag(
    "Explain the mathematical foundations of neural networks",
    strategy_type=RAGStrategyType.SELF_REFLECTIVE,
    max_iterations=2
)

print(f"Answer: {result['answer']}")
print(f"Answer quality: {result.get('answer_quality', 'unknown')}")
print(f"Reflection: {result.get('reflection', '')}")
```

**返回格式**：
```python
{
    "answer": "生成的答案",
    "source": "local",
    "context": "检索到的上下文",
    "strategy": "self_reflective",
    "reflection": "自我反思结果",
    "answer_quality": "good" or "needs_improvement" or "poor"
}
```

**关键参数**：
- `max_iterations`: 最大迭代次数（默认 3）

**答案质量评估维度**：
1. **准确性**：答案是否基于上下文事实正确
2. **完整性**：答案是否完整回答了问题的所有方面
3. **相关性**：答案是否直接相关于问题
4. **清晰度**：答案是否清晰且结构良好

---

## 策略对比

| 策略 | 复杂度 | 延迟 | 灵活性 | 质量保证 | 适用场景 |
|------|--------|------|--------|----------|----------|
| **2-Step RAG** | 低 | 低 | 低 | 中 | FAQ、简单问答 |
| **Agentic RAG** | 高 | 中-高 | 高 | 中 | 研究助手、多工具 |
| **Hybrid RAG** | 中-高 | 中-高 | 中 | 高 | 领域问答、质量要求高 |
| **Adaptive RAG** | 中 | 中 | 中 | 中 | 通用问答、智能路由 |
| **Corrective RAG** | 中-高 | 中-高 | 中 | 高 | 复杂查询、检索优化 |
| **Self-Reflective RAG** | 高 | 高 | 低 | 极高 | 关键应用、高准确性 |

### 选择指南

**选择 2-Step RAG 如果**：
- 需要最低延迟
- 问题简单直接
- 不需要复杂的决策逻辑
- 资源有限

**选择 Agentic RAG 如果**：
- 需要动态决策
- 需要多工具协作
- 查询可能需要多步检索
- 需要高灵活性

**选择 Hybrid RAG 如果**：
- 需要质量保证
- 查询可能需要优化
- 答案需要验证
- 领域特定应用

**选择 Adaptive RAG 如果**：
- 需要智能路由
- 混合本地和网络知识
- 通用问答场景
- 平衡性能和灵活性

**选择 Corrective RAG 如果**：
- 检索质量不稳定
- 复杂查询
- 需要自动优化检索
- 检索结果需要验证

**选择 Self-Reflective RAG 如果**：
- 需要极高答案质量
- 关键应用场景
- 答案需要自我验证
- 可以接受较高延迟

---

## API 参考

### query_rag()

统一的 RAG 查询入口函数。

**函数签名**：
```python
def query_rag(
    question: str,
    strategy_type: Union[RAGStrategyType, str] = RAGStrategyType.ADAPTIVE,
    llm: Optional[Any] = None,
    vector_store: Optional[Any] = None,
    query_engine: Optional[Any] = None,
    reranker: Optional[Any] = None,
    web_search_client: Optional[Any] = None,
    max_iterations: int = 3,
    relevance_threshold: float = 0.7,
    similarity_top_k: int = 10,
    rerank_top_n: int = 3,
    enable_rerank: bool = True,
    enable_web_search: bool = True,
    **extra_params
) -> Dict[str, Any]
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `question` | str | 必需 | 用户问题 |
| `strategy_type` | Union[RAGStrategyType, str] | `ADAPTIVE` | RAG 策略类型 |
| `llm` | Optional[Any] | None | LLM 实例（默认使用全局配置） |
| `vector_store` | Optional[Any] | None | 向量存储实例（默认使用全局配置） |
| `query_engine` | Optional[Any] | None | 查询引擎实例 |
| `reranker` | Optional[Any] | None | 重排序器实例 |
| `web_search_client` | Optional[Any] | None | 网络搜索客户端 |
| `max_iterations` | int | 3 | 最大迭代次数（用于循环策略） |
| `relevance_threshold` | float | 0.7 | 相关性阈值 |
| `similarity_top_k` | int | 10 | 检索 top-k |
| `rerank_top_n` | int | 3 | 重排序 top-n |
| `enable_rerank` | bool | True | 是否启用重排序 |
| `enable_web_search` | bool | True | 是否启用网络搜索 |
| `enable_cache` | bool | True | 是否启用缓存 |
| `cache_ttl` | int | 3600 | 缓存有效期（秒） |
| `enable_logging` | bool | True | 是否启用日志 |
| `enable_monitoring` | bool | True | 是否启用监控 |
| `**extra_params` | dict | {} | 其他策略特定参数 |

**返回值**：
```python
Dict[str, Any]  # 包含 answer, source, context, strategy 等字段
```

### RAGStrategyType

策略类型枚举。

```python
class RAGStrategyType(str, Enum):
    TWO_STEP = "two_step"
    AGENTIC = "agentic"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"
    CORRECTIVE = "corrective"
    SELF_REFLECTIVE = "self_reflective"
```

### RAGStrategyConfig

策略配置数据类。

```python
@dataclass
class RAGStrategyConfig:
    strategy_type: Union[RAGStrategyType, str] = RAGStrategyType.ADAPTIVE
    llm: Optional[Any] = None
    vector_store: Optional[Any] = None
    query_engine: Optional[Any] = None
    reranker: Optional[Any] = None
    web_search_client: Optional[Any] = None
    max_iterations: int = 3
    relevance_threshold: float = 0.7
    similarity_top_k: int = 10
    rerank_top_n: int = 3
    enable_rerank: bool = True
    enable_web_search: bool = True
    extra_params: Dict[str, Any] = field(default_factory=dict)
```

### RAGStrategyFactory

策略工厂类。

```python
class RAGStrategyFactory:
    @staticmethod
    def create_strategy(config: RAGStrategyConfig) -> BaseRAGStrategy:
        """创建 RAG 策略实例"""
        pass
```

---

## 高级用法

### 自定义 LLM

```python
from langchain_litellm import ChatLiteLLM
from app.rag.strategies import query_rag, RAGStrategyType

# 使用自定义 LLM
custom_llm = ChatLiteLLM(
    model="gpt-4",
    temperature=0.7,
    max_tokens=2000
)

result = query_rag(
    "What is machine learning?",
    strategy_type=RAGStrategyType.TWO_STEP,
    llm=custom_llm
)
```

### 自定义向量存储

```python
from app.rag.ingestion import get_vector_store
from app.rag.strategies import query_rag, RAGStrategyType

# 使用自定义向量存储
vector_store = get_vector_store()

result = query_rag(
    "What is machine learning?",
    strategy_type=RAGStrategyType.ADAPTIVE,
    vector_store=vector_store
)
```

### 策略切换

```python
from app.rag.strategies import query_rag, RAGStrategyType
from core.config import settings

def get_rag_result(question: str):
    """根据配置选择策略"""
    strategy_type = getattr(settings, 'RAG_STRATEGY', RAGStrategyType.ADAPTIVE)
    
    return query_rag(
        question,
        strategy_type=strategy_type,
        max_iterations=getattr(settings, 'RAG_MAX_ITERATIONS', 3)
    )
```

### 批量处理

```python
from app.rag.strategies import query_rag, RAGStrategyType

questions = [
    "What is machine learning?",
    "Explain neural networks",
    "What is deep learning?"
]

results = []
for question in questions:
    result = query_rag(
        question,
        strategy_type=RAGStrategyType.TWO_STEP
    )
    results.append(result)
```

---

## 性能优化建议

### 1. 延迟优化

- **2-Step RAG**：最低延迟，适合实时场景
- **减少迭代次数**：对于循环策略，减少 `max_iterations`
- **禁用不必要的功能**：如不需要网络搜索，设置 `enable_web_search=False`
- **启用缓存**：对相同查询使用缓存，大幅减少延迟

### 2. 质量优化

- **启用重排序**：`enable_rerank=True` 可以提高检索质量
- **增加检索数量**：增加 `similarity_top_k` 获取更多上下文
- **使用 Self-Reflective RAG**：最高质量，但延迟较高
- **调整相关性阈值**：根据场景调整 `relevance_threshold`

### 3. 成本优化

- **选择合适的策略**：简单场景使用 2-Step RAG
- **限制迭代次数**：避免无限循环
- **启用缓存**：对相同问题缓存结果，减少重复计算
- **批量处理**：将多个查询合并处理

### 4. 缓存机制

系统内置了智能缓存机制：

```python
from app.rag.strategies import query_rag, clear_cache

# 启用缓存（默认启用）
result1 = query_rag("What is machine learning?", enable_cache=True, cache_ttl=3600)

# 相同查询会从缓存获取（几乎瞬间返回）
result2 = query_rag("What is machine learning?", enable_cache=True)

# 清空缓存
clear_cache()
```

**缓存策略**：
- 缓存键基于：问题内容 + 策略类型 + 关键配置参数
- 默认 TTL：3600 秒（1 小时）
- 自动过期：过期缓存自动清理
- 内存存储：生产环境建议使用 Redis

### 5. 日志和监控

系统内置了日志和监控功能：

```python
import logging

# 配置日志级别
logging.basicConfig(level=logging.INFO)

# 查询会自动记录日志
result = query_rag("What is machine learning?", enable_logging=True)

# 结果中包含性能指标
print(result.get('_metrics', {}))
```

**监控指标**：
- 查询延迟
- 缓存命中率
- 策略执行时间
- 错误率

---

## 故障排查

### 常见问题

**1. 策略创建失败**
```python
# 错误：ValueError: 不支持的策略类型
# 解决：检查策略类型拼写
result = query_rag(question, strategy_type="adaptive")  # 正确
result = query_rag(question, strategy_type="Adaptive")  # 错误
```

**2. 网络搜索不可用**
```python
# 错误：Web search is disabled
# 解决：检查 TAVILY_API_KEY 或设置 enable_web_search=False
result = query_rag(question, enable_web_search=False)
```

**3. 迭代次数过多**
```python
# 问题：策略陷入循环
# 解决：减少 max_iterations 或检查逻辑
result = query_rag(question, max_iterations=2)
```

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查返回结果
result = query_rag(question)
print(f"Strategy: {result.get('strategy')}")
print(f"Source: {result.get('source')}")
print(f"Context length: {len(result.get('context', ''))}")
```

---

## 工具函数

系统提供了丰富的工具函数，可以在自定义策略中使用：

### 缓存工具

```python
from app.rag.strategies import get_cache_key, get_cached_result, set_cached_result

# 生成缓存键
cache_key = get_cache_key(question, strategy_type)

# 获取缓存
cached = get_cached_result(cache_key)

# 设置缓存
set_cached_result(cache_key, result, ttl_seconds=3600)
```

### 验证工具

```python
from app.rag.strategies import validate_question, check_context_quality

# 验证问题
if validate_question(question):
    # 处理问题
    pass

# 检查上下文质量
if check_context_quality(context):
    # 使用上下文
    pass
```

### 格式化工具

```python
from app.rag.strategies import format_context, sanitize_result

# 格式化上下文（限制长度）
formatted = format_context(context, max_length=2000)

# 清理结果（移除内部字段）
cleaned = sanitize_result(result)
```

### 装饰器

```python
from app.rag.strategies.utils import with_cache, with_logging, with_monitoring

# 使用缓存装饰器
@with_cache(ttl_seconds=3600)
def my_function(question: str):
    # 函数逻辑
    pass

# 使用日志装饰器
@with_logging(log_level=logging.INFO)
def my_function(question: str):
    # 函数逻辑
    pass

# 使用监控装饰器
@with_monitoring(metric_name="my_metric")
def my_function(question: str):
    # 函数逻辑
    pass
```

---

## 扩展开发

### 添加新策略

1. **创建策略文件**：在 `strategies/` 目录下创建新文件
2. **实现 BaseRAGStrategy**：继承并实现 `query()` 方法
3. **注册到工厂**：在 `base.py` 的 `RAGStrategyFactory` 中注册
4. **添加枚举**：在 `RAGStrategyType` 中添加新类型

**示例**：
```python
# strategies/custom_rag.py
from .base import BaseRAGStrategy, RAGStrategyConfig
from .utils import validate_question, format_context

class CustomRAGStrategy(BaseRAGStrategy):
    def query(self, question: str) -> dict:
        # 验证问题
        if not self._validate_question(question):
            raise ValueError("Invalid question")
        
        # 实现自定义逻辑
        # ...
        
        result = {
            "answer": "...",
            "source": "custom",
            "context": "..."
        }
        
        # 格式化结果
        return self._format_result(result)
```

### 最佳实践

1. **使用基类方法**：利用 `_validate_question()` 和 `_format_result()` 方法
2. **添加日志**：使用 `self._logger` 记录关键操作
3. **错误处理**：妥善处理异常，提供有意义的错误信息
4. **性能考虑**：对于耗时操作，考虑添加缓存
5. **文档完善**：添加详细的文档字符串和使用示例

---

## 系统增强功能

### v1.1.0 新增功能

#### 1. 智能缓存系统
- **自动缓存**：相同查询自动使用缓存结果
- **TTL 支持**：可配置缓存有效期
- **智能键生成**：基于查询和配置生成唯一缓存键
- **自动过期**：过期缓存自动清理

#### 2. 日志和监控
- **结构化日志**：详细的查询日志记录
- **性能监控**：自动记录执行时间和指标
- **错误追踪**：完整的错误堆栈记录
- **可配置级别**：支持不同日志级别

#### 3. 工具函数库
- **验证工具**：问题验证、上下文质量检查
- **格式化工具**：上下文格式化、结果清理
- **装饰器**：缓存、日志、监控装饰器
- **工具函数**：Token 估算、上下文处理等

#### 4. 增强的配置系统
- **配置验证**：自动验证配置参数
- **默认值优化**：合理的默认配置
- **扩展参数**：支持自定义参数

#### 5. 错误处理改进
- **输入验证**：问题格式和长度验证
- **异常处理**：完善的异常捕获和处理
- **错误信息**：清晰的错误提示

---

## 更新日志

### v1.1.0 (2024)
- 新增智能缓存系统
- 新增日志和监控功能
- 新增工具函数库
- 增强配置系统和错误处理
- 优化代码结构和性能

### v1.0.0 (2024)
- 实现 6 种 RAG 策略
- 统一接口和工厂模式
- 完整的文档和示例

---

## 参考资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LlamaIndex 文档](https://docs.llamaindex.ai/)
- [LangChain RAG 指南](https://python.langchain.com/docs/use_cases/question_answering/)

---

## 贡献指南

欢迎贡献新的 RAG 策略或改进现有实现。请确保：
1. 遵循现有代码风格
2. 添加完整的文档字符串
3. 包含使用示例
4. 通过所有测试

---

## 许可证

本项目遵循项目主许可证。
