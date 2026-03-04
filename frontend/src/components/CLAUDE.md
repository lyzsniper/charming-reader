# Components - UI组件库

[根目录](../../../docs/CLAUDE.md) > [frontend](../../CLAUDE.md) > [src](../CLAUDE.md) > **components**

## 模块职责

Components 模块是 PaperAgent 前端的核心UI组件库，采用组件化架构设计，提供可复用的UI组件。该模块基于 Radix UI 和 Tailwind CSS 构建，确保组件的一致性和可维护性。

## 入口与启动

### 主要入口文件
- `App.tsx` - 主应用组件，包含路由和状态管理
- `main.tsx` - React应用入口

### 组件加载流程
```typescript
// 组件按需加载
const HomeView = lazy(() => import('./home/HomeView'));
const WorkspaceView = lazy(() => import('./workspace/WorkspaceView'));

// 全局组件注册
import { Sidebar } from './layout/Sidebar';
import { LoadingSpinner } from './common/LoadingSpinner';
```

## 对外接口

### 组件接口
```typescript
// 主要视图组件
<HomeView onStartChat={handleStartChat} />
<WorkspaceView
  file={currentFile}
  initialMessage={initialMessage}
  onGoHome={handleGoHome}
/>

// 通用组件
<LoadingSpinner fullScreen text="加载中..." />
<ErrorBoundary fallback={<ErrorFallback />}>
  <Component />
</ErrorBoundary>
```

### 状态管理接口
```typescript
// 使用自定义Hooks
const { theme, toggleTheme } = useTheme();
const { shortcuts, registerShortcut } = useKeyboardShortcuts();

// 全局状态
const [viewMode, setViewMode] = useState<'home' | 'workspace'>('home');
const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
```

## 关键依赖与配置

### 依赖项
```json
{
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-slot": "^1.2.4",
    "@radix-ui/react-scroll-area": "^1.2.10",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.4.0",
    "framer-motion": "^12.24.0"
  }
}
```

### 组件库结构
```
components/
├── common/          # 通用组件
│   ├── LoadingSpinner.tsx
│   ├── ErrorBoundary.tsx
│   ├── EmptyState.tsx
│   ├── MarkdownRenderer.tsx
│   └── ...
├── layout/          # 布局组件
│   ├── Sidebar.tsx
│   ├── SettingsModal.tsx
│   ├── HistoryModal.tsx
│   └── ...
├── workspace/       # 工作区组件
│   ├── WorkspaceView.tsx
│   ├── ChatPanel.tsx
│   ├── ContextPanel.tsx
│   └── ThinkingProcess.tsx
├── knowledge/       # 知识库组件
│   ├── KnowledgeView.tsx
│   ├── KnowledgeModal.tsx
│   └── ...
└── home/           # 首页组件
    └── HomeView.tsx
```

### 样式配置
```typescript
// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

## 组件详解

### 1. 通用组件 (common/)

#### LoadingSpinner
```typescript
interface LoadingSpinnerProps {
  fullScreen?: boolean;
  text?: string;
  size?: "sm" | "md" | "lg";
}

// 使用示例
<LoadingSpinner fullScreen text="正在加载..." />
```

#### ErrorBoundary
```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

// 使用示例
<ErrorBoundary fallback={<div>出错了</div>}>
  <Component />
</ErrorBoundary>
```

#### MarkdownRenderer
```typescript
interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// 使用示例
<MarkdownRenderer content={markdownContent} />
```

### 2. 布局组件 (layout/)

#### Sidebar
```typescript
interface SidebarProps {
  viewMode: 'home' | 'workspace';
  isKnowledgeOpen: boolean;
  isHistoryOpen: boolean;
  isSettingsOpen: boolean;
  onOpenKnowledge: () => void;
  onOpenHistory: () => void;
  onOpenSettings: () => void;
  onGoHome: () => void;
}

