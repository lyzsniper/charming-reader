import React, { useEffect, useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { Sidebar } from '../layout/Sidebar';
import { ChatPanel } from './ChatPanel';
import { ContextPanel } from './ContextPanel';
import { KnowledgeView } from '../knowledge/KnowledgeView';
import { History, X, Clock, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import type { SessionHistoryItem } from '@/services/api';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

interface WorkspaceViewProps {
  file: File | null;
  initialMessage: string | null;
  conversationKey: number;
  onGoHome: () => void;
  isKnowledgeOpen?: boolean;
  onKnowledgeClose?: () => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({
  file,
  initialMessage,
  conversationKey,
  onGoHome,
  isKnowledgeOpen: externalIsKnowledgeOpen,
  onKnowledgeClose,
}) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'workspace' | 'knowledge'>('workspace');
  
  useEffect(() => {
    if (externalIsKnowledgeOpen !== undefined) {
      setViewMode(externalIsKnowledgeOpen ? 'knowledge' : 'workspace');
    }
  }, [externalIsKnowledgeOpen]);
  
  const handleKnowledgeClose = () => {
    setViewMode('workspace');
    onKnowledgeClose?.();
  };
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [knowledgeBaseIds, setKnowledgeBaseIds] = useState<string[]>([]);
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [initialHistory, setInitialHistory] = useState<Array<{ role: 'user' | 'agent'; text: string; created_at?: string | null }>>([]);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setFileUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setFileUrl(null);
  }, [file]);

  // 不再自动上传文件到知识库，而是让ChatPanel直接处理文件对话
  // 文件上传到知识库的逻辑已移除，改为在ChatPanel中使用chatWithFile API

  useEffect(() => {
    const loadSessions = async () => {
      if (!isHistoryOpen) return;
      try {
        setIsLoadingSessions(true);
        const data = await api.listSessions({ limit: 50 });
        setSessions(data.sessions);
      } catch (error) {
        console.error('Failed to load sessions', error);
      } finally {
        setIsLoadingSessions(false);
      }
    };
    void loadSessions();
  }, [isHistoryOpen]);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative">
      {/* Sidebar */}
      <Sidebar 
        onOpenKnowledge={() => setViewMode('knowledge')}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onGoHome={onGoHome}
      />
      
      {/* Main Content Area */}
      {viewMode === 'workspace' ? (
        <div className="flex-1 flex flex-col h-full">
          <PanelGroup direction="horizontal" className="flex-1">
            {/* Chat Panel - 40% default */}
            <Panel defaultSize={40} minSize={30} order={1} className="bg-white z-10">
              <ChatPanel
                knowledgeBaseIds={knowledgeBaseIds}
                initialMessage={initialMessage || (file ? '请分析这个文档' : undefined)}
                conversationKey={conversationKey}
                uploadState={uploadState}
                uploadError={uploadError}
                initialSessionId={selectedSessionId}
                initialHistory={initialHistory}
                initialFile={file}
                onSessionIdChange={setCurrentSessionId}
              />
            </Panel>
            
            <PanelResizeHandle className="w-1 bg-gray-100 hover:bg-blue-500 transition-colors cursor-col-resize z-20" />
            
            {/* Context Panel - 60% default */}
            <Panel defaultSize={60} minSize={30} order={2} className="bg-gray-50">
              <ContextPanel fileUrl={fileUrl} file={file} sessionId={currentSessionId} />
            </Panel>
          </PanelGroup>
        </div>
      ) : (
        <div className="flex-1 flex flex-col h-full">
          <KnowledgeView onClose={handleKnowledgeClose} />
        </div>
      )}
      
      {/* History Slide-over */}
      {isHistoryOpen && (
        <>
           <div className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" onClick={() => setIsHistoryOpen(false)} />
           <div className="fixed inset-y-0 left-16 z-50 w-80 bg-white border-r shadow-2xl animate-in slide-in-from-left duration-200">
             <div className="flex flex-col h-full">
               <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
                 <div className="flex items-center gap-2">
                   <History className="w-4 h-4 text-gray-500" />
                   <h2 className="font-semibold">History</h2>
                 </div>
                 <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsHistoryOpen(false)}>
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
                         onClick={() => {
                          // 加载会话历史消息
                          setSelectedSessionId(session.session_id);
                          setIsHistoryOpen(false);
                          setInitialHistory([]);
                          void (async () => {
                            try {
                              const res = await api.listSessionMessages(session.session_id);
                              const mapped = (res.messages ?? []).map((m) => {
                                // 确保 role 是 'user' 或 'agent'
                                let role: 'user' | 'agent' = 'user';
                                if (m.role === 'agent' || m.role === 'model') {
                                  role = 'agent';
                                } else if (m.role === 'user') {
                                  role = 'user';
                                }
                                return {
                                  role,
                                  text: m.text ?? '',
                                  created_at: m.created_at,
                                };
                              });
                              setInitialHistory(mapped);
                            } catch (err) {
                              console.error('加载历史消息失败', err);
                            }
                          })();
                          // 切换到聊天视图
                          setViewMode('workspace');
                          setConversationKey((k) => k + 1);
                         }}
                         className="w-full text-left p-3 rounded-lg hover:bg-gray-100 transition-colors group"
                       >
                         <div className="flex items-start gap-3">
                           <MessageSquare className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" />
                           <div className="flex-1 min-w-0">
                             <div className="font-medium text-sm truncate">{session.title}</div>
                             <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                               <Clock className="w-3 h-3" />
                               {timeStr}
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

      {/* Settings Modal - Simple Center Pop */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setIsSettingsOpen(false)}>
           <div className="w-[500px] bg-white rounded-2xl shadow-2xl p-6 animate-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
             <div className="flex justify-between items-center mb-6">
               <h2 className="text-xl font-bold">Settings</h2>
               <Button variant="ghost" size="icon" onClick={() => setIsSettingsOpen(false)}>
                 <X className="w-5 h-5" />
               </Button>
             </div>
             
             <div className="space-y-6">
               <div className="space-y-2">
                 <label className="text-sm font-medium">Model Configuration</label>
                 <select className="w-full p-2 border rounded-md bg-gray-50 text-sm">
                   <option>GPT-4o (Default)</option>
                   <option>Claude 3.5 Sonnet</option>
                   <option>Llama 3 70B</option>
                 </select>
               </div>
               
               <div className="space-y-2">
                 <label className="text-sm font-medium">RAG Sensitivity</label>
                 <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                   <div className="h-full w-2/3 bg-black" />
                 </div>
                 <div className="flex justify-between text-xs text-gray-400">
                    <span>Precise</span>
                    <span>Creative</span>
                 </div>
               </div>
             </div>
             
             <div className="mt-8 flex justify-end gap-2">
               <Button variant="outline" onClick={() => setIsSettingsOpen(false)}>Cancel</Button>
               <Button onClick={() => setIsSettingsOpen(false)}>Save Changes</Button>
             </div>
           </div>
        </div>
      )}
    </div>
  );
};
