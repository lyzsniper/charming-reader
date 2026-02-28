/**
 * Tools表格 - 完整CRUD功能
 */
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import type { ToolResponse, ToolCreate, ToolUpdate } from '@/services/agentSkillsApi';
import { Plus, Search, Wrench, Info, Pencil, Trash2 } from 'lucide-react';
import { showError, showSuccess, showWarning } from '@/utils/dialogs';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';

export const ToolsTable: React.FC = () => {
  const [tools, setTools] = useState<ToolResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<ToolResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(20);
  const [pageInput, setPageInput] = useState('1');
  const [formData, setFormData] = useState<ToolCreate>({
    name: '',
    display_name: '',
    description: '',
    tool_type: 'mcp',
  });
  const [updateData, setUpdateData] = useState<ToolUpdate>({});

  const normalizeTools = (data: unknown): { items: ToolResponse[]; total?: number } => {
    if (Array.isArray(data)) {
      return { items: data };
    }
    if (data && typeof data === 'object') {
      const container = data as { items?: ToolResponse[]; total?: number; count?: number };
      return {
        items: Array.isArray(container.items) ? container.items : [],
        total: container.total ?? container.count,
      };
    }
    return { items: [] };
  };

  const loadTools = async () => {
    setLoading(true);
    try {
      const data = await agentSkillsApi.listTools({
        limit: pageSize,
        skip: page * pageSize,
        tool_type: typeFilter || undefined,
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        search: searchQuery || undefined,
        include_total: true,
      });
      const normalized = normalizeTools(data);
      setTools(normalized.items);
      setTotalCount(typeof normalized.total === 'number' ? normalized.total : null);
      if (typeof normalized.total === 'number') {
        setHasMore((page + 1) * pageSize < normalized.total);
      } else {
        setHasMore(normalized.items.length === pageSize);
      }
      setPageInput(String(page + 1));
    } catch (error) {
      console.error('Failed to load tools:', error);
      showError((error as Error).message || '加载 Tools 失败');
      setTools([]);
      setTotalCount(null);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  const handleDiscover = async () => {
    setLoading(true);
    try {
      const result = await agentSkillsApi.discoverMcpTools();
      showSuccess(`发现 MCP 工具：${result.discovered} 个已注册`);
      loadTools();
    } catch (error) {
      console.error('Discover failed:', error);
      showError((error as Error).message || '发现工具失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.tool_type) {
      showWarning('请填写必填字段：名称和类型', '缺少必填信息');
      return;
    }

    setLoading(true);
    try {
      await agentSkillsApi.createTool(formData);
      showSuccess('Tool 创建成功');
      setIsCreateDialogOpen(false);
      setPage(0);
      setFormData({
        name: '',
        display_name: '',
        description: '',
        tool_type: 'mcp',
      });
      loadTools();
    } catch (error) {
      console.error('Create failed:', error);
      showError((error as Error).message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (tool: ToolResponse) => {
    setSelectedTool(tool);
    setUpdateData({
      display_name: tool.display_name ?? '',
      description: tool.description ?? '',
      category: tool.category ?? '',
      status: tool.status,
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdate = async () => {
    if (!selectedTool) return;
    setLoading(true);
    try {
      await agentSkillsApi.updateTool(selectedTool.id, updateData);
      showSuccess('Tool 更新成功');
      setIsEditDialogOpen(false);
      setSelectedTool(null);
      loadTools();
    } catch (error) {
      console.error('Update failed:', error);
      showError((error as Error).message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (tool: ToolResponse) => {
    setSelectedTool(tool);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!selectedTool) return;
    setLoading(true);
    try {
      await agentSkillsApi.deleteTool(selectedTool.id);
      showSuccess('Tool 已删除');
      setSelectedTool(null);
      loadTools();
    } catch (error) {
      console.error('Delete failed:', error);
      showError((error as Error).message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDetail = (tool: ToolResponse) => {
    setSelectedTool(tool);
    setIsDetailDialogOpen(true);
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
    loadTools();
  }, [searchQuery, typeFilter, statusFilter, categoryFilter, page, pageSize]);

  const getToolTypeColor = (type: string) => {
    switch (type) {
      case 'mcp':
        return 'default';
      case 'python':
        return 'secondary';
      case 'api':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Tools 列表 ({totalCount ?? tools.length})</h2>
        <div className="flex gap-2">
          <Button onClick={handleDiscover} variant="outline" disabled={loading}>
            <Search className="h-4 w-4 mr-2" />
            发现MCP工具
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            新建 Tool
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mb-4">
        <Input
          placeholder="搜索名称或描述..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
            setPageInput('1');
          }}
          className="max-w-xs"
        />
        <Input
          placeholder="类别（可选）"
          value={categoryFilter}
          onChange={(e) => {
            setCategoryFilter(e.target.value);
            setPage(0);
            setPageInput('1');
          }}
          className="max-w-xs"
        />
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(0);
            setPageInput('1');
          }}
          className="p-2 border rounded"
        >
          <option value="">全部类型</option>
          <option value="mcp">MCP</option>
          <option value="python">Python</option>
          <option value="api">API</option>
        </select>
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
              <th className="p-3 text-left font-medium">描述</th>
              <th className="p-3 text-left font-medium">类型</th>
              <th className="p-3 text-left font-medium">类别</th>
              <th className="p-3 text-left font-medium">状态</th>
              <th className="p-3 text-left font-medium">使用次数</th>
              <th className="p-3 text-left font-medium">创建时间</th>
              <th className="p-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="p-8 text-center text-muted-foreground">
                  加载中...
                </td>
              </tr>
            ) : tools.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-8 text-center text-muted-foreground">
                  暂无Tools，点击"发现MCP工具"或"新建Tool"开始
                </td>
              </tr>
            ) : (
              tools.map((tool) => (
                <tr key={tool.id} className="border-b hover:bg-muted/50">
                  <td className="p-3 font-medium flex items-center gap-2">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                    {tool.name}
                  </td>
                  <td className="p-3">{tool.display_name || '-'}</td>
                  <td className="p-3 text-sm max-w-xs truncate">
                    {tool.description || '-'}
                  </td>
                  <td className="p-3">
                    <Badge variant={getToolTypeColor(tool.tool_type)}>
                      {tool.tool_type}
                    </Badge>
                  </td>
                  <td className="p-3">
                    <Badge variant="outline">{tool.category || 'general'}</Badge>
                  </td>
                  <td className="p-3">
                    <Badge variant={tool.status === 'active' ? 'default' : 'secondary'}>
                      {tool.status}
                    </Badge>
                  </td>
                  <td className="p-3 text-sm">{tool.usage_count}</td>
                  <td className="p-3 text-sm">
                    {new Date(tool.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => handleDetail(tool)}>
                        <Info className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleEdit(tool)}>
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(tool)}>
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
            第 {page + 1} 页 · 当前 {tools.length} 条
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
            <DialogTitle>创建 Tool</DialogTitle>
            <DialogDescription>
              注册一个新的工具到系统中
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="tool_name">名称 *</Label>
              <Input
                id="tool_name"
                placeholder="例如：search-papers"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool_display_name">显示名称</Label>
              <Input
                id="tool_display_name"
                placeholder="例如：论文搜索工具"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool_type">类型 *</Label>
              <select
                id="tool_type"
                value={formData.tool_type}
                onChange={(e) =>
                  setFormData({ ...formData, tool_type: e.target.value as 'mcp' | 'python' | 'api' })
                }
                className="w-full p-2 border rounded"
              >
                <option value="mcp">MCP (Model Context Protocol)</option>
                <option value="python">Python 函数</option>
                <option value="api">外部 API</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool_description">描述</Label>
              <Textarea
                id="tool_description"
                placeholder="工具的功能描述..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool_category">类别</Label>
              <Input
                id="tool_category"
                placeholder="例如：search, analysis, utils"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
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
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑 Tool</DialogTitle>
            <DialogDescription>修改 {selectedTool?.display_name || selectedTool?.name} 的配置</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit_tool_display_name">显示名称</Label>
              <Input
                id="edit_tool_display_name"
                value={updateData.display_name ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, display_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_tool_description">描述</Label>
              <Textarea
                id="edit_tool_description"
                value={updateData.description ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_tool_category">类别</Label>
              <Input
                id="edit_tool_category"
                value={updateData.category ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, category: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_tool_status">状态</Label>
              <select
                id="edit_tool_status"
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
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">
              {selectedTool?.display_name || selectedTool?.name}
            </DialogTitle>
            <DialogDescription>{selectedTool?.name}</DialogDescription>
          </DialogHeader>
          {selectedTool && (
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">描述</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedTool.description || '暂无描述'}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold mb-2">类型</h4>
                  <Badge variant={getToolTypeColor(selectedTool.tool_type)}>
                    {selectedTool.tool_type}
                  </Badge>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">类别</h4>
                  <Badge variant="outline">{selectedTool.category || 'general'}</Badge>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">状态</h4>
                  <Badge variant={selectedTool.status === 'active' ? 'default' : 'secondary'}>
                    {selectedTool.status}
                  </Badge>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">使用次数</h4>
                  <p className="text-sm text-muted-foreground">{selectedTool.usage_count}</p>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <h4 className="font-semibold mb-2">source_config</h4>
                  <pre className="text-xs bg-muted/50 p-2 rounded whitespace-pre-wrap">
                    {selectedTool.source_config
                      ? JSON.stringify(selectedTool.source_config, null, 2)
                      : '暂无'}
                  </pre>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">schema_config</h4>
                  <pre className="text-xs bg-muted/50 p-2 rounded whitespace-pre-wrap">
                    {selectedTool.schema_config
                      ? JSON.stringify(selectedTool.schema_config, null, 2)
                      : '暂无'}
                  </pre>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">tool_metadata</h4>
                  <pre className="text-xs bg-muted/50 p-2 rounded whitespace-pre-wrap">
                    {selectedTool.tool_metadata
                      ? JSON.stringify(selectedTool.tool_metadata, null, 2)
                      : '暂无'}
                  </pre>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  创建于 {new Date(selectedTool.created_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  更新于 {new Date(selectedTool.updated_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-muted-foreground">ID: {selectedTool.id}</div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="删除 Tool"
        description={`确定要删除 "${selectedTool?.display_name || selectedTool?.name}" 吗？此操作无法撤销。`}
        confirmText="删除"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  );
};
