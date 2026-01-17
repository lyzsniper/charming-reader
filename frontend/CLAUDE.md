# Frontend - 前端用户界面

[根目录](../../CLAUDE.md) > **frontend**

## 模块职责

Frontend 模块是 PaperAgent 的用户界面，基于 React 19 和 TypeScript 构建，提供现代化的Web应用体验。该模块采用组件化设计，支持响应式布局，提供直观的论文管理、知识库操作和对话交互功能。

## 入口与启动

### 主入口文件
- `src/main.tsx` - React应用入口
- `src/App.tsx` - 主应用组件
- 启动命令：`npm run dev`

### 关键配置
- Vite配置：`vite.config.ts`
- TypeScript配置：`tsconfig.json`
- Tailwind配置：`tailwind.config.js`

## 对外接口

### 组件接口
应用采用组件化架构，主要组件包括：

#### 核心视图组件
- `HomeView` - 首页视图
- `WorkspaceView` - 工作区视图
- `Sidebar` - 侧边栏导航

#### 功能组件
- `ChatPanel` - 对话面板
- `ContextPanel` - 上下文面板
- `KnowledgeView` - 知识库管理
- `SettingsModal` - 设置模态框

### API 服务
- `src/services/api.ts` - 后端API封装
- 支持RESTful调用和WebSocket连接

## 关键依赖与配置

### 核心依赖
```json
{
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "typescript": "~5.9.3",
    "vite": "^7.2.4",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-slot": "^1.2.4",
    "tailwindcss": "^3.4.17",
    "react-markdown": "^10.1.0",
    "react-pdf": "^10.3.0",
    "framer-motion": "^12.24.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.1",
    "eslint": "^9.39.1",
    "typescript-eslint": "^8.46.4"
  }
}
```

### 环境变量配置
```env
VITE_API_BASE_URL=http://localhost:18000
VITE_WS_URL=ws://localhost:18000
```

## 数据模型

### 状态管理
使用 React Hooks 进行状态管理：
- `useState` - 组件状态
- `useContext` - 全局状态
- `useReducer` - 复杂状态逻辑
- 自定义Hooks封装业务逻辑

### 数据流
```
用户操作 → 组件事件 → API调用 → 后端处理 → 状态更新 → UI刷新
```

## 测试与质量

### 测试结构
```
src/
├── __tests__/          # 测试文件
├── components/         # 组件测试
└── services/          # 服务测试
```

### 代码质量工具
- ESLint: 代码检查
- Prettier: 代码格式化
- TypeScript: 类型检查
- React Testing Library: 组件测试

## 常见问题 (FAQ)

### Q: 如何添加新的UI组件？
A:
1. 在 `src/components/` 下创建新组件目录
2. 遵循现有的组件命名规范（PascalCase）
3. 使用 TypeScript 定义组件Props接口
4. 导出组件并在需要的地方导入

### Q: 如何处理API响应？
A: 使用 `src/services/api.ts` 中的封装方法：
```typescript
// 获取知识库列表
const { data, error, isLoading } = useApi<KnowledgeBase[]>(
  '/api/knowledge-bases'
);

// 发送消息
const sendMessage = async (message: string) => {
  const response = await api.post('/api/chat', { message });
  return response.data;
};
```

### Q: 如何实现主题切换？
A: 使用 `src/hooks/useTheme.tsx` Hook：
```typescript
const { theme, toggleTheme } = useTheme();

// 在组件中使用
<div className={theme === 'dark' ? 'dark' : ''}>
  {/* 内容 */}
</div>
```

## 相关文件清单

### 核心模块
- `src/main.tsx` - 应用入口
- `src/App.tsx` - 主应用组件
- `src/index.css` - 全局样式
- `src/vite-env.d.ts` - 环境类型声明

### 组件模块
- `src/components/` - 所有UI组件
  - `common/` - 通用组件
  - `layout/` - 布局组件
  - `workspace/` - 工作区组件
  - `knowledge/` - 知识库组件
  - `home/` - 首页组件

### 服务和工具
- `src/services/` - API服务
- `src/hooks/` - 自定义Hooks
- `src/utils/` - 工具函数

### 配置文件
- `package.json` - 依赖配置
- `tsconfig.json` - TypeScript配置
- `tailwind.config.js` - Tailwind配置
- `vite.config.ts` - Vite配置

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新组件接口文档
- ✅ 完善配置说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*