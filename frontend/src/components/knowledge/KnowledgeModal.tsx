import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, Upload, Search, Database, Plus, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { KnowledgeBaseResponse, KnowledgeBaseDetailResponse, DocumentSimpleResponse, SearchResult } from '@/services/api';
import { DocumentDetailModal } from './DocumentDetailModal';
import { showSuccess, showError, showWarning } from '@/utils/dialogs';
import { PromptDialog } from '@/components/common/PromptDialog';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

interface KnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KnowledgeModal: React.FC<KnowledgeModalProps> = ({ isOpen, onClose }) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseResponse[]>([]);
  const [selectedKb, setSelectedKb] = useState<string | null>(null);
  const [kbDetail, setKbDetail] = useState<KnowledgeBaseDetailResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [isDocDetailOpen, setIsDocDetailOpen] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [kbToDelete, setKbToDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleOpenDocDetail = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.docId) {
        setSelectedDocId(detail.docId);
        setIsDocDetailOpen(true);
      }
    };
    window.addEventListener('open-document-detail', handleOpenDocDetail);
    return () => window.removeEventListener('open-document-detail', handleOpenDocDetail);
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadKnowledgeBases();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedKb) {
      loadKnowledgeBaseDetail(selectedKb);
    } else {
      setKbDetail(null);
      setSearchResults([]);
    }
  }, [selectedKb]);

  const loadKnowledgeBases = async () => {
    try {
      setIsLoading(true);
      const data = await api.listKnowledgeBases();
      setKnowledgeBases(data);
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0].id);
      }
    } catch (error) {
      console.error('Failed to load knowledge bases', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadKnowledgeBaseDetail = async (kbId: string) => {
    try {
      setIsLoading(true);
      const data = await api.getKnowledgeBase(kbId);
      setKbDetail(data);
    } catch (error) {
      console.error('Failed to load knowledge base detail', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !selectedKb) return;
    try {
      setIsSearching(true);
      const results = await api.ragSearch({
        query: searchQuery,
        knowledge_base_ids: [selectedKb],
        top_k: 10,
      });
      console.log('Search results:', results); // 调试日志
      setSearchResults(Array.isArray(results) ? results : []);
    } catch (error) {
      console.error('Search failed', error);
      setSearchResults([]);
      showError('搜索失败: ' + (error instanceof Error ? error.message : '未知错误'), '搜索错误');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCreateKnowledgeBase = async (name: string) => {
    if (!name?.trim()) return;
    try {
      setIsCreating(true);
      await api.createKnowledgeBase({ name, description: null });
      await loadKnowledgeBases();
      showSuccess('知识库创建成功');
    } catch (error) {
      console.error('Failed to create knowledge base', error);
      showError('创建知识库失败，请稍后重试');
    } finally {
      setIsCreating(false);
      setPromptOpen(false);
    }
  };

  const handleDeleteKnowledgeBase = async (kbId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setKbToDelete(kbId);
    setConfirmDeleteOpen(true);
  };

  const confirmDelete = async () => {
    if (!kbToDelete) return;
    try {
      await api.deleteKnowledgeBase(kbToDelete);
      if (selectedKb === kbToDelete) {
        setSelectedKb(null);
      }
      await loadKnowledgeBases();
      showSuccess('知识库删除成功');
    } catch (error) {
      console.error('Failed to delete knowledge base', error);
      showError('删除知识库失败，请稍后重试');
    } finally {
      setConfirmDeleteOpen(false);
      setKbToDelete(null);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!selectedKb) {
      showWarning('请先选择知识库', '提示');
      return;
    }
    try {
      setIsLoading(true);
      const doc = await api.uploadPdf(file, { knowledgeBaseIds: [selectedKb] });
      await loadKnowledgeBaseDetail(selectedKb);
      showSuccess('文档上传成功', '上传成功');
    } catch (error) {
      console.error('Upload failed', error);
      showError(error instanceof Error ? error.message : '文档上传失败', '上传失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
      handleFileUpload(files[0]);
    }
  };

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
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <div className="flex items-center justify-between p-6 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-black text-white rounded-xl flex items-center justify-center">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold font-serif">知识库管理</h2>
                  <p className="text-sm text-gray-500">管理研究资源和向量化文档块</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="flex-1 flex overflow-hidden">
              <div className="w-64 bg-gray-50 border-r p-4 flex flex-col gap-2">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">知识库</div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => setPromptOpen(true)}
                    disabled={isCreating}
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                
                {isLoading && knowledgeBases.length === 0 ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                  </div>
                ) : knowledgeBases.length === 0 ? (
                  <div className="text-sm text-gray-400 py-4 text-center">暂无知识库</div>
                ) : (
                  knowledgeBases.map((kb) => (
                    <div key={kb.id} className="relative group">
                      <Button
                        variant={selectedKb === kb.id ? 'secondary' : 'ghost'}
                        className={cn(
                          "justify-start w-full",
                          selectedKb === kb.id && "bg-white shadow-sm text-black"
                        )}
                        onClick={() => setSelectedKb(kb.id)}
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        <span className="flex-1 text-left truncate">{kb.name}</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-1 top-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => handleDeleteKnowledgeBase(kb.id, e)}
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </Button>
                    </div>
                  ))
                )}

                <div className="mt-auto pt-4 border-t border-gray-200">
                  <div
                    className="border-2 border-dashed border-gray-300 rounded-xl p-4 flex flex-col items-center justify-center text-gray-400 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-500 transition-colors cursor-pointer group"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-medium">上传 PDF</span>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  />
                </div>
              </div>

              <div className="flex-1 flex flex-col bg-white">
                <div className="p-4 border-b flex items-center gap-3">
                  <Search className="w-5 h-5 text-gray-400" />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="flex-1 text-sm outline-none placeholder:text-gray-400"
                    placeholder="搜索文档块或测试召回..."
                  />
                  <Button
                    onClick={handleSearch}
                    disabled={!searchQuery.trim() || !selectedKb || isSearching}
                    size="sm"
                  >
                    {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : '搜索'}
                  </Button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                  {/* 左侧：知识库详情或搜索结果 */}
                  <div className={cn(
                    "p-6 overflow-y-auto bg-gray-50/30 transition-all",
                    searchResults.length > 0 ? "w-1/2 border-r" : "flex-1"
                  )}>
                    {selectedKb && !kbDetail ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                      </div>
                    ) : searchResults.length > 0 ? (
                      // 有搜索结果时，显示搜索结果
                      <div className="space-y-3">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-semibold text-gray-700">搜索结果 ({searchResults.length})</h3>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSearchResults([]);
                              setSearchQuery('');
                            }}
                          >
                            <X className="w-4 h-4 mr-1" />
                            清除
                          </Button>
                        </div>
                        {searchResults.map((result, idx) => (
                          <div key={idx} className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="bg-blue-100 text-blue-700 text-[10px] font-mono px-1.5 py-0.5 rounded">
                                  #{idx + 1}
                                </span>
                                {typeof result.score === 'number' && (
                                  <span className="text-xs text-gray-500">相似度: {(result.score * 100).toFixed(1)}%</span>
                                )}
                              </div>
                            </div>
                            <p className="text-sm text-gray-700 leading-relaxed font-serif">
                              {typeof result.content === 'string' ? result.content : JSON.stringify(result)}
                            </p>
                            {result.metadata && Object.keys(result.metadata).length > 0 && (
                              <div className="mt-2 pt-2 border-t text-xs text-gray-400">
                                {Object.entries(result.metadata).slice(0, 3).map(([key, value]) => (
                                  <span key={key} className="mr-3">
                                    {key}: {String(value)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : kbDetail ? (
                      // 没有搜索结果时，显示知识库详情
                      <div className="space-y-4 max-w-3xl mx-auto">
                        <div className="bg-white rounded-xl p-4 border">
                          <h3 className="font-semibold mb-2">{kbDetail.name}</h3>
                          {kbDetail.description && (
                            <p className="text-sm text-gray-600 mb-2">{kbDetail.description}</p>
                          )}
                          <p className="text-xs text-gray-400">
                            文档数量: {kbDetail.document_count ?? kbDetail.documents.length}
                          </p>
                        </div>
                        {kbDetail.documents.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-sm font-semibold text-gray-700">文档列表</h4>
                            {kbDetail.documents.map((doc) => (
                              <button
                                key={doc.id}
                                onClick={() => {
                                  window.dispatchEvent(new CustomEvent('open-document-detail', { detail: { docId: doc.id } }));
                                }}
                                className="w-full text-left bg-white border rounded-lg p-3 hover:border-blue-300 hover:shadow-sm transition-all"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                                    <p className="text-xs text-gray-400 mt-1">
                                      {doc.is_processed ? '已处理' : '处理中'} • {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : ''}
                                    </p>
                                  </div>
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
                        <Database className="w-16 h-16 text-gray-300" />
                        <p>选择一个知识库开始管理</p>
                      </div>
                    )}
                  </div>

                  {/* 右侧：当有搜索结果时，显示知识库详情 */}
                  {searchResults.length > 0 && kbDetail && (
                    <div className="w-1/2 flex flex-col bg-white border-l p-6 overflow-y-auto">
                      <div className="mb-4">
                        <h3 className="font-semibold mb-2">{kbDetail.name}</h3>
                        {kbDetail.description && (
                          <p className="text-sm text-gray-600 mb-2">{kbDetail.description}</p>
                        )}
                        <p className="text-xs text-gray-400">
                          文档数量: {kbDetail.document_count ?? kbDetail.documents.length}
                        </p>
                      </div>
                      {kbDetail.documents.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">文档列表</h4>
                          {kbDetail.documents.map((doc) => (
                            <button
                              key={doc.id}
                              onClick={() => {
                                window.dispatchEvent(new CustomEvent('open-document-detail', { detail: { docId: doc.id } }));
                              }}
                              className="w-full text-left bg-gray-50 border rounded-lg p-3 hover:border-blue-300 hover:shadow-sm transition-all"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                                  <p className="text-xs text-gray-400 mt-1">
                                    {doc.is_processed ? '已处理' : '处理中'} • {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : ''}
                                  </p>
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>

          {/* 文档详情模态框 */}
          <DocumentDetailModal
            docId={selectedDocId}
            isOpen={isDocDetailOpen}
            onClose={() => {
              setIsDocDetailOpen(false);
              setSelectedDocId(null);
            }}
          />

          {/* Prompt Dialog for creating knowledge base */}
          <PromptDialog
            open={promptOpen}
            onOpenChange={setPromptOpen}
            title="创建知识库"
            description="请输入知识库名称"
            placeholder="例如：论文知识库"
            confirmText="创建"
            cancelText="取消"
            onConfirm={handleCreateKnowledgeBase}
            validator={(value) => {
              if (!value.trim()) {
                return '知识库名称不能为空';
              }
              if (value.length > 50) {
                return '知识库名称不能超过 50 个字符';
              }
              return null;
            }}
          />

          {/* Confirm Dialog for deleting knowledge base */}
          <ConfirmDialog
            open={confirmDeleteOpen}
            onOpenChange={setConfirmDeleteOpen}
            title="确认删除"
            description="确定要删除这个知识库吗？删除后无法恢复。"
            confirmText="删除"
            cancelText="取消"
            onConfirm={confirmDelete}
            variant="destructive"
          />
        </>
      )}
    </AnimatePresence>
  );
};


