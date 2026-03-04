# ✅ Agent Skills中心 - 启动检查清单

## 在启动前，请确认以下事项：

### 后端检查 ✅

- [ ] PostgreSQL 正在运行
- [ ] `.env` 文件配置正确
- [ ] 运行了 `alembic upgrade head`
- [ ] `main.py` 包含以下代码：
  ```python
  from api.agent_skills_center import router as skills_center_router
  app.include_router(skills_center_router, prefix="/api", tags=["Agent Skills Center"])
  ```

### 前端检查 ✅

- [ ] 运行了 `npm install`
- [ ] `App.tsx` 包含新的路由
- [ ] `Sidebar.tsx` 包含新的菜单按钮
- [ ] 所有新组件文件都已创建

### 依赖检查 ✅

**后端依赖** (应该已在 requirements.txt 中):
- fastapi
- sqlalchemy
- alembic
- psycopg2-binary
- pydantic

**前端依赖** (可能需要安装):
```bash
npm install @radix-ui/react-tabs
npm install lucide-react
```

## 🚀 启动命令

### 终端 1 - 后端
```bash
cd backend
alembic upgrade head
python -m uvicorn app.main:app --reload --port 18000
```

### 终端 2 - 前端
```bash
cd frontend
npm run dev
```

## 🎯 验证测试

### 1. 后端验证
访问 http://localhost:18000/docs
- 查找 "Agent Skills Center" 标签
- 应该看到 29 个新的 API 端点

### 2. 前端验证
访问 http://localhost:5173
- 左侧边栏应该有 6 个按钮
- 点击 ✨ 图标 → Skills市场
- 点击 🎛️ 图标 → 配置面板

### 3. 功能验证
在配置面板 > Skills 标签:
- 点击"从文件系统同步"
- 应该看到 `.claude/skills/` 目录下的所有 Skills

## ❌ 如果出现问题

### 后端 404 错误
```bash
# 检查 main.py 是否正确注册路由
grep "skills_center_router" backend/app/main.py
```

### 前端编译错误
```bash
# 重新安装依赖
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 数据库错误
```bash
# 检查数据库连接
cd backend
python -c "from core.db import test_db_connection; print(test_db_connection())"
```

## 📞 获取帮助

查看文档:
- `QUICKSTART.md` - 快速开始
- `FINAL_REPORT.md` - 完整报告
- `FRONTEND_COMPLETION_SUMMARY.md` - 前端详情

---

**准备好了吗？开始启动吧！** 🚀
