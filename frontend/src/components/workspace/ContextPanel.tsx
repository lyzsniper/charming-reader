import React, { useState, useEffect } from 'react';
import { FileText, List, Search, ZoomIn, ZoomOut, RotateCw, Loader2, ChevronLeft, ChevronRight, Languages, Download, X, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { CITATION_EVENT } from './ChatPanel';
import { api, type DocumentTranslationResponse } from '@/services/api';
import { showError } from '@/utils/dialogs';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { EmptyState } from '@/components/common/EmptyState';

// Setup pdf worker - 使用 CDN 确保可用性
if (typeof window !== 'undefined') {
  // 使用 CDN 版本的 worker，确保在所有环境下都能工作
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface RAGSource {
  content: string;
  score?: number;
  metadata?: {
    document_id?: string;
    filename?: string;
    chunk_index?: number;
    knowledge_base_ids?: string[];
    upload_date?: string;
    [key: string]: unknown;
  };
}

// 定义上下文数据类型
export type ContextDataType = 'rag-sources' | 'tool-calls' | 'preview' | 'chunks' | 'translated';

export interface ContextData {
  type: ContextDataType;
  data: any; // 根据 type 不同，data 的类型也不同
}

interface ContextPanelProps {
  fileUrl?: string | null;
  file?: File | null;
  sessionId?: string | null;
  ragSources?: RAGSource[] | null; // 兼容旧接口：RAG 检索结果
  contextData?: ContextData | null; // 新增：统一的上下文数据
  onClose?: () => void; // 关闭回调
}

export const ContextPanel: React.FC<ContextPanelProps> = ({ fileUrl, file, sessionId, ragSources, contextData, onClose }) => {
  // 确定当前显示的内容类型
  // 优先级：contextData > ragSources > preview (如果有文件或预览数据)
  const getActiveTab = (): ContextDataType => {
    if (contextData) {
      return contextData.type;
    }
    if (ragSources && ragSources.length > 0) {
      return 'rag-sources';
    }
    // 如果有文件或预览数据，显示预览
    if (file || fileUrl) {
      return 'preview';
    }
    return 'chunks';
  };
  
  const [activeTab, setActiveTab] = useState<ContextDataType>(getActiveTab());
  
  // 当 contextData 或 ragSources 变化时，自动切换 tab
  useEffect(() => {
    const newTab = getActiveTab();
    setActiveTab(newTab);
  }, [contextData, ragSources, file, fileUrl]);
  
  // 获取预览数据
  const previewData = contextData?.type === 'preview' ? contextData.data : null;
  
  // 判断预览类型：PDF 还是 Markdown
  const getPreviewType = (): 'pdf' | 'markdown' | 'text' | null => {
    // 如果有预览数据，使用预览数据的类型
    if (previewData) {
      if (previewData.fileType === 'markdown' || previewData.fileType === 'md') {
        return 'markdown';
      }
      if (previewData.fileType === 'pdf') {
        return 'pdf';
      }
      return 'text';
    }
    // 如果有文件，根据文件类型判断
    if (file) {
      if (file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf')) {
        return 'pdf';
      }
      if (file.type === 'text/markdown' || file.name?.toLowerCase().endsWith('.md')) {
        return 'markdown';
      }
    }
    // 如果有fileUrl，假设是PDF（因为通常fileUrl用于PDF）
    if (fileUrl) {
      return 'pdf';
    }
    return null;
  };
  
  const previewType = getPreviewType();
  
  // 获取PDF源：优先使用fileUrl（已经是blob URL），如果没有则从file创建
  const [pdfSource, setPdfSource] = useState<string | File | null>(fileUrl || file);
  const [createdBlobUrl, setCreatedBlobUrl] = useState<string | null>(null);
  
  useEffect(() => {
    // 清理之前创建的blob URL
    if (createdBlobUrl) {
      URL.revokeObjectURL(createdBlobUrl);
      setCreatedBlobUrl(null);
    }
    
    // 如果有file但没有fileUrl，创建blob URL
    if (file && !fileUrl && previewType === 'pdf') {
      const url = URL.createObjectURL(file);
      setPdfSource(url);
      setCreatedBlobUrl(url);
    } else if (fileUrl) {
      setPdfSource(fileUrl);
    } else if (file) {
      setPdfSource(file);
    } else {
      setPdfSource(null);
    }
    
    // 清理函数
    return () => {
      if (createdBlobUrl) {
        URL.revokeObjectURL(createdBlobUrl);
      }
    };
  }, [file, fileUrl, previewType]);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [chunks, setChunks] = useState<Array<{ content: string; score?: number; metadata?: Record<string, unknown> }>>([]);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [chunkSearchQuery, setChunkSearchQuery] = useState('');
  
  // 翻译相关状态
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationResult, setTranslationResult] = useState<DocumentTranslationResponse | null>(null);
  const [toLanguage, setToLanguage] = useState('en');
  const [fromLanguage, setFromLanguage] = useState('auto');
  const [showTranslationModal, setShowTranslationModal] = useState(false);
  
  // 移除文档加载功能，不再加载和显示 PDF 预览

  // Listen for citation clicks
  useEffect(() => {
    const handleCitationClick = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      console.log("Jump to citation:", detail.id);
      // Mock logic: Jump to page based on ID (randomly for demo)
      // In real app, you'd map Citation ID -> Page Number
      const targetPage = (parseInt(detail.id) % (numPages || 1)) + 1;
      setPageNumber(targetPage);
      setActiveTab('preview');
    };

    window.addEventListener(CITATION_EVENT, handleCitationClick);
    return () => window.removeEventListener(CITATION_EVENT, handleCitationClick);
  }, [numPages]);

  // Load chunks when sessionId changes or when switching to chunks tab
  useEffect(() => {
    const loadChunks = async () => {
      if (!sessionId || activeTab !== 'chunks') {
        setChunks([]);
        return;
      }

      try {
        setIsLoadingChunks(true);
        // 如果有搜索词，使用搜索词；否则使用通用查询词获取所有 chunks
        const query = chunkSearchQuery.trim() || 'document text content';
        const results = await api.ragSearch({
          query,
          session_id: sessionId,
          top_k: 50, // 获取更多 chunks
        });
        setChunks(results);
      } catch (error) {
        console.error('Failed to load chunks', error);
        setChunks([]);
      } finally {
        setIsLoadingChunks(false);
      }
    };

    void loadChunks();
  }, [sessionId, activeTab, chunkSearchQuery]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1); // 重置到第一页
  }

  const goToPreviousPage = () => {
    if (numPages && pageNumber > 1) {
      setPageNumber(pageNumber - 1);
    }
  };

  const goToNextPage = () => {
    if (numPages && pageNumber < numPages) {
      setPageNumber(pageNumber + 1);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 border-l border-gray-200 overflow-hidden">
      {/* Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b h-14">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="font-semibold text-sm text-gray-700 truncate max-w-[150px]">
            {activeTab === 'preview' && previewData
              ? previewData.fileName || "方案预览"
              : activeTab === 'preview' && (file || fileUrl)
              ? (file?.name || "Document.pdf")
              : activeTab === 'rag-sources' && ragSources && ragSources.length > 0
              ? `RAG 检索结果 (${ragSources.length})`
              : "No Document"}
          </span>
          {previewType === 'pdf' && numPages && activeTab === 'preview' && (
            <span className="text-xs text-gray-400">
              ({pageNumber} / {numPages})
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* View Controls */}
        {activeTab === 'preview' && previewType === 'pdf' && pdfSource && (
          <div className="flex items-center gap-2 mr-2">
            {/* Page Navigation */}
            {numPages && numPages > 1 && (
              <div className="flex items-center gap-1 border-r pr-2 mr-2">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8" 
                  onClick={goToPreviousPage}
                  disabled={pageNumber <= 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-xs text-gray-600 min-w-[60px] text-center">
                  {pageNumber} / {numPages}
                </span>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8" 
                  onClick={goToNextPage}
                  disabled={pageNumber >= numPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
            {/* Zoom Controls */}
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-xs w-10 text-center">{Math.round(scale * 100)}%</span>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setScale(s => Math.min(2.0, s + 0.1))}>
                <ZoomIn className="w-4 h-4" />
              </Button>
            </div>
            {/* Translation Button */}
            {file && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5"
                onClick={() => setShowTranslationModal(true)}
                disabled={isTranslating}
              >
                <Languages className="w-3.5 h-3.5" />
                翻译
              </Button>
            )}
          </div>
        )}
        
        {/* Close Button */}
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            aria-label="关闭右侧面板"
          >
            <X className="w-4 h-4" />
          </Button>
        )}
        </div>

        <div className="flex bg-gray-100/80 rounded-lg p-1 gap-1">
          {(file || fileUrl || previewData) && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('preview')}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all relative",
                activeTab === 'preview' ? "text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {activeTab === 'preview' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-md shadow-sm"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span className="relative z-10">预览</span>
            </motion.button>
          )}
          {sessionId && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('chunks')}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all relative",
                activeTab === 'chunks' ? "text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {activeTab === 'chunks' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-md shadow-sm"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span className="relative z-10">Chunks</span>
            </motion.button>
          )}
          {(ragSources && ragSources.length > 0) || (contextData?.type === 'rag-sources' && contextData.data) && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('rag-sources')}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all relative",
                activeTab === 'rag-sources' ? "text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {activeTab === 'rag-sources' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-md shadow-sm"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span className="relative z-10">
                RAG 来源 ({ragSources?.length || (contextData?.type === 'rag-sources' && Array.isArray(contextData.data) ? contextData.data.length : 0)})
              </span>
            </motion.button>
          )}
          {contextData?.type === 'tool-calls' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('tool-calls')}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all relative",
                activeTab === 'tool-calls' ? "text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {activeTab === 'tool-calls' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-md shadow-sm"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span className="relative z-10">
                工具调用 ({Array.isArray(contextData.data) ? contextData.data.length : 1})
              </span>
            </motion.button>
          )}
          {translationResult && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('translated')}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all relative",
                activeTab === 'translated' ? "text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              {activeTab === 'translated' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-white rounded-md shadow-sm"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <span className="relative z-10">翻译结果</span>
            </motion.button>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative bg-gray-100/50 min-h-0">
        <AnimatePresence mode="wait">
          {activeTab === 'preview' ? (
            // 统一的预览视图 - 根据类型自动判断显示PDF还是Markdown
            previewType === 'pdf' && pdfSource ? (
              // PDF预览
              <motion.div
                key="pdf-preview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="h-full overflow-auto flex justify-center p-4"
              >
                <Document
                  file={pdfSource}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={(error) => {
                    console.error('PDF load error:', error);
                    console.error('PDF source:', pdfSource);
                    console.error('File type:', file?.type);
                    console.error('File size:', file?.size);
                  }}
                  loading={
                    <div className="flex flex-col items-center justify-center p-8 text-gray-400">
                      <Loader2 className="w-8 h-8 animate-spin mb-2" />
                      <p>加载 PDF...</p>
                    </div>
                  }
                  error={
                    <div className="flex flex-col items-center justify-center p-8 text-red-400">
                      <FileText className="w-8 h-8 mb-2" />
                      <p>无法加载 PDF 文件</p>
                      <p className="text-xs mt-2 text-gray-500">请确保文件格式正确且可访问</p>
                    </div>
                  }
                  className="shadow-lg"
                >
                  <Page 
                    pageNumber={pageNumber} 
                    scale={scale} 
                    rotate={rotation}
                    renderAnnotationLayer={true}
                    renderTextLayer={true}
                    className="border border-gray-200"
                    loading={
                      <div className="flex items-center justify-center p-4 text-gray-400">
                        <Loader2 className="w-4 h-4 animate-spin" />
                      </div>
                    }
                  />
                </Document>
              </motion.div>
            ) : previewData ? (
              // Markdown或其他文本预览
              <motion.div
                key="text-preview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="h-full flex flex-col min-h-0 bg-white"
              >
                {/* Preview Header */}
                <div className="px-4 py-3 bg-white border-b flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-purple-500" />
                    <span className="text-sm font-medium">{previewData.fileName || "方案预览"}</span>
                    <span className="text-xs text-gray-400">
                      {previewData.fileType === 'markdown' || previewData.fileType === 'md' ? 'Markdown' : previewData.fileType}
                    </span>
                  </div>
                  {previewData.downloadUrl && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1.5"
                      onClick={async () => {
                        try {
                          // 使用 fetch 获取文件内容，确保强制下载
                          const response = await fetch(previewData.downloadUrl);
                          if (!response.ok) {
                            throw new Error('下载失败');
                          }
                          const blob = await response.blob();
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = previewData.fileName || `download.${previewData.fileType === 'markdown' || previewData.fileType === 'md' ? 'md' : previewData.fileType || 'txt'}`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);
                        } catch (error) {
                          console.error('下载文件失败:', error);
                          // 如果 fetch 失败，回退到直接打开链接
                          window.open(previewData.downloadUrl, '_blank');
                        }
                      }}
                    >
                      <Download className="w-3.5 h-3.5" />
                      下载文件
                    </Button>
                  )}
                </div>
                {/* Preview Content */}
                <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 bg-white min-h-0">
                  {previewData.fileType === 'markdown' || previewData.fileType === 'md' ? (
                    <div className="max-w-4xl mx-auto prose prose-sm max-w-none">
                      <MarkdownRenderer content={previewData.content} />
                    </div>
                  ) : (
                    <div className="max-w-4xl mx-auto">
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap break-words bg-gray-50 p-4 rounded-lg border border-gray-200">
                        {previewData.content}
                      </pre>
                    </div>
                  )}
                </div>
              </motion.div>
            ) : (
              <EmptyState
                icon={FileText}
                title="暂无预览内容"
                description="上传文件或生成预览后，内容会显示在这里"
                size="md"
              />
            )
          ) : activeTab === 'tool-calls' ? (
            // 工具调用结果视图
            contextData?.type === 'tool-calls' && contextData.data ? (
              <div className="h-full flex flex-col min-h-0">
                <div className="px-4 py-2 bg-white border-b flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-orange-500" />
                    <span className="text-sm font-medium">工具调用详情</span>
                    <span className="text-xs text-gray-400">
                      {Array.isArray(contextData.data) ? contextData.data.length : 1} 个调用
                    </span>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 bg-white min-h-0">
                  {(Array.isArray(contextData.data) ? contextData.data : [contextData.data]).map((toolCall: any, idx: number) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="bg-white p-4 rounded-xl border-2 border-gray-200 hover:border-orange-300 shadow-md hover:shadow-lg transition-all"
                    >
                      {/* Tool Call Header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono bg-orange-100 text-orange-700 px-2 py-1 rounded">
                            {toolCall.tool_name || `调用 ${idx + 1}`}
                          </span>
                          {toolCall.status === 'start' && (
                            <span className="text-xs text-orange-600">⏳ 调用中...</span>
                          )}
                          {toolCall.status === 'complete' && toolCall.success && (
                            <span className="text-xs text-green-600">✅ 完成</span>
                          )}
                          {toolCall.status === 'complete' && !toolCall.success && (
                            <span className="text-xs text-red-600">❌ 失败</span>
                          )}
                        </div>
                        {toolCall.timestamp && (
                          <span className="text-xs text-gray-400">
                            {new Date(toolCall.timestamp).toLocaleString('zh-CN')}
                          </span>
                        )}
                      </div>
                      
                      {/* Tool Call Arguments */}
                      {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
                        <div className="mb-3">
                          <div className="text-xs font-medium text-gray-700 mb-2">调用参数：</div>
                          <div className="bg-orange-50 p-3 rounded-lg border border-orange-200">
                            <pre className="text-xs text-gray-800 whitespace-pre-wrap break-words overflow-auto">
                              {JSON.stringify(toolCall.arguments, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                      
                      {/* Tool Call Result */}
                      {toolCall.result && (
                        <div className="mb-3">
                          <div className="text-xs font-medium text-gray-700 mb-2">调用结果：</div>
                          <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                            <pre className="text-xs text-gray-800 whitespace-pre-wrap break-words overflow-auto max-h-96">
                              {typeof toolCall.result === 'string' 
                                ? toolCall.result 
                                : JSON.stringify(toolCall.result, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                      
                      {/* Tool Call Error */}
                      {toolCall.error && (
                        <div className="mb-3">
                          <div className="text-xs font-medium text-red-700 mb-2">错误信息：</div>
                          <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                            <pre className="text-xs text-red-800 whitespace-pre-wrap break-words">
                              {toolCall.error}
                            </pre>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={FileText}
                title="暂无工具调用结果"
                description="工具调用结果会显示在这里"
                size="md"
              />
            )
          ) : activeTab === 'rag-sources' ? (
            (ragSources && ragSources.length > 0) || (contextData?.type === 'rag-sources' && contextData.data) ? (
            <div className="h-full flex flex-col min-h-0">
              {/* RAG Sources Header */}
              <div className="px-4 py-2 bg-white border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-medium">RAG 检索来源</span>
                  <span className="text-xs text-gray-400">
                    {ragSources.length} 个来源
                  </span>
                </div>
              </div>
              {/* RAG Sources Content */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 bg-white min-h-0">
                {(ragSources || (contextData?.type === 'rag-sources' && Array.isArray(contextData.data) ? contextData.data : [])).map((source, idx) => {
                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      whileHover={{ scale: 1.02, y: -2 }}
                      className="bg-white p-4 rounded-xl border-2 border-gray-200 hover:border-green-300 shadow-md hover:shadow-lg transition-all"
                    >
                      {/* Source Header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono bg-green-100 text-green-700 px-2 py-1 rounded">
                            来源 {idx + 1}
                          </span>
                          {source.metadata?.filename && (
                            <span className="text-xs text-gray-600">
                              {source.metadata.filename}
                            </span>
                          )}
                        </div>
                        {source.score !== undefined && (
                          <span className="text-xs font-medium text-green-600">
                            相似度: {source.score.toFixed(2)}
                          </span>
                        )}
                      </div>
                      
                      {/* Source Content - 显示完整的 chunk 内容 */}
                      <div className="mb-3">
                        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap break-words">
                          {source.content}
                        </div>
                      </div>
                      
                      {/* Source Metadata */}
                      <div className="text-xs text-gray-500 space-y-1 border-t pt-2">
                        {source.metadata?.document_id && (
                          <div>文档ID: {String(source.metadata.document_id).slice(0, 8)}...</div>
                        )}
                        {source.metadata?.chunk_index !== undefined && (
                          <div>块索引: {source.metadata.chunk_index}</div>
                        )}
                        {source.metadata?.upload_date && (
                          <div>上传时间: {new Date(source.metadata.upload_date as string).toLocaleString('zh-CN')}</div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={BookOpen}
              title="暂无 RAG 检索结果"
              description="当 AI 引用知识库内容时，检索结果会显示在这里"
              size="md"
            />
          )
          ) : activeTab === 'translated' ? (
          translationResult ? (
            <div className="h-full flex flex-col">
              {/* Translation Result Header */}
              <div className="px-4 py-2 bg-white border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Languages className="w-4 h-4 text-blue-500" />
                  <span className="text-sm font-medium">翻译结果</span>
                  <span className="text-xs text-gray-400">
                    {translationResult.from_language} → {translationResult.to_language}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5"
                  onClick={() => {
                    // 下载翻译后的文档为Markdown文件
                    const blob = new Blob([translationResult.translated_text], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${file?.name?.replace(/\.[^/.]+$/, '') || 'document'}_translated.md`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <Download className="w-3.5 h-3.5" />
                  下载
                </Button>
              </div>
              {/* Translation Content */}
              <div className="flex-1 overflow-y-auto p-6 bg-white">
                <MarkdownRenderer content={translationResult.translated_text} />
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Languages}
              title="暂无翻译结果"
              description="翻译文档后，结果会显示在这里"
              size="md"
            />
          )
        ) : (
          <div className="p-4 space-y-4 overflow-y-auto h-full">
             <div className="flex items-center gap-2 mb-4 bg-white p-2 rounded-lg border sticky top-0 shadow-sm z-10">
               <Search className="w-4 h-4 text-gray-400" />
               <input 
                 className="flex-1 text-sm outline-none" 
                 placeholder="搜索文档块..."
                 value={chunkSearchQuery}
                 onChange={(e) => setChunkSearchQuery(e.target.value)}
               />
             </div>
             
             {/* Actual Chunks */}
             {isLoadingChunks ? (
               <div className="flex items-center justify-center py-8">
                 <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                 <span className="ml-2 text-sm text-gray-400">加载中...</span>
               </div>
             ) : chunks.length === 0 ? (
               <EmptyState
                 icon={FileText}
                 title={sessionId ? '暂无文档块' : '上传文档后查看文档块'}
                 description={sessionId ? '当前会话没有可用的文档块' : '上传文档后，文档会被分割成块并显示在这里'}
                 size="sm"
                 className="py-8"
               />
             ) : (
               chunks.map((chunk, i) => (
                 <div key={i} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:border-blue-300 transition-colors cursor-pointer group">
                   <div className="flex justify-between items-start mb-2">
                     <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-500">
                       Chunk #{i + 1}
                       {chunk.metadata?.chunk_index !== undefined && ` (Index: ${chunk.metadata.chunk_index})`}
                     </span>
                     {chunk.score !== undefined && (
                       <span className="text-xs text-gray-400">Score: {chunk.score.toFixed(3)}</span>
                     )}
                   </div>
                   <p className="text-sm text-gray-600 leading-relaxed group-hover:text-gray-900 font-serif">
                     {chunk.content || '无内容'}
                   </p>
                   {chunk.metadata?.document_id && (
                     <div className="mt-2 text-xs text-gray-400">
                       文档ID: {String(chunk.metadata.document_id).slice(0, 8)}...
                     </div>
                   )}
                 </div>
               ))
             )}
          </div>
        )}
        </AnimatePresence>
      </div>

      {/* Translation Modal */}
      {showTranslationModal && file && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => !isTranslating && setShowTranslationModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Languages className="w-5 h-5 text-blue-500" />
                翻译文档
              </h3>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setShowTranslationModal(false)}
                disabled={isTranslating}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">源语言</label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  value={fromLanguage}
                  onChange={(e) => setFromLanguage(e.target.value)}
                >
                  <option value="auto">自动检测</option>
                  <option value="zh">中文</option>
                  <option value="en">英语</option>
                  <option value="ja">日语</option>
                  <option value="ko">韩语</option>
                  <option value="fr">法语</option>
                  <option value="de">德语</option>
                  <option value="es">西班牙语</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">目标语言</label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  value={toLanguage}
                  onChange={(e) => setToLanguage(e.target.value)}
                >
                  <option value="en">英语</option>
                  <option value="zh">中文</option>
                  <option value="ja">日语</option>
                  <option value="ko">韩语</option>
                  <option value="fr">法语</option>
                  <option value="de">德语</option>
                  <option value="es">西班牙语</option>
                </select>
              </div>
              
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowTranslationModal(false)}
                  disabled={isTranslating}
                >
                  取消
                </Button>
                <Button
                  className="flex-1"
                  onClick={async () => {
                    if (!file) return;
                    
                    setIsTranslating(true);
                    try {
                      const result = await api.translateDocument(
                        file,
                        toLanguage,
                        fromLanguage,
                        'google'
                      );
                      setTranslationResult(result);
                      setActiveTab('translated');
                      setShowTranslationModal(false);
                    } catch (error) {
                      console.error('Translation failed', error);
                      showError(`翻译失败: ${error instanceof Error ? error.message : '未知错误'}`, '翻译错误');
                    } finally {
                      setIsTranslating(false);
                    }
                  }}
                  disabled={isTranslating}
                >
                  {isTranslating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      翻译中...
                    </>
                  ) : (
                    '开始翻译'
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
