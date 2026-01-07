---
name: data-extraction
description: 从学术论文中提取结构化数据，包括表格、图表、实验结果和性能指标
triggers:
  - extract data
  - 提取数据
  - extract table
  - 提取表格
  - extract results
  - 提取结果
  - performance metrics
  - 性能指标
  - experimental data
  - 实验数据
version: 1.0.0
---

# 学术数据提取技能 (Data Extraction Skill)

## 目标

当需要从学术论文中提取结构化数据时，使用此技能识别和提取表格、图表、实验参数、性能指标、统计结果等数值信息。

## 核心能力

本技能专注于从非结构化的学术文本中提取结构化数据，包括表格解析、数值识别、实验结果整理和性能对比矩阵构建。

## 数据类型识别

学术论文中常见的数据类型：

### 1. 表格数据 (Tables)

**常见表格类型**：

**性能对比表**：
```
| Model      | Accuracy | F1-Score | Training Time |
|------------|----------|----------|---------------|
| BERT-base  | 92.3%    | 0.915    | 2.5h          |
| GPT-2      | 89.1%    | 0.883    | 3.2h          |
| RoBERTa    | 94.2%    | 0.937    | 2.8h          |
```

**数据集统计表**：
```
| Dataset    | # Samples | # Classes | Avg Length |
|------------|-----------|-----------|------------|
| IMDB       | 50,000    | 2         | 231        |
| SST-2      | 67,349    | 2         | 19         |
```

**超参数配置表**：
```
| Parameter        | Value    |
|------------------|----------|
| Learning Rate    | 2e-5     |
| Batch Size       | 32       |
| Epochs           | 3        |
| Optimizer        | Adam     |
```

### 2. 实验结果 (Experimental Results)

**正文中的数值**：
```
"Our model achieves 94.2% accuracy on the test set, 
outperforming BERT-base (92.3%) by 1.9 percentage points."

提取：
- Our model: 94.2% accuracy
- BERT-base: 92.3% accuracy
- Improvement: +1.9 pp
```

**统计显著性**：
```
"The improvement is statistically significant (p < 0.01)."

提取：
- Statistical significance: Yes
- p-value: < 0.01
```

### 3. 图表数据 (Figures and Charts)

**性能曲线图**：
- Training/Validation loss curves
- Accuracy over epochs
- Learning rate schedules

**对比柱状图**：
- Model performance comparison
- Ablation study results

**注意**：图表数据提取通常需要 OCR 或图像理解能力。在纯文本环境中，应提取图表的 caption 和论文中对图表的描述性说明。

### 4. 架构参数 (Architectural Parameters)

```
"We use a 12-layer transformer with 768 hidden dimensions, 
12 attention heads, and a vocabulary size of 30,000."

提取：
- Layers: 12
- Hidden dimensions: 768
- Attention heads: 12
- Vocabulary size: 30,000
```

## 提取策略

### 策略 1：表格识别与解析

#### 1.1 表格定位

在论文文本中，表格通常有以下特征：

**Markdown 格式表格**：
```
| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |
```

**文本描述的表格**：
```
Table 1: Performance comparison
Model X: 92.3%
Model Y: 89.1%
Model Z: 94.2%
```

**表格引用**：
```
"As shown in Table 1..."
"See Table 3 for detailed results..."
"Table 2 presents the comparison..."
```

#### 1.2 表格解析

**提取表头**：
```
识别列名（通常在第一行）：
["Model", "Accuracy", "F1-Score", "Training Time"]
```

**提取数据行**：
```
逐行解析：
Row 1: ["BERT-base", "92.3%", "0.915", "2.5h"]
Row 2: ["GPT-2", "89.1%", "0.883", "3.2h"]
Row 3: ["RoBERTa", "94.2%", "0.937", "2.8h"]
```

**数据类型识别**：
```
- Percentage: "92.3%" → 92.3 (float)
- Decimal: "0.915" → 0.915 (float)
- Time: "2.5h" → 2.5 (hours)
- Integer: "50,000" → 50000 (int)
```

#### 1.3 表格结构化

转换为标准数据结构：

