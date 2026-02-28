/**
 * Skills表格 - CRUD操作
 */
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import type { SkillResponse, SkillCreate, SkillUpdate } from '@/services/agentSkillsApi';
import { Plus, Pencil, Trash2, RefreshCw } from 'lucide-react';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { showError, showSuccess, showWarning } from '@/utils/dialogs';

export const SkillsTable: React.FC = () => {
  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(20);
  const [pageInput, setPageInput] = useState('1');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<SkillResponse | null>(null);
  const [tagInput, setTagInput] = useState('');
  const [triggerInput, setTriggerInput] = useState('');
  const [formData, setFormData] = useState<SkillCreate>({
    name: '',
    display_name: '',
    description: '',
    version: '',
    content: '',
    category: 'general',
    tags: [],
    triggers: [],
    author: '',
  });
  const [updateData, setUpdateData] = useState<SkillUpdate>({});

  const normalizeSkills = (data: unknown): { items: SkillResponse[]; total?: number } => {
    if (Array.isArray(data)) {
      return { items: data };
    }
    if (data && typeof data === 'object') {
      const container = data as {
        items?: SkillResponse[];
        data?: SkillResponse[];
        results?: SkillResponse[];
        skills?: SkillResponse[];
        total?: number;
        count?: number;
      };
      const list =
        container.items ?? container.data ?? container.results ?? container.skills ?? [];
      return {
        items: Array.isArray(list) ? list : [],
        total: container.total ?? container.count,
      };
    }
    return { items: [] };
  };

  const loadSkills = async () => {
    setLoading(true);
    try {
      const data = await agentSkillsApi.listSkills({
        limit: pageSize,
        skip: page * pageSize,
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        include_total: true,
      });
      const normalized = normalizeSkills(data);
      setSkills(normalized.items);
      setTotalCount(typeof normalized.total === 'number' ? normalized.total : null);
      if (typeof normalized.total === 'number') {
        setHasMore((page + 1) * pageSize < normalized.total);
      } else {
        setHasMore(normalized.items.length === pageSize);
      }
      setPageInput(String(page + 1));
    } catch (error) {
      console.error('Failed to load skills:', error);
      showError((error as Error).message || '加载 Skills 失败');
      setSkills([]);
      setTotalCount(null);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  };

  const parseListInput = (value: string) => {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.version || !formData.content) {
      showWarning('请填写必填字段：名称、版本、内容', '缺少必填信息');
      return;
    }

    setLoading(true);
    try {
      const payload: SkillCreate = {
        ...formData,
        tags: parseListInput(tagInput),
        triggers: parseListInput(triggerInput),
      };
      await agentSkillsApi.createSkill(payload);
      showSuccess('Skill 创建成功');
      setIsCreateDialogOpen(false);
      setPage(0);
      setFormData({
        name: '',
        display_name: '',
        description: '',
        version: '',
        content: '',
        category: 'general',
        tags: [],
        triggers: [],
        author: '',
      });
      setTagInput('');
      setTriggerInput('');
      loadSkills();
    } catch (error) {
      console.error('Create failed:', error);
      showError((error as Error).message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (skill: SkillResponse) => {
    setSelectedSkill(skill);
    setUpdateData({
      display_name: skill.display_name || '',
      description: skill.description || '',
      version: skill.version,
      content: '',
      category: skill.category || 'general',
      status: skill.status,
      tags: skill.tags ?? [],
      triggers: skill.triggers ?? [],
    });
    setTagInput((skill.tags ?? []).join(', '));
    setTriggerInput((skill.triggers ?? []).join(', '));
    setIsEditDialogOpen(true);
  };

  const handleUpdate = async () => {
    if (!selectedSkill) return;
    setLoading(true);
    try {
      const payload: SkillUpdate = {
        ...updateData,
        tags: parseListInput(tagInput),
        triggers: parseListInput(triggerInput),
      };
      if (!payload.content) {
        delete payload.content;
      }
      await agentSkillsApi.updateSkill(selectedSkill.id, payload);
      showSuccess('Skill 更新成功');
      setIsEditDialogOpen(false);
      setSelectedSkill(null);
      setTagInput('');
      setTriggerInput('');
      setPage(0);
      loadSkills();
    } catch (error) {
      console.error('Update failed:', error);
      showError((error as Error).message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (skill: SkillResponse) => {
    setSelectedSkill(skill);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!selectedSkill) return;
    setLoading(true);
    try {
      await agentSkillsApi.deleteSkill(selectedSkill.id);
      showSuccess('Skill 已删除');
      setSelectedSkill(null);
      setPage(0);
      loadSkills();
    } catch (error) {
      console.error('Delete failed:', error);
      showError((error as Error).message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    try {
      const result = await agentSkillsApi.syncSkillsFromFilesystem();
      showSuccess(`同步完成：${result.synced} 个Skills已同步`);
      setPage(0);
      loadSkills();
    } catch (error) {
      console.error('Sync failed:', error);
      showError((error as Error).message || '同步失败');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = totalCount ? Math.max(1, Math.ceil(totalCount / pageSize)) : null;

  useEffect(() => {
    loadSkills();
  }, [searchQuery, statusFilter, categoryFilter, page, pageSize]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Skills 列表 ({totalCount ?? skills.length})</h2>
        <div className="flex gap-2">
          <Button onClick={handleSync} variant="outline" disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            从文件系统同步
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            新建 Skill
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
              <th className="p-3 text-left font-medium">版本</th>
              <th className="p-3 text-left font-medium">类别</th>
              <th className="p-3 text-left font-medium">来源</th>
              <th className="p-3 text-left font-medium">状态</th>
              <th className="p-3 text-left font-medium">激活次数</th>
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
            ) : skills.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-muted-foreground">
                  暂无数据
                </td>
              </tr>
            ) : (
              skills.map((skill) => (
                <tr key={skill.id} className="border-b hover:bg-muted/50">
                  <td className="p-3 font-medium">{skill.display_name || skill.name}</td>
                  <td className="p-3 text-sm">{skill.version}</td>
                  <td className="p-3">
                    <Badge variant="outline">{skill.category || 'N/A'}</Badge>
                  </td>
                  <td className="p-3">
                    <Badge variant="secondary">{skill.source_type}</Badge>
                  </td>
                  <td className="p-3">
                    <Badge variant={skill.status === 'active' ? 'default' : 'secondary'}>
                      {skill.status}
                    </Badge>
                  </td>
                  <td className="p-3 text-sm">{skill.activation_count}</td>
                  <td className="p-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => handleEdit(skill)}>
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(skill)}>
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
            第 {page + 1} 页 · 当前 {skills.length} 条
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
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>创建 Skill</DialogTitle>
            <DialogDescription>创建新的 Skill 并提交到系统</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="skill_name">名称 *</Label>
              <Input
                id="skill_name"
                placeholder="例如：paper-analysis"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_display_name">显示名称</Label>
              <Input
                id="skill_display_name"
                placeholder="例如：论文分析技能"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_version">版本 *</Label>
              <Input
                id="skill_version"
                placeholder="例如：1.0.0"
                value={formData.version}
                onChange={(e) => setFormData({ ...formData, version: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_category">类别</Label>
              <Input
                id="skill_category"
                placeholder="例如：academic"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_tags">标签（逗号分隔）</Label>
              <Input
                id="skill_tags"
                placeholder="例如：analysis, summary"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_triggers">触发词（逗号分隔）</Label>
              <Input
                id="skill_triggers"
                placeholder="例如：分析论文, summary"
                value={triggerInput}
                onChange={(e) => setTriggerInput(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_description">描述</Label>
              <Textarea
                id="skill_description"
                placeholder="描述该 Skill 的用途"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_content">内容 *</Label>
              <Textarea
                id="skill_content"
                placeholder="Skill 的核心内容或指令"
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={6}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill_author">作者</Label>
              <Input
                id="skill_author"
                placeholder="例如：System"
                value={formData.author}
                onChange={(e) => setFormData({ ...formData, author: e.target.value })}
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
            <DialogTitle>编辑 Skill</DialogTitle>
            <DialogDescription>修改 {selectedSkill?.display_name || selectedSkill?.name} 的配置</DialogDescription>
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
              <Label htmlFor="edit_version">版本</Label>
              <Input
                id="edit_version"
                value={updateData.version ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, version: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_category">类别</Label>
              <Input
                id="edit_category"
                value={updateData.category ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, category: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_tags">标签（逗号分隔）</Label>
              <Input
                id="edit_tags"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_triggers">触发词（逗号分隔）</Label>
              <Input
                id="edit_triggers"
                value={triggerInput}
                onChange={(e) => setTriggerInput(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_description">描述</Label>
              <Textarea
                id="edit_description"
                value={updateData.description ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_content">内容（留空则不更新）</Label>
              <Textarea
                id="edit_content"
                value={updateData.content ?? ''}
                onChange={(e) => setUpdateData({ ...updateData, content: e.target.value })}
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
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        title="删除 Skill"
        description={`确定要删除 "${selectedSkill?.display_name || selectedSkill?.name}" 吗？此操作无法撤销。`}
        confirmText="删除"
        variant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  );
};
