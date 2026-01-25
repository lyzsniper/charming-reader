/**
 * 模型选择器组件
 * 用于在对话中选择模型
 */
import React, { useState, useEffect } from 'react';
import { Brain, X, Check, Loader2, ChevronDown, Search, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api, type ModelConfiguration } from '@/services/api';

interface ModelSelectorProps {
  selectedId: string | null;
  onSelectionChange: (id: string | null) => void;
  className?: string;
  variant?: 'default' | 'light';
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedId,
  onSelectionChange,
  className,
  variant = 'default',
}) => {
  const [models, setModels] = useState<ModelConfiguration[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentModelInfo, setCurrentModelInfo] = useState<{ model_name: string; source: string } | null>(null);

  useEffect(() => {
    const loadModels = async () => {
      try {
        setIsLoading(true);
        const [modelList, modelInfo] = await Promise.all([
          api.listModelConfigurations(),
          api.getCurrentModelInfo().catch(() => null),
        ]);
        setModels(modelList);
        if (modelInfo) {
          setCurrentModelInfo(modelInfo);
          // 如果没有选中模型，且没有激活的模型，使用默认模型
          if (!selectedId && modelInfo.source === 'default') {
            // 默认模型不需要设置selectedId，后端会自动使用
          }
        }
      } catch (error) {
        console.error('Failed to load models', error);
      } finally {
        setIsLoading(false);
      }
    };
    void loadModels();
  }, []);

  const selectedModel = models.find(m => m.id === selectedId);
  const activeModel = models.find(m => m.is_active);
  
  // 当前显示的模型名称
  const displayModelName = selectedModel?.name || activeModel?.name || currentModelInfo?.model_name || '默认模型';

  const filteredModels = models.filter(m =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.model_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isLight = variant === 'light';

  return (
    <div className={cn('relative', className)}>
      <motion.button
        type="button"
        aria-label="选择模型"
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
          <Brain className="w-4 h-4" />
          <span className="text-sm font-medium truncate max-w-[150px]">
            {displayModelName}
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
              aria-label="模型列表"
              className="absolute top-full left-0 mt-2 w-full bg-white border border-gray-200 rounded-xl shadow-2xl z-20 max-h-80 overflow-hidden flex flex-col"
            >
              {models.length > 5 && (
                <div className="p-2 border-b border-gray-100">
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="搜索模型..."
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
              ) : filteredModels.length === 0 ? (
                <div className="p-6 text-sm text-gray-400 text-center">
                  {searchQuery ? '未找到匹配的模型' : '暂无模型，将使用默认模型'}
                </div>
              ) : (
                <>
                  <div className="p-2 border-b border-gray-100 bg-gray-50/50">
                    <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider px-2">
                      选择对话模型
                    </div>
                  </div>
                  <div className="p-1 overflow-y-auto max-h-64">
                    {/* 默认模型选项 */}
                    <motion.button
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      whileHover={{ scale: 1.02, x: 4 }}
                      whileTap={{ scale: 0.98 }}
                      type="button"
                      role="option"
                      aria-selected={!selectedId}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onSelectionChange(null);
                        setIsOpen(false);
                      }}
                      className={cn(
                        'w-full flex items-center gap-2.5 p-2.5 rounded-lg text-sm transition-all mb-1',
                        !selectedId
                          ? 'bg-gradient-to-r from-blue-50 to-blue-100/50 text-blue-900 border border-blue-200 shadow-sm'
                          : 'hover:bg-gray-50 text-gray-700'
                      )}
                    >
                      <motion.div
                        animate={!selectedId ? { scale: [1, 1.2, 1] } : {}}
                        transition={{ duration: 0.3 }}
                        className={cn(
                          'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all',
                          !selectedId ? 'bg-blue-600 border-blue-600 shadow-sm' : 'border-gray-300'
                        )}
                      >
                        {!selectedId && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 200 }}
                          >
                            <Check className="w-3 h-3 text-white" />
                          </motion.div>
                        )}
                      </motion.div>
                      <Sparkles className={cn('w-4 h-4 flex-shrink-0', !selectedId ? 'text-blue-600' : 'text-gray-400')} />
                      <div className="flex-1 text-left">
                        <div className="font-medium">默认模型</div>
                        <div className="text-xs text-gray-500">{currentModelInfo?.model_name || '系统默认'}</div>
                      </div>
                    </motion.button>
                    {/* 模型列表 */}
                    {filteredModels.map((model, index) => {
                      const isSelected = selectedId === model.id;
                      const isActive = model.is_active;
                      return (
                        <motion.button
                          key={model.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.03 }}
                          whileHover={{ scale: 1.02, x: 4 }}
                          whileTap={{ scale: 0.98 }}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onSelectionChange(model.id);
                            setIsOpen(false);
                          }}
                          className={cn(
                            'w-full flex items-center gap-2.5 p-2.5 rounded-lg text-sm transition-all',
                            isSelected || isActive
                              ? 'bg-gradient-to-r from-blue-50 to-blue-100/50 text-blue-900 border border-blue-200 shadow-sm'
                              : 'hover:bg-gray-50 text-gray-700'
                          )}
                        >
                          <motion.div
                            animate={isSelected ? { scale: [1, 1.2, 1] } : {}}
                            transition={{ duration: 0.3 }}
                            className={cn(
                              'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all',
                              isSelected || isActive ? 'bg-blue-600 border-blue-600 shadow-sm' : 'border-gray-300'
                            )}
                          >
                            {(isSelected || isActive) && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200 }}
                              >
                                <Check className="w-3 h-3 text-white" />
                              </motion.div>
                            )}
                          </motion.div>
                          <Brain className={cn('w-4 h-4 flex-shrink-0', isSelected || isActive ? 'text-blue-600' : 'text-gray-400')} />
                          <div className="flex-1 text-left min-w-0">
                            <div className="font-medium truncate">{model.name}</div>
                            <div className="text-xs text-gray-500 truncate">{model.model_name}</div>
                          </div>
                          {isActive && (
                            <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">激活</span>
                          )}
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
    </div>
  );
};
