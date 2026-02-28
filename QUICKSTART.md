# 🚀 Agent Skills中心 - 快速启动指南

## 立即开始使用

### 第1步：启动后端

```bash
cd backend

# 1. 运行数据库迁移（仅首次需要）
alembic upgrade head

# 2. 确保API路由已注册（检查 app/main.py）
# 应包含：
# from api.agent_skills_center import router as skills_center_router
# app.include_router(skills_center_router, prefix="/api")

# 3. 启动服务
python -m uvicorn app.main:app --reload --port 18000
```

### 第2步：启动前端

```bash
cd frontend

# 如果缺少依赖，先安装
npm install

# 启动开发服务器
npm run dev
```

### 第3步：访问新功能

打开浏览器访问: **http://localhost:5173**

在左侧边栏中找到：
- **✨ Sparkles图标** → Skills市场
- **🎛️ Sliders图标** → 配置管理面板

## 📍 注册API路由

如果后端API返回404，需要在 `backend/app/main.py` 中添加路由注册：

```python
# 在文件顶部导入
from api.agent_skills_center import router as skills_center_router

# 在app实例化后添加
app.include_router(skills_center_router, prefix="/api", tags=["Agent Skills Center"])
```

## 🎯 功能快速测试

### 1. Skills市场（推荐首先访问）
1. 点击左侧 **Sparkles图标**
2. 浏览Skills卡片
3. 使用搜索框搜索
4. 点击分类按钮过滤
5. 点击任意卡片查看详情

### 2. Skills管理
1. 点击左侧 **Sliders图标**
2. 确保在"Skills"标签
3. 点击"从文件系统同步"按钮
4. 查看Skills列表（应显示.claude/skills/目录下的所有Skills）

### 3. Agent配置
1. 在配置面板中切换到"Agents"标签
2. 点击"新建Agent"
3. 填写表单：
   - 名称: `test-agent`
   - 显示名称: `测试助手`
   - 指令: `You are a helpful assistant.`
4. 点击"创建"
5. 在列表中看到新创建的Agent
6. 点击编辑按钮修改
7. 点击删除按钮删除

### 4. Tools管理
1. 切换到"Tools"标签
2. 点击"发现MCP工具"（自动扫描注册MCP工具）
3. 或点击"新建Tool"手动创建
4. 查看Tool列表和统计

## ⚠️ 常见问题

### Q1: 点击菜单没反应？
**A**: 检查浏览器控制台是否有错误，确保前端正确编译。

### Q2: API返回404？
**A**: 确保后端API路由已注册（见上方"注册API路由"）。

### Q3: Skills列表为空？
**A**: 点击"从文件系统同步"按钮，将.claude/skills/目录下的Skills导入数据库。

### Q4: 数据库迁移失败？
**A**: 确保PostgreSQL正在运行，检查.env中的数据库配置。

### Q5: 前端编译错误？
**A**: 运行 `npm install` 确保所有依赖已安装。

## 📚 更多文档

- **详细实施文档**: `IMPLEMENTATION_SUMMARY.md`
- **前端补完文档**: `FRONTEND_COMPLETION_SUMMARY.md`
- **API文档**: http://localhost:18000/docs (启动后端后访问)

## 🎉 享受使用！

现在你可以：
- ✅ 浏览Skills市场
- ✅ 管理Agent配置
- ✅ 注册和发现Tools
- ✅ 从文件系统同步Skills
- ✅ 创建自定义Agent

Happy Coding! 🚀
