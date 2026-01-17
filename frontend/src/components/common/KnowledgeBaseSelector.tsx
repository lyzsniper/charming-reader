/**
 * 知识库选择器组件
 * 用于在对话中选择知识库进行 RAG 检索
 */
import React, { useState, useEffect } from 'react';
import { Database, X, Check, Loader2, ChevronDown, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { KnowledgeBaseResponse } from '@/services/api';

interface KnowledgeBaseSelectorProps {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  className?: string;
  variant?: 'default' | 'light'; // light 用于首页，与快速操作按钮样式一致
}

export const KnowledgeBaseSelector: React.FC<KnowledgeBaseSelectorProps> = ({
  selectedIds,
  onSelectionChange,
  className,
  variant = 'default',
}) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const loadKnowledgeBases = async () => {
      try {
        setIsLoading(true);
        const data = await api.listKnowledgeBases();
        setKnowledgeBases(data);
      } catch (error) {
        console.error('Failed to load knowledge bases', error);
      } finally {
        setIsLoading(false);
      }
    };
    void loadKnowledgeBases();
  }, []);

  const toggleKnowledgeBase = (kbId: string) => {
    if (selectedIds.includes(kbId)) {
      onSelectionChange(selectedIds.filter(id => id !== kbId));
    } else {
      onSelectionChange([...selectedIds, kbId]);
    }
  };

  const selectedBases = knowledgeBases.filter(kb => selectedIds.includes(kb.id));
  
  const filteredBases = knowledgeBases.filter(kb =>
    kb.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isLight = variant === 'light';

  return (
    <div className={cn('relative', className)}>
      <motion.button
        type="button"
        aria-label="选择知识库"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-all shadow-md hover:shadow-lg',
          isLight
            ? 'bg-white/70 hover:bg-white/90 backdrop-blur-sm border border-gray-200/50 text-gray-700 hover:text-black'
            : 'w-full justify-between border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 rounded-md px-3 text-xs'
        )}
      >
        <div className={cn('flex items-center gap-2', isLight ? '' : 'flex-1')}>
          <Database className="w-4 h-4" />
          <span className="text-sm font-medium">
            {selectedIds.length > 0
              ? `已选择 ${selectedIds.length} 个知识库`
              : '选择知识库'}
          </span>
        </div>
        {!isLight && (
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4" />
          </motion.div>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              role="listbox"
              aria-label="知识库列表"
              className="absolute top-full left-0 mt-2 w-full bg-white border border-gray-200 rounded-xl shadow-2xl z-20 max-h-80 overflow-hidden flex flex-col"
            >
              {knowledgeBases.length > 5 && (
                <div className="p-2 border-b border-gray-100">
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="搜索知识库..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                </div>
              )}
              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                </div>
              ) : filteredBases.length === 0 ? (
                <div className="p-6 text-sm text-gray-400 text-center">
                  {searchQuery ? '未找到匹配的知识库' : '暂无知识库'}
                </div>
              ) : (
                <>
                  <div className="p-2 border-b border-gray-100 bg-gray-50/50">
                    <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-2">
                      选择知识库进行 RAG 检索
                    </div>
                  </div>
                  <div className="p-1 overflow-y-auto max-h-64">
                    {filteredBases.map((kb, index) => {
                      const isSelected = selectedIds.includes(kb.id);
                      return (
                        <motion.button
                          key={kb.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.03 }}
                          whileHover={{ scale: 1.02, x: 4 }}
                          whileTap={{ scale: 0.98 }}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          aria-label={`${kb.name}知识库${isSelected ? '已选择' : '未选择'}`}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            toggleKnowledgeBase(kb.id);
                          }}
                          className={cn(
                            'w-full flex items-center gap-2.5 p-2.5 rounded-lg text-sm transition-all',
                            isSelected
                              ? 'bg-gradient-to-r from-blue-50 to-blue-100/50 text-blue-900 border border-blue-200 shadow-sm'
                              : 'hover:bg-gray-50 text-gray-700'
                          )}
                        >
                          <motion.div
                            animate={isSelected ? { scale: [1, 1.2, 1] } : {}}
                            transition={{ duration: 0.3 }}
                            className={cn(
                              'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all',
                              isSelected ? 'bg-blue-600 border-blue-600 shadow-sm' : 'border-gray-300'
                            )}
                          >
                            {isSelected && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200 }}
                              >
                                <Check className="w-3 h-3 text-white" />
                              </motion.div>
                            )}
                          </motion.div>
                          <Database className={cn('w-4 h-4 flex-shrink-0', isSelected ? 'text-blue-600' : 'text-gray-400')} />
                          <span className="flex-1 text-left truncate font-medium">{kb.name}</span>
                        </motion.button>
                      );
                    })}
                  </div>
                </>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* 显示已选择的知识库标签 */}
      <AnimatePresence>
        {selectedBases.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className={cn('flex flex-wrap gap-1.5', isLight ? 'mt-2' : 'mt-2')}
          >
            {selectedBases.map((kb, index) => (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ delay: index * 0.05 }}
                className={cn(
                  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium shadow-sm',
                  isLight
                    ? 'bg-white/80 text-gray-700 border border-gray-200/50 backdrop-blur-sm'
                    : 'bg-gradient-to-r from-blue-100 to-blue-50 text-blue-700 border border-blue-200'
                )}
              >
                <span className="truncate max-w-[120px]">{kb.name}</span>
                <motion.button
                  type="button"
                  whileHover={{ scale: 1.2, rotate: 90 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleKnowledgeBase(kb.id);
                  }}
                  className={cn(
                    'rounded-full p-0.5 transition-colors flex-shrink-0',
                    isLight ? 'hover:bg-gray-200' : 'hover:bg-blue-200'
                  )}
                >
                  <X className="w-3 h-3" />
                </motion.button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
