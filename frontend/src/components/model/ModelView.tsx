/**
 * 模型管理页面
 * 用于添加、编辑和管理模型配置
 */
import React, { useState, useEffect } from 'react';
import { Brain, Plus, Trash2, Loader2, X, Save, Check, Edit2, Sparkles, Settings as SettingsIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { api, type ModelConfiguration, type ModelConfigurationCreate, type ModelConfigurationUpdate } from '@/services/api';
import { showSuccess, showError, showWarning } from '@/utils/dialogs';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { EmptyState } from '@/components/common/EmptyState';

interface ModelViewProps {
  onClose: () => void;
}

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI (兼容)' },
  { value: 'qwen', label: '通义千问' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'glm', label: '智谱AI (GLM)' },
];

export const ModelView: React.FC<ModelViewProps> = ({ onClose }) => {
  const [models, setModels] = useState<ModelConfiguration[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<string | null>(null);
  
  // 表单状态
  const [formData, setFormData] = useState<Partial<ModelConfigurationCreate>>({
    name: '',
    model_name: '',
    api_key: '',
    base_url: '',
    provider: 'openai',
    description: '',
    temperature: 0.7,
    max_tokens: null,
    top_p: null,
    frequency_penalty: null,
    presence_penalty: null,
  });
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModel) {
      const model = models.find(m => m.id === selectedModel);
      if (model) {
        setFormData({
          name: model.name,
          model_name: model.model_name,
          api_key: model.api_key || '',
          base_url: model.base_url || '',
          provider: model.provider || 'openai',
          description: model.description || '',
          temperature: model.temperature ?? 0.7,
          max_tokens: model.max_tokens ?? null,
          top_p: model.top_p ?? null,
          frequency_penalty: model.frequency_penalty ?? null,
          presence_penalty: model.presence_penalty ?? null,
        });
        setIsEditing(true);
      }
    } else {
      resetForm();
    }
  }, [selectedModel, models]);

  const loadModels = async () => {
    try {
      setIsLoading(true);
      const data = await api.listModelConfigurations();
      setModels(data);
      if (data.length > 0 && !selectedModel) {
        const activeModel = data.find(m => m.is_active);
        setSelectedModel(activeModel?.id || data[0].id);
      }
    } catch (error) {
      console.error('Failed to load models', error);
      showError('加载模型列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      model_name: '',
      api_key: '',
      base_url: '',
      provider: 'openai',
      description: '',
      temperature: 0.7,
      max_tokens: null,
      top_p: null,
      frequency_penalty: null,
      presence_penalty: null,
    });
    setIsEditing(false);
  };

  const handleCreate = () => {
    setSelectedModel(null);
    resetForm();
  };

  const handleSave = async () => {
    if (!formData.name?.trim() || !formData.model_name?.trim()) {
      showWarning('请填写模型名称和模型标识');
      return;
    }

    try {
      setIsSaving(true);
      if (isEditing && selectedModel) {
        // 更新现有模型
        const updateData: ModelConfigurationUpdate = {
          name: formData.name,
          model_name: formData.model_name,
          api_key: formData.api_key || null,
          base_url: formData.base_url || null,
          provider: formData.provider || null,
          description: formData.description || null,
          temperature: formData.temperature ?? null,
          max_tokens: formData.max_tokens ?? null,
          top_p: formData.top_p ?? null,
          frequency_penalty: formData.frequency_penalty ?? null,
          presence_penalty: formData.presence_penalty ?? null,
        };
        await api.updateModelConfiguration(selectedModel, updateData);
        showSuccess('模型更新成功');
      } else {
        // 创建新模型
        const createData: ModelConfigurationCreate = {
          name: formData.name!,
          model_name: formData.model_name!,
          api_key: formData.api_key || null,
          base_url: formData.base_url || null,
          provider: formData.provider || null,
          description: formData.description || null,
          is_active: false,
          temperature: formData.temperature ?? null,
          max_tokens: formData.max_tokens ?? null,
          top_p: formData.top_p ?? null,
          frequency_penalty: formData.frequency_penalty ?? null,
          presence_penalty: formData.presence_penalty ?? null,
        };
        await api.createModelConfiguration(createData);
        showSuccess('模型创建成功');
      }
      await loadModels();
      if (!isEditing) {
        resetForm();
      }
    } catch (error) {
      console.error('Failed to save model', error);
      showError(error instanceof Error ? error.message : '保存模型失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleActivate = async (modelId: string) => {
    try {
      await api.activateModelConfiguration(modelId);
      showSuccess('模型激活成功');
      await loadModels();
      setSelectedModel(modelId);
    } catch (error) {
      console.error('Failed to activate model', error);
      showError('激活模型失败');
    }
  };

  const handleDelete = (modelId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setModelToDelete(modelId);
    setConfirmDeleteOpen(true);
  };

  const confirmDelete = async () => {
    if (!modelToDelete) return;
    try {
      await api.deleteModelConfiguration(modelToDelete);
      if (selectedModel === modelToDelete) {
        setSelectedModel(null);
        resetForm();
      }
      await loadModels();
      showSuccess('模型删除成功');
    } catch (error) {
      console.error('Failed to delete model', error);
      showError(error instanceof Error ? error.message : '删除模型失败');
    } finally {
      setConfirmDeleteOpen(false);
      setModelToDelete(null);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black text-white rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold font-serif">模型管理</h2>
            <p className="text-sm text-gray-500">管理对话模型配置</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Models */}
        <div className="w-80 bg-gray-50 border-r p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">模型列表</div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCreate}
              className="h-7 px-2 text-xs"
            >
              <Plus className="w-3 h-3 mr-1" />
              新建
            </Button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          ) : models.length === 0 ? (
            <EmptyState
              icon={Brain}
              title="暂无模型"
              description="创建第一个模型配置开始使用"
              size="sm"
            />
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {models.map((model) => (
                <motion.div
                  key={model.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  whileHover={{ scale: 1.02, x: 4 }}
                  className={cn(
                    "bg-white border rounded-lg p-3 cursor-pointer hover:shadow-lg transition-all group",
                    selectedModel === model.id && "border-blue-500 shadow-lg bg-blue-50/30"
                  )}
                  onClick={() => setSelectedModel(model.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {model.is_active ? (
                          <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                        ) : (
                          <Brain className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        )}
                        <p className="text-sm font-medium truncate">{model.name}</p>
                      </div>
                      <p className="text-xs text-gray-500 truncate mb-1">{model.model_name}</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        {model.provider && (
                          <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-medium">
                            {model.provider}
                          </span>
                        )}
                        {model.is_active && (
                          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium">
                            激活中
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {!model.is_active && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleActivate(model.id);
                          }}
                          title="激活"
                        >
                          <Sparkles className="w-3 h-3 text-blue-500" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50"
                        onClick={(e) => handleDelete(model.id, e)}
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Right Content Area - Form */}
        <div className="flex-1 p-6 overflow-y-auto bg-white">
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">模型名称 *</label>
                <Input
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：Qwen Flash"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">模型标识 *</label>
                <Input
                  value={formData.model_name || ''}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  placeholder="例如：qwen-flash-2025-07-28"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">提供商</label>
                <select
                  value={formData.provider || 'openai'}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {PROVIDER_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">API Key</label>
                <Input
                  type="password"
                  value={formData.api_key || ''}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder="输入API密钥（可选）"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Base URL</label>
                <Input
                  value={formData.base_url || ''}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  placeholder="例如：https://dashscope.aliyuncs.com/compatible-mode/v1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">描述</label>
                <Textarea
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="模型描述（可选）"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Temperature</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={formData.temperature ?? ''}
                    onChange={(e) => setFormData({ ...formData, temperature: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="0.7"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Max Tokens</label>
                  <Input
                    type="number"
                    value={formData.max_tokens ?? ''}
                    onChange={(e) => setFormData({ ...formData, max_tokens: e.target.value ? parseInt(e.target.value) : null })}
                    placeholder="留空为默认"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Top P</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={formData.top_p ?? ''}
                    onChange={(e) => setFormData({ ...formData, top_p: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="留空为默认"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Frequency Penalty</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="-2"
                    max="2"
                    value={formData.frequency_penalty ?? ''}
                    onChange={(e) => setFormData({ ...formData, frequency_penalty: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="留空为默认"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Presence Penalty</label>
                <Input
                  type="number"
                  step="0.1"
                  min="-2"
                  max="2"
                  value={formData.presence_penalty ?? ''}
                  onChange={(e) => setFormData({ ...formData, presence_penalty: e.target.value ? parseFloat(e.target.value) : null })}
                  placeholder="留空为默认"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-4 border-t">
              <Button
                onClick={handleSave}
                disabled={isSaving || !formData.name?.trim() || !formData.model_name?.trim()}
                className="flex-1"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    {isEditing ? '更新模型' : '创建模型'}
                  </>
                )}
              </Button>
              {isEditing && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelectedModel(null);
                    resetForm();
                  }}
                >
                  取消
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmDeleteOpen}
        onClose={() => setConfirmDeleteOpen(false)}
        onConfirm={confirmDelete}
        title="确认删除"
        message="确定要删除这个模型配置吗？此操作不可恢复。"
      />
    </div>
  );
};
