import React, { useEffect, useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
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
  initialKnowledgeBaseIds?: string[];
  initialSessionId?: string | null;
  isHistoryOpen?: boolean;
  onHistoryOpen?: () => void;
  onHistoryClose?: () => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({
  file,
  initialMessage,
  conversationKey,
  onGoHome,
  isKnowledgeOpen: externalIsKnowledgeOpen,
  onKnowledgeClose,
  initialKnowledgeBaseIds = [],
  initialSessionId: externalInitialSessionId,
  isHistoryOpen: externalIsHistoryOpen,
  onHistoryOpen,
  onHistoryClose,
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
  const [isHistoryOpen, setIsHistoryOpen] = useState(externalIsHistoryOpen || false);
  
  // 同步外部传入的 isHistoryOpen
  useEffect(() => {
    if (externalIsHistoryOpen !== undefined) {
      setIsHistoryOpen(externalIsHistoryOpen);
    }
  }, [externalIsHistoryOpen]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [knowledgeBaseIds, setKnowledgeBaseIds] = useState<string[]>(initialKnowledgeBaseIds);
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(externalInitialSessionId || null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [initialHistory, setInitialHistory] = useState<Array<{ role: 'user' | 'agent' | 'model'; text: string; created_at?: string | null }>>([]);
  const [showContextPanel, setShowContextPanel] = useState(false);

  // 当外部传入 initialSessionId 时，加载该会话的历史
  useEffect(() => {
    if (externalInitialSessionId && !selectedSessionId) {
      setSelectedSessionId(externalInitialSessionId);
    }
  }, [externalInitialSessionId]);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setFileUrl(url);
      setShowContextPanel(true); // 有文件时自动显示 ContextPanel
      return () => URL.revokeObjectURL(url);
    }
    setFileUrl(null);
    setShowContextPanel(false); // 没有文件时隐藏 ContextPanel
  }, [file]);

  // 不再自动上传文件到知识库，而是让ChatPanel直接处理文件对话
  // 文件上传到知识库的逻辑已移除，改为在ChatPanel中使用chatWithFile API

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
        // 显示错误提示
        if (error instanceof Error) {
          console.error('Error loading sessions:', error.message);
        }
      } finally {
        setIsLoadingSessions(false);
      }
    };
    void loadSessions();
  }, [isHistoryOpen]);

  useEffect(() => {
    const loadSessionMessages = async () => {
      if (!selectedSessionId) {
        setInitialHistory([]);
        setCurrentSessionId(null);
        return;
      }
      try {
        // 使用新的Chat表接口获取消息
        const chatMessages = await api.getChatMessages(selectedSessionId, {
          role: undefined, // 获取所有角色
          message_type: undefined,
          skip: 0,
          limit: 100
        });
        
        // 转换消息格式，确保 role 类型正确
        const messages = chatMessages
          .filter(msg => msg.role === 'user' || msg.role === 'assistant') // 只保留用户和助手消息
          .map((msg) => {
            // 标准化 role：'assistant' -> 'agent'，'user' -> 'user'
            const normalizedRole: 'user' | 'agent' = msg.role === 'assistant' ? 'agent' : 'user';
            
            return {
              role: normalizedRole,
              text: msg.content || '',
              created_at: msg.created_at || null,
            };
          });
        setInitialHistory(messages);
        setCurrentSessionId(selectedSessionId);
      } catch (error) {
        console.error('Failed to load session messages', error);
        setInitialHistory([]);
        setCurrentSessionId(null);
        if (error instanceof Error) {
          console.error('Error loading session messages:', error.message);
        }
      }
    };
    void loadSessionMessages();
  }, [selectedSessionId]);

  return (
    <div className="flex h-full w-full bg-background overflow-hidden relative">
      {/* Main Content Area */}
      {viewMode === 'workspace' ? (
        <div className="flex-1 flex flex-col h-full">
          {showContextPanel && (file || fileUrl) ? (
            <PanelGroup direction="horizontal" className="flex-1">
              {/* Chat Panel - 40% default */}
              <Panel defaultSize={40} minSize={30} order={1} className="bg-white z-10 min-h-0">
                <ChatPanel
                  knowledgeBaseIds={knowledgeBaseIds}
                  initialMessage={selectedSessionId ? null : (initialMessage || (file ? '请分析这个文档' : undefined))}
                  conversationKey={conversationKey}
                  uploadState={uploadState}
                  uploadError={uploadError}
                  initialSessionId={selectedSessionId}
                  initialHistory={initialHistory}
                  initialFile={selectedSessionId ? null : file}
                  onSessionIdChange={setCurrentSessionId}
                />
              </Panel>
              
              <PanelResizeHandle className="w-1 bg-gray-100 hover:bg-blue-500 transition-colors cursor-col-resize z-20" />
              
              {/* Context Panel - 60% default */}
              <Panel defaultSize={60} minSize={30} order={2} className="bg-gray-50">
                <ContextPanel fileUrl={fileUrl} file={file} sessionId={currentSessionId} />
              </Panel>
            </PanelGroup>
          ) : (
            <div className="flex-1 flex flex-col h-full">
              <ChatPanel
                knowledgeBaseIds={knowledgeBaseIds}
                initialMessage={selectedSessionId ? null : (initialMessage || (file ? '请分析这个文档' : undefined))}
                conversationKey={conversationKey}
                uploadState={uploadState}
                uploadError={uploadError}
                initialSessionId={selectedSessionId}
                initialHistory={initialHistory}
                initialFile={selectedSessionId ? null : file}
                onSessionIdChange={setCurrentSessionId}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex flex-col h-full">
          <KnowledgeView onClose={handleKnowledgeClose} />
        </div>
      )}
      
      {/* History Slide-over */}
      {isHistoryOpen && (
        <>
          <div className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" onClick={() => {
            setIsHistoryOpen(false);
            onHistoryClose?.();
          }} />
          <div className="fixed inset-y-0 left-16 z-50 w-80 bg-white border-r shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="flex flex-col h-full">
              <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-gray-500" />
                  <h2 className="font-semibold">History</h2>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => {
                  setIsHistoryOpen(false);
                  onHistoryClose?.();
                }}>
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
                          // 加载会话历史消息
                          setSelectedSessionId(session.session_id);
                          setIsHistoryOpen(false);
                          // 不立即清空历史，等待加载完成
                        }}
                        className="w-full text-left p-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-200 transition-colors group cursor-pointer active:bg-gray-100"
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
      
      {/* Settings Modal - Placeholder */}
      {isSettingsOpen && (
        <>
          <div className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" onClick={() => setIsSettingsOpen(false)} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b flex items-center justify-between">
                <h2 className="text-xl font-semibold">Settings</h2>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsSettingsOpen(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              <div className="p-6">
                <p className="text-gray-500">Settings content goes here...</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
