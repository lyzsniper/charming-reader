import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, StopCircle, Info, RotateCw, FileText, Download, Loader2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ThinkingProcess } from './ThinkingProcess';
import { api } from '@/services/api';
import type { ChatResponse } from '@/services/api';
import { KnowledgeBaseSelector } from '@/components/common/KnowledgeBaseSelector';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { useKeyboardShortcuts, COMMON_SHORTCUTS } from '@/hooks/useKeyboardShortcuts';
import { Copy, Check } from 'lucide-react';
import { showSuccess, showError } from '@/utils/dialogs';

interface ToolCall {
  tool_name: string;
  arguments: Record<string, any>;
  status: 'start' | 'running' | 'complete';
  result?: any;
  success?: boolean;
  error?: string;
  timestamp: string;
}

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  thinking?: string[];
  sources?: ChatResponse['sources'];
  knowledgeBaseIds?: string[] | null;
  createdAt?: string;
  vectorizationStep?: {
    step: string;
    message: string;
    progress?: number;
    details?: Record<string, unknown>;
  };
  activatedSkills?: ChatResponse['activated_skills'];
  skillsPrompt?: string | null;
  fileName?: string;
  toolCalls?: ToolCall[];
}

export const CITATION_EVENT = 'citation-click';

interface ChatPanelProps {
  knowledgeBaseIds?: string[];
  initialMessage?: string | null;
  conversationKey?: number;
  uploadState?: 'idle' | 'uploading' | 'success' | 'error';
  uploadError?: string | null;
  initialSessionId?: string | null;
  initialHistory?: Array<{ role: 'user' | 'agent' | 'model'; text: string; created_at?: string | null; sources?: any[] }>;
  initialFile?: File | null;
  onSessionIdChange?: (sessionId: string | null) => void;
  onSourceClick?: (sources: any[]) => void; // 新增：RAG source 点击回调
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  knowledgeBaseIds,
  initialMessage,
  conversationKey,
  uploadState = 'idle',
  uploadError,
  initialSessionId,
  initialHistory,
  initialFile,
  onSessionIdChange,
  onSourceClick,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localKnowledgeBaseIds, setLocalKnowledgeBaseIds] = useState<string[]>(knowledgeBaseIds || []);
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);
  const [messageMenuOpen, setMessageMenuOpen] = useState<string | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null); // 跟踪已复制的消息
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [summaryResult, setSummaryResult] = useState<{
    download_url: string;
    plan_content: string;
    messages_used: number;
    total_messages: number;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasSentInitialRef = useRef(false); // 使用ref来跟踪，避免重复发送

  // 当 conversationKey 变化时，重置 hasSentInitialRef
  useEffect(() => {
    hasSentInitialRef.current = false;
  }, [conversationKey]);

  useEffect(() => {
    const intro: Message = {
      id: 'intro',
      role: 'agent',
      content: localKnowledgeBaseIds.length > 0
        ? `已选择 ${localKnowledgeBaseIds.length} 个知识库，RAG 检索已开启。直接提问即可引用知识库内容。`
        : initialFile
        ? '文档已准备就绪，正在分析...'
        : "Hello! 我是 CharMing Reader (查·明)。选择知识库或上传文件开始对话。",
    };
    const historyMsgs: Message[] = (initialHistory ?? [])
      .filter((m) => m.text && m.text.trim().length > 0) // 过滤掉空消息
      .map((m, idx) => {
        // 确保 role 正确映射：'model' 和 'agent' -> 'agent'，其他 -> 'user'
        const roleStr = String(m.role); // 转换为字符串以处理可能的其他值
        const normalizedRole: 'user' | 'agent' = 
          (roleStr === 'agent' || roleStr === 'model' || roleStr === 'assistant') ? 'agent' : 'user';
        
        return {
          id: `hist-${idx}`,
          role: normalizedRole,
          content: m.text || '',
          createdAt: m.created_at ?? undefined,
          sources: m.sources, // 恢复 sources 信息
        };
      });
    setMessages([intro, ...historyMsgs]);
    const newSessionId = initialSessionId ?? null;
    setSessionId(newSessionId);
    onSessionIdChange?.(newSessionId);
    setIsThinking(false);
    hasSentInitialRef.current = false; // 重置ref
    setInput(initialMessage ?? '');
    // 如果有初始文件，设置为选中文件
    if (initialFile) {
      setSelectedFile(initialFile);
    }
  }, [knowledgeBaseIds, conversationKey, initialMessage, initialHistory, initialSessionId, initialFile, onSessionIdChange]);

  // 当外部传入的 knowledgeBaseIds 改变时，同步到本地状态
  useEffect(() => {
    if (knowledgeBaseIds) {
      setLocalKnowledgeBaseIds(knowledgeBaseIds);
    }
  }, [knowledgeBaseIds]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  // 键盘快捷键
  useKeyboardShortcuts([
    {
      ...COMMON_SHORTCUTS.SEND_MESSAGE,
      action: () => {
        if (!isThinking && (input.trim() || selectedFile)) {
          void handleSend();
        }
      },
    },
    {
      key: 'Escape',
      action: () => {
        if (selectedFile) {
          setSelectedFile(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }
      },
    },
  ]);

  useEffect(() => {
    // 使用ref来防止重复发送
    if (hasSentInitialRef.current) return;
    
    // 如果有历史记录，说明是加载已有会话，不应该自动发送
    if (initialHistory && initialHistory.length > 0) {
      hasSentInitialRef.current = true;
      return;
    }
    
    // 如果有初始消息或初始文件，自动发送（仅在新对话时）
    if (initialMessage || initialFile) {
      hasSentInitialRef.current = true;
      const message = initialMessage || (initialFile ? '请分析这个文档' : '');
      // 使用 setTimeout 确保在下一个事件循环中执行，避免重复调用
      const timer = setTimeout(() => {
        void handleSend(message, true, initialFile ?? undefined);
      }, 100); // 增加延迟，确保状态已更新
      return () => clearTimeout(timer);
    }
  }, [conversationKey, initialMessage, initialFile, initialHistory]); // 使用conversationKey确保每次新对话时重置

  const preprocessContent = (content: string) => {
    return content.replace(/\[(\d+)\]/g, '[`[$1]`](#citation-$1)');
  };

  const renderUploadNotice = () => {
    if (uploadState === 'idle') return null;
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className={cn(
            "mx-4 mt-3 flex items-center gap-2 text-xs rounded-lg px-3 py-2 shadow-sm",
            uploadState === 'uploading' && "text-amber-700 bg-gradient-to-r from-amber-50 to-amber-100/50 border border-amber-200",
            uploadState === 'error' && "text-red-700 bg-gradient-to-r from-red-50 to-red-100/50 border border-red-200",
            uploadState === 'success' && "text-emerald-700 bg-gradient-to-r from-emerald-50 to-emerald-100/50 border border-emerald-200"
          )}
        >
          <Info className="w-4 h-4" />
          {uploadState === 'uploading' && '正在上传并解析文档，请稍候...'}
          {uploadState === 'error' && `文档上传失败：${uploadError ?? '请重试'}`}
          {uploadState === 'success' && '文档已上传完成，后续问题将结合文档进行回答。'}
        </motion.div>
      </AnimatePresence>
    );
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleSend = async (contentOverride?: string, skipInputClear?: boolean, fileOverride?: File | null) => {
    const content = (contentOverride ?? input).trim();
    const file = fileOverride ?? selectedFile;
    
    // 防止重复发送：如果正在思考中，直接返回
    if (!content || isThinking) return;
    
    // 立即设置 isThinking，防止重复调用
    setIsThinking(true);
    if (file && !content.trim()) {
      // 如果有文件但没有消息，自动添加提示消息
      contentOverride = '请分析这个文档';
    }

    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: contentOverride ?? content,
      fileName: file?.name,
    };

    const agentId = `${Date.now()}-agent`;
    setMessages((prev) => [
      ...prev,
      userMsg,
      {
        id: agentId,
        role: 'agent',
        content: '',
        thinking: file ? undefined : ['解析问题...', '检索上下文...', '生成回答...'],
        vectorizationStep: file ? {
          step: 'uploading',
          message: '准备上传文件...',
          progress: 0
        } : undefined,
      },
    ]);
    if (!skipInputClear) {
      setInput('');
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }

    try {
      // 如果有文件，使用带文件的聊天接口
      if (file) {
        await api.chatWithFile({
          file,
          message: contentOverride ?? content,
          session_id: sessionId,
          user_id: 'default_user',
          knowledge_base_ids: localKnowledgeBaseIds.length > 0 ? localKnowledgeBaseIds : undefined,
          use_rag: localKnowledgeBaseIds.length > 0 ? true : undefined,
          onVectorizationStep: (step) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      vectorizationStep: step,
                      thinking: step.step === 'chat_start' ? ['生成回答...'] : undefined,
                    }
                  : m,
              ),
            );
          },
          onSkillLoading: (data) => {
            console.log('[ChatPanel] 收到 skill_loading 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), `${data.message}...`].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onSkillActivated: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      thinking: [...(m.thinking || []), `技能已激活: ${data.skill_name}`].filter((v, i, a) => a.indexOf(v) === i), // 去重
                      activatedSkills: [
                        ...(m.activatedSkills || []),
                        {
                          name: data.skill_name,
                          description: data.description || '',
                          version: data.version || null,
                        },
                      ],
                    }
                  : m,
              ),
            );
          },
          onRagRetrieval: (data) => {
            console.log('[ChatPanel] 收到 rag_retrieval 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), data.message].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onRagSources: (data) => {
            console.log('[ChatPanel] 收到 rag_sources 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      sources: data.sources,
                    }
                  : m,
              ),
            );
          },
          onAgentThinking: (data) => {
            console.log('[ChatPanel] 收到 agent_thinking 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), data.message].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onAgentContent: (data) => {
            console.log('[ChatPanel] 收到 agent_content 事件:', { contentLength: data.content?.length, isComplete: data.is_complete });
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: data.content || '',
                      // 如果内容开始显示且长度足够，清除 thinking；如果完成，也清除 thinking
                      thinking: (data.is_complete || (data.content && data.content.length > 50)) ? undefined : m.thinking,
                    }
                  : m,
              ),
            );
          },
          onToolCall: (data) => {
            console.log('[ChatPanel] 收到 tool_call 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      toolCalls: [
                        ...(m.toolCalls || []),
                        {
                          tool_name: data.tool_name,
                          arguments: data.arguments,
                          status: data.status as 'start' | 'running' | 'complete',
                          timestamp: data.timestamp,
                        },
                      ],
                    }
                  : m,
              ),
            );
          },
          onToolResult: (data) => {
            console.log('[ChatPanel] 收到 tool_result 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      toolCalls: (m.toolCalls || []).map((tc) =>
                        tc.tool_name === data.tool_name
                          ? {
                              ...tc,
                              status: 'complete' as const,
                              result: data.result,
                              success: data.success,
                              error: data.error,
                            }
                          : tc,
                      ),
                    }
                  : m,
              ),
            );
          },
          onChatResponse: (response) => {
            console.log('[ChatPanel] 收到 chat_response 事件:', response);
            setSessionId(response.session_id);
            onSessionIdChange?.(response.session_id);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: response.response || m.content || '',
                      thinking: undefined,
                      vectorizationStep: undefined,
                      // 保留之前设置的 sources（如果 response 中没有 sources，使用之前的）
                      sources: response.sources ?? m.sources ?? undefined,
                      knowledgeBaseIds: response.knowledge_base_ids ?? m.knowledgeBaseIds ?? undefined,
                      // 保留之前设置的 activatedSkills（如果 response 中没有，使用之前的）
                      activatedSkills: response.activated_skills ?? m.activatedSkills ?? undefined,
                      skillsPrompt: response.skills_prompt ?? m.skillsPrompt ?? undefined,
                      createdAt: response.created_at,
                    }
                  : m,
              ),
            );
            setIsThinking(false);
          },
          onError: (error) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: `⚠️ ${error}`,
                      thinking: undefined,
                      vectorizationStep: undefined,
                    }
                  : m,
              ),
            );
            setIsThinking(false);
          },
        });
      } else {
        // 没有文件，使用流式聊天接口
        let accumulatedContent = '';
        await api.chat({
          message: contentOverride ?? content,
          session_id: sessionId,
          knowledge_base_ids: localKnowledgeBaseIds.length > 0 ? localKnowledgeBaseIds : undefined,
          use_rag: localKnowledgeBaseIds.length > 0 ? true : undefined,
          onSkillLoading: (data) => {
            console.log('[ChatPanel] 收到 skill_loading 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), `${data.message}...`].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onSkillActivated: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      thinking: [...(m.thinking || []), `技能已激活: ${data.skill_name}`].filter((v, i, a) => a.indexOf(v) === i), // 去重
                      activatedSkills: [
                        ...(m.activatedSkills || []),
                        {
                          name: data.skill_name,
                          description: data.description || '',
                          version: data.version || null,
                        },
                      ],
                    }
                  : m,
              ),
            );
          },
          onRagRetrieval: (data) => {
            console.log('[ChatPanel] 收到 rag_retrieval 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), data.message].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onRagSources: (data) => {
            console.log('[ChatPanel] 收到 rag_sources 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      sources: data.sources,
                    }
                  : m,
              ),
            );
          },
          onAgentThinking: (data) => {
            console.log('[ChatPanel] 收到 agent_thinking 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 累积 thinking 步骤，而不是替换
                      thinking: [...(m.thinking || []), data.message].filter((v, i, a) => a.indexOf(v) === i), // 去重
                    }
                  : m,
              ),
            );
          },
          onAgentContent: (data) => {
            console.log('[ChatPanel] 收到 agent_content 事件:', { contentLength: data.content?.length, isComplete: data.is_complete });
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: data.content || '',
                      // 如果内容开始显示且长度足够，清除 thinking；如果完成，也清除 thinking
                      thinking: (data.is_complete || (data.content && data.content.length > 50)) ? undefined : m.thinking,
                    }
                  : m,
              ),
            );
          },
          onToolCall: (data) => {
            console.log('[ChatPanel] 收到 tool_call 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      toolCalls: [
                        ...(m.toolCalls || []),
                        {
                          tool_name: data.tool_name,
                          arguments: data.arguments,
                          status: data.status as 'start' | 'running' | 'complete',
                          timestamp: data.timestamp,
                        },
                      ],
                    }
                  : m,
              ),
            );
          },
          onToolResult: (data) => {
            console.log('[ChatPanel] 收到 tool_result 事件:', data);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      toolCalls: (m.toolCalls || []).map((tc) =>
                        tc.tool_name === data.tool_name
                          ? {
                              ...tc,
                              status: 'complete' as const,
                              result: data.result,
                              success: data.success,
                              error: data.error,
                            }
                          : tc,
                      ),
                    }
                  : m,
              ),
            );
          },
          onAgentComplete: (response) => {
            console.log('[ChatPanel] 收到 agent_complete 事件:', response);
            setSessionId(response.session_id);
            onSessionIdChange?.(response.session_id);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      // 如果 response.response 存在，使用它；否则保留已有内容
                      content: response.response || m.content || '',
                      // 不清除 thinking，让用户看到处理过程，但标记为完成
                      // thinking 会在内容开始显示时自然消失（通过 onAgentContent）
                      thinking: m.content ? undefined : m.thinking, // 如果已有内容，清除thinking；否则保留
                      // 保留之前设置的 sources（如果 agent_complete 中没有 sources，使用之前的）
                      sources: response.sources ?? m.sources ?? undefined,
                      knowledgeBaseIds: response.knowledge_base_ids ?? m.knowledgeBaseIds ?? undefined,
                      // 保留之前设置的 activatedSkills（如果 agent_complete 中没有，使用之前的）
                      activatedSkills: response.activated_skills ?? m.activatedSkills ?? undefined,
                      skillsPrompt: response.skills_prompt ?? m.skillsPrompt ?? undefined,
                      createdAt: response.created_at,
                    }
                  : m,
              ),
            );
            setIsThinking(false);
          },
          onError: (error) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: `⚠️ ${error}`,
                      thinking: undefined,
                    }
                  : m,
              ),
            );
            setIsThinking(false);
          },
        });
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '请求失败，请稍后重试';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentId
          ? { 
              ...m, 
                content: `⚠️ ${message}`,
                thinking: undefined,
                vectorizationStep: undefined,
            } 
            : m,
        ),
      );
      setIsThinking(false);
    }
  };

  // 一键总结为方案
  const handleGenerateSummary = async () => {
    if (!sessionId || isGeneratingSummary) return;

    setIsGeneratingSummary(true);
    setSummaryResult(null);

    try {
      const response = await api.generateSummaryPlan(sessionId, {
        top_k: 20,
      });

      if (response.success && response.data) {
        setSummaryResult({
          download_url: response.data.download_url,
          plan_content: response.data.plan_content,
          messages_used: response.data.messages_used,
          total_messages: response.data.total_messages,
        });
        showSuccess('方案生成完成！');
      } else {
        throw new Error(response.error || '生成方案失败');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '生成方案失败，请重试';
      showError(message);
      console.error('生成方案失败:', error);
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  // 判断是否应该显示"一键总结为方案"按钮（需要有对话历史且不是intro消息）
  const hasConversationHistory = messages.length > 1 && messages.some((m) => m.id !== 'intro');
  const canGenerateSummary = sessionId && hasConversationHistory && !isGeneratingSummary;

  return (
    <div className="h-full flex flex-col bg-white min-h-0 overflow-hidden">
      {renderUploadNotice()}

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-6 scroll-smooth min-h-0"
      >
        {/* 一键总结为方案按钮和结果卡片 */}
        {hasConversationHistory && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="sticky top-0 z-10 mb-4"
          >
            <AnimatePresence mode="wait">
              {summaryResult ? (
                // 生成结果卡片
                <motion.div
                  key="summary-result"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-4 shadow-lg"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-5 h-5 text-green-600" />
                      <h3 className="text-sm font-semibold text-green-800">方案已生成</h3>
                    </div>
                    <button
                      onClick={() => setSummaryResult(null)}
                      className="p-1 rounded hover:bg-green-100 text-green-600 transition-colors"
                      aria-label="关闭"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-xs text-green-700 mb-3">
                    已从 {summaryResult.total_messages} 条消息中筛选出 {summaryResult.messages_used} 条重要消息，生成完整方案。
                  </p>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        window.open(summaryResult.download_url, '_blank');
                      }}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                      size="sm"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      下载方案文档
                    </Button>
                    <Button
                      onClick={handleGenerateSummary}
                      variant="outline"
                      size="sm"
                      disabled={isGeneratingSummary}
                    >
                      <RotateCw className={cn("w-4 h-4 mr-2", isGeneratingSummary && "animate-spin")} />
                      重新生成
                    </Button>
                  </div>
                  {summaryResult.plan_content && (
                    <details className="mt-3">
                      <summary className="text-xs text-green-700 cursor-pointer hover:text-green-800">
                        预览方案内容
                      </summary>
                      <div className="mt-2 p-3 bg-white rounded-lg border border-green-200 max-h-40 overflow-auto text-xs">
                        <MarkdownRenderer content={summaryResult.plan_content} />
                      </div>
                    </details>
                  )}
                </motion.div>
              ) : isGeneratingSummary ? (
                // 生成中状态
                <motion.div
                  key="summary-generating"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-4 shadow-lg"
                >
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-blue-800 mb-1">正在生成方案...</h3>
                      <p className="text-xs text-blue-600">
                        正在分析对话历史，筛选重要信息并生成方案文档
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 w-full bg-blue-200 rounded-full h-2 overflow-hidden">
                    <motion.div
                      className="bg-blue-600 h-2 rounded-full"
                      initial={{ width: '0%' }}
                      animate={{ width: '70%' }}
                      transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
                    />
                  </div>
                </motion.div>
              ) : (
                // 一键总结为方案按钮
                <motion.div
                  key="summary-button"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex justify-center"
                >
                  <Button
                    onClick={handleGenerateSummary}
                    disabled={!canGenerateSummary}
                    className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white shadow-md hover:shadow-lg transition-all"
                    size="sm"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    一键总结为方案
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {messages.map((msg, index) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ 
              duration: 0.3,
              delay: index === messages.length - 1 ? 0.1 : 0
            }}
            onMouseEnter={() => setHoveredMessageId(msg.id)}
            onMouseLeave={() => setHoveredMessageId(null)}
            className={cn(
              "flex gap-3 mb-4 group/message-item",
              msg.role === 'user' ? "flex-row-reverse" : "flex-row"
            )}
          >
            {/* 用户消息头像 */}
            {msg.role === 'user' && (
              <motion.div
                whileHover={{ scale: 1.1 }}
                className="w-9 h-9 flex-shrink-0 bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center text-xs font-semibold shadow-lg ring-2 ring-blue-100/50"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </motion.div>
            )}
            
            {/* AI消息头像 */}
            {msg.role === 'agent' && (
              <motion.div
                whileHover={{ scale: 1.1 }}
                className="w-9 h-9 flex-shrink-0 bg-gradient-to-br from-gray-800 via-gray-900 to-black text-white rounded-full flex items-center justify-center font-serif text-xs font-bold shadow-lg ring-2 ring-gray-100/50"
              >
                AI
              </motion.div>
            )}
            
            <motion.div
              whileHover={{ scale: 1.02 }}
              className={cn(
                "px-4 py-3 text-sm leading-relaxed max-w-[80%] transition-all duration-200 relative",
                msg.role === 'user' 
                  ? "bg-gradient-to-br from-blue-500 via-blue-600 to-blue-700 text-white rounded-2xl rounded-tr-md shadow-lg hover:shadow-xl" 
                  : "bg-white border border-gray-200/80 text-gray-800 rounded-2xl rounded-tl-md shadow-md hover:shadow-lg hover:border-gray-300"
              )}
            >
              {/* 消息操作菜单 */}
              {hoveredMessageId === msg.id && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={cn(
                    "absolute -top-2 right-2 flex gap-1 rounded-lg shadow-lg p-1 z-10",
                    msg.role === 'user'
                      ? "bg-white/95 backdrop-blur-sm border border-white/50"
                      : "bg-white border border-gray-200"
                  )}
                >
                  {/* AI 消息的重新生成按钮 */}
                  {msg.role === 'agent' && (
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => {
                        // 重新生成功能
                        if (msg.content) {
                          void handleSend(msg.content);
                        }
                      }}
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-600 transition-colors"
                      aria-label="重新生成"
                      title="重新生成"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                    </motion.button>
                  )}
                  {/* 复制 Markdown 源码按钮 */}
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={async () => {
                      try {
                        // 复制原始 Markdown 源码（msg.content 就是 Markdown 源码）
                        await navigator.clipboard.writeText(msg.content || '');
                        setCopiedMessageId(msg.id);
                        showSuccess('已复制 Markdown 源码到剪贴板');
                        setTimeout(() => setCopiedMessageId(null), 2000);
                      } catch (err) {
                        console.error('复制失败', err);
                        showSuccess('复制失败，请重试');
                      }
                    }}
                    className={cn(
                      "p-1.5 rounded transition-colors",
                      msg.role === 'user'
                        ? "hover:bg-white/80 text-gray-700"
                        : "hover:bg-gray-100 text-gray-600"
                    )}
                    aria-label="复制 Markdown 源码"
                    title="复制 Markdown 源码"
                  >
                    {copiedMessageId === msg.id ? (
                      <Check className="w-3.5 h-3.5 text-green-600" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </motion.button>
                </motion.div>
              )}
              
              {/* 用户消息的装饰性光效 */}
              {msg.role === 'user' && (
                <div className="absolute inset-0 rounded-2xl rounded-tr-md bg-gradient-to-br from-white/20 via-white/5 to-transparent pointer-events-none" />
              )}
              {msg.thinking && (
                <ThinkingProcess steps={msg.thinking} isThinking={isThinking} />
              )}

              {msg.vectorizationStep && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-blue-700">
                      {msg.vectorizationStep.step === 'uploading' && '📤 上传中'}
                      {msg.vectorizationStep.step === 'parsing' && '📄 解析中'}
                      {msg.vectorizationStep.step === 'chunking' && '✂️ 分块中'}
                      {msg.vectorizationStep.step === 'embedding' && '🔢 向量化中'}
                      {msg.vectorizationStep.step === 'storing' && '💾 存储中'}
                      {msg.vectorizationStep.step === 'completed' && '✅ 完成'}
                      {msg.vectorizationStep.step === 'error' && '❌ 错误'}
                      {msg.vectorizationStep.step === 'chat_start' && '💬 生成回答中'}
                    </span>
                    {msg.vectorizationStep.progress !== undefined && (
                      <span className="text-xs text-blue-600">{Math.round(msg.vectorizationStep.progress)}%</span>
                    )}
                  </div>
                  <div className="text-xs text-blue-600 mb-2">{msg.vectorizationStep.message}</div>
                  {msg.vectorizationStep.progress !== undefined && (
                    <div className="w-full bg-blue-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${msg.vectorizationStep.progress}%` }}
                      />
                    </div>
                  )}
                  {msg.vectorizationStep.details && (
                    <details className="mt-2 text-xs text-blue-600">
                      <summary className="cursor-pointer hover:text-blue-800">详细信息</summary>
                      <pre className="mt-1 p-2 bg-blue-100 rounded text-xs overflow-auto">
                        {JSON.stringify(msg.vectorizationStep.details, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {msg.activatedSkills && msg.activatedSkills.length > 0 && (
                <div className="mb-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="flex items-center mb-2">
                    <span className="text-xs font-medium text-purple-700">🎯 已激活技能 ({msg.activatedSkills.length})</span>
                  </div>
                  <div className="space-y-2">
                    {msg.activatedSkills.map((skill, idx) => (
                      <div key={idx} className="text-xs">
                        <div className="font-medium text-purple-800">{skill.name}</div>
                        {skill.description && (
                          <div className="text-purple-600 mt-0.5">{skill.description}</div>
                        )}
                        {skill.version && (
                          <div className="text-purple-400 mt-0.5">v{skill.version}</div>
                        )}
                      </div>
                    ))}
                  </div>
                  {msg.skillsPrompt && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer text-purple-700 hover:text-purple-800">查看技能提示词</summary>
                      <pre className="mt-2 p-2 bg-purple-100 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                        {msg.skillsPrompt}
                      </pre>
                    </details>
                  )}
                </div>
              )}
              
              {msg.content && (
                <div className={cn(
                  "relative z-10",
                  msg.role === 'user' && "prose prose-invert prose-sm max-w-none [&_*]:text-white/95 [&_p]:text-white [&_strong]:text-white [&_em]:text-blue-100 [&_a]:text-blue-100 [&_a:hover]:text-white [&_code]:bg-white/20 [&_code]:text-white [&_pre]:bg-white/10 [&_pre]:border-white/20 [&_pre_code]:text-white"
                )}>
                  <MarkdownRenderer
                    content={preprocessContent(msg.content)}
                    citationEventName={CITATION_EVENT}
                  />
                </div>
              )}

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center mb-2">
                    <span className="text-xs font-medium text-green-700">📚 RAG 检索结果 ({msg.sources.length} 个来源)</span>
                  </div>
                  <div className="space-y-2">
                    {msg.sources.map((source: any, idx: number) => (
                      <div
                        key={idx}
                        className={cn(
                          "text-xs border-b border-green-200 pb-2 last:border-b-0 last:pb-0",
                          onSourceClick && "cursor-pointer hover:bg-green-100 rounded px-2 py-1 transition-colors"
                        )}
                        onClick={() => {
                          if (onSourceClick) {
                            onSourceClick(msg.sources || []);
                          }
                        }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-green-800">
                            来源 {idx + 1}
                            {source.metadata?.filename && (
                              <span className="ml-2 text-green-600">({source.metadata.filename})</span>
                            )}
                            {onSourceClick && (
                              <span className="ml-2 text-xs text-green-500">点击查看详情 →</span>
                            )}
                          </span>
                          {source.score !== undefined && (
                            <span className="text-green-600">相似度: {source.score.toFixed(2)}</span>
                          )}
                        </div>
                        {source.content && (
                          <div className="text-green-700 mt-1 line-clamp-2">
                            {source.content.substring(0, 150)}...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <div className="flex items-center mb-2">
                    <span className="text-xs font-medium text-orange-700">🔧 工具调用 ({msg.toolCalls.length})</span>
                  </div>
                  <div className="space-y-2">
                    {msg.toolCalls.map((toolCall, idx) => (
                      <div key={idx} className="text-xs border-b border-orange-200 pb-2 last:border-b-0 last:pb-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-orange-800">
                            {toolCall.tool_name}
                            {toolCall.status === 'start' && (
                              <span className="ml-2 text-orange-600">⏳ 调用中...</span>
                            )}
                            {toolCall.status === 'complete' && toolCall.success && (
                              <span className="ml-2 text-green-600">✅ 完成</span>
                            )}
                            {toolCall.status === 'complete' && !toolCall.success && (
                              <span className="ml-2 text-red-600">❌ 失败</span>
                            )}
                          </span>
                        </div>
                        {Object.keys(toolCall.arguments || {}).length > 0 && (
                          <details className="mt-1">
                            <summary className="cursor-pointer text-orange-600 hover:text-orange-800 text-xs">
                              查看参数
                            </summary>
                            <div className="mt-1 p-2 bg-orange-100 rounded text-xs overflow-auto max-h-32 max-w-full">
                              <pre className="whitespace-pre-wrap break-words">
                                {JSON.stringify(toolCall.arguments, null, 2)}
                              </pre>
                            </div>
                          </details>
                        )}
                        {toolCall.result && (
                          <details className="mt-1">
                            <summary className="cursor-pointer text-orange-600 hover:text-orange-800 text-xs">
                              查看结果
                            </summary>
                            <div className="mt-1 p-2 bg-orange-100 rounded text-xs overflow-auto max-h-48 max-w-full">
                              <pre className="whitespace-pre-wrap break-words">
                                {typeof toolCall.result === 'string' 
                                  ? toolCall.result 
                                  : JSON.stringify(toolCall.result, null, 2)}
                              </pre>
                            </div>
                          </details>
                        )}
                        {toolCall.error && (
                          <div className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                            错误: {toolCall.error}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="p-4 bg-white/90 backdrop-blur-md border-t border-gray-200/80 shadow-lg"
      >
        {/* 知识库选择器 */}
        <div className="mb-2">
          <KnowledgeBaseSelector
            selectedIds={localKnowledgeBaseIds}
            onSelectionChange={setLocalKnowledgeBaseIds}
          />
        </div>
        
        <AnimatePresence>
          {selectedFile && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-2 flex items-center gap-2 text-xs text-gray-600 bg-gradient-to-r from-gray-50 to-gray-100/50 border border-gray-200 rounded-lg px-3 py-2 shadow-sm"
            >
              <Paperclip className="w-4 h-4 text-blue-500" />
              <span className="flex-1 truncate font-medium">{selectedFile.name}</span>
              <motion.button
                whileHover={{ scale: 1.2 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                  }
                }}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                ×
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
        <div className="relative flex items-end gap-2 p-2 bg-gradient-to-br from-gray-50 to-white border border-gray-200/80 rounded-xl focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-300/50 transition-all shadow-sm">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.md,.txt,.xls,.xlsx,.ppt,.pptx,.csv,.html,.xml,.json"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-blue-600 hover:bg-blue-50 h-10 w-10 shrink-0 transition-colors"
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
          </motion.div>
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                // 防止重复发送：检查是否正在思考
                if (!isThinking && (input.trim() || selectedFile)) {
                  void handleSend();
                }
              }
            }}
            placeholder="输入问题，按 Enter 发送"
            aria-label="消息输入框"
            aria-describedby="input-hint"
            className="flex-1 bg-transparent border-none resize-none focus:ring-0 max-h-32 min-h-[40px] py-2 text-sm outline-none placeholder:text-gray-400"
            rows={1}
          />
          
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button 
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                // 防止重复发送：检查是否正在思考
                if (!isThinking && (input.trim() || selectedFile)) {
                  void handleSend();
                }
              }}
              disabled={(!input.trim() && !selectedFile) || isThinking}
              size="icon"
              variant={input.trim() || selectedFile ? "default" : "secondary"}
              className={cn(
                "h-10 w-10 shrink-0 transition-all shadow-md",
                (input.trim() || selectedFile) && "hover:shadow-lg"
              )}
            >
              {isThinking ? <StopCircle className="w-5 h-5" /> : <Send className="w-5 h-5" />}
            </Button>
          </motion.div>
        </div>
        <div id="input-hint" className="text-center mt-2 text-xs text-gray-400" role="note">
          AI may be imperfect — 请核对关键信息。
        </div>
      </motion.div>
    </div>
  );
};
