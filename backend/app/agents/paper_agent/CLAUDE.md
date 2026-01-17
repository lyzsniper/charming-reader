# Paper Agent - 论文智能体

[根目录](../../../CLAUDE.md) > [backend](../../CLAUDE.md) > [agents](../CLAUDE.md) > **paper_agent**

## 模块职责

Paper Agent 是整个系统的核心智能组件，基于 Google ADK (Agent Development Kit) 构建，负责理解和响应用户的学术研究需求。该模块通过集成技能系统，实现论文分析、文献检索、知识问答等功能。

## 入口与启动

### 主要入口文件
- `agent.py` - Agent创建和管理核心逻辑
- `__init__.py` - 模块初始化

### Agent创建函数
```python
# 创建带有激活技能的Agent
agent = await create_agent_with_skills()

# 创建基础Agent（不包含技能）
agent = create_agent()
```

## 对外接口

### 核心接口
```python
async def create_agent_with_skills() -> Agent:
    """创建带有激活技能的Agent"""
    # 1. 获取激活的技能内容
    skills_prompt = skills_manager.get_skills_prompt_extension()

    # 2. 合并基础instruction和技能prompt
    full_instruction = base_instruction + "\n\n" + skills_prompt

    # 3. 初始化LLM模型
    model = LiteLlm(...)

    # 4. 创建Agent实例
    agent = Agent(...)

    return agent
```

### 技能集成接口
- 自动检测GitHub技能激活状态
- 动态加载GitHub MCP工具
- 技能prompt注入机制

## 关键依赖与配置

### 依赖项
```python
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from skills.manager import skills_manager
from tools.mcp_tool_adapter import get_github_mcp_tools
```

### 基础Instruction
```python
base_instruction = """You are an academic research assistant.
Your goal is to help users find and understand academic papers.
You have access to a scholar search tool to find real papers and a knowledge retriever to look up information in uploaded documents.
Always cite your sources when providing information from papers.

IMPORTANT: When using tools, you must use the EXACT tool names that are available in your tools list.
Do not invent tool names. If a tool doesn't exist or fails, gracefully handle the error and try alternative approaches.
Tool failures should not block the conversation - provide helpful feedback and continue with available methods."""
```

### 模型配置
```python
model = LiteLlm(
    model="openai/" + settings.DEFAULT_LLM_MODEL,
    api_base=settings.QWEN_BASE_URL,
    api_key=settings.QWEN_API_KEY,
    custom_llm_provider="openai"
)
```

## 数据模型

### Agent状态管理
- 使用 `AgentState` TypedDict 定义状态结构
- 支持问题、上下文、答案、来源等字段

### 技能状态
- 通过 `skills_manager` 管理激活的技能
- 支持技能prompt动态注入
- GitHub MCP工具集成

## 测试与质量

### 测试策略
- 单元测试：Agent创建逻辑
- 集成测试：技能注入功能
- 端到端测试：完整对话流程

### 质量保证
- 日志记录：关键操作和错误处理
- 异常处理：工具失败优雅降级
- 配置验证：模型和API密钥检查

## 常见问题 (FAQ)

### Q: 如何添加新的技能？
A: 在 `.claude/skills/` 目录下创建新的技能目录，按照SKILL.md模板定义技能，技能管理器会自动加载。

### Q: GitHub MCP工具如何集成？
A: 当检测到 `github-integration` 技能激活时，系统会自动：
1. 导入 `tools.mcp_tool_adapter`
2. 调用 `get_github_mcp_tools()` 获取工具列表
3. 将工具添加到Agent的工具列表中

### Q: 如何修改Agent的基础行为？
A: 修改 `base_instruction` 字符串，或在 `create_agent_with_skills()` 函数中添加额外的instruction逻辑。

## 相关文件清单

### 核心文件
- `agent.py` - Agent主要实现
- `__init__.py` - 模块初始化

### 相关模块
- `../../skills/manager.py` - 技能管理器
- `../../tools/mcp_tool_adapter.py` - MCP工具适配器
- `../flow.py` - Agent流程控制

### 配置文件
- `../../../core/config.py` - 全局配置

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新Agent接口文档
- ✅ 完善技能集成说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*