```json
{
  "table_id": "table_1",
  "caption": "Performance comparison on test set",
  "columns": ["Model", "Accuracy", "F1-Score", "Training Time"],
  "rows": [
    {"Model": "BERT-base", "Accuracy": 92.3, "F1-Score": 0.915, "Training Time": "2.5h"},
    {"Model": "GPT-2", "Accuracy": 89.1, "F1-Score": 0.883, "Training Time": "3.2h"},
    {"Model": "RoBERTa", "Accuracy": 94.2, "F1-Score": 0.937, "Training Time": "2.8h"}
  ],
  "best_model": {"column": "Accuracy", "model": "RoBERTa", "value": 94.2}
}
```

### 策略 2：数值提取

#### 2.1 性能指标识别

**常见指标及其模式**：

```
Accuracy: "accuracy of 92.3%", "92.3% accuracy", "achieves 92.3%"
Precision: "precision: 0.915", "91.5% precision"
Recall: "recall of 0.883", "88.3% recall"
F1-Score: "F1 score: 0.937", "F1 = 0.937"
BLEU: "BLEU score of 32.5", "BLEU-4: 32.5"
Perplexity: "perplexity of 15.2", "PPL = 15.2"
AUC: "AUC-ROC: 0.95", "AUC of 0.95"
```

**正则表达式模式**（示例）：
```python
accuracy_pattern = r"accuracy\s*(?:of|:)?\s*(\d+\.?\d*)%?"
f1_pattern = r"F1[-\s]?score\s*(?:of|:)?\s*(\d+\.?\d*)"
percentage_pattern = r"(\d+\.?\d*)%"
decimal_pattern = r"(\d+\.?\d+)"
```

#### 2.2 对比关系提取

识别模型之间的比较：

```
"Our model (94.2%) outperforms BERT (92.3%) by 1.9 pp"

提取：
- Model 1: "Our model", 94.2%
- Model 2: "BERT", 92.3%
- Comparison: "outperforms"
- Difference: +1.9 percentage points
```

**比较词识别**：
- Positive: outperforms, exceeds, better than, superior to, improves over
- Negative: worse than, inferior to, underperforms
- Equal: comparable to, similar to, on par with

#### 2.3 统计显著性提取

```
"The improvement is statistically significant (p < 0.01)"
"Significant at 95% confidence level"
"No significant difference (p = 0.12)"

提取：
- p-value: < 0.01 (or 0.12)
- Significance level: 0.01 (or 0.05)
- Significant: Yes (or No)
```

### 策略 3：实验设置提取

#### 3.1 数据集信息

```
"We evaluate on three datasets: IMDB (50K samples), 
SST-2 (67K samples), and AG News (120K samples)."

提取：
Dataset 1:
  - Name: IMDB
  - Size: 50,000 samples

Dataset 2:
  - Name: SST-2
  - Size: 67,000 samples

Dataset 3:
  - Name: AG News
  - Size: 120,000 samples
```

#### 3.2 超参数配置

```
"We train the model using Adam optimizer with learning rate 2e-5, 
batch size 32, for 3 epochs."

提取：
- Optimizer: Adam
- Learning rate: 2e-5
- Batch size: 32
- Epochs: 3
```

#### 3.3 计算资源

```
"Training took 2.5 hours on 8 V100 GPUs with 32GB memory each."

提取：
- Training time: 2.5 hours
- Hardware: 8 × V100 GPU
- Memory: 32GB per GPU
```

### 策略 4：构建对比矩阵

对于多篇论文或多个模型的比较，构建统一的对比矩阵：

```
输入：
- Paper A: Model X achieves 92.3% accuracy
- Paper B: Model Y achieves 94.1% accuracy
- Paper C: Model Z achieves 91.8% accuracy

输出对比矩阵：
| Model | Paper | Year | Accuracy | F1-Score | Dataset |
|-------|-------|------|----------|----------|---------|
| X     | A     | 2020 | 92.3%    | 0.915    | IMDB    |
| Y     | B     | 2021 | 94.1%    | 0.932    | IMDB    |
| Z     | C     | 2019 | 91.8%    | 0.908    | IMDB    |

排序：按 Accuracy 降序
最佳：Model Y (94.1%)
```

## 使用指南

### 何时使用此技能

- 用户需要"提取表格"、"提取数据"
- 用户询问"性能指标"、"实验结果"
- 用户需要"对比不同模型"
- 用户要求"整理实验数据"
- 进行系统性文献综述，需要汇总多篇论文的结果

### 如何使用此技能

