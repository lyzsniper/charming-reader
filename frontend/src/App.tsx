import React, { useState, lazy, Suspense } from 'react';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { Toaster } from './components/ui/toast-sonner';
import { Sidebar } from './components/layout/Sidebar';

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
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const handleStartChat = (message?: string, file?: File, knowledgeBaseIds?: string[], sessionId?: string) => {
    setInitialMessage(message ?? null);
    setCurrentFile(file ?? null);
    setSelectedKnowledgeBaseIds(knowledgeBaseIds ?? []);
    setSelectedSessionId(sessionId ?? null);
    setViewMode('workspace');
    setConversationKey((key) => key + 1);
  };

  const handleGoHome = () => {
    setViewMode('home');
    setCurrentFile(null);
    setInitialMessage(null);
  };

  const handleOpenKnowledge = () => {
    if (viewMode === 'workspace') {
      setIsKnowledgeOpen(true);
    } else {
      // 如果不在工作区，先切换到工作区再打开知识库
      setViewMode('workspace');
      setTimeout(() => setIsKnowledgeOpen(true), 100);
    }
  };

  const handleOpenHistory = () => {
    setIsHistoryOpen(true);
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background text-foreground font-sans">
        <div className="flex h-screen w-full bg-background overflow-hidden relative">
          {/* 侧边栏 - 在所有页面都显示 */}
          <Sidebar 
            onOpenKnowledge={handleOpenKnowledge}
            onOpenHistory={handleOpenHistory}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onGoHome={handleGoHome}
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
              isHistoryOpen={isHistoryOpen}
              onHistoryClose={() => setIsHistoryOpen(false)}
            />
              )}
            </Suspense>
          </div>
        </div>
        <Toaster />
      </div>
    </ErrorBoundary>
  );
}

export default App;
