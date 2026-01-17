const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:18000';

export const API_ROUTES = {
  chat: '/chat',
  chatForm: '/chat/form',
  uploadPdf: '/upload',
  knowledgeBases: '/knowledge-bases',
  documents: '/documents',
  ragQuery: '/rag/query',
  ragSearch: '/rag/search',
  ragUpload: '/rag/upload',
  skills: '/skills',
  suggestSkills: '/skills/suggest',
  sessions: '/sessions',
  sessionMessages: (sessionId: string) => `/sessions/${sessionId}/messages`,
  // Chat表相关接口
  chatSessions: '/chat/sessions',
  chatSession: (sessionId: string) => `/chat/sessions/${sessionId}`,
  chatSessionMessages: (sessionId: string) => `/chat/sessions/${sessionId}/messages`,
  chatSessionHistory: (sessionId: string) => `/chat/sessions/${sessionId}/history`,
  generateSummaryPlan: (sessionId: string) => `/chat/sessions/${sessionId}/generate-summary`,
  translate: '/translate',
  translateBatch: '/translate/batch',
  translateDetect: '/translate/detect',
  translateProviders: '/translate/providers',
  translateDocument: '/translate/document',
  // 模型配置相关接口
  modelConfigurations: '/model-configurations',
  modelConfiguration: (id: string) => `/model-configurations/${id}`,
  activeModelConfiguration: '/model-configurations/active',
  activateModelConfiguration: (id: string) => `/model-configurations/${id}/activate`,
  currentModelInfo: '/model-configurations/current/info',
} as const;

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions extends RequestInit {
  query?: Query;
}

const buildUrl = (path: string, query?: Query) => {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }
  return url.toString();
};

const request = async <T>(path: string, options: RequestOptions = {}): Promise<T> => {
  const { query, headers, ...rest } = options;
  const url = buildUrl(path, query);

  try {
    // 如果是 FormData，不要设置 Content-Type，让浏览器自动设置（包括 boundary）
    const isFormData = rest.body instanceof FormData;
    const requestHeaders: HeadersInit = isFormData
      ? { ...headers } // FormData 时不设置 Content-Type
      : {
          'Content-Type': 'application/json',
          ...headers,
        };

    const response = await fetch(url, {
      ...rest,
      headers: requestHeaders,
    });

    const text = await response.text();
    let data: unknown = null;
    
    try {
      data = text ? JSON.parse(text) : null;
    } catch (parseError) {
      // 如果响应不是 JSON，可能是纯文本错误
      throw new Error(text || response.statusText);
    }

    // 检查是否是统一错误格式
    if (data && typeof data === 'object' && 'success' in data && !data.success) {
      const errorData = data as { error: { code: string; message: string; details?: unknown } };
      const error = new Error(errorData.error.message);
      (error as { code?: string; details?: unknown }).code = errorData.error.code;
      (error as { code?: string; details?: unknown }).details = errorData.error.details;
      throw error;
    }

    if (!response.ok) {
      const message = 
        (data && typeof data === 'object' && 'detail' in data ? data.detail : null) ||
        (data && typeof data === 'object' && 'message' in data ? data.message : null) ||
        response.statusText ||
        '请求失败';
      throw new Error(typeof message === 'string' ? message : '请求失败');
    }

    // 如果响应是统一格式，提取 data 字段
    if (data && typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { data: T }).data;
    }

    return data as T;
  } catch (error) {
    // 网络错误或其他错误
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('网络连接失败，请检查网络设置');
    }
    throw error;
  }
};

export interface ChatRequest {
  message: string;
  session_id?: string | null;
  user_id?: string | null;
  knowledge_base_ids?: string[] | null;
  use_rag?: boolean;
  rag_top_k?: number;
  enable_rerank?: boolean;
}

export interface SkillInfo {
  name: string;
  description: string;
  version?: string | null;
}

