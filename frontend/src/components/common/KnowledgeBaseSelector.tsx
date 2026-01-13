/**
 * 知识库选择器组件
 * 用于在对话中选择知识库进行 RAG 检索
 */
import React, { useState, useEffect } from 'react';
import { Database, X, Check, Loader2, ChevronDown } from 'lucide-react';
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

  const isLight = variant === 'light';

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5',
          isLight
            ? 'bg-white/50 hover:bg-white/80 backdrop-blur-sm border border-black/5 text-gray-600 hover:text-black'
            : 'w-full justify-between border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 rounded-md px-3 text-xs'
        )}
      >
        <div className={cn('flex items-center gap-2', isLight ? '' : 'flex-1')}>
          <Database className="w-4 h-4" />
          <span className="text-sm">
            {selectedIds.length > 0
              ? `已选择 ${selectedIds.length} 个知识库`
              : '选择知识库'}
          </span>
        </div>
        {!isLight && <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-full bg-white border rounded-lg shadow-lg z-20 max-h-64 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              </div>
            ) : knowledgeBases.length === 0 ? (
              <div className="p-4 text-sm text-gray-400 text-center">
                暂无知识库
              </div>
            ) : (
              <>
                <div className="p-2 border-b">
                  <div className="text-xs font-semibold text-gray-500 uppercase">
                    选择知识库进行 RAG 检索
                  </div>
                </div>
                <div className="p-1">
                  {knowledgeBases.map((kb) => {
                    const isSelected = selectedIds.includes(kb.id);
                    return (
                      <button
                        key={kb.id}
                        onClick={() => toggleKnowledgeBase(kb.id)}
                        className={cn(
                          'w-full flex items-center gap-2 p-2 rounded-md text-sm transition-colors',
                          isSelected
                            ? 'bg-blue-50 text-blue-900'
                            : 'hover:bg-gray-50 text-gray-700'
                        )}
                      >
                        <div className={cn(
                          'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0',
                          isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
                        )}>
                          {isSelected && <Check className="w-3 h-3 text-white" />}
                        </div>
                        <Database className="w-4 h-4 flex-shrink-0" />
                        <span className="flex-1 text-left truncate">{kb.name}</span>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* 显示已选择的知识库标签 */}
      {selectedBases.length > 0 && (
        <div className={cn('flex flex-wrap gap-1', isLight ? 'mt-2' : 'mt-2')}>
          {selectedBases.map((kb) => (
            <div
              key={kb.id}
              className={cn(
                'inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs',
                isLight
                  ? 'bg-white/60 text-gray-700 border border-black/5'
                  : 'bg-blue-100 text-blue-700'
              )}
            >
              <span>{kb.name}</span>
              <button
                onClick={() => toggleKnowledgeBase(kb.id)}
                className={cn(
                  'rounded-full p-0.5',
                  isLight ? 'hover:bg-gray-200' : 'hover:bg-blue-200'
                )}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
