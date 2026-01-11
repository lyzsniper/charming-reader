# Agent Skills 验证演示

这是一个轻量化的 Agent Skills 验证项目，用于快速测试和验证技能系统的功能。

## 项目结构

```
agent-demo/
├── config.py          # 简化配置
├── agent.py           # Agent 实现（使用 Google ADK + LiteLLM）
├── main.py            # 主入口文件
├── requirements.txt   # 依赖列表
├── README.md          # 本文档
└── skills/            # 技能系统（从 backend 复制）
    ├── __init__.py
    ├── loader.py      # 技能加载器
    ├── registry.py    # 技能注册表
    ├── activator.py   # 技能激活器
    └── manager.py     # 技能管理器
```

## 功能特点

- ✅ **轻量化**：不依赖数据库、RAG 等复杂系统
- ✅ **独立运行**：与 backend 项目完全分离
- ✅ **自动激活**：根据用户查询自动匹配和激活技能
- ✅ **实时验证**：交互式测试技能功能

## 快速开始

### 1. 安装依赖

```bash
cd agent-demo
pip install -r requirements.txt
```

### 2. 配置 API Key

在 `config.py` 中设置你的 API Key，或通过环境变量：

```bash
export QWEN_API_KEY="your_key"
export GLM_API_KEY="your_key"
export DEFAULT_LLM_MODEL="qwen-flash-2025-07-28"
```

### 3. 运行演示

**交互模式**（推荐）：
```bash
python main.py
```

**测试模式**（运行预设测试用例）：
```bash
python main.py test
```

## 使用示例

### 交互式使用

启动后，输入查询即可自动激活相关技能：

```
👤 您: 帮我分析这篇论文的研究方法

[技能激活] 已激活 1 个技能:
  - paper-analysis: 论文深度分析

[技能注入] 已将 1 个技能注入 Agent 上下文

🤖 Agent: [根据 paper-analysis 技能生成的回答]
```

### 测试查询示例

- `"帮我分析这篇论文"` → 激活 `paper-analysis` 技能
- `"格式化引用"` → 激活 `citation-management` 技能
- `"生成文献综述"` → 激活 `literature-review` 技能
- `"优化检索"` → 激活 `rag-enhancement` 技能

## 技能系统说明

### 技能目录

技能文件位于项目根目录的 `.claude/skills/`，与 backend 项目共享。

### 自动激活机制

1. **触发词匹配**：系统根据查询中的关键词匹配技能
2. **自动激活**：匹配到的技能自动激活（最多 2 个）
3. **内容注入**：激活的技能内容注入到 Agent 的 instruction 中
4. **智能管理**：超过最大并发数时，自动停用最旧的技能

### 技能状态

- `available` - 可用但未加载
- `loaded` - 已加载元数据
- `active` - 已激活（完整内容已加载）

## 配置说明

在 `config.py` 中可以配置：

```python
# 模型配置
DEFAULT_LLM_MODEL = "qwen-flash-2025-07-28"

# 技能配置
SKILLS_DIR = "../.claude/skills"           # 技能目录
SKILLS_AUTO_ACTIVATION = True             # 是否自动激活
SKILLS_MAX_CONCURRENT = 3                  # 最大并发技能数
```

## 与 backend 项目的区别

| 特性 | backend | agent-demo |
|------|---------|------------|
| 数据库 | ✅ PostgreSQL | ❌ 无 |
| RAG 系统 | ✅ 完整实现 | ❌ 无 |
| API 接口 | ✅ FastAPI | ❌ 无 |
| 工具函数 | ✅ 多个工具 | ❌ 无 |
| 技能系统 | ✅ 完整 | ✅ 完整 |
| Agent 框架 | ✅ Google ADK | ✅ Google ADK |
| 用途 | 生产环境 | 快速验证 |

## 故障排除

### 技能未加载

检查技能目录路径是否正确：
```python
# config.py
SKILLS_DIR = "../.claude/skills"  # 相对于 agent-demo 目录
```

### API Key 错误

确保设置了正确的 API Key：
```python
# config.py 或环境变量
QWEN_API_KEY = "your_key"
```

### 模型调用失败

检查模型名称和 API 配置是否正确。

## 下一步

验证通过后，可以将技能系统集成到你的实际项目中：

1. 复制 `skills/` 目录到你的项目
2. 在 Agent 初始化时集成技能管理器
3. 根据查询自动激活技能
4. 将技能内容注入 Agent instruction

## 参考文档

- [Agent Skills 集成总结](../docs/Agent_Skills_集成总结.md)
- [Skills 使用指南](../docs/Skills_使用指南.md)
- [Skills 开发指南](../docs/Skills_开发指南.md)