export interface ChatResponse {
  session_id: string;
  user_id: string;
  message: string;
  response: string;
  sources?: Array<Record<string, unknown>> | null;
  knowledge_base_ids?: string[] | null;
  activated_skills?: SkillInfo[] | null;
  skills_prompt?: string | null;
  created_at?: string;
}

export interface KnowledgeBaseResponse {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  document_count?: number | null;
}

export interface DocumentResponse {
  id: string;
  original_filename: string;
  file_size?: number | null;
  upload_date: string;
  is_processed: boolean;
  storage_object_name: string;
  storage_path?: string | null;
  file_download_url?: string | null;
  content_type: string;
  content_markdown?: string | null;
  knowledge_bases: KnowledgeBaseResponse[];
}

export interface DocumentSimpleResponse {
  id: string;
  original_filename: string;
  file_size?: number | null;
  upload_date: string;
  is_processed: boolean;
}

export interface KnowledgeBaseDetailResponse {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  document_count?: number | null;
  documents: DocumentSimpleResponse[];
}

export interface KnowledgeBaseCreate {
  name: string;
  description?: string | null;
}

export interface KnowledgeBaseUpdate {
  name?: string | null;
  description?: string | null;
}

export interface SearchRequest {
  query: string;
  knowledge_base_ids?: string[] | null;
  session_id?: string | null;
  top_k?: number;
}

export interface SearchResult {
  id?: string;
  content?: string;
  score?: number;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

interface ChatOptions {
  message: string;
  session_id?: string | null;
  user_id?: string | null;
  model_id?: string | null;
  knowledge_base_ids?: string[] | null;
  use_rag?: boolean;
  rag_top_k?: number;
  enable_rerank?: boolean;
  onSkillLoading?: (data: { step: string; message: string; skill_name?: string }) => void;
  onSkillActivated?: (data: { skill_name: string; description: string; version?: string }) => void;
  onSkillContent?: (data: { skill_name: string; content_length: number }) => void;
  onRagRetrieval?: (data: { step: string; message: string; type?: string; count?: number }) => void;
  onRagSources?: (data: { sources: Array<Record<string, unknown>>; type?: string }) => void;
  onAgentThinking?: (data: { message: string }) => void;
  onAgentContent?: (data: { content: string; is_complete: boolean }) => void;
  onAgentComplete?: (response: ChatResponse) => void;
  onToolCall?: (data: { tool_name: string; arguments: Record<string, any>; status: string; timestamp: string }) => void;
  onToolResult?: (data: { tool_name: string; result: any; success: boolean; error?: string; timestamp: string }) => void;
  onError?: (error: string) => void;
}

const chat = async (options: ChatOptions): Promise<void> => {
  const url = buildUrl(API_ROUTES.chat);
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: options.message,
      session_id: options.session_id,
      user_id: options.user_id || 'default_user',
      model_id: options.model_id || undefined,
      knowledge_base_ids: options.knowledge_base_ids,
      use_rag: options.use_rag,
      rag_top_k: options.rag_top_k,
      enable_rerank: options.enable_rerank,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    const message = data?.detail || data?.error || response.statusText;
    throw new Error(typeof message === 'string' ? message : '请求失败');
  }