**场景 1：提取单篇论文的表格**
```
1. 定位表格（通过"Table X"关键词）
2. 解析表格结构（列名、数据行）
3. 识别数据类型（数值、百分比、文本）
4. 结构化输出（JSON 或 Markdown 表格）
5. 识别最佳结果（如最高准确率）
```

**场景 2：从正文提取性能数据**
```
1. 搜索性能指标关键词（accuracy, F1, BLEU, etc.）
2. 提取数值和对应的模型/方法名称
3. 识别对比关系（outperforms, better than）
4. 提取统计显著性信息
5. 生成结构化的结果摘要
```

**场景 3：构建多论文对比矩阵**
```
1. 从每篇论文提取关键指标
2. 统一指标名称（F1-score = F1 = F1 Score）
3. 确保数据集和设置可比
4. 构建对比表格
5. 排序并标识最佳结果
6. 注明不可直接比较的情况（不同数据集、不同设置）
```

**场景 4：提取实验配置**
```
1. 定位 Methods / Experimental Setup 章节
2. 提取数据集信息
3. 提取模型架构参数
4. 提取训练超参数
5. 提取计算资源信息
6. 生成可复现的配置清单
```

### 注意事项

#### 数据质量检查

1. **单位统一**：
   - 确保百分比和小数不混用（92.3% vs 0.923）
   - 时间单位统一（秒、分钟、小时）
   - 内存单位统一（MB, GB, TB）

2. **数据一致性**：
   - 检查表格内数据是否与正文描述一致
   - 如有矛盾，标注并询问用户

3. **完整性**：
   - 标识缺失的数据（用 N/A 或 - 表示）
   - 不要填充或猜测缺失的数值

4. **可比性**：
   - 注明实验条件差异（不同数据集、不同train/test split）
   - 避免不公平比较

#### 常见错误

1. ❌ 混淆不同指标
   - 准确率 (Accuracy) ≠ 精确率 (Precision)
   - F1-Score ≠ F1-Measure（通常相同，但要确认）

2. ❌ 忽略上下文
   - "92.3" 可能是百分比、小数或其他单位
   - 需要结合上下文确定

3. ❌ 错误解析表格
   - 注意合并单元格
   - 注意多级表头

4. ❌ 忽略统计显著性
   - 小的性能提升可能无统计显著性
   - 应该标注 p-value

## 输出格式

### 格式 1：表格摘要

```
## 表格 1：模型性能对比

**来源**：[论文标题], [作者], [年份]

| 模型      | 准确率   | F1分数 | 训练时间 |
|-----------|---------|--------|----------|
| BERT-base | 92.3%   | 0.915  | 2.5h     |
| GPT-2     | 89.1%   | 0.883  | 3.2h     |
| RoBERTa   | 94.2%   | 0.937  | 2.8h     |

**最佳结果**：RoBERTa 在准确率（94.2%）和 F1 分数（0.937）上表现最佳

**数据集**：IMDB 测试集
**评估指标**：Accuracy, F1-Score
```

### 格式 2：实验结果摘要

```
## 实验结果提取

**论文**：[标题]

### 主要发现：
- **基线模型**：BERT-base, 92.3% accuracy
- **提出模型**：Enhanced-BERT, 94.2% accuracy
- **性能提升**：+1.9 percentage points
- **统计显著性**：p < 0.01 ✓

### 实验设置：
- **数据集**：IMDB (50K samples)
- **划分**：Train 80% / Val 10% / Test 10%
- **超参数**：
  - Learning Rate: 2e-5
  - Batch Size: 32
  - Epochs: 3
  - Optimizer: Adam

### 计算资源：
- **硬件**：8 × V100 GPU (32GB)
- **训练时间**：2.5 hours
```

### 格式 3：多论文对比矩阵

```
## 跨论文性能对比

**对比指标**：Accuracy on IMDB dataset

| 模型         | 论文来源      | 年份 | 准确率 | F1分数 | 备注              |
|-------------|--------------|------|--------|--------|-------------------|
| BERT-base   | Devlin et al | 2019 | 92.3%  | 0.915  | 基线模型           |
| RoBERTa     | Liu et al    | 2019 | 94.2%  | 0.937  | 改进训练策略       |
| ELECTRA     | Clark et al  | 2020 | 93.8%  | 0.929  | 判别式预训练       |
| DeBERTa     | He et al     | 2021 | 95.1%  | 0.946  | 当前最佳 (SOTA)    |

**趋势分析**：
- 2019-2021年，IMDB准确率从92.3%提升到95.1%
- 主要改进来自训练方法创新和架构优化

**注意**：
- 所有模型使用相同的数据集划分
- 结果具有可比性
```

