import React, { useEffect, useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatPanel } from './ChatPanel';
import { ContextPanel, type ContextData } from './ContextPanel';
import { KnowledgeView } from '../knowledge/KnowledgeView';
import { ModelView } from '../model/ModelView';
import { History, X, Clock, MessageSquare, FileText, Download, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/EmptyState';
import { api, type ChatAttachment } from '@/services/api';
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
  initialModelId?: string | null;
  selectedAgentConfigId?: string | null;
  onAgentConfigChange?: (agentConfigId: string | null) => void;
  initialUseMultiAgent?: boolean;
  isHistoryOpen?: boolean;
  onHistoryOpen?: () => void;
  onHistoryClose?: () => void;
  isModelsOpen?: boolean;
  onModelsClose?: () => void;
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
  initialModelId,
  selectedAgentConfigId,
  onAgentConfigChange,
  initialUseMultiAgent = false,
  isHistoryOpen: externalIsHistoryOpen,
  onHistoryOpen,
  onHistoryClose,
  isModelsOpen: externalIsModelsOpen,
  onModelsClose,
}) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'workspace' | 'knowledge' | 'models'>('workspace');
  
  useEffect(() => {
    if (externalIsModelsOpen) {
      setViewMode('models');
    } else if (externalIsKnowledgeOpen) {
      setViewMode('knowledge');
    } else {
      setViewMode('workspace');
    }
  }, [externalIsKnowledgeOpen, externalIsModelsOpen]);
  
  const handleKnowledgeClose = () => {
    setViewMode('workspace');
    onKnowledgeClose?.();
  };

  const handleModelsClose = () => {
    setViewMode('workspace');
    onModelsClose?.();
  };
  
  // 直接使用外部传入的 isHistoryOpen，不维护内部状态
  const isHistoryOpen = externalIsHistoryOpen || false;
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [knowledgeBaseIds, setKnowledgeBaseIds] = useState<string[]>(initialKnowledgeBaseIds);
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(externalInitialSessionId || null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [initialHistory, setInitialHistory] = useState<Array<{ role: 'user' | 'agent' | 'model'; text: string; created_at?: string | null; sources?: any[] }>>([]);
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [ragSources, setRagSources] = useState<any[] | null>(null); // RAG 检索结果（兼容旧接口）
  const [contextData, setContextData] = useState<ContextData | null>(null); // 统一的上下文数据
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]); // 会话附件列表
  const [isLoadingAttachments, setIsLoadingAttachments] = useState(false);
  const [showAttachmentsPanel, setShowAttachmentsPanel] = useState(false);

  // 当外部传入 initialSessionId 时，加载该会话的历史
  useEffect(() => {
    if (externalInitialSessionId && !selectedSessionId) {
      setSelectedSessionId(externalInitialSessionId);
    }
  }, [externalInitialSessionId]);

  // 加载附件列表
  const loadAttachments = async () => {
    if (!currentSessionId) {
      setAttachments([]);
      return;
    }
    
    try {
      setIsLoadingAttachments(true);
      const data = await api.getChatAttachments(currentSessionId);
      setAttachments(data || []);
    } catch (error) {
      console.error('加载附件失败:', error);
      setAttachments([]);
    } finally {
      setIsLoadingAttachments(false);
    }
  };
  
  useEffect(() => {
    void loadAttachments();
  }, [currentSessionId]);
  
  // 监听附件更新事件
  useEffect(() => {
    const handleAttachmentUpdate = () => {
      void loadAttachments();
    };
    
    window.addEventListener('attachment-updated', handleAttachmentUpdate);
    return () => {
      window.removeEventListener('attachment-updated', handleAttachmentUpdate);
    };
  }, [currentSessionId]);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setFileUrl(url);
      setShowContextPanel(true); // 有文件时自动显示 ContextPanel
      return () => URL.revokeObjectURL(url);
    }
    // 如果有 RAG sources 或 contextData，也显示 ContextPanel
    if (ragSources && ragSources.length > 0) {
      setShowContextPanel(true);
    } else if (contextData) {
      setShowContextPanel(true);
    } else if (!file) {
      setFileUrl(null);
      // 如果没有文件也没有其他数据，隐藏 ContextPanel
      if (!ragSources || ragSources.length === 0) {
        setShowContextPanel(false);
      }
    }
  }, [file, ragSources, contextData]);

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
            
            // 从 message_metadata 中提取 sources
            let sources: any[] | undefined = undefined;
            if (msg.message_metadata) {
              // 检查是否有 sources 字段
              if (msg.message_metadata.sources && Array.isArray(msg.message_metadata.sources)) {
                sources = msg.message_metadata.sources;
              }
            }
            
            return {
              role: normalizedRole,
              text: msg.content || '',
              created_at: msg.created_at || null,
              sources: sources, // 包含 sources 信息
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
        <div className="flex-1 flex flex-col h-full min-h-0">
          {showContextPanel && (file || fileUrl || (ragSources && ragSources.length > 0) || contextData) ? (
            <PanelGroup direction="horizontal" className="flex-1 min-h-0 overflow-hidden">
              {/* Chat Panel - 40% default */}
              <Panel defaultSize={40} minSize={30} order={1} className="bg-white z-10">
                <div className="h-full w-full overflow-hidden flex flex-col">
                  <ChatPanel
                  knowledgeBaseIds={knowledgeBaseIds}
                  initialMessage={selectedSessionId ? null : (initialMessage || (file ? '请分析这个文档' : undefined))}
                  conversationKey={conversationKey}
                  uploadState={uploadState}
                  uploadError={uploadError}
                  initialSessionId={selectedSessionId}
                  initialModelId={initialModelId}
                  selectedAgentConfigId={selectedAgentConfigId}
                  onAgentConfigChange={onAgentConfigChange}
                  initialUseMultiAgent={initialUseMultiAgent}
                  initialHistory={initialHistory}
                  initialFile={selectedSessionId ? null : file}
                  onSessionIdChange={setCurrentSessionId}
                  onSourceClick={(sources) => {
                    setRagSources(sources);
                    setContextData({ type: 'rag-sources', data: sources });
                    setShowContextPanel(true);
                  }}
                  onToolCallClick={(toolCalls) => {
                    setContextData({ type: 'tool-calls', data: toolCalls });
                    setShowContextPanel(true);
                  }}
                  onPreviewClick={(previewData) => {
                    setContextData({ 
                      type: 'preview', 
                      data: previewData 
                    });
                    setShowContextPanel(true);
                  }}
                />
                </div>
              </Panel>
              
              <PanelResizeHandle className="w-1 bg-gray-100 hover:bg-blue-500 transition-colors cursor-col-resize z-20" />
              
              {/* Context Panel - 60% default */}
              <Panel defaultSize={60} minSize={30} order={2} className="bg-gray-50">
                <div className="h-full w-full overflow-hidden flex flex-col">
                  <ContextPanel 
                    fileUrl={fileUrl} 
                    file={file} 
                    sessionId={currentSessionId}
                    ragSources={ragSources}
                    contextData={contextData}
                    onClose={() => {
                      setShowContextPanel(false);
                      setContextData(null);
                    }}
                  />
                </div>
              </Panel>
            </PanelGroup>
          ) : (
            <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
              <ChatPanel
                knowledgeBaseIds={knowledgeBaseIds}
                initialMessage={selectedSessionId ? null : (initialMessage || (file ? '请分析这个文档' : undefined))}
                conversationKey={conversationKey}
                uploadState={uploadState}
                uploadError={uploadError}
                initialSessionId={selectedSessionId}
                initialModelId={initialModelId}
                selectedAgentConfigId={selectedAgentConfigId}
                onAgentConfigChange={onAgentConfigChange}
                initialUseMultiAgent={initialUseMultiAgent}
                initialHistory={initialHistory}
                initialFile={selectedSessionId ? null : file}
                onSessionIdChange={setCurrentSessionId}
                onSourceClick={(sources) => {
                  setRagSources(sources);
                  setContextData({ type: 'rag-sources', data: sources });
                  setShowContextPanel(true);
                }}
                  onToolCallClick={(toolCalls) => {
                    setContextData({ type: 'tool-calls', data: toolCalls });
                    setShowContextPanel(true);
                  }}
                  onPreviewClick={(previewData) => {
                    setContextData({ 
                      type: 'preview', 
                      data: previewData 
                    });
                    setShowContextPanel(true);
                  }}
              />
            </div>
          )}
        </div>
      ) : viewMode === 'knowledge' ? (
        <div className="flex-1 flex flex-col h-full">
          <KnowledgeView onClose={handleKnowledgeClose} />
        </div>
      ) : (
        <div className="flex-1 flex flex-col h-full">
          <ModelView onClose={handleModelsClose} />
        </div>
      )}
      
      {/* History Slide-over */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" 
              onClick={() => {
                onHistoryClose?.();
              }} 
            />
            <motion.div
              initial={{ x: -320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-16 z-50 w-80 bg-white border-r shadow-2xl"
            >
            <div className="flex flex-col h-full">
              <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-gray-500" />
                  <h2 className="font-semibold">History</h2>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => {
                  onHistoryClose?.();
                }}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {/* 当前会话附件快速访问 */}
                {currentSessionId && attachments.length > 0 && (
                  <div className="mb-4 pb-4 border-b">
                    <div className="flex items-center gap-2 mb-2 px-2">
                      <Paperclip className="w-4 h-4 text-gray-500" />
                      <h3 className="text-sm font-semibold text-gray-700">会话附件</h3>
                      <span className="text-xs text-gray-400">({attachments.length})</span>
                    </div>
                    <div className="space-y-1">
                      {attachments.map((att) => (
                        <motion.button
                          key={att.id}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => {
                            if (att.download_url) {
                              if (att.file_type === 'markdown' || att.file_type === 'md') {
                                // 如果是Markdown，尝试从attachment_metadata获取内容预览
                                const content = att.attachment_metadata?.plan_content_preview || '';
                                if (content) {
                                  setContextData({
                                    type: 'preview',
                                    data: {
                                      content: att.attachment_metadata?.plan_content_full || content,
                                      fileType: att.file_type,
                                      fileName: att.file_name,
                                      downloadUrl: att.download_url,
                                    }
                                  });
                                  setShowContextPanel(true);
                                } else {
                                  window.open(att.download_url, '_blank');
                                }
                              } else {
                                window.open(att.download_url, '_blank');
                              }
                            }
                          }}
                          className="w-full text-left px-2 py-1.5 rounded-md hover:bg-gray-100 transition-colors flex items-center gap-2 group"
                        >
                          <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          <span className="text-xs text-gray-700 truncate flex-1">{att.file_name}</span>
                          {att.download_url && (
                            <Download className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                          )}
                        </motion.button>
                      ))}
                    </div>
                  </div>
                )}
                
                {isLoadingSessions ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-sm text-gray-400">加载中...</div>
                  </div>
                ) : sessions.length === 0 ? (
                  <EmptyState
                    icon={History}
                    title="暂无对话历史"
                    description="开始新的对话后，历史记录会显示在这里"
                    size="sm"
                    className="py-8"
                  />
                ) : (
                  sessions.map((session, index) => {
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
                      <motion.button
                        key={session.session_id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.03 }}
                        whileHover={{ scale: 1.02, x: 4 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          // 加载会话历史消息
                          setSelectedSessionId(session.session_id);
                          // 关闭历史记录面板
                          onHistoryClose?.();
                          // 不立即清空历史，等待加载完成
                        }}
                        className="w-full text-left p-3 rounded-lg hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50/30 border border-transparent hover:border-blue-200 transition-all group cursor-pointer shadow-sm hover:shadow-md"
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
                      </motion.button>
                    );
                  })
                )}
              </div>
            </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      
      {/* Settings Modal - Placeholder */}
      <AnimatePresence>
        {isSettingsOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" 
              onClick={() => setIsSettingsOpen(false)} 
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
            >
              <motion.div
                className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-gray-200"
              >
              <div className="p-6 border-b flex items-center justify-between">
                <h2 className="text-xl font-semibold">Settings</h2>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsSettingsOpen(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              <div className="p-6">
                <p className="text-gray-500">Settings content goes here...</p>
              </div>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
