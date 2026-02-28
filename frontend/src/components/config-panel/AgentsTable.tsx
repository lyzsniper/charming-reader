/**
 * Agents表格 - 完整CRUD功能
 */
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import type { AgentConfigResponse, AgentConfigCreate, AgentConfigUpdate, AgentConfigDetail } from '@/services/agentSkillsApi';
import { Plus, Pencil, Trash2, Star, Info } from 'lucide-react';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { showError, showSuccess, showWarning } from '@/utils/dialogs';

export const AgentsTable: React.FC = () => {
  const [agents, setAgents] = useState<AgentConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(20);
  const [pageInput, setPageInput] = useState('1');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfigResponse | null>(null);
  const [detailData, setDetailData] = useState<AgentConfigDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [formData, setFormData] = useState<AgentConfigCreate>({
    name: '',
    display_name: '',
    instruction: '',
  });
  const [updateData, setUpdateData] = useState<AgentConfigUpdate>({});

  const normalizeAgents = (
    data: unknown
  ): { items: AgentConfigResponse[]; total?: number } => {
    if (Array.isArray(data)) {
      return { items: data };
    }
    if (data && typeof data === 'object') {
      const container = data as { items?: AgentConfigResponse[]; total?: number; count?: number };
      return {
        items: Array.isArray(container.items) ? container.items : [],
        total: container.total ?? container.count,
      };
    }
    return { items: [] };
  };

  const loadAgents = async () => {
    setLoading(true);
    try {
      const data = await agentSkillsApi.listAgentConfigs({
        limit: pageSize,
        skip: page * pageSize,
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        include_total: true,
      });
      const normalized = normalizeAgents(data);
      setAgents(normalized.items);
      setTotalCount(typeof normalized.total === 'number' ? normalized.total : null);
      if (typeof normalized.total === 'number') {
        setHasMore((page + 1) * pageSize < normalized.total);
      } else {
        setHasMore(normalized.items.length === pageSize);
      }
      setPageInput(String(page + 1));
    } catch (error) {
      console.error('Failed to load agents:', error);
      showError((error as Error).message || '加载 Agent 配置失败');
      setAgents([]);
      setTotalCount(null);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.instruction) {
      showWarning('请填写必填字段：名称和指令', '缺少必填信息');
      return;
    }

    setLoading(true);
    try {
      await agentSkillsApi.createAgentConfig(formData);
      showSuccess('Agent 配置创建成功');
      setIsCreateDialogOpen(false);
      setPage(0);
      setFormData({ name: '', display_name: '', instruction: '' });
      loadAgents();
    } catch (error) {
      console.error('Create failed:', error);
      showError((error as Error).message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (agent: AgentConfigResponse) => {
    setSelectedAgent(agent);
    setUpdateData({
      display_name: agent.display_name || '',
      instruction: agent.instruction,
      status: agent.status,
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdate = async () => {
    if (!selectedAgent) return;

    setLoading(true);
    try {
      await agentSkillsApi.updateAgentConfig(selectedAgent.id, updateData);
      showSuccess('Agent 配置更新成功');
      setIsEditDialogOpen(false);
      setSelectedAgent(null);
      setPage(0);
      loadAgents();
    } catch (error) {
      console.error('Update failed:', error);
      showError((error as Error).message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (agent: AgentConfigResponse) => {
    setSelectedAgent(agent);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!selectedAgent) return;
    setLoading(true);
    try {
      await agentSkillsApi.deleteAgentConfig(selectedAgent.id);
      showSuccess('Agent 配置已删除');
      setSelectedAgent(null);
      setPage(0);
      loadAgents();
    } catch (error) {
      console.error('Delete failed:', error);
      showError((error as Error).message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDetail = async (agent: AgentConfigResponse) => {
    setSelectedAgent(agent);
    setDetailData(null);
    setDetailLoading(true);
    setIsDetailDialogOpen(true);
    try {
      const detail = await agentSkillsApi.getAgentConfig(agent.id);
      setDetailData(detail);
    } catch (error) {
      console.error('Load detail failed:', error);
      showError((error as Error).message || '加载详情失败');
      setDetailData(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const totalPages = totalCount ? Math.max(1, Math.ceil(totalCount / pageSize)) : null;
  const pageItems = () => {
    if (!totalPages) return [];
    const current = page + 1;
    const windowSize = 2;
    const start = Math.max(1, current - windowSize);
    const end = Math.min(totalPages, current + windowSize);
    const items: Array<number | 'ellipsis'> = [];
    if (start > 1) {
      items.push(1);
      if (start > 2) items.push('ellipsis');
    }
    for (let i = start; i <= end; i += 1) {
      items.push(i);
    }
    if (end < totalPages) {
      if (end < totalPages - 1) items.push('ellipsis');
      items.push(totalPages);
    }
    return items;
  };

  useEffect(() => {
    loadAgents();
  }, [searchQuery, statusFilter, page, pageSize]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Agent 配置列表 ({totalCount ?? agents.length})</h2>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          新建 Agent
        </Button>
      </div>
      <div className="flex flex-wrap gap-3 mb-4">
        <Input
          placeholder="搜索名称或显示名称..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
            setPageInput('1');
          }}
          className="max-w-xs"
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(0);
            setPageInput('1');
          }}
          className="p-2 border rounded"
        >
          <option value="">全部状态</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="draft">Draft</option>
        </select>
        <select
          value={pageSize}
          onChange={(e) => {
            setPageSize(Number(e.target.value));
            setPage(0);
            setPageInput('1');
          }}
          className="p-2 border rounded"
        >
          <option value={10}>每页 10 条</option>
          <option value={20}>每页 20 条</option>
          <option value={50}>每页 50 条</option>
        </select>
      </div>

      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">名称</th>
              <th className="p-3 text-left font-medium">显示名称</th>
              <th className="p-3 text-left font-medium">指令</th>
              <th className="p-3 text-left font-medium">状态</th>
              <th className="p-3 text-left font-medium">默认</th>
              <th className="p-3 text-left font-medium">创建时间</th>
              <th className="p-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-muted-foreground">
                  加载中...
                </td>
              </tr>
            ) : agents.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-muted-foreground">
                  暂无Agent配置，点击"新建Agent"开始创建
                </td>
              </tr>
            ) : (
              agents.map((agent) => (
                <tr key={agent.id} className="border-b hover:bg-muted/50">
                  <td className="p-3 font-medium">{agent.name}</td>
                  <td className="p-3">{agent.display_name || '-'}</td>
                  <td className="p-3 text-sm max-w-xs truncate">{agent.instruction}</td>
                  <td className="p-3">
                    <Badge variant={agent.status === 'active' ? 'default' : 'secondary'}>
                      {agent.status}
                    </Badge>
                  </td>
                  <td className="p-3">
                    {agent.is_default && <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />}
                  </td>
                  <td className="p-3 text-sm">
                    {new Date(agent.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => handleDetail(agent)}>
                        <Info className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleEdit(agent)}>
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(agent)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between mt-6">
        <Button
          variant="outline"
          disabled={page === 0 || loading}
          onClick={() => setPage((prev) => Math.max(0, prev - 1))}
        >
          上一页
        </Button>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            第 {page + 1} 页 · 当前 {agents.length} 条
            {totalCount !== null ? ` · 共 ${totalCount} 条` : ''}
          </span>
          <Input
            type="number"
            min={1}
            max={totalPages ?? undefined}
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value)}
            className="w-20"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const nextPage = Math.max(1, Number(pageInput || 1));
              const capped = totalPages ? Math.min(nextPage, totalPages) : nextPage;
              setPage(capped - 1);
            }}
          >
            跳转
          </Button>
        </div>
        <Button
          variant="outline"
          disabled={!hasMore || loading}
          onClick={() => setPage((prev) => prev + 1)}
        >
          下一页
        </Button>
      </div>
      {totalPages && totalPages > 1 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {pageItems().map((item, index) =>
            item === 'ellipsis' ? (
              <span key={`ellipsis-${index}`} className="px-2 text-sm text-muted-foreground">
                ...
              </span>
            ) : (
              <Button
                key={item}
                variant={item === page + 1 ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPage(item - 1)}
              >
                {item}
              </Button>
            )
          )}
        </div>
      )}

      {/* 创建对话框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>创建 Agent 配置</DialogTitle>
            <DialogDescription>
              配置一个新的 Agent，包括名称、指令等信息
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">名称 *</Label>
              <Input
                id="name"
                placeholder="例如：paper-analysis-agent"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="display_name">显示名称</Label>
              <Input
                id="display_name"
                placeholder="例如：论文分析助手"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="instruction">系统指令 *</Label>
              <Textarea
                id="instruction"
                placeholder="例如：You are a helpful assistant specialized in academic paper analysis..."
                value={formData.instruction}
                onChange={(e) => setFormData({ ...formData, instruction: e.target.value })}
                rows={6}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={loading}>
              {loading ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑 Agent 配置</DialogTitle>
            <DialogDescription>
              修改 {selectedAgent?.display_name || selectedAgent?.name} 的配置
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit_display_name">显示名称</Label>
              <Input
                id="edit_display_name"
                value={updateData.display_name ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, display_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_instruction">系统指令</Label>
              <Textarea
                id="edit_instruction"
                value={updateData.instruction ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, instruction: e.target.value })}
                rows={6}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_status">状态</Label>
              <select
                id="edit_status"
                value={updateData.status ?? 'active'}
                onChange={(e) => setUpdateData({ ...updateData, status: e.target.value })}
                className="w-full p-2 border rounded"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleUpdate} disabled={loading}>
              {loading ? '更新中...' : '更新'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">
              {detailData?.display_name || selectedAgent?.display_name || selectedAgent?.name}
            </DialogTitle>
            <DialogDescription>{detailData?.name || selectedAgent?.name}</DialogDescription>
          </DialogHeader>
          {detailLoading ? (
            <div className="py-8 text-center text-muted-foreground">加载中...</div>
          ) : detailData ? (
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">系统指令</h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {detailData.instruction}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold mb-2">状态</h4>
                  <Badge variant={detailData.status === 'active' ? 'default' : 'secondary'}>
                    {detailData.status}
                  </Badge>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">默认</h4>
                  <Badge variant={detailData.is_default ? 'default' : 'secondary'}>
                    {detailData.is_default ? '是' : '否'}
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold mb-2">Skills</h4>
                  {detailData.skills.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无</p>
                  ) : (
                    <div className="space-y-2">
                      {detailData.skills.map((skill) => (
                        <div key={skill.id} className="rounded-md border p-2">
                          <div className="font-medium text-sm">
                            {skill.display_name || skill.name}
                          </div>
                          <div className="flex flex-wrap gap-2 mt-2">
                            <Badge variant="outline">优先级 {skill.priority}</Badge>
                            <Badge variant={skill.auto_activate ? 'default' : 'secondary'}>
                              {skill.auto_activate ? '自动激活' : '手动激活'}
                            </Badge>
                            <Badge variant={skill.is_required ? 'default' : 'secondary'}>
                              {skill.is_required ? '必需' : '可选'}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Tools</h4>
                  {detailData.tools.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无</p>
                  ) : (
                    <div className="space-y-2">
                      {detailData.tools.map((tool) => (
                        <div key={tool.id} className="rounded-md border p-2">
                          <div className="font-medium text-sm">
                            {tool.display_name || tool.name}
                          </div>
                          <div className="flex flex-wrap gap-2 mt-2">
                            <Badge variant="outline">{tool.tool_type}</Badge>
                            <Badge variant={tool.is_required ? 'default' : 'secondary'}>
                              {tool.is_required ? '必需' : '可选'}
                            </Badge>
                          </div>
                          {tool.configuration && (
                            <pre className="mt-2 text-xs bg-muted/50 p-2 rounded whitespace-pre-wrap">
                              {JSON.stringify(tool.configuration, null, 2)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  创建于 {new Date(detailData.created_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  更新于 {new Date(detailData.updated_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-muted-foreground">ID: {detailData.id}</div>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground">暂无详情</div>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="删除 Agent 配置"
        description={`确定要删除 "${selectedAgent?.display_name || selectedAgent?.name}" 吗？此操作无法撤销。`}
        confirmText="删除"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  );
};
