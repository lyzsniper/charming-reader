/**
 * Skills市场 - 展示、搜索和管理Skills
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import type { SkillResponse } from '@/services/agentSkillsApi';
import { Search, TrendingUp, Tag, Calendar, Download, Activity } from 'lucide-react';
import { showError } from '@/utils/dialogs';

export const SkillsMarket: React.FC = () => {
  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [popularSkills, setPopularSkills] = useState<SkillResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedSkill, setSelectedSkill] = useState<SkillResponse | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(20);
  const [pageInput, setPageInput] = useState('1');

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

  // 加载Skills列表
  const loadSkills = async () => {
    setLoading(true);
    try {
      const data = await agentSkillsApi.listSkills({
        search: searchQuery || undefined,
        category: selectedCategory,
        skip: page * pageSize,
        limit: pageSize,
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

  // 加载热门Skills
  const loadPopularSkills = async () => {
    try {
      const data = await agentSkillsApi.getPopularSkills(5);
      setPopularSkills(normalizeSkills(data).items);
    } catch (error) {
      console.error('Failed to load popular skills:', error);
      showError((error as Error).message || '加载热门 Skills 失败');
      setPopularSkills([]);
    }
  };

  useEffect(() => {
    loadSkills();
  }, [searchQuery, selectedCategory, page, pageSize]);

  useEffect(() => {
    loadPopularSkills();
  }, []);

  const handleSkillClick = (skill: SkillResponse) => {
    setSelectedSkill(skill);
    setDetailDialogOpen(true);
  };

  const categories = ['academic', 'developer', 'business', 'general'];
  const canGoPrev = page > 0;
  const canGoNext = hasMore;
  const totalPages = totalCount ? Math.max(1, Math.ceil(totalCount / pageSize)) : null;

  return (
    <div className="container mx-auto p-6 max-h-[calc(100vh-4rem)] overflow-y-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Skills 市场</h1>
        <p className="text-muted-foreground">
          浏览和发现可用的 Skills，为你的 Agent 添加新能力
        </p>
      </div>

      {/* 搜索和过滤 */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索 Skills..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0);
              setPageInput('1');
            }}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={selectedCategory === undefined ? 'default' : 'outline'}
            onClick={() => {
              setSelectedCategory(undefined);
              setPage(0);
              setPageInput('1');
            }}
          >
            全部
          </Button>
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? 'default' : 'outline'}
              onClick={() => {
                setSelectedCategory(cat);
                setPage(0);
                setPageInput('1');
              }}
            >
              {cat}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
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
      </div>

      {/* 热门Skills */}
      {popularSkills.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5" />
            <h2 className="text-xl font-semibold">热门 Skills</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {popularSkills.map((skill) => (
              <Card
                key={skill.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => handleSkillClick(skill)}
              >
                <CardHeader className="p-4">
                  <CardTitle className="text-sm">{skill.display_name || skill.name}</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Activity className="h-3 w-3" />
                    <span>{skill.activation_count} 次激活</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Skills 列表 */}
      <div>
        <h2 className="text-xl font-semibold mb-4">
          所有 Skills ({totalCount ?? skills.length})
        </h2>
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">加载中...</div>
        ) : skills.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            没有找到 Skills
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {skills.map((skill) => (
              <Card
                key={skill.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => handleSkillClick(skill)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">
                        {skill.display_name || skill.name}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        v{skill.version} • {skill.author || 'System'}
                      </CardDescription>
                    </div>
                    <Badge variant={skill.status === 'active' ? 'default' : 'secondary'}>
                      {skill.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {skill.description || '暂无描述'}
                  </p>
                  {skill.tags && skill.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {skill.tags.slice(0, 3).map((tag: string) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
                <CardFooter className="flex justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    <span>{skill.activation_count}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Download className="h-3 w-3" />
                    <span>{skill.download_count}</span>
                  </div>
                  {skill.category && (
                    <div className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      <span>{skill.category}</span>
                    </div>
                  )}
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between mt-6">
        <Button
          variant="outline"
          disabled={!canGoPrev || loading}
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
          disabled={!canGoNext || loading}
          onClick={() => setPage((prev) => prev + 1)}
        >
          下一页
        </Button>
      </div>

      {/* Skill 详情对话框 */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selectedSkill && (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl">
                  {selectedSkill.display_name || selectedSkill.name}
                </DialogTitle>
                <DialogDescription>
                  v{selectedSkill.version} • {selectedSkill.author || 'System'}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">描述</h4>
                  <p className="text-sm text-muted-foreground">
                    {selectedSkill.description || '暂无描述'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold mb-2">类别</h4>
                    <Badge>{selectedSkill.category || 'general'}</Badge>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">来源</h4>
                    <Badge variant="outline">{selectedSkill.source_type}</Badge>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">状态</h4>
                    <Badge variant={selectedSkill.status === 'active' ? 'default' : 'secondary'}>
                      {selectedSkill.status}
                    </Badge>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">作者</h4>
                    <p className="text-sm text-muted-foreground">
                      {selectedSkill.author || 'System'}
                    </p>
                  </div>
                </div>
                {selectedSkill.triggers && selectedSkill.triggers.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">触发词</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedSkill.triggers.map((trigger: string) => (
                        <Badge key={trigger} variant="secondary">
                          {trigger}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {selectedSkill.tags && selectedSkill.tags.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">标签</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedSkill.tags.map((tag: string) => (
                        <Badge key={tag} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{selectedSkill.activation_count} 次激活</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Download className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{selectedSkill.download_count} 次下载</span>
                  </div>
                  {selectedSkill.rating && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm">评分: {selectedSkill.rating.toFixed(1)}/5.0</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">
                      {new Date(selectedSkill.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">
                      更新于 {new Date(selectedSkill.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">ID: {selectedSkill.id}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