// 使用示例
<Sidebar
  viewMode={viewMode}
  onOpenKnowledge={handleOpenKnowledge}
  onGoHome={handleGoHome}
/>
```

#### SettingsModal
```typescript
interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// 使用示例
<SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
```

### 3. 工作区组件 (workspace/)

#### WorkspaceView
```typescript
interface WorkspaceViewProps {
  file: File | null;
  initialMessage: string | null;
  conversationKey: number;
  onGoHome: () => void;
  isKnowledgeOpen: boolean;
  onKnowledgeClose: () => void;
  initialKnowledgeBaseIds: string[];
  initialSessionId: string | null;
}

// 使用示例
<WorkspaceView
  file={currentFile}
  initialMessage={initialMessage}
  conversationKey={conversationKey}
  onGoHome={handleGoHome}
/>
```

#### ChatPanel
```typescript
interface ChatPanelProps {
  sessionId: string | null;
  knowledgeBaseIds: string[];
}

// 使用示例
<ChatPanel sessionId={selectedSessionId} knowledgeBaseIds={selectedKnowledgeBaseIds} />
```

### 4. 知识库组件 (knowledge/)

#### KnowledgeView
```typescript
interface KnowledgeViewProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectKnowledgeBase: (id: string) => void;
}

// 使用示例
<KnowledgeView
  isOpen={isKnowledgeOpen}
  onClose={() => setIsKnowledgeOpen(false)}
  onSelectKnowledgeBase={handleKnowledgeBaseSelect}
/>
```

## 自定义Hooks

### useTheme
```typescript
const { theme, toggleTheme } = useTheme();

// 在组件中使用
<div className={theme === 'dark' ? 'dark' : ''}>
  {/* 内容 */}
</div>
```

### useKeyboardShortcuts
```typescript
const shortcuts = useKeyboardShortcuts([
  {
    key: 'k',
    action: () => console.log('快捷键触发'),
  },
]);
```

## 测试与质量

### 测试策略
- 组件测试：React Testing Library
- 快照测试：Jest
- E2E测试：Playwright（计划中）

### 代码质量
- TypeScript严格模式
- ESLint + Prettier
- 组件Props类型定义
- 无障碍性考虑

## 常见问题 (FAQ)

### Q: 如何添加新组件？
A:
1. 在相应目录创建组件文件
2. 遵循现有的命名规范（PascalCase）
3. 使用 TypeScript 定义 Props 接口
4. 导出组件并在需要的地方导入

### Q: 如何处理主题切换？
A: 使用 `useTheme` Hook：
```typescript
// 在组件中
const { theme, toggleTheme } = useTheme();

// 切换主题
<button onClick={toggleTheme}>切换主题</button>

// 应用主题
<div className={theme === 'dark' ? 'dark' : ''}>
  {/* 内容 */}
</div>
```

### Q: 如何实现懒加载？
A: 使用 React.lazy 和 Suspense：
```typescript
const LazyComponent = lazy(() => import('./LazyComponent'));

// 在组件中使用
<Suspense fallback={<LoadingSpinner />}>
  <LazyComponent />
</Suspense>
```

### Q: 如何优化组件性能？
A:
1. 使用 React.memo 避免不必要的重渲染
2. 使用 useMemo 和 useCallback 优化计算
3. 实现虚拟滚动（对于长列表）
4. 使用代码分割和懒加载

## 相关文件清单

### 核心文件
- `App.tsx` - 主应用组件
- `main.tsx` - 应用入口
- `index.css` - 全局样式

### 组件目录
- `common/` - 通用组件
- `layout/` - 布局组件
- `workspace/` - 工作区组件
- `knowledge/` - 知识库组件
- `home/` - 首页组件
- `ui/` - 基础UI组件

### 配置文件
- `package.json` - 依赖配置
- `tsconfig.json` - TypeScript配置
- `tailwind.config.js` - Tailwind配置

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新组件库接口文档
- ✅ 完善组件使用说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*