  // 使用SSE流式响应
  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) {
      throw new Error('无法读取响应流');
    }

    let buffer = '';
    let currentEventType = '';
    let accumulatedContent = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue; // 跳过空行
        
        if (line.startsWith('event: ')) {
          currentEventType = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim();
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              
              // 添加调试日志
              console.log(`[SSE] 收到事件: ${currentEventType}`, data);
              
              // 处理技能加载事件
              if (currentEventType === 'skill_loading' && options.onSkillLoading) {
                console.log('[SSE] 处理 skill_loading 事件');
                options.onSkillLoading(data);
              } 
              // 处理技能激活事件
              else if (currentEventType === 'skill_activated' && options.onSkillActivated) {
                console.log('[SSE] 处理 skill_activated 事件');
                options.onSkillActivated(data);
              } 
              // 处理技能内容事件
              else if (currentEventType === 'skill_content' && options.onSkillContent) {
                console.log('[SSE] 处理 skill_content 事件');
                options.onSkillContent(data);
              } 
              // 处理RAG检索事件
              else if (currentEventType === 'rag_retrieval' && options.onRagRetrieval) {
                console.log('[SSE] 处理 rag_retrieval 事件');
                options.onRagRetrieval(data);
              } 
              // 处理RAG检索结果事件
              else if (currentEventType === 'rag_sources' && options.onRagSources) {
                console.log('[SSE] 处理 rag_sources 事件, sources数量:', data.sources?.length);
                options.onRagSources(data);
              } 
              // 处理Agent思考事件
              else if (currentEventType === 'agent_thinking' && options.onAgentThinking) {
                console.log('[SSE] 处理 agent_thinking 事件');
                options.onAgentThinking(data);
              } 
              // 处理Agent内容事件（流式输出）
              else if (currentEventType === 'agent_content' && options.onAgentContent) {
                // data.content 是增量内容，需要累积
                // 注意：如果 is_complete 为 true 但 content 为空，表示只是完成标记
                if (data.content) {
                  accumulatedContent += data.content;
                }
                // 即使 content 为空，也要发送更新（可能是完成标记）
                options.onAgentContent({ 
                  content: accumulatedContent, 
                  is_complete: data.is_complete || false 
                });
              } 
              // 处理Agent完成事件
              else if (currentEventType === 'agent_complete' && options.onAgentComplete) {
                // 如果agent_complete事件中有response，使用它；否则使用累积的内容
                if (data.response && accumulatedContent !== data.response) {
                  accumulatedContent = data.response;
                }
                options.onAgentComplete(data as ChatResponse);
              } 
              // 处理工具调用事件
              else if (currentEventType === 'tool_call' && options.onToolCall) {
                console.log('[SSE] 处理 tool_call 事件:', data);
                options.onToolCall(data);
              }
              // 处理工具调用结果事件
              else if (currentEventType === 'tool_result' && options.onToolResult) {
                console.log('[SSE] 处理 tool_result 事件:', data);
                options.onToolResult(data);
              }
              // 处理错误事件
              else if (currentEventType === 'error' && options.onError) {
                options.onError(data.error || '未知错误');
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e, dataStr, '事件类型:', currentEventType);
            }
          }
          // 重置事件类型，准备处理下一个事件
          currentEventType = '';
        }
      }
    }
  } else {
    // 兼容旧格式（JSON响应）
    const data = await response.json();
    if (options.onAgentComplete) {
      options.onAgentComplete(data as ChatResponse);
    }
  }
};

interface ChatWithFileOptions {
  file?: File;
  message: string;
  session_id?: string | null;
  user_id?: string | null;
  model_id?: string | null;
  knowledge_base_ids?: string[] | null;
  use_rag?: boolean;
  rag_top_k?: number;
  enable_rerank?: boolean;
  onVectorizationStep?: (step: {
    step: string;
    message: string;
    progress?: number;
    details?: Record<string, unknown>;
  }) => void;
  onSkillLoading?: (data: { step: string; message: string; skill_name?: string }) => void;
  onSkillActivated?: (data: { skill_name: string; description: string; version?: string }) => void;
  onSkillContent?: (data: { skill_name: string; content_length: number }) => void;
  onRagRetrieval?: (data: { step: string; message: string; type?: string; count?: number }) => void;
  onRagSources?: (data: { sources: Array<Record<string, unknown>>; type?: string }) => void;
  onAgentThinking?: (data: { message: string }) => void;
  onAgentContent?: (data: { content: string; is_complete: boolean }) => void;
  onChatResponse?: (response: ChatResponse) => void;
  onToolCall?: (data: { tool_name: string; arguments: Record<string, any>; status: string; timestamp: string }) => void;
  onToolResult?: (data: { tool_name: string; result: any; success: boolean; error?: string; timestamp: string }) => void;
  onError?: (error: string) => void;
}

