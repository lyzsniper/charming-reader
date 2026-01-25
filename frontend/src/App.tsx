import React, { useState, lazy, Suspense } from 'react';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { Toaster } from './components/ui/toast-sonner';
import { Sidebar } from './components/layout/Sidebar';
import { SettingsModal } from './components/layout/SettingsModal';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { useKeyboardShortcuts, COMMON_SHORTCUTS } from './hooks/useKeyboardShortcuts';
import { ThemeProvider } from './hooks/useTheme';

// 懒加载组件以提升首屏加载速度
const HomeView = lazy(() => import('./components/home/HomeView').then(m => ({ default: m.HomeView })));
const WorkspaceView = lazy(() => import('./components/workspace/WorkspaceView').then(m => ({ default: m.WorkspaceView })));

type ViewMode = 'home' | 'workspace';

function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('home');
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [initialMessage, setInitialMessage] = useState<string | null>(null);
  const [conversationKey, setConversationKey] = useState(0);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<string[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isModelsOpen, setIsModelsOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);

  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [useMultiAgent, setUseMultiAgent] = useState<boolean>(false);

  const handleStartChat = (message?: string, file?: File, knowledgeBaseIds?: string[], sessionId?: string, modelId?: string | null, multiAgent?: boolean) => {
    setInitialMessage(message ?? null);
    setCurrentFile(file ?? null);
    setSelectedKnowledgeBaseIds(knowledgeBaseIds ?? []);
    setSelectedSessionId(sessionId ?? null);
    setSelectedModelId(modelId ?? null);
    setUseMultiAgent(multiAgent ?? false);
    setViewMode('workspace');
    setConversationKey((key) => key + 1);
  };

  const handleGoHome = () => {
    // 关闭所有打开的面板
    setIsKnowledgeOpen(false);
    setIsHistoryOpen(false);
    setIsSettingsOpen(false);
    setIsModelsOpen(false);
    // 切换到首页
    setViewMode('home');
    setCurrentFile(null);
    setInitialMessage(null);
    setSelectedSessionId(null);
  };

  const handleOpenModels = () => {
    if (isModelsOpen) {
      setIsModelsOpen(false);
    } else {
      // 确保关闭其他面板
      if (isKnowledgeOpen) setIsKnowledgeOpen(false);
      if (isHistoryOpen) setIsHistoryOpen(false);
      if (isSettingsOpen) setIsSettingsOpen(false);
      if (viewMode !== 'workspace') {
        setViewMode('workspace');
      }
      setIsModelsOpen(true);
    }
  };

  const handleOpenKnowledge = () => {
    // 如果已经在 workspace 且知识库已打开，则关闭；否则打开
    if (viewMode === 'workspace' && isKnowledgeOpen) {
      setIsKnowledgeOpen(false);
      return;
    }
    
    // 如果不在工作区，先切换到工作区
    if (viewMode !== 'workspace') {
      setViewMode('workspace');
    }
    
    // 确保关闭历史记录和设置面板，避免同时打开多个面板
    if (isHistoryOpen) {
      setIsHistoryOpen(false);
    }
    if (isSettingsOpen) {
      setIsSettingsOpen(false);
    }
    
    // 使用 useEffect 的批处理特性，React 会自动批处理这些状态更新
    setIsKnowledgeOpen(true);
  };

  const handleOpenHistory = () => {
    // 如果历史记录已打开，则关闭；否则打开
    if (isHistoryOpen) {
      setIsHistoryOpen(false);
    } else {
      // 确保关闭知识库，避免同时打开多个面板
      if (isKnowledgeOpen) {
        setIsKnowledgeOpen(false);
      }
      setIsHistoryOpen(true);
    }
  };

  // 全局键盘快捷键
  useKeyboardShortcuts([
    {
      ...COMMON_SHORTCUTS.HELP,
      action: () => setIsShortcutsOpen(true),
    },
    {
      key: 'Escape',
      action: () => {
        if (isKnowledgeOpen) setIsKnowledgeOpen(false);
        if (isHistoryOpen) setIsHistoryOpen(false);
        if (isSettingsOpen) setIsSettingsOpen(false);
        if (isModelsOpen) setIsModelsOpen(false);
      },
    },
  ]);

  return (
    <ThemeProvider>
      <ErrorBoundary>
        <div className="min-h-screen bg-background text-foreground font-sans">
        <div className="flex h-screen w-full bg-background overflow-hidden relative">
          {/* 侧边栏 - 在所有页面都显示 */}
          <Sidebar 
            onOpenKnowledge={handleOpenKnowledge}
            onOpenHistory={handleOpenHistory}
            onOpenSettings={() => {
              if (isSettingsOpen) {
                setIsSettingsOpen(false);
              } else {
                // 关闭其他面板
                if (isKnowledgeOpen) setIsKnowledgeOpen(false);
                if (isHistoryOpen) setIsHistoryOpen(false);
                if (isModelsOpen) setIsModelsOpen(false);
                setIsSettingsOpen(true);
              }
            }}
            onOpenModels={handleOpenModels}
            onGoHome={handleGoHome}
            isKnowledgeOpen={isKnowledgeOpen}
            isHistoryOpen={isHistoryOpen}
            isSettingsOpen={isSettingsOpen}
            isModelsOpen={isModelsOpen}
            viewMode={viewMode}
          />
          
          {/* 主内容区域 */}
          <div className="flex-1 flex flex-col h-full">
            <Suspense fallback={<LoadingSpinner fullScreen text="加载中..." />}>
              {viewMode === 'home' ? (
                <HomeView 
                  onStartChat={handleStartChat} 
                  onOpenKnowledge={handleOpenKnowledge}
                  isHistoryOpen={isHistoryOpen}
                  onHistoryClose={() => setIsHistoryOpen(false)}
                />
              ) : (
            <WorkspaceView
              file={currentFile}
              initialMessage={initialMessage}
              conversationKey={conversationKey}
              onGoHome={handleGoHome}
              isKnowledgeOpen={isKnowledgeOpen}
              onKnowledgeClose={() => setIsKnowledgeOpen(false)}
              initialKnowledgeBaseIds={selectedKnowledgeBaseIds}
              initialSessionId={selectedSessionId}
              initialModelId={selectedModelId}
              initialUseMultiAgent={useMultiAgent}
              isHistoryOpen={isHistoryOpen}
              onHistoryClose={() => setIsHistoryOpen(false)}
              isModelsOpen={isModelsOpen}
              onModelsClose={() => setIsModelsOpen(false)}
            />
              )}
            </Suspense>
          </div>
        </div>
        <Toaster />
        <SettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
        />
        <KeyboardShortcutsModal
          isOpen={isShortcutsOpen}
          onClose={() => setIsShortcutsOpen(false)}
        />
      </div>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
