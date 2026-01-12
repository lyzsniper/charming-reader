import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Paperclip, StopCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ThinkingProcess } from './ThinkingProcess';
import { api } from '@/services/api';
import type { ChatResponse } from '@/services/api';

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
  fileName?: string;
}

export const CITATION_EVENT = 'citation-click';

interface ChatPanelProps {
  knowledgeBaseIds?: string[];
  initialMessage?: string | null;
  conversationKey?: number;
  uploadState?: 'idle' | 'uploading' | 'success' | 'error';
  uploadError?: string | null;
  initialSessionId?: string | null;
  initialHistory?: Array<{ role: 'user' | 'agent'; text: string; created_at?: string | null }>;
  initialFile?: File | null;
  onSessionIdChange?: (sessionId: string | null) => void;
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
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [hasSentInitial, setHasSentInitial] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const intro: Message = {
      id: 'intro',
      role: 'agent',
      content: knowledgeBaseIds?.length
        ? '文档已上传，RAG 检索已开启。直接提问即可引用文档内容。'
        : initialFile
        ? '文档已准备就绪，正在分析...'
        : "Hello! 我是 CharMing Reader (查·明)。上传 PDF 或直接提问开始对话。",
    };
    const historyMsgs: Message[] = (initialHistory ?? [])
      .filter((m) => m.text && m.text.trim().length > 0) // 过滤掉空消息
      .map((m, idx) => ({
        id: `hist-${idx}`,
        role: m.role === 'agent' || m.role === 'model' ? 'agent' : 'user',
        content: m.text || '',
        createdAt: m.created_at ?? undefined,
      }));
    setMessages([intro, ...historyMsgs]);
    const newSessionId = initialSessionId ?? null;
    setSessionId(newSessionId);
    onSessionIdChange?.(newSessionId);
    setIsThinking(false);
    setHasSentInitial(false);
    setInput(initialMessage ?? '');
    // 如果有初始文件，设置为选中文件
    if (initialFile) {
      setSelectedFile(initialFile);
    }
  }, [knowledgeBaseIds, conversationKey, initialMessage, initialHistory, initialSessionId, initialFile, onSessionIdChange]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  useEffect(() => {
    if (hasSentInitial) return;
    // 如果有初始消息或初始文件，自动发送
    if (initialMessage || initialFile) {
      setHasSentInitial(true);
      const message = initialMessage || (initialFile ? '请分析这个文档' : '');
      void handleSend(message, true, initialFile ?? undefined);
    }
  }, [initialMessage, initialFile, hasSentInitial]);

  const preprocessContent = (content: string) => {
    return content.replace(/\[(\d+)\]/g, '[`[$1]`](#citation-$1)');
  };

  const renderUploadNotice = () => {
    if (uploadState === 'idle') return null;
    if (uploadState === 'uploading') {
      return (
        <div className="mx-4 mt-3 flex items-center gap-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Info className="w-4 h-4" />
          正在上传并解析文档，请稍候...
        </div>
      );
    }
    if (uploadState === 'error') {
      return (
        <div className="mx-4 mt-3 flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <Info className="w-4 h-4" />
          文档上传失败：{uploadError ?? '请重试'}
        </div>
      );
    }
    if (uploadState === 'success') {
      return (
        <div className="mx-4 mt-3 flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
          <Info className="w-4 h-4" />
          文档已上传完成，后续问题将结合文档进行回答。
        </div>
      );
    }
    return null;
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
    
    if (!content || isThinking) return;
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
    setIsThinking(true);

    try {
      // 如果有文件，使用带文件的聊天接口
      if (file) {
        await api.chatWithFile({
          file,
          message: contentOverride ?? content,
          session_id: sessionId,
          user_id: 'default_user',
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
          onChatResponse: (response) => {
            setSessionId(response.session_id);
            onSessionIdChange?.(response.session_id);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentId
                  ? {
                      ...m,
                      content: response.response,
                      thinking: undefined,
                      vectorizationStep: undefined,
                      sources: response.sources ?? undefined,
                      knowledgeBaseIds: response.knowledge_base_ids ?? undefined,
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
        // 没有文件，使用普通聊天接口
        const response = await api.chat({
          message: contentOverride ?? content,
          session_id: sessionId,
          knowledge_base_ids: knowledgeBaseIds?.length ? knowledgeBaseIds : undefined,
          use_rag: knowledgeBaseIds?.length ? true : undefined,
        });

        setSessionId(response.session_id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentId
              ? {
                  ...m,
                  content: response.response,
                  thinking: undefined,
                  sources: response.sources ?? undefined,
                  knowledgeBaseIds: response.knowledge_base_ids ?? undefined,
                  createdAt: response.created_at,
                }
              : m,
          ),
        );
        setIsThinking(false);
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

  return (
    <div className="h-full flex flex-col bg-white">
      {renderUploadNotice()}

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth"
      >
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={cn(
              "flex flex-col max-w-[90%]",
              msg.role === 'user' ? "self-end items-end" : "self-start items-start"
            )}
          >
            {msg.role === 'agent' && (
               <div className="w-8 h-8 mb-2 bg-black text-white rounded-lg flex items-center justify-center font-serif text-xs font-bold shadow-sm">
                 AI
               </div>
            )}
            
            <div className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
              msg.role === 'user' 
                ? "bg-blue-600 text-white rounded-tr-sm" 
                : "bg-white border border-gray-100 text-gray-800 rounded-tl-sm w-full"
            )}>
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
              
              {msg.content && (
                <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2">
                  <ReactMarkdown 
                    components={{
                      a: ({node, ...props}) => {
                         if (props.href?.startsWith('#citation-')) {
                           const id = props.href.split('-')[1];
                           return (
                             <button 
                               className="inline-flex items-center justify-center min-w-[1.2em] h-[1.2em] mx-0.5 text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 hover:scale-110 transition-all align-text-top cursor-pointer"
                               onClick={(e) => {
                                 e.preventDefault();
                                 window.dispatchEvent(new CustomEvent(CITATION_EVENT, { detail: { id } }));
                               }}
                             >
                               {id}
                             </button>
                           );
                         }
                         return <a {...props} className="text-blue-600 hover:underline" />;
                      }
                    }}
                  >
                    {preprocessContent(msg.content)}
                  </ReactMarkdown>
                </div>
              )}

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {msg.sources.map((_, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2 py-1 text-[11px] rounded-md bg-gray-100 text-gray-600 border border-gray-200"
                    >
                      来源 {idx + 1}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 bg-white/80 backdrop-blur-md border-t border-gray-100">
        {selectedFile && (
          <div className="mb-2 flex items-center gap-2 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
            <Paperclip className="w-4 h-4" />
            <span className="flex-1 truncate">{selectedFile.name}</span>
            <button
              onClick={() => {
                setSelectedFile(null);
                if (fileInputRef.current) {
                  fileInputRef.current.value = '';
                }
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
        )}
        <div className="relative flex items-end gap-2 p-2 bg-gray-50 border rounded-xl focus-within:ring-1 focus-within:ring-black/10 transition-all">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.md,.txt,.xls,.xlsx,.ppt,.pptx,.csv,.html,.xml,.json"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-400 hover:text-gray-600 h-10 w-10 shrink-0"
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            <Paperclip className="w-5 h-5" />
          </Button>
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder="输入问题，按 Enter 发送"
            className="flex-1 bg-transparent border-none resize-none focus:ring-0 max-h-32 min-h-[40px] py-2 text-sm outline-none"
            rows={1}
          />
          
          <Button 
            onClick={() => void handleSend()}
            disabled={(!input.trim() && !selectedFile) || isThinking}
            size="icon"
            className={cn(
              "h-10 w-10 shrink-0 transition-all",
              (input.trim() || selectedFile) ? "bg-black text-white" : "bg-gray-200 text-gray-400"
            )}
          >
            {isThinking ? <StopCircle className="w-5 h-5" /> : <Send className="w-5 h-5" />}
          </Button>
        </div>
        <div className="text-center mt-2 text-xs text-gray-400">
          AI may be imperfect — 请核对关键信息。
        </div>
      </div>
    </div>
  );
};