const chatWithFile = async (options: ChatWithFileOptions): Promise<void> => {
  const formData = new FormData();
  
  if (options.file) {
    formData.append('file', options.file);
  }
  formData.append('message', options.message);
  if (options.session_id) {
    formData.append('session_id', options.session_id);
  }
  formData.append('user_id', options.user_id || 'default_user');
  if (options.model_id) {
    formData.append('model_id', options.model_id);
  }
  if (options.knowledge_base_ids?.length) {
    formData.append('knowledge_base_ids', options.knowledge_base_ids.join(','));
  }
  formData.append('use_rag', String(options.use_rag ?? false));
  formData.append('rag_top_k', String(options.rag_top_k ?? 5));
  formData.append('enable_rerank', String(options.enable_rerank ?? true));

  // 使用 /chat/form 端点来处理文件上传
  const url = buildUrl(API_ROUTES.chatForm);
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    const message = data?.detail || data?.error || response.statusText;
    throw new Error(typeof message === 'string' ? message : '请求失败');
  }

  // 如果有文件，使用SSE流式响应
  if (options.file && response.headers.get('content-type')?.includes('text/event-stream')) {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) {
      throw new Error('无法读取响应流');
    }

    let buffer = '';
    let currentEventType = '';
    let accumulatedContent = ''; // 累积流式内容
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue; // 跳过空行
        
        if (line.startsWith('event: ')) {
          currentEventType = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim();
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              
              // 处理向量化步骤事件
              if (currentEventType === 'vectorization_step' && options.onVectorizationStep) {
                options.onVectorizationStep(data);
              } 
              // 处理技能加载事件
              else if (currentEventType === 'skill_loading' && options.onSkillLoading) {
                options.onSkillLoading(data);
              } 
              // 处理技能激活事件
              else if (currentEventType === 'skill_activated' && options.onSkillActivated) {
                options.onSkillActivated(data);
              } 
              // 处理技能内容事件
              else if (currentEventType === 'skill_content' && options.onSkillContent) {
                options.onSkillContent(data);
              } 
              // 处理RAG检索事件
              else if (currentEventType === 'rag_retrieval' && options.onRagRetrieval) {
                options.onRagRetrieval(data);
              } 
              // 处理RAG检索结果事件
              else if (currentEventType === 'rag_sources' && options.onRagSources) {
                options.onRagSources(data);
              } 
              // 处理Agent思考事件
              else if (currentEventType === 'agent_thinking' && options.onAgentThinking) {
                options.onAgentThinking(data);
              } 
              // 处理Agent内容事件（流式输出）
              else if (currentEventType === 'agent_content' && options.onAgentContent) {
                // data.content 是增量内容，需要累积
                // 注意：如果 is_complete 为 true 但 content 为空，表示只是完成标记
                if (data.content) {
                  accumulatedContent += data.content;
                }
                // 即使 content 为空，也要发送更新（可能是完成标记）
                options.onAgentContent({ 
                  content: accumulatedContent, 
                  is_complete: data.is_complete || false 
                });
              } 
              // 处理Agent完成事件
              else if (currentEventType === 'agent_complete' && options.onChatResponse) {
                // 如果agent_complete事件中有response，使用它；否则使用累积的内容
                if (data.response && accumulatedContent !== data.response) {
                  accumulatedContent = data.response;
                }
                options.onChatResponse(data as ChatResponse);
              } 
              // 处理聊天响应事件（兼容旧格式）
              else if (currentEventType === 'chat_response' && options.onChatResponse) {
                options.onChatResponse(data as ChatResponse);
              }
              // 处理工具调用事件
              else if (currentEventType === 'tool_call' && options.onToolCall) {
                console.log('[SSE] 处理 tool_call 事件:', data);
                options.onToolCall(data);
              }
              // 处理工具调用结果事件
              else if (currentEventType === 'tool_result' && options.onToolResult) {
                console.log('[SSE] 处理 tool_result 事件:', data);
                options.onToolResult(data);
              }
              // 处理错误事件
              else if (currentEventType === 'error' && options.onError) {
                options.onError(data.error || '未知错误');
              } 
              // 处理聊天开始事件
              else if (currentEventType === 'chat_start' && options.onVectorizationStep) {
                options.onVectorizationStep({
                  step: 'chat_start',
                  message: data.message || '开始生成回答...',
                  progress: undefined,
                  details: undefined
                });
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e, dataStr, '事件类型:', currentEventType);
            }
          }
          // 重置事件类型，准备处理下一个事件
          currentEventType = '';
        }
      }
    }
  } else {
    // 没有文件，使用普通JSON响应
    const data = await response.json();
    if (options.onChatResponse) {
      options.onChatResponse(data as ChatResponse);
    }
  }
};

