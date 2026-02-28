/**
 * 配置面板 - 管理Skills、Agents和Tools
 */
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { SkillsTable } from './SkillsTable';
import { AgentsTable } from './AgentsTable';
import { ToolsTable } from './ToolsTable';
import { Button } from '@/components/ui/button';
import { agentSkillsApi } from '@/services/agentSkillsApi';
import { showError, showSuccess } from '@/utils/dialogs';

export const ConfigPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState('skills');
  const [seeding, setSeeding] = useState(false);

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      const result = await agentSkillsApi.seedDemoData();
      showSuccess(
        `已插入：Skills ${result.created.skills.length} / Tools ${result.created.tools.length} / Agents ${result.created.agents.length}`
      );
    } catch (error) {
      showError((error as Error).message || '插入示例数据失败');
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-h-[calc(100vh-4rem)] overflow-y-auto">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">配置中心</h1>
          <p className="text-muted-foreground">
            管理 Skills、Agent 配置和 Tools
          </p>
        </div>
        <Button variant="outline" onClick={handleSeedDemo} disabled={seeding}>
          {seeding ? '插入中...' : '插入示例数据'}
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>

        <TabsContent value="skills" className="mt-6">
          <SkillsTable />
        </TabsContent>

        <TabsContent value="agents" className="mt-6">
          <AgentsTable />
        </TabsContent>

        <TabsContent value="tools" className="mt-6">
          <ToolsTable />
        </TabsContent>
      </Tabs>
    </div>
  );
};
