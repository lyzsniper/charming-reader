import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, Download, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { DocumentResponse } from '@/services/api';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Setup pdf worker - 使用 CDN 确保可用性
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface DocumentDetailModalProps {
  docId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({ docId, isOpen, onClose }) => {
  const [doc, setDoc] = useState<DocumentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'chunks' | 'pdf'>('chunks');
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [chunks, setChunks] = useState<string[]>([]);

  useEffect(() => {
    if (isOpen && docId) {
      loadDocument();
    } else {
      setDoc(null);
      setChunks([]);
    }
  }, [isOpen, docId]);

  const loadDocument = async () => {
    if (!docId) return;
    try {
      setIsLoading(true);
      const data = await api.getDocument(docId);
      setDoc(data);
      
      // 从 markdown 内容中提取 chunks（简单按段落分割）
      if (data.content_markdown) {
        const extractedChunks = data.content_markdown
          .split(/\n\s*\n/)
          .filter(chunk => chunk.trim().length > 50)
          .slice(0, 50); // 限制最多50个chunks
        setChunks(extractedChunks);
      }
    } catch (error) {
      console.error('Failed to load document', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (doc?.file_download_url) {
      window.open(doc.file_download_url, '_blank');
    }
  };

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  
  useEffect(() => {
    const loadPdfUrl = async () => {
      if (doc?.file_download_url) {
        // 先尝试使用提供的URL
        setPdfUrl(doc.file_download_url);
      } else if (doc?.id) {
        // 如果没有URL，通过API获取新的预签名URL
        try {
          const result = await api.getDocumentDownloadUrl(doc.id);
          setPdfUrl(result.file_download_url);
        } catch (error) {
          console.error('Failed to get document download URL', error);
          setPdfUrl(null);
        }
      } else {
        setPdfUrl(null);
      }
    };
    
    void loadPdfUrl();
  }, [doc]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="fixed inset-4 md:inset-10 bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 bg-black text-white rounded-xl flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-xl font-bold font-serif truncate">
                    {doc?.original_filename || '文档详情'}
                  </h2>
                  <p className="text-sm text-gray-500 truncate">
                    {doc?.file_size ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB` : ''} • {doc?.content_type}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {doc?.file_download_url && (
                  <Button variant="ghost" size="icon" onClick={handleDownload}>
                    <Download className="w-5 h-5" />
                  </Button>
                )}
                <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 px-6 pt-4 border-b">
              <button
                onClick={() => setActiveTab('chunks')}
                className={cn(
                  "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors",
                  activeTab === 'chunks'
                    ? "bg-white border-t border-x text-black"
                    : "text-gray-500 hover:text-gray-700"
                )}
              >
                文档块 ({chunks.length})
              </button>
              {pdfUrl && (
                <button
                  onClick={() => setActiveTab('pdf')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors",
                    activeTab === 'pdf'
                      ? "bg-white border-t border-x text-black"
                      : "text-gray-500 hover:text-gray-700"
                  )}
                >
                  PDF 预览
                </button>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex">
              {isLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                </div>
              ) : activeTab === 'chunks' ? (
                <div className="flex-1 overflow-y-auto p-6 bg-gray-50/30">
                  {chunks.length > 0 ? (
                    <div className="space-y-4 max-w-4xl mx-auto">
                      {chunks.map((chunk, idx) => (
                        <div
                          key={idx}
                          className="bg-white border rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow group"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="bg-blue-100 text-blue-700 text-xs font-mono px-2 py-1 rounded">
                              Chunk #{idx + 1}
                            </span>
                            <span className="text-xs text-gray-400">
                              {chunk.length} 字符
                            </span>
                          </div>
                          <p className="text-sm text-gray-700 leading-relaxed font-serif whitespace-pre-wrap">
                            {chunk.trim()}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
                      <FileText className="w-16 h-16 text-gray-300" />
                      <p>暂无文档块数据</p>
                    </div>
                  )}
                </div>
              ) : pdfUrl ? (
                <div className="flex-1 flex flex-col bg-gray-100">
                  <div className="flex items-center justify-between px-4 py-2 bg-white border-b">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">
                        {numPages && `第 ${pageNumber} / ${numPages} 页`}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setScale(s => Math.max(0.5, s - 0.1))}
                      >
                        <span className="text-xs">-</span>
                      </Button>
                      <span className="text-xs w-12 text-center">{Math.round(scale * 100)}%</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setScale(s => Math.min(2.0, s + 0.1))}
                      >
                        <span className="text-xs">+</span>
                      </Button>
                    </div>
                  </div>
                  <div className="flex-1 overflow-auto flex justify-center p-4">
                    <Document
                      file={pdfUrl}
                      onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                      loading={
                        <div className="flex items-center justify-center h-full">
                          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                        </div>
                      }
                    >
                      <Page
                        pageNumber={pageNumber}
                        scale={scale}
                        className="shadow-lg border border-gray-200"
                      />
                    </Document>
                  </div>
                  {numPages && numPages > 1 && (
                    <div className="flex items-center justify-center gap-2 px-4 py-2 bg-white border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageNumber(p => Math.max(1, p - 1))}
                        disabled={pageNumber <= 1}
                      >
                        上一页
                      </Button>
                      <span className="text-sm text-gray-600">
                        {pageNumber} / {numPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageNumber(p => Math.min(numPages, p + 1))}
                        disabled={pageNumber >= numPages}
                      >
                        下一页
                      </Button>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
