# Agent Skills中心 - 快速开始指南

## 🎉 项目概述

Agent Skills中心是PaperAgent的核心扩展功能，提供：
- ✅ Skills动态管理（文件+数据库混合模式）
- ✅ Agent配置可视化
- ✅ Tools统一注册
- ✅ 运行时监控

**完成度**: 80% (核心功能完整，高级UI待补充)

## 🚀 快速启动

### 1. 后端设置

```bash
cd backend

# 运行数据库迁移
alembic upgrade head

# 注册API路由
# 编辑 app/main.py，添加：
from api.agent_skills_center import router as skills_center_router
app.include_router(skills_center_router, prefix="/api")

# 启动服务
python -m uvicorn app.main:app --reload --port 18000
```

### 2. 前端设置

```bash
cd frontend

# 安装依赖（如果需要）
npm install lucide-react

# 添加路由到 App.tsx
import { SkillsMarket } from './components/skills/SkillsMarket';
import { ConfigPanel } from './components/config-panel/ConfigPanel';

# 在路由配置中添加：
<Route path="/skills-market" element={<SkillsMarket />} />
<Route path="/config-panel" element={<ConfigPanel />} />

# 启动开发服务器
npm run dev
```

### 3. 访问功能

- Skills市场: http://localhost:5173/skills-market
- 配置面板: http://localhost:5173/config-panel
- API文档: http://localhost:18000/docs

## 📚 API端点

### Skills相关
- `GET /api/skills` - 列出所有Skills
- `GET /api/skills/popular` - 热门Skills
- `GET /api/skills/{id}` - Skill详情
- `POST /api/skills` - 创建Skill
- `PUT /api/skills/{id}` - 更新Skill
- `DELETE /api/skills/{id}` - 删除Skill
- `POST /api/skills/sync` - 文件系统同步

### Agent Config相关
- `GET /api/agent-configs` - 列出配置
- `GET /api/agent-configs/{id}` - 配置详情
- `POST /api/agent-configs` - 创建配置
- `POST /api/agent-configs/{id}/skills` - 分配Skills
- `POST /api/agent-configs/{id}/tools` - 分配Tools

### Tools相关
- `GET /api/tools` - 列出Tools
- `POST /api/tools` - 创建Tool
- `POST /api/tools/discover` - 发现MCP工具

### Runtime监控
- `GET /api/runtime/skills/active` - 当前激活Skills
- `GET /api/runtime/agents/{id}/stats` - Agent统计
- `GET /api/runtime/skills/{id}/logs` - Skill激活日志

## 🧪 测试示例

### 同步文件系统Skills

```bash
curl -X POST http://localhost:18000/api/skills/sync
```

### 创建Agent配置

```bash
curl -X POST http://localhost:18000/api/agent-configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-custom-agent",
    "display_name": "我的自定义Agent",
    "instruction": "You are a helpful assistant...",
    "skill_ids": [],
    "tool_ids": []
  }'
```

### 列出所有Skills

```bash
curl http://localhost:18000/api/skills?limit=20
```

## 📁 文件结构

```
backend/
├── alembic/versions/
│   └── 13_add_agent_skills_center_tables.py  # 数据库迁移
├── app/
│   ├── dao/                    # 数据访问层
│   │   ├── skill_dao.py
│   │   ├── agent_config_dao.py
│   │   ├── tool_dao.py
│   │   └── runtime_dao.py
│   ├── services/               # 业务逻辑层
│   │   ├── skill_service.py
│   │   ├── agent_service.py
│   │   ├── tool_service.py
│   │   └── runtime_monitor_service.py
│   └── api/
│       └── agent_skills_center.py  # API端点

frontend/src/
├── services/
│   └── agentSkillsApi.ts      # API客户端
├── components/
│   ├── skills/
│   │   └── SkillsMarket.tsx   # Skills市场
│   └── config-panel/
│       ├── ConfigPanel.tsx    # 配置面板
│       └── SkillsTable.tsx    # Skills表格
```

## 🔧 配置说明

### 混合加载模式

Skills支持两种来源：
1. **文件系统** (`.claude/skills/`) - 开发者Skills，Git追踪
2. **数据库** - 用户自定义Skills，动态创建

优先级：文件系统 > 数据库

### 同步策略

- 启动时自动扫描文件系统
- 手动点击"同步"按钮
- 版本检查：文件版本更高时更新数据库

## 🐛 常见问题

### 1. 数据库迁移失败

**错误**: `metadata` is reserved
**解决**: 已修复，重新运行 `alembic upgrade head`

### 2. API 404错误

**原因**: 未注册API路由
**解决**: 在 `main.py` 中添加router注册

### 3. 前端类型错误

**原因**: 缺少类型定义
**解决**: 确保导入 `agentSkillsApi.ts` 中的类型

## 📈 下一步开发

### 立即可做
- [x] 测试Skills市场功能
- [x] 测试同步功能
- [ ] 完善创建/编辑对话框
- [ ] 添加删除确认提示

### 短期目标（1周）
- [ ] 完善AgentsTable组件
- [ ] 完善ToolsTable组件
- [ ] 添加表单验证
- [ ] 错误处理优化

### 中期目标（2-3周）
- [ ] Agent构建器（拖拽UI）
- [ ] 运行时监控图表
- [ ] Skills评分系统
- [ ] 批量操作功能

## 🤝 贡献指南

1. 遵循现有代码风格
2. 后端：Python类型注解 + Pydantic验证
3. 前端：TypeScript + ESLint
4. 提交前运行测试

## 📞 支持

如有问题，请查看：
- `IMPLEMENTATION_SUMMARY.md` - 详细实施文档
- `CLAUDE.md` - 项目架构文档
- API文档: `/docs`

---

**版本**: 1.0.0  
**最后更新**: 2026-01-25  
**状态**: 核心功能就绪，高级UI待完善
