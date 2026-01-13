import React, { useState, useEffect } from 'react';
import { FileText, List, Search, ZoomIn, ZoomOut, RotateCw, Loader2, ChevronLeft, ChevronRight, Languages, Download, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { CITATION_EVENT } from './ChatPanel';
import { api, type DocumentTranslationResponse } from '@/services/api';
import { showError } from '@/utils/dialogs';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';

// Setup pdf worker - 使用 CDN 确保可用性
if (typeof window !== 'undefined') {
  // 使用 CDN 版本的 worker，确保在所有环境下都能工作
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface ContextPanelProps {
  fileUrl?: string | null;
  file?: File | null;
  sessionId?: string | null;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({ fileUrl, file, sessionId }) => {
  // 优先使用 File 对象，如果没有则使用 fileUrl
  const pdfSource = file || fileUrl;
  const [activeTab, setActiveTab] = useState<'pdf' | 'chunks' | 'translated'>('pdf');
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

  // Listen for citation clicks
  useEffect(() => {
    const handleCitationClick = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      console.log("Jump to citation:", detail.id);
      // Mock logic: Jump to page based on ID (randomly for demo)
      // In real app, you'd map Citation ID -> Page Number
      const targetPage = (parseInt(detail.id) % (numPages || 1)) + 1;
      setPageNumber(targetPage);
      setActiveTab('pdf');
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
    <div className="h-full flex flex-col bg-gray-50 border-l border-gray-200">
      {/* Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b h-14">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="font-semibold text-sm text-gray-700 truncate max-w-[150px]">
            {pdfSource ? (file?.name || "Document.pdf") : "No Document"}
          </span>
          {pdfSource && numPages && (
            <span className="text-xs text-gray-400">
              ({pageNumber} / {numPages})
            </span>
          )}
        </div>
        
        {/* View Controls */}
        {activeTab === 'pdf' && pdfSource && (
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

        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('pdf')}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-all",
              activeTab === 'pdf' ? "bg-white shadow-sm text-black" : "text-gray-500 hover:text-gray-700"
            )}
          >
            PDF View
          </button>
          <button
            onClick={() => setActiveTab('chunks')}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-all",
              activeTab === 'chunks' ? "bg-white shadow-sm text-black" : "text-gray-500 hover:text-gray-700"
            )}
          >
            Chunks
          </button>
          {translationResult && (
            <button
              onClick={() => setActiveTab('translated')}
              className={cn(
                "px-3 py-1 rounded-md text-xs font-medium transition-all",
                activeTab === 'translated' ? "bg-white shadow-sm text-black" : "text-gray-500 hover:text-gray-700"
              )}
            >
              翻译结果
            </button>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative bg-gray-100/50">
        {activeTab === 'pdf' ? (
          pdfSource ? (
            <div className="h-full overflow-auto flex justify-center p-4">
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
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
              <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <p>Upload a PDF to view it here</p>
            </div>
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
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
              <Languages className="w-16 h-16 text-gray-300" />
              <p>暂无翻译结果</p>
            </div>
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
               <div className="flex flex-col items-center justify-center py-8 text-gray-400 gap-2">
                 <FileText className="w-8 h-8 text-gray-300" />
                 <p className="text-sm">
                   {sessionId ? '暂无文档块' : '上传文档后查看文档块'}
                 </p>
               </div>
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
