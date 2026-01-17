import React, { useState, useEffect, useRef } from 'react';
import { FileText, Upload, Database, Plus, Trash2, Loader2, X, ChevronRight, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { KnowledgeBaseResponse, KnowledgeBaseDetailResponse } from '@/services/api';
import { DocumentDetailModal } from './DocumentDetailModal';
import { KnowledgeSearchModal } from './KnowledgeSearchModal';
import { showSuccess, showError, showWarning } from '@/utils/dialogs';
import { PromptDialog } from '@/components/common/PromptDialog';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { EmptyState } from '@/components/common/EmptyState';

interface KnowledgeViewProps {
  onClose: () => void;
}

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({ onClose }) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseResponse[]>([]);
  const [selectedKb, setSelectedKb] = useState<string | null>(null);
  const [kbDetail, setKbDetail] = useState<KnowledgeBaseDetailResponse | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDocDetailOpen, setIsDocDetailOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [kbToDelete, setKbToDelete] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  useEffect(() => {
    if (selectedKb) {
      loadKnowledgeBaseDetail(selectedKb);
      setSelectedDoc(null);
    } else {
      setKbDetail(null);
    }
  }, [selectedKb]);

  useEffect(() => {
    if (selectedDoc) {
      setIsDocDetailOpen(true);
    }
  }, [selectedDoc]);

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

    // 检查文件格式
    const allowedExtensions = ['.pdf', '.doc', '.docx', '.md', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.html', '.xml', '.json'];
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      showError(`不支持的文件格式。允许的格式: ${allowedExtensions.join(', ')}`, '文件格式错误');
      return;
    }

    try {
      setIsUploading(true);
      await api.uploadPdf(file, { knowledgeBaseIds: [selectedKb] });
      await loadKnowledgeBaseDetail(selectedKb);
      showSuccess('文档上传成功，正在处理中...', '上传成功');
      // 刷新文档列表
      setTimeout(() => {
        loadKnowledgeBaseDetail(selectedKb);
      }, 2000);
    } catch (error) {
      console.error('Upload failed', error);
      showError(error instanceof Error ? error.message : '文档上传失败', '上传失败');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const formatFileSize = (bytes: number | null | undefined) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
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
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setIsSearchOpen(true)}>
            文档块搜索
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Knowledge Bases */}
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
            <EmptyState
              icon={Database}
              title="暂无知识库"
              description="创建你的第一个知识库开始管理文档"
              action={{
                label: "创建知识库",
                onClick: () => setPromptOpen(true),
              }}
              size="sm"
              className="py-8"
            />
          ) : (
            knowledgeBases.map((kb, index) => (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="relative group"
              >
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    variant={selectedKb === kb.id ? 'secondary' : 'ghost'}
                    className={cn(
                      "justify-start w-full transition-all",
                      selectedKb === kb.id && "bg-white shadow-md text-black border border-gray-200"
                    )}
                    onClick={() => setSelectedKb(kb.id)}
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    <span className="flex-1 text-left truncate font-medium">{kb.name}</span>
                  </Button>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileHover={{ opacity: 1, scale: 1.1 }}
                  className="absolute right-1 top-1"
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
                    onClick={(e) => handleDeleteKnowledgeBase(kb.id, e)}
                  >
                    <Trash2 className="w-3 h-3 text-red-500" />
                  </Button>
                </motion.div>
              </motion.div>
            ))
          )}

          <div className="mt-auto pt-4 border-t border-gray-200">
            <motion.div
              whileHover={!isUploading ? { scale: 1.02 } : {}}
              whileTap={!isUploading ? { scale: 0.98 } : {}}
              className={cn(
                "border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-gray-400 hover:border-blue-400 hover:bg-gradient-to-br hover:from-blue-50 hover:to-blue-100/50 hover:text-blue-600 transition-all cursor-pointer group shadow-sm hover:shadow-md",
                isUploading && "opacity-50 cursor-not-allowed"
              )}
              onClick={() => !isUploading && fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add('border-blue-400', 'bg-blue-50');
              }}
              onDragLeave={(e) => {
                e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50');
              }}
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-6 h-6 mb-2 animate-spin text-blue-500" />
                  <span className="text-xs font-medium">上传中...</span>
                </>
              ) : (
                <>
                  <motion.div
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Upload className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
                  </motion.div>
                  <span className="text-xs font-medium">上传文档</span>
                </>
              )}
            </motion.div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.md,.txt,.xls,.xlsx,.ppt,.pptx,.csv,.html,.xml,.json"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            />
          </div>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 flex flex-col bg-white">
          <div className="flex-1 overflow-hidden flex">
            {/* Document List */}
            <div className="w-80 border-r bg-gray-50/30 p-4 overflow-y-auto">
              {selectedKb && !kbDetail ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              ) : kbDetail ? (
                <div className="space-y-4">
                  <div className="bg-white rounded-xl p-4 border">
                    <h3 className="font-semibold mb-2">{kbDetail.name}</h3>
                    {kbDetail.description && (
                      <p className="text-sm text-gray-600 mb-2">{kbDetail.description}</p>
                    )}
                    <p className="text-xs text-gray-400">
                      文档数量: {kbDetail.document_count ?? kbDetail.documents.length}
                    </p>
                  </div>
                  {kbDetail.documents.length > 0 ? (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">文档列表</div>
                      {kbDetail.documents.map((doc, index) => (
                        <motion.div
                          key={doc.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.03 }}
                          whileHover={{ scale: 1.02, x: 4 }}
                          className={cn(
                            "bg-white border rounded-lg p-3 cursor-pointer hover:shadow-lg transition-all group",
                            selectedDoc === doc.id && "border-blue-500 shadow-lg bg-blue-50/30"
                          )}
                          onClick={() => setSelectedDoc(doc.id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                              </div>
                              <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                                <span className={cn(
                                  "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                  doc.is_processed ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                                )}>
                                  {doc.is_processed ? '已处理' : '处理中'}
                                </span>
                                {doc.file_size && (
                                  <span>• {formatFileSize(doc.file_size)}</span>
                                )}
                              </div>
                            </div>
                            <ChevronRight className={cn(
                              "w-4 h-4 text-gray-400 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity",
                              selectedDoc === doc.id && "opacity-100"
                            )} />
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={FileText}
                      title="暂无文档"
                      description="上传文档到知识库开始使用"
                      size="sm"
                      className="py-8"
                    />
                  )}
                </div>
              ) : (
                <EmptyState
                  icon={Database}
                  title="选择一个知识库"
                  description="从左侧列表中选择一个知识库开始管理文档"
                  size="md"
                />
              )}
            </div>

            {/* Document Detail Placeholder */}
            <div className="flex-1 p-6 overflow-y-auto bg-white border-l">
              {selectedDoc ? (
                <EmptyState
                  icon={FileText}
                  title="文档详情"
                  description="查看文档的详细信息和内容"
                  action={{
                    label: "查看详情",
                    onClick: () => setIsDocDetailOpen(true),
                  }}
                  size="md"
                />
              ) : (
                <EmptyState
                  icon={Info}
                  title="选择一个文档"
                  description="从左侧列表中选择一个文档查看详情"
                  size="md"
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Document Detail Modal */}
      <DocumentDetailModal
        docId={selectedDoc}
        isOpen={isDocDetailOpen}
        onClose={() => {
          setIsDocDetailOpen(false);
          setSelectedDoc(null);
        }}
      />

      <KnowledgeSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        defaultKnowledgeBaseId={selectedKb ?? undefined}
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
    </div>
  );
};