const uploadPdf = (file: File, opts?: { knowledgeBaseIds?: string[] }) => {
  const formData = new FormData();
  formData.append('file', file);

  return request<DocumentResponse>(API_ROUTES.uploadPdf, {
    method: 'POST',
    body: formData,
    query: opts?.knowledgeBaseIds?.length
      ? { knowledge_base_ids: opts.knowledgeBaseIds.join(',') }
      : undefined,
  });
};

const listKnowledgeBases = (params?: { skip?: number; limit?: number }) => {
  return request<KnowledgeBaseResponse[]>(API_ROUTES.knowledgeBases, {
    method: 'GET',
    query: {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const listDocuments = (params?: { knowledge_base_id?: string; skip?: number; limit?: number }) => {
  return request<DocumentResponse[]>(API_ROUTES.documents, {
    method: 'GET',
    query: {
      knowledge_base_id: params?.knowledge_base_id,
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const getDocument = (docId: string) => {
  return request<DocumentResponse>(`${API_ROUTES.documents}/${docId}`, {
    method: 'GET',
  });
};

const createKnowledgeBase = (payload: KnowledgeBaseCreate) => {
  return request<KnowledgeBaseResponse>(API_ROUTES.knowledgeBases, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
};

const getKnowledgeBase = (kbId: string) => {
  return request<KnowledgeBaseDetailResponse>(`${API_ROUTES.knowledgeBases}/${kbId}`, {
    method: 'GET',
  });
};

const updateKnowledgeBase = (kbId: string, payload: KnowledgeBaseUpdate) => {
  return request<KnowledgeBaseResponse>(`${API_ROUTES.knowledgeBases}/${kbId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
};

const deleteKnowledgeBase = (kbId: string) => {
  return request<void>(`${API_ROUTES.knowledgeBases}/${kbId}`, {
    method: 'DELETE',
  });
};

const getKnowledgeBaseDocuments = (kbId: string) => {
  return request<DocumentSimpleResponse[]>(`${API_ROUTES.knowledgeBases}/${kbId}/documents`, {
    method: 'GET',
  });
};

const addDocumentToKnowledgeBase = (docId: string, kbId: string) => {
  return request<void>(`${API_ROUTES.documents}/${docId}/knowledge-bases/${kbId}`, {
    method: 'POST',
  });
};

const removeDocumentFromKnowledgeBase = (docId: string, kbId: string) => {
  return request<void>(`${API_ROUTES.documents}/${docId}/knowledge-bases/${kbId}`, {
    method: 'DELETE',
  });
};

const ragSearch = async (payload: SearchRequest) => {
  const response = await request<{ results: SearchResult[]; count: number }>(API_ROUTES.ragSearch, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  // 返回results数组
  return response.results || [];
};

export interface SessionHistoryItem {
  session_id: string;
  title: string;
  last_message_time: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SessionsResponse {
  sessions: SessionHistoryItem[];
  total: number;
}

export interface SessionMessage {
  role: string;
  text: string;
  created_at?: string | null;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: SessionMessage[];
}

const listSessions = (params?: { user_id?: string; skip?: number; limit?: number }) => {
  return request<SessionsResponse>(API_ROUTES.sessions, {
    method: 'GET',
    query: {
      user_id: params?.user_id ?? 'default_user',
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const getDocumentDownloadUrl = (docId: string) => {
  return request<{ file_download_url: string; storage_object_name: string }>(
    `${API_ROUTES.documents}/${docId}/download-url`,
    {
      method: 'GET',
    }
  );
};

const listSessionMessages = (sessionId: string, params?: { user_id?: string }) => {
  return request<SessionMessagesResponse>(API_ROUTES.sessionMessages(sessionId), {
    method: 'GET',
    query: {
      user_id: params?.user_id ?? 'default_user',
    },
  });
};

// ===== 翻译相关 API =====

export interface TranslationRequest {
  text: string;
  from_language?: string;
  to_language: string;
  provider?: string;
}

export interface TranslationResponse {
  original_text: string;
  translated_text: string | null;
  from_language: string;
  to_language: string;
  provider: string;
  success: boolean;
  error?: string | null;
}

export interface DocumentTranslationResponse {
  original_text: string;
  translated_text: string;
  from_language: string;
  to_language: string;
  provider: string;
  original_filename: string;
  chunks_count: number;
  success: boolean;
}

// ===== Chat表相关接口类型 =====

export interface ChatSessionResponse {
  id: string;
  session_id: string;
  session_title?: string | null;
  user_id: string;
  custom_metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionUpdate {
  session_title?: string | null;
  custom_metadata?: Record<string, unknown> | null;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: string;
  message_type: string;
  content: string;
  message_metadata?: Record<string, unknown> | null;
  parent_message_id?: string | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  id: string;
  session_id: string;
  turn_index: number;
  user_message_id?: string | null;
  assistant_message_id?: string | null;
  summary?: string | null;
  created_at: string;
}

export interface ChatHistoryDetailResponse extends ChatHistoryResponse {
  user_message?: ChatMessageResponse | null;
  assistant_message?: ChatMessageResponse | null;
}

const translate = (payload: TranslationRequest) => {
  return request<TranslationResponse>(API_ROUTES.translate, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
};

const translateDocument = async (
  file: File,
  to_language: string,
  from_language: string = 'auto',
  provider: string = 'google'
): Promise<DocumentTranslationResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('from_language', from_language);
  formData.append('to_language', to_language);
  formData.append('provider', provider);

  const url = buildUrl(API_ROUTES.translateDocument);
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message = data?.detail || data?.error || response.statusText;
    throw new Error(typeof message === 'string' ? message : '翻译失败');
  }

  return data as DocumentTranslationResponse;
};

// ===== Chat表相关API =====

const listChatSessions = (params?: { user_id?: string; skip?: number; limit?: number }) => {
  return request<ChatSessionResponse[]>(API_ROUTES.chatSessions, {
    method: 'GET',
    query: {
      user_id: params?.user_id ?? 'default_user',
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const getChatSession = (sessionId: string) => {
  return request<ChatSessionResponse>(API_ROUTES.chatSession(sessionId), {
    method: 'GET',
  });
};

const updateChatSession = (sessionId: string, payload: ChatSessionUpdate) => {
  return request<ChatSessionResponse>(API_ROUTES.chatSession(sessionId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
};

const deleteChatSession = (sessionId: string) => {
  return request<{ success: boolean; message: string }>(API_ROUTES.chatSession(sessionId), {
    method: 'DELETE',
  });
};

const getChatMessages = (sessionId: string, params?: { 
  role?: string; 
  message_type?: string; 
  skip?: number; 
  limit?: number 
}) => {
  return request<ChatMessageResponse[]>(API_ROUTES.chatSessionMessages(sessionId), {
    method: 'GET',
    query: {
      role: params?.role,
      message_type: params?.message_type,
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const getChatHistory = (sessionId: string, params?: { skip?: number; limit?: number }) => {
  return request<ChatHistoryDetailResponse[]>(API_ROUTES.chatSessionHistory(sessionId), {
    method: 'GET',
    query: {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

// 一键总结为方案相关接口
export interface SummaryPlanResponse {
  success: boolean;
  data: {
    object_name: string;
    download_url: string;
    plan_content: string;
    messages_used: number;
    total_messages: number;
  };
  error?: string;
}

const generateSummaryPlan = (sessionId: string, params?: { top_k?: number; max_messages?: number }) => {
  return request<SummaryPlanResponse>(API_ROUTES.generateSummaryPlan(sessionId), {
    method: 'POST',
    query: {
      top_k: params?.top_k ?? 20,
      max_messages: params?.max_messages,
    },
  });
};

// 模型配置相关接口类型
export interface ModelConfiguration {
  id: string;
  name: string;
  model_name: string;
  api_key?: string | null;
  base_url?: string | null;
  provider?: string | null;
  description?: string | null;
  is_active: boolean;
  temperature?: number | null;
  max_tokens?: number | null;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigurationCreate {
  name: string;
  model_name: string;
  api_key?: string | null;
  base_url?: string | null;
  provider?: string | null;
  description?: string | null;
  is_active?: boolean;
  temperature?: number | null;
  max_tokens?: number | null;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
}

export interface ModelConfigurationUpdate {
  name?: string;
  model_name?: string;
  api_key?: string | null;
  base_url?: string | null;
  provider?: string | null;
  description?: string | null;
  is_active?: boolean;
  temperature?: number | null;
  max_tokens?: number | null;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
}

const listModelConfigurations = (params?: { skip?: number; limit?: number }) => {
  return request<ModelConfiguration[]>(API_ROUTES.modelConfigurations, {
    method: 'GET',
    query: {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    },
  });
};

const getModelConfiguration = (id: string) => {
  return request<ModelConfiguration>(API_ROUTES.modelConfiguration(id), {
    method: 'GET',
  });
};

const getActiveModelConfiguration = () => {
  return request<ModelConfiguration>(API_ROUTES.activeModelConfiguration, {
    method: 'GET',
  });
};

const createModelConfiguration = (config: ModelConfigurationCreate) => {
  return request<ModelConfiguration>(API_ROUTES.modelConfigurations, {
    method: 'POST',
    body: JSON.stringify(config),
  });
};

const updateModelConfiguration = (id: string, config: ModelConfigurationUpdate) => {
  return request<ModelConfiguration>(API_ROUTES.modelConfiguration(id), {
    method: 'PUT',
    body: JSON.stringify(config),
  });
};

const deleteModelConfiguration = (id: string) => {
  return request<void>(API_ROUTES.modelConfiguration(id), {
    method: 'DELETE',
  });
};

const activateModelConfiguration = (id: string) => {
  return request<ModelConfiguration>(API_ROUTES.activateModelConfiguration(id), {
    method: 'POST',
  });
};

const getCurrentModelInfo = () => {
  return request<{ model_name: string; source: string; description?: string }>(API_ROUTES.currentModelInfo, {
    method: 'GET',
  });
};

export const api = {
  routes: API_ROUTES,
  chat,
  chatWithFile,
  uploadPdf,
  listKnowledgeBases,
  listDocuments,
  getDocument,
  getDocumentDownloadUrl,
  createKnowledgeBase,
  getKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBaseDocuments,
  addDocumentToKnowledgeBase,
  removeDocumentFromKnowledgeBase,
  ragSearch,
  listSessions,
  listSessionMessages,
  // Chat表相关API
  listChatSessions,
  getChatSession,
  updateChatSession,
  deleteChatSession,
  getChatMessages,
  getChatHistory,
  generateSummaryPlan,
  translate,
  translateDocument,
  // 模型配置相关API
  listModelConfigurations,
  getModelConfiguration,
  getActiveModelConfiguration,
  createModelConfiguration,
  updateModelConfiguration,
  deleteModelConfiguration,
  activateModelConfiguration,
  getCurrentModelInfo,
};
