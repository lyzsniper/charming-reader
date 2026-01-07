import React, { useState } from 'react';
import { HomeView } from './components/home/HomeView';
import { WorkspaceView } from './components/workspace/WorkspaceView';

type ViewMode = 'home' | 'workspace';

function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('home');
  const [currentFile, setCurrentFile] = useState<File | null>(null);

  const handleStartChat = (message?: string, file?: File) => {
    if (file) {
      setCurrentFile(file);
    }
    setViewMode('workspace');
  };

  const handleGoHome = () => {
    setViewMode('home');
    setCurrentFile(null);
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {viewMode === 'home' ? (
        <HomeView onStartChat={handleStartChat} />
      ) : (
        <WorkspaceView file={currentFile} onGoHome={handleGoHome} />
      )}
    </div>
  );
}

export default App;
