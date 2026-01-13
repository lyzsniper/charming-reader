import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, ArrowUp, FileText, Search, Sparkles, Database, History, X, Clock, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { showError } from '@/utils/dialogs';
import { KnowledgeBaseSelector } from '@/components/common/KnowledgeBaseSelector';
import { api } from '@/services/api';
import type { SessionHistoryItem } from '@/services/api';

interface HomeViewProps {
  onStartChat: (message?: string, file?: File, knowledgeBaseIds?: string[], sessionId?: string) => void;
  onOpenKnowledge?: () => void;
  isHistoryOpen?: boolean;
  onHistoryClose?: () => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onStartChat, onOpenKnowledge, isHistoryOpen, onHistoryClose }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<string[]>([]);
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const loadSessions = async () => {
      if (!isHistoryOpen) return;
      try {
        setIsLoadingSessions(true);
        const data = await api.listSessions({ limit: 50 });
        setSessions(data.sessions || []);
      } catch (error) {
        console.error('Failed to load sessions', error);
        setSessions([]);
      } finally {
        setIsLoadingSessions(false);
      }
    };
    void loadSessions();
  }, [isHistoryOpen]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = (file: File) => {
    // 允许所有文件类型上传到对话中
    onStartChat("", file, selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined);
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim()) {
      onStartChat(inputValue, undefined, selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined);
    }
  };

  const quickActions = [
    { icon: <FileText className="w-4 h-4" />, text: "Upload paper & summarize" },
    { icon: <Search className="w-4 h-4" />, text: "Search Transformer variants" },
    { icon: <Sparkles className="w-4 h-4" />, text: "Explain RAG concepts" },
  ];

  return (
    <div 
      className={cn(
        "w-full h-full flex flex-col items-center justify-center p-4 transition-colors duration-300 relative overflow-hidden",
        isDragging ? "bg-blue-50/50" : "bg-background"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Background Decor */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-100/30 blur-[120px]" />
        <div className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] rounded-full bg-purple-100/30 blur-[100px]" />
      </div>

      <div className="w-full max-w-2xl z-10 flex flex-col gap-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-black text-white text-3xl font-serif font-bold rounded-2xl mx-auto flex items-center justify-center shadow-xl">
            P
          </div>
          <h1 className="text-4xl font-serif font-medium tracking-tight text-primary">
            CharMing Reader
          </h1>
          <p className="text-muted-foreground text-lg font-light">
            查·明 - Your streamlined academic workspace.
          </p>
        </div>

        {/* Omnibox */}
        <div className="relative group">
          <div className={cn(
            "absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-2xl blur-xl transition-opacity duration-500",
            isDragging || inputValue ? "opacity-100" : "opacity-0"
          )} />
          
          <div className="relative bg-white/80 backdrop-blur-xl border border-white/20 shadow-2xl rounded-2xl p-2 transition-all duration-300 hover:shadow-blue-900/5 ring-1 ring-black/5 z-10 pointer-events-auto">
            <form onSubmit={handleSubmit} className="flex flex-col gap-2 pointer-events-auto">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Ask anything or drag a file here..."
                className="w-full bg-transparent border-none text-lg px-4 py-3 placeholder:text-gray-400 focus:ring-0 resize-none min-h-[60px] max-h-[200px] pointer-events-auto"
                rows={1}
              />
              
              <div className="flex justify-between items-center px-2 pb-1 pointer-events-auto">
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost" 
                    size="icon"
                    className="text-gray-400 hover:text-gray-600 hover:bg-gray-100/50 rounded-xl pointer-events-auto"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    <Paperclip className="w-5 h-5" />
                  </Button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="*/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  />
                </div>
                
                <Button 
                  type="submit" 
                  size="icon"
                  className={cn(
                    "rounded-xl transition-all duration-300 pointer-events-auto",
                    inputValue ? "bg-black text-white hover:bg-gray-800" : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                  )}
                  disabled={!inputValue.trim()}
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  <ArrowUp className="w-5 h-5" />
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Knowledge Base Selector */}
        <div className="flex justify-center">
          <KnowledgeBaseSelector
            selectedIds={selectedKnowledgeBaseIds}
            onSelectionChange={setSelectedKnowledgeBaseIds}
            variant="light"
            className="inline-block"
          />
        </div>

        {/* Pills */}
        <div className="flex flex-wrap justify-center gap-3">
          {quickActions.map((action, i) => (
            <button
              key={i}
              onClick={() => onStartChat(action.text, undefined, selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined)}
              className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/80 backdrop-blur-sm border border-black/5 rounded-full text-sm text-gray-600 hover:text-black transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5"
            >
              {action.icon}
              {action.text}
            </button>
          ))}
          {onOpenKnowledge && (
            <button
              onClick={onOpenKnowledge}
              className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/80 backdrop-blur-sm border border-black/5 rounded-full text-sm text-gray-600 hover:text-black transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5"
            >
              <Database className="w-4 h-4" />
              知识库管理
            </button>
          )}
        </div>
      </div>
      
      {/* Footer Hint */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-blue-50/90 backdrop-blur-sm border-2 border-dashed border-blue-400 m-4 rounded-3xl animate-pulse">
          <div className="text-2xl font-medium text-blue-600">
            Drop file to analyze
          </div>
        </div>
      )}

      {/* History Slide-over */}
      {isHistoryOpen && (
        <>
          <div className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-[100]" onClick={onHistoryClose} />
          <div className="fixed inset-y-0 left-16 z-[101] w-80 bg-white border-r shadow-2xl animate-in slide-in-from-left duration-200 pointer-events-auto">
            <div className="flex flex-col h-full">
              <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-gray-500" />
                  <h2 className="font-semibold">History</h2>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onHistoryClose}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {isLoadingSessions ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-sm text-gray-400">加载中...</div>
                  </div>
                ) : sessions.length === 0 ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-sm text-gray-400">暂无对话历史</div>
                  </div>
                ) : (
                  sessions.map((session) => {
                    const timeAgo = session.last_message_time
                      ? new Date(session.last_message_time * 1000)
                      : null;
                    const timeStr = timeAgo
                      ? timeAgo.toLocaleString('zh-CN', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '未知时间';
                    
                    return (
                      <button
                        key={session.session_id}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          onHistoryClose?.();
                          onStartChat(undefined, undefined, undefined, session.session_id);
                        }}
                        className="w-full text-left p-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200 transition-colors group cursor-pointer active:bg-gray-100 pointer-events-auto"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0 mt-0.5">
                            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                              <MessageSquare className="w-4 h-4 text-blue-600" />
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <div className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600 transition-colors">
                                {session.title || 'Untitled Conversation'}
                              </div>
                              <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
                                <Clock className="w-3 h-3" />
                                <span>{timeStr}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
