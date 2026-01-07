# Agent Skills 开发指南

本指南面向开发者，详细说明如何为 PaperAgent 创建、测试和贡献新的技能。

## Skills 概述

Agent Skills 是 Anthropic 提出的开放标准，用于给 AI Agent 提供可复用的专业能力。每个技能是一个独立的文件夹，包含指令、参考资料和辅助脚本。

### 为什么使用 Skills？

- **模块化**：技能独立开发和维护
- **可复用**：一次编写，多处使用（IDE、运行时）
- **可扩展**：轻松添加新能力
- **标准化**：遵循开放规范，兼容多种工具

## 技能结构

### 标准目录结构

```
.claude/skills/my-skill/
├── SKILL.md              # 主文件（必需）
├── references/           # 参考文档（可选）
│   ├── guide.md
│   └── examples.md
├── scripts/              # 辅助脚本（可选）
│   └── helper.py
├── templates/            # 模板文件（可选）
│   └── template.md
└── assets/               # 其他资源（可选）
    └── diagram.png
```

### SKILL.md 格式

SKILL.md 是技能的核心文件，包含两部分：

1. **YAML Frontmatter**（元数据）
2. **Markdown Body**（指令内容）

#### 完整示例

```markdown
---
name: my-skill
description: 简洁的一句话描述（不超过100字）
triggers:
  - trigger word 1
  - trigger word 2
  - 触发词3
version: 1.0.0
---

# 技能标题

## 目标

简明扼要说明此技能的目的。

## 核心能力

列出技能提供的主要能力。

## 使用指南

### 何时使用此技能

描述适用场景。

### 如何使用此技能

提供具体使用方法。

## 注意事项

列出使用时需要注意的要点。

## 示例

提供具体的使用示例。
```

## 创建新技能

### 步骤1：规划技能

回答以下问题：

1. **目标是什么？** 技能要解决什么问题？
2. **适用场景？** 什么情况下使用此技能？
3. **输入输出？** 需要什么输入，产生什么输出？
4. **依赖关系？** 是否依赖其他技能或资源？

### 步骤2：创建目录和文件

```bash
mkdir -p .claude/skills/my-skill
cd .claude/skills/my-skill
touch SKILL.md
```

### 步骤3：编写元数据

在 SKILL.md 顶部添加 YAML frontmatter：

```yaml
---
name: my-skill               # 唯一标识符，使用 kebab-case
description: 技能的简短描述  # 50-100字，说明技能作用
triggers:                    # 触发关键词列表
  - main trigger
  - alternative phrase
  - 中文触发词
version: 1.0.0              # 语义化版本号
---
```

**命名规范**：
- `name`: 小写字母，连字符分隔（如 `paper-analysis`）
- `description`: 清晰简洁，避免技术术语
- `triggers`: 用户可能输入的自然语言短语

### 步骤4：编写指令内容

使用祈使句编写清晰的指令：

#### 好的示例

```markdown
## 何时使用

当用户需要分析论文结构时，使用此技能。

## 分析步骤

1. **识别章节**：找到 Introduction, Methods, Results, Discussion
2. **提取关键信息**：
   - 研究问题：明确的问题陈述
   - 方法论：使用的技术和方法
   - 主要发现：核心实验结果

3. **生成报告**：按照以下格式输出
   
## 研究概览
[一段话概述]

## 方法论
- 技术：...
- 数据：...
```

#### 避免的写法

```markdown
❌ "你可能想要分析论文..."（不明确）
✓ "当用户请求分析论文时..."（明确）

❌ "尝试找到研究问题"（模糊）
✓ "识别明确的研究问题陈述"（具体）

❌ "参考XXX"（假设知识）
✓ "使用references/guide.md中的结构"（明确引用）
```

### 步骤5：添加参考资源

如果技能需要详细的参考信息：

```bash
mkdir references
echo "# 详细指南" > references/guide.md
```

在 SKILL.md 中引用：

```markdown
详细的引用格式说明请参考 `references/apa-format.md`。
```

### 步骤6：测试技能

#### 本地测试

1. 重启 PaperAgent 后端
2. 调用 API 检查技能是否加载：

```bash
curl http://localhost:8000/api/skills
```

3. 尝试激活技能：

```bash
curl -X POST http://localhost:8000/api/skills/my-skill/activate
```

4. 测试触发词：

发送包含触发词的查询，观察技能是否被激活。

#### IDE 测试

在 Cursor 或 Claude Code 中：

1. 打开项目
2. 询问包含触发词的问题
3. 观察 AI 是否应用了技能知识

### 步骤7：文档化

更新 `AGENTS.md`：

```bash
npm run skills:sync
```

## 技能编写最佳实践

### 1. 清晰的结构

使用一致的章节结构：

```markdown
## 目标
## 核心能力
## 使用指南
  ### 何时使用
  ### 如何使用
## 注意事项
## 示例
## 参考资源
```

### 2. 具体的指令

❌ 不好：
```markdown
帮用户分析论文
```

✓ 好：
```markdown
按照 IMRaD 结构（Introduction, Methods, Results, Discussion）
分析论文各部分，提取：
- 研究问题（1-2句）
- 方法论（使用的技术、数据集）
- 主要发现（关键数值结果）
- 创新点（与现有工作的区别）
```

### 3. 实用的示例

提供完整的输入输出示例：

```markdown
## 示例

**用户输入**：
"分析这篇论文的贡献"

**技能输出**：
## 论文贡献分析

### 理论贡献
- 提出了新的...模型

### 方法贡献
- 改进了...算法，速度提升30%

### 实证贡献
- 在3个数据集上达到SOTA
```

