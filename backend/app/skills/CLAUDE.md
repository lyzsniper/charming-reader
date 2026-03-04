# Skills - 技能系统

[根目录](../../../docs/CLAUDE.md) > [backend](../../CLAUDE.md) > **skills**

## 模块职责

Skills 模块是 PaperAgent 的可扩展功能系统，基于 Claude 技能架构构建。该模块实现了技能的动态加载、注册、激活和管理，使系统能够根据用户需求动态扩展功能。

## 入口与启动

### 主要入口文件
- `manager.py` - 技能管理器（单例模式）
- `loader.py` - 技能加载器
- `registry.py` - 技能注册表
- `activator.py` - 技能激活器

### 全局实例
```python
# 全局技能管理器实例
skills_manager = SkillsManager()
```

## 对外接口

### 核心接口
```python
# 列出所有可用技能
skills = skills_manager.list_all_skills()

# 获取指定技能信息
skill_info = skills_manager.get_skill_info("paper-analysis")

# 激活/停用技能
success = skills_manager.activate_skill("github-integration")
success = skills_manager.deactivate_skill("github-integration")

# 获取激活的技能
active_skills = skills_manager.get_active_skills()

# 根据查询自动激活技能
activated = skills_manager.auto_activate_for_query("分析这篇论文的方法论")

# 获取技能prompt扩展
skills_prompt = skills_manager.get_skills_prompt_extension()
```

### 技能推荐
```python
# 为查询推荐技能
suggestions = skills_manager.suggest_skills("如何写文献综述", top_k=3)
```

## 关键依赖与配置

### 依赖项
```python
from .loader import SkillLoader
from .registry import SkillRegistry, Skill
from .activator import SkillActivator
from core.config import settings
```

### 配置项
```python
# 在 core/config.py 中
SKILLS_DIR: str = ".claude/skills"           # 技能目录
SKILLS_AUTO_ACTIVATION: bool = True          # 自动激活
SKILLS_MAX_CONCURRENT: int = 3               # 最大并发技能数
```

### 技能目录结构
```
.claude/skills/
├── paper-analysis/
│   ├── SKILL.md
│   └── scripts/
├── literature-review/
│   ├── SKILL.md
│   └── templates/
├── citation-management/
│   ├── SKILL.md
│   └── references/
└── github-integration/
    └── SKILL.md
```

## 数据模型

### 技能元数据
```python
class Skill:
    name: str
    description: str
    triggers: List[str]          # 触发词列表
    version: str
    file_path: str
    is_active: bool = False
```

### 技能统计信息
```python
{
    "loader": {"total_skills": 6, "loaded_skills": 6},
    "registry": {"total_skills": 6, "active_skills": 2},
    "activator": {"activation_count": 15, "success_rate": 100}
}
```

## 测试与质量

### 技能测试
- 技能元数据加载测试
- 触发词匹配测试
- 技能激活/停用测试
- 自动激活算法测试

### 质量保证
- 技能文件格式验证
- 循环依赖检测
- 技能冲突处理
- 性能监控（加载时间、激活时间）

## 常见问题 (FAQ)

### Q: 如何添加新技能？
A:
1. 在 `.claude/skills/` 下创建新技能目录
2. 创建 `SKILL.md` 文件，定义技能元数据
3. 可选：添加脚本或模板文件
4. 重启应用或调用 `skills_manager.reload_skills()`

### Q: 技能触发词如何工作？
A: 每个技能定义一组触发词（中英文），当用户查询包含这些词时，技能会被自动激活。触发词匹配采用模糊匹配算法。

### Q: 技能冲突如何解决？
A: 系统采用以下策略：
1. 后激活的技能覆盖先前的技能
2. 相同触发词的技能，优先级高的获胜
3. 提供技能统计信息供分析

### Q: 如何调试技能系统？
A:
```python
# 查看技能加载状态
stats = skills_manager.get_statistics()
print(stats)

# 检查特定技能
skill = skills_manager.get_skill_info("paper-analysis")
print(skill)

# 重新加载技能
skills_manager.reload_skills()
```

## 相关文件清单

### 核心模块
- `manager.py` - 技能管理器
- `loader.py` - 技能加载器
- `registry.py` - 技能注册表
- `activator.py` - 技能激活器
- `__init__.py` - 模块初始化

### 配置和工具
- `../../core/config.py` - 技能配置
- `../../tools/definitions.py` - 工具定义

### 技能示例
- `../../../.claude/skills/paper-analysis/` - 论文分析技能
- `../../../.claude/skills/literature-review/` - 文献综述技能
- `../../../.claude/skills/citation-management/` - 引文管理技能

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新技能系统接口文档
- ✅ 完善技能管理说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*