## 辅助脚本

本技能包含辅助脚本用于自动化数据提取：

### scripts/table_parser.py
- 解析 Markdown 表格
- 解析文本描述的表格
- 数据类型推断和转换

### scripts/figure_extractor.py
- 提取图表 caption
- 分析论文中对图表的描述
- （如果有 OCR 能力）提取图表中的数值

**注意**：脚本需要在支持 Python 执行的环境中使用。在纯文本环境中，技能将提供手动提取的指导。

## 技能协作

- 与 `paper-analysis` 技能配合：先分析论文结构，定位 Results 章节
- 与 `literature-review` 技能配合：为综述提供汇总的性能对比
- 与 `rag-enhancement` 技能配合：优化对表格和数值内容的检索

## 质量检查清单

提取数据后，检查：
- [ ] 所有数值都有明确的单位
- [ ] 指标名称准确（不混淆相似指标）
- [ ] 表格结构完整（列名、数据行对齐）
- [ ] 最佳结果已标识
- [ ] 数据来源已标注（论文、表格编号）
- [ ] 统计显著性已记录（如有）
- [ ] 实验条件已说明（数据集、设置）
- [ ] 不可比较的情况已注明
- [ ] 数据与原文一致（复核）

## 使用示例

### 示例 1：用户请求提取表格

**用户输入**：
```
提取这篇论文Table 2中的性能数据
```

**技能输出**：
```
已提取 Table 2: Model Performance Comparison

| 模型           | Accuracy | Precision | Recall | F1-Score |
|---------------|----------|-----------|--------|----------|
| Baseline CNN  | 87.2%    | 0.865     | 0.858  | 0.861    |
| LSTM          | 89.5%    | 0.891     | 0.882  | 0.886    |
| BERT-base     | 92.3%    | 0.920     | 0.911  | 0.915    |
| Our Model     | 94.1%    | 0.938     | 0.925  | 0.931    |

**关键发现**：
- 最佳模型：Our Model (94.1% accuracy)
- 相比BERT提升：+1.8 percentage points
- 所有指标上Our Model均为最佳

**数据集**：IMDB sentiment analysis (基于table caption)
**评估**：测试集，single run（基于论文描述）
```

### 示例 2：提取正文中的实验结果

**用户输入**：
```
这篇论文的模型效果怎么样？
```

**技能输出**（应用data-extraction技能）：
```
## 实验效果摘要

从论文 Results 章节提取的性能数据：

### 主要指标：
- **Test Accuracy**: 94.1%
- **Test F1-Score**: 0.931
- **Validation Accuracy**: 93.8%

### 与基线对比：
- BERT-base baseline: 92.3% accuracy
- 性能提升: +1.8 percentage points
- 统计显著性: p < 0.05 (显著)

### 数据集：
- IMDB: 94.1% accuracy
- SST-2: 91.7% accuracy
- AG News: 93.4% accuracy

**总体评价**：模型在所有三个数据集上均超越基线，
在IMDB上达到最佳效果（94.1%）。
```

## 高级技巧

### 处理不规范的表格

有些论文中的表格格式不规范：
```
原文：
Results:
Model A: 92.3
Model B: 89.1
Model C: 94.2

识别为隐式表格：
| Model | Accuracy |
|-------|----------|
| A     | 92.3%    |
| B     | 89.1%    |
| C     | 94.2%    |
```

### 处理多级表头

```
|           | Dataset 1 |       | Dataset 2 |       |
|-----------|-----------|-------|-----------|-------|
| Model     | Acc       | F1    | Acc       | F1    |
| BERT      | 92.3      | 0.915 | 88.5      | 0.872 |

解析为嵌套结构：
{
  "Dataset 1": {"Acc": 92.3, "F1": 0.915},
  "Dataset 2": {"Acc": 88.5, "F1": 0.872}
}
```

### 处理缺失数据

```
| Model | Acc  | F1    |
|-------|------|-------|
| BERT  | 92.3 | 0.915 |
| GPT-2 | 89.1 | -     |
| RoBERTa | 94.2 | 0.937 |

标注：GPT-2 的 F1 分数未报告（原文未提供）
```

