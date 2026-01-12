import React, { useState, lazy, Suspense } from 'react';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { Toaster } from './components/ui/toast-sonner';

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

  const handleStartChat = (message?: string, file?: File) => {
    setInitialMessage(message ?? null);
    setCurrentFile(file ?? null);
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

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background text-foreground font-sans">
        <Suspense fallback={<LoadingSpinner fullScreen text="加载中..." />}>
          {viewMode === 'home' ? (
            <HomeView onStartChat={handleStartChat} onOpenKnowledge={handleOpenKnowledge} />
          ) : (
            <WorkspaceView
              file={currentFile}
              initialMessage={initialMessage}
              conversationKey={conversationKey}
              onGoHome={handleGoHome}
              isKnowledgeOpen={isKnowledgeOpen}
              onKnowledgeClose={() => setIsKnowledgeOpen(false)}
            />
          )}
        </Suspense>
        <Toaster />
      </div>
    </ErrorBoundary>
  );
}

export default App;