### 4. 适当的粒度

- **太粗**：只说"分析论文"
- **太细**：详细到每个字段的格式
- **刚好**：提供结构框架和关键要点

### 5. 避免重复

如果多个技能有相似的内容，考虑：

1. 创建共享的参考文档
2. 技能间引用（如 "配合 citation-management 技能"）
3. 提取公共部分到基础技能

## 高级特性

### 1. 条件逻辑

```markdown
如果查询包含"系统综述"：
    使用系统综述模板
否则如果查询包含"叙事性综述"：
    使用叙事性综述模板
否则：
    询问用户需要哪种类型
```

### 2. 多步骤工作流

```markdown
## 工作流程

### 第一步：信息收集
[详细步骤]

### 第二步：数据分析
[详细步骤]

### 第三步：结果生成
[详细步骤]
```

### 3. 输出格式模板

```markdown
## 输出格式

```
## [标题]

### 1. [部分1]
- 要点1
- 要点2

### 2. [部分2]
...
```（注：原markdown需要转义）
```

### 4. 错误处理

```markdown
## 常见问题处理

**如果缺少必要信息**：
- 明确告知用户缺少什么信息
- 不要猜测或编造

**如果格式不规范**：
- 尽力解析
- 标注不确定的部分

**如果超出能力范围**：
- 坦诚说明限制
- 建议替代方案
```

## 辅助脚本

如果技能需要计算或解析：

```python
# scripts/helper.py
def parse_table(text: str) -> dict:
    """
    Parse markdown table to structured data.
    
    Args:
        text: Markdown table text
    
    Returns:
        Parsed table dictionary
    """
    # implementation
    pass
```

在 SKILL.md 中引用：

```markdown
对于复杂表格，可以使用 `scripts/table_parser.py` 辅助解析。
```

**注意**：脚本应该：
- 有清晰的文档
- 处理边界情况
- 不依赖外部服务
- 快速执行（<1秒）

## 版本管理

### 语义化版本

`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的更改（如改变输出格式）
- **MINOR**: 向后兼容的新功能
- **PATCH**: 向后兼容的修复

示例：
- `1.0.0` → `1.0.1`: 修复文档错误
- `1.0.0` → `1.1.0`: 添加新的分析维度
- `1.0.0` → `2.0.0`: 改变输出结构

### 更新日志

在技能目录添加 `CHANGELOG.md`：

```markdown
# Changelog

## [1.1.0] - 2024-01-15
### Added
- 支持多级表头解析

### Fixed
- 修复百分比识别错误

## [1.0.0] - 2024-01-01
- 初始发布
```

## 测试清单

发布技能前，检查：

### 内容质量
- [ ] 元数据完整且准确
- [ ] 指令清晰无歧义
- [ ] 包含实用示例
- [ ] 列出注意事项
- [ ] 引用的资源存在且正确

### 技术验证
- [ ] YAML frontmatter 格式正确
- [ ] 文件路径使用相对路径
- [ ] 没有语法错误
- [ ] 触发词合理

### 功能测试
- [ ] 技能能被正确加载
- [ ] 触发词能匹配到技能
- [ ] 激活后指令被应用
- [ ] 与其他技能协作正常

### 用户体验
- [ ] 文档易于理解
- [ ] 示例覆盖常见场景
- [ ] 错误提示友好
- [ ] 输出格式一致

## 贡献技能

### 提交流程

1. Fork 项目仓库
2. 创建技能分支：`git checkout -b skill/my-skill`
3. 创建技能目录和文件
4. 测试技能功能
5. 提交代码：`git commit -m "Add my-skill"`
6. 推送分支：`git push origin skill/my-skill`
7. 创建 Pull Request

### PR 描述模板

```markdown
## 技能信息

- **名称**: my-skill
- **类别**: 数据分析 / 文献处理 / 其他
- **版本**: 1.0.0

## 功能描述

简要描述技能的功能和使用场景。

## 测试情况

- [x] 本地测试通过
- [x] IDE 集成测试
- [x] 与其他技能协作正常

## 示例用法

提供技能的实际使用示例。

## 额外说明

其他需要说明的内容。
```

## 常见问题

**Q: 技能多大合适？**
A: 单个专注的职责。通常 SKILL.md 在 200-1000 行之间。过大考虑拆分。

**Q: 技能可以互相引用吗？**
A: 可以。在指令中提及"配合 XXX 技能使用"。但避免强依赖。

**Q: 如何处理敏感信息？**
A: 不要在技能中硬编码密钥或敏感数据。使用环境变量或配置文件。

**Q: 技能可以调用外部 API 吗？**
A: 技能本身是指令，不直接调用 API。如需外部数据，应创建 Agent Tool。

**Q: 如何调试技能？**
A: 
1. 检查加载日志
2. 调用 `/api/skills/{name}` 查看技能信息
3. 激活技能后发送测试查询
4. 查看 Agent 响应是否应用了技能指导

**Q: 技能会自动更新吗？**
A: 文件修改后需要重启服务或调用 reload API。开发模式可配置热重载。

## 资源

- [Agent Skills 规范](https://github.com/agentskills/agentskills)
- [示例技能库](https://github.com/anthropics/skills)
- [PaperAgent 现有技能](.claude/skills/)
- [Anthropic 技能编写指南](https://docs.anthropic.com/skills)

---

开始创建您的第一个技能吧！如有问题，欢迎在项目仓库提 Issue。

