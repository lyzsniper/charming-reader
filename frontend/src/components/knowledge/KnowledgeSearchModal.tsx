import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Loader2, Database, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import type { KnowledgeBaseResponse, SearchResult } from '@/services/api';
import { cn } from '@/lib/utils';

interface KnowledgeSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultKnowledgeBaseId?: string;
}

export const KnowledgeSearchModal: React.FC<KnowledgeSearchModalProps> = ({
  isOpen,
  onClose,
  defaultKnowledgeBaseId,
}) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseResponse[]>([]);
  const [selectedKb, setSelectedKb] = useState<string | null>(defaultKnowledgeBaseId ?? null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isKbLoading, setIsKbLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      void loadKnowledgeBases();
    }
  }, [isOpen]);

  useEffect(() => {
    if (defaultKnowledgeBaseId) {
      setSelectedKb(defaultKnowledgeBaseId);
    }
  }, [defaultKnowledgeBaseId]);

  const loadKnowledgeBases = async () => {
    try {
      setIsKbLoading(true);
      const data = await api.listKnowledgeBases();
      setKnowledgeBases(data);
      if (!selectedKb && data.length > 0) {
        setSelectedKb(data[0].id);
      }
    } catch (error) {
      console.error('加载知识库失败', error);
    } finally {
      setIsKbLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    try {
      setIsLoading(true);
      const res = await api.ragSearch({
        query,
        knowledge_base_ids: selectedKb ? [selectedKb] : undefined,
        top_k: 10,
      });
      setResults(Array.isArray(res) ? res : []);
    } catch (error) {
      console.error('搜索失败', error);
      setResults([]);
    } finally {
      setIsLoading(false);
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
            initial={{ opacity: 0, scale: 0.97, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 10 }}
            onClick={(e) => e.stopPropagation()}
            className="fixed inset-0 md:inset-6 bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-2">
                <Search className="w-5 h-5 text-gray-600" />
                <div>
                  <h2 className="text-lg font-semibold">文档块搜索</h2>
                  <p className="text-xs text-gray-500">独立搜索，不影响知识库列表视图</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="p-4 border-b flex items-center gap-3">
              <div className="flex items-center gap-2 bg-gray-50 border rounded-lg px-3 py-2 min-w-[200px]">
                <Database className="w-4 h-4 text-gray-500" />
                {isKbLoading ? (
                  <span className="text-sm text-gray-400">加载中...</span>
                ) : (
                  <select
                    className="bg-transparent text-sm outline-none"
                    value={selectedKb ?? ''}
                    onChange={(e) => setSelectedKb(e.target.value || null)}
                  >
                    <option value="">全部知识库</option>
                    {knowledgeBases.map((kb) => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="flex-1 flex items-center gap-2">
                <div className="flex-1 flex items-center gap-2 bg-gray-50 border rounded-lg px-3 py-2">
                  <Search className="w-4 h-4 text-gray-500" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="flex-1 text-sm outline-none bg-transparent"
                    placeholder="输入关键词搜索文档块..."
                  />
                </div>
                <Button onClick={handleSearch} disabled={!query.trim() || isLoading}>
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '搜索'}
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-3 bg-gray-50">
              {isLoading ? (
                <div className="flex items-center justify-center h-full text-gray-400">搜索中...</div>
              ) : results.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
                  <Search className="w-10 h-10" />
                  <p className="text-sm">暂无搜索结果</p>
                </div>
              ) : (
                results.map((result, idx) => (
                  <div key={idx} className="bg-white border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="bg-blue-100 text-blue-700 text-[10px] font-mono px-1.5 py-0.5 rounded">
                          #{idx + 1}
                        </span>
                        {typeof result.score === 'number' && (
                          <span className="text-xs text-gray-500">相似度: {(result.score * 100).toFixed(1)}%</span>
                        )}
                      </div>
                      {result.metadata?.document_id && (
                        <span className="text-xs text-gray-400">
                          文档: {String(result.metadata.document_id).slice(0, 8)}...
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed font-serif whitespace-pre-wrap">
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
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
