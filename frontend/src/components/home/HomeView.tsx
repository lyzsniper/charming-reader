import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, ArrowUp, FileText, Search, Sparkles, Database, History, X, Clock, MessageSquare, Users } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { showError } from '@/utils/dialogs';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import type { AgentConfigResponse } from '@/services/agentSkillsApi';
import { KnowledgeBaseSelector } from '@/components/common/KnowledgeBaseSelector';
import { ModelSelector } from '@/components/common/ModelSelector';
import { EmptyState } from '@/components/common/EmptyState';
import { api } from '@/services/api';
import type { SessionHistoryItem } from '@/services/api';

interface HomeViewProps {
  onStartChat: (
    message?: string,
    file?: File,
    knowledgeBaseIds?: string[],
    sessionId?: string,
    modelId?: string | null,
    useMultiAgent?: boolean,
    agentConfigId?: string | null
  ) => void;
  selectedAgentConfigId?: string | null;
  onAgentConfigChange?: (agentConfigId: string | null) => void;
  onOpenKnowledge?: () => void;
  isHistoryOpen?: boolean;
  onHistoryClose?: () => void;
}

export const HomeView: React.FC<HomeViewProps> = ({
  onStartChat,
  selectedAgentConfigId,
  onAgentConfigChange,
  onOpenKnowledge,
  isHistoryOpen,
  onHistoryClose,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<string[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [useMultiAgent, setUseMultiAgent] = useState<boolean>(false);
  const [agentOptions, setAgentOptions] = useState<AgentConfigResponse[]>([]);
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

  useEffect(() => {
    let mounted = true;
    const loadAgents = async () => {
      try {
        const response = await agentSkillsApi.listAgentConfigs({
          skip: 0,
          limit: 100,
          include_total: false,
        });
        const items = Array.isArray(response) ? response : response.items || [];
        if (mounted) {
          setAgentOptions(items);
        }
      } catch (error) {
        if (mounted) {
          showError('加载 Agent 列表失败');
        }
      }
    };
    loadAgents();
    return () => {
      mounted = false;
    };
  }, []);

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
    onStartChat(
      "",
      file,
      selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined,
      undefined,
      selectedModelId,
      useMultiAgent,
      selectedAgentConfigId ?? null
    );
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim()) {
      onStartChat(
        inputValue,
        undefined,
        selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined,
        undefined,
        selectedModelId,
        useMultiAgent,
        selectedAgentConfigId ?? null
      );
    }
  };

  const quickActions = [
    { icon: <FileText className="w-4 h-4" />, text: "Upload paper & summarize" },
    { icon: <Search className="w-4 h-4" />, text: "Search Transformer variants" },
    { icon: <Sparkles className="w-4 h-4" />, text: "Explain RAG concepts" },
  ];

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
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
        <motion.div 
          animate={{ 
            x: [0, 20, 0],
            y: [0, 30, 0],
          }}
          transition={{ 
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-gradient-to-br from-blue-100/40 via-blue-50/30 to-transparent blur-[120px]" 
        />
        <motion.div 
          animate={{ 
            x: [0, -15, 0],
            y: [0, -25, 0],
          }}
          transition={{ 
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] rounded-full bg-gradient-to-br from-purple-100/40 via-purple-50/30 to-transparent blur-[100px]" 
        />
      </div>

      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="w-full max-w-2xl z-10 flex flex-col gap-8"
      >
        {/* Header */}
        <motion.div 
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-center space-y-4"
        >
          <motion.div 
            whileHover={{ scale: 1.05, rotate: [0, -5, 5, -5, 0] }}
            transition={{ duration: 0.5 }}
            className="w-16 h-16 bg-gradient-to-br from-black to-gray-800 text-white text-3xl font-serif font-bold rounded-2xl mx-auto flex items-center justify-center shadow-2xl ring-2 ring-gray-200/50"
          >
            P
          </motion.div>
          <h1 className="text-3xl sm:text-4xl font-serif font-medium tracking-tight text-primary bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
            CharMing Reader
          </h1>
          <p className="text-muted-foreground text-base sm:text-lg font-light">
            查·明 - Your streamlined academic workspace.
          </p>
        </motion.div>

        {/* Omnibox */}
        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="relative group"
        >
          <motion.div 
            animate={{
              opacity: isDragging || inputValue ? 1 : 0,
              scale: isDragging || inputValue ? 1.02 : 1,
            }}
            transition={{ duration: 0.3 }}
            className={cn(
              "absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-blue-500/10 rounded-2xl blur-xl",
            )} 
          />
          
          <motion.div 
            whileHover={{ scale: 1.01 }}
            className="relative bg-white/90 backdrop-blur-xl border border-white/30 shadow-2xl rounded-2xl p-2 transition-all duration-300 hover:shadow-3xl ring-1 ring-black/5 z-10 pointer-events-auto"
          >
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
                aria-label="输入问题或上传文件"
                className="w-full bg-transparent border-none text-base sm:text-lg px-4 py-3 placeholder:text-gray-400 focus:ring-0 resize-none min-h-[60px] max-h-[200px] pointer-events-auto transition-all"
                rows={1}
              />
              
              <div className="flex justify-between items-center px-2 pb-1 pointer-events-auto">
                <div className="flex flex-wrap gap-2">
                  <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      type="button"
                      variant="ghost" 
                      size="icon"
                      className="text-gray-400 hover:text-gray-600 hover:bg-gray-100/50 rounded-xl pointer-events-auto transition-colors"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        fileInputRef.current?.click();
                      }}
                    >
                      <Paperclip className="w-5 h-5" />
                    </Button>
                  </motion.div>
                  {/* 模型选择器 */}
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <ModelSelector
                      selectedId={selectedModelId}
                      onSelectionChange={setSelectedModelId}
                      variant="light"
                      className="pointer-events-auto"
                    />
                  </motion.div>
                  {/* 多智能体模式切换 */}
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      type="button"
                      variant={useMultiAgent ? "default" : "ghost"}
                      size="icon"
                      className={cn(
                        "rounded-xl pointer-events-auto transition-all",
                        useMultiAgent 
                          ? "bg-blue-600 hover:bg-blue-700 text-white shadow-md" 
                          : "text-gray-400 hover:text-gray-600 hover:bg-gray-100/50"
                      )}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setUseMultiAgent(!useMultiAgent);
                      }}
                      title={useMultiAgent ? "多智能体协作模式已开启" : "点击开启多智能体协作模式"}
                    >
                      <Users className={cn("w-5 h-5", useMultiAgent && "text-white")} />
                    </Button>
                  </motion.div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="*/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  />
                </div>
                
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button 
                    type="submit" 
                    size="icon"
                    variant={inputValue ? "default" : "secondary"}
                    className={cn(
                      "rounded-xl transition-all duration-300 pointer-events-auto shadow-md",
                      inputValue && "hover:shadow-lg"
                    )}
                    disabled={!inputValue.trim()}
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                  >
                    <ArrowUp className="w-5 h-5" />
                  </Button>
                </motion.div>
              </div>
            </form>
          </motion.div>
        </motion.div>

        {/* Knowledge Base Selector */}
        <motion.div 
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex justify-center"
        >
          <KnowledgeBaseSelector
            selectedIds={selectedKnowledgeBaseIds}
            onSelectionChange={setSelectedKnowledgeBaseIds}
            variant="light"
            className="inline-block"
          />
        </motion.div>

        <motion.div
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.45 }}
          className="flex justify-center"
        >
          <div className="flex items-center gap-2 bg-white/70 border border-gray-200/60 rounded-full px-4 py-2 shadow-sm">
            <span className="text-xs text-gray-500">Agent 工具组</span>
            <select
              value={selectedAgentConfigId ?? ''}
              onChange={(event) => {
                const value = event.target.value || null;
                onAgentConfigChange?.(value);
              }}
              className="h-8 px-2 rounded-md border border-gray-200 bg-white text-xs text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              title="选择 Agent 工具组"
            >
              <option value="">默认Agent工具组</option>
              {agentOptions.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.display_name || agent.name || agent.id}
                </option>
              ))}
            </select>
          </div>
        </motion.div>

        {/* Pills */}
        <motion.div 
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="flex flex-wrap justify-center gap-2 sm:gap-3"
        >
          {quickActions.map((action, i) => (
            <motion.button
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.6 + i * 0.1 }}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() =>
                onStartChat(
                  action.text,
                  undefined,
                  selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined,
                  undefined,
                  selectedModelId,
                  useMultiAgent,
                  selectedAgentConfigId ?? null
                )
              }
              className="flex items-center gap-2 px-4 py-2 bg-white/70 hover:bg-white/90 backdrop-blur-sm border border-gray-200/50 rounded-full text-sm text-gray-700 hover:text-black transition-all shadow-md hover:shadow-lg hover:border-gray-300/50"
            >
              {action.icon}
              {action.text}
            </motion.button>
          ))}
        </motion.div>
      </motion.div>
      
      {/* Footer Hint */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-blue-50/95 to-purple-50/95 backdrop-blur-md border-2 border-dashed border-blue-400 m-4 rounded-3xl"
          >
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-2xl font-medium text-blue-600 flex items-center gap-3"
            >
              <FileText className="w-8 h-8" />
              Drop file to analyze
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History Slide-over */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-[100]" 
              onClick={onHistoryClose} 
            />
            <motion.div
              initial={{ x: -320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-16 z-[101] w-80 bg-white border-r shadow-2xl pointer-events-auto"
            >
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
                  <EmptyState
                    icon={History}
                    title="暂无对话历史"
                    description="开始新的对话后，历史记录会显示在这里"
                    size="sm"
                    className="py-8"
                  />
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
                          onStartChat(undefined, undefined, undefined, session.session_id, selectedModelId, useMultiAgent);
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
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
