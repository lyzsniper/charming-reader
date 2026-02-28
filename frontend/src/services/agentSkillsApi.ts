/**
 * Agent Skills Center API types and methods
 */

// ===== Type Definitions =====

export interface SkillResponse {
  id: string;
  name: string;
  display_name?: string | null;
  description?: string | null;
  version: string;
  source_type: string;
  category?: string | null;
  tags?: string[] | null;
  triggers?: string[] | null;
  status: string;
  author?: string | null;
  activation_count: number;
  download_count: number;
  rating?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  display_name?: string;
  description?: string;
  version: string;
  content: string;
  category?: string;
  tags?: string[];
  triggers?: string[];
  author?: string;
}

export interface SkillUpdate {
  display_name?: string;
  description?: string;
  version?: string;
  content?: string;
  category?: string;
  tags?: string[];
  triggers?: string[];
  status?: string;
}

export interface AgentConfigResponse {
  id: string;
  name: string;
  display_name?: string | null;
  instruction: string;
  status: string;
  is_default: boolean;
  user_id?: string | null;
  template_id?: string | null;
  model_config_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentConfigDetail {
  id: string;
  name: string;
  display_name?: string | null;
  instruction: string;
  status: string;
  is_default: boolean;
  template_id?: string | null;
  model_config_id?: string | null;
  skills: Array<{
    id: string;
    name: string;
    display_name?: string | null;
    description?: string | null;
    priority: number;
    auto_activate: boolean;
    is_required: boolean;
  }>;
  tools: Array<{
    id: string;
    name: string;
    display_name?: string | null;
    description?: string | null;
    tool_type: string;
    is_required: boolean;
    configuration?: Record<string, unknown>;
  }>;
  agent_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentConfigCreate {
  name: string;
  display_name?: string;
  template_id?: string;
  instruction: string;
  model_config_id?: string;
  skill_ids?: string[];
  tool_ids?: string[];
  user_id?: string;
  agent_metadata?: Record<string, unknown>;
}

export interface AgentConfigUpdate {
  display_name?: string;
  instruction?: string;
  model_config_id?: string;
  status?: string;
  agent_metadata?: Record<string, unknown>;
}

export interface ToolResponse {
  id: string;
  name: string;
  display_name?: string | null;
  description?: string | null;
  tool_type: string;
  category?: string | null;
  source_config?: Record<string, unknown> | null;
  schema_config?: Record<string, unknown> | null;
  status: string;
  usage_count: number;
  tool_metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ToolCreate {
  name: string;
  display_name?: string;
  description?: string;
  tool_type: 'mcp' | 'python' | 'api';
  category?: string;
  source_config?: Record<string, unknown>;
  schema_config?: Record<string, unknown>;
}

export interface ToolUpdate {
  display_name?: string;
  description?: string;
  category?: string;
  source_config?: Record<string, unknown>;
  schema_config?: Record<string, unknown>;
  status?: string;
}

export interface ActiveSkill {
  log_id: string;
  skill_id: string;
  skill_name?: string | null;
  skill_display_name?: string | null;
  session_id: string;
  activated_at: string;
  activation_reason?: string | null;
  query_text?: string | null;
}

export interface AgentStats {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
  avg_execution_time_ms: number;
  avg_token_count: number;
  time_range_days: number;
}

export interface SkillActivationLog {
  id: string;
  skill_id: string;
  session_id: string;
  activated_at: string;
  deactivated_at?: string | null;
  activation_reason?: string | null;
  query_text?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

// ===== API Base URL =====
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:18000';
const API_PREFIX = '/api';

// ===== Helper Functions =====
type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions extends RequestInit {
  query?: Query;
}

const buildUrl = (path: string, query?: Query) => {
  const url = new URL(`${API_PREFIX}${path}`, API_BASE_URL);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }
  return url.toString();
};

const request = async <T>(path: string, options: RequestOptions = {}): Promise<T> => {
  const { query, headers, ...rest } = options;
  const url = buildUrl(path, query);

  try {
    const requestHeaders: HeadersInit = {
      'Content-Type': 'application/json',
      ...headers,
    };

    const response = await fetch(url, {
      ...rest,
      headers: requestHeaders,
    });

    const text = await response.text();
    let data: unknown = null;
    
    try {
      data = text ? JSON.parse(text) : null;
    } catch (parseError) {
      throw new Error(text || response.statusText);
    }

    if (!response.ok) {
      const message = 
        (data && typeof data === 'object' && 'detail' in data ? data.detail : null) ||
        (data && typeof data === 'object' && 'message' in data ? data.message : null) ||
        response.statusText ||
        'Request failed';
      throw new Error(typeof message === 'string' ? message : 'Request failed');
    }

    return data as T;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network connection failed');
    }
    throw error;
  }
};

// ===== Skills API =====

export const listSkills = (params?: {
  category?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
  include_total?: boolean;
}) => {
  return request<SkillResponse[] | PaginatedResponse<SkillResponse>>('/skills', {
    method: 'GET',
    query: params,
  });
};

export const getSkill = (skillId: string) => {
  return request<SkillResponse>(`/skills/${skillId}`, {
    method: 'GET',
  });
};

export const getPopularSkills = (limit: number = 10) => {
  return request<SkillResponse[]>('/skills/popular', {
    method: 'GET',
    query: { limit },
  });
};

export const createSkill = (skill: SkillCreate) => {
  return request<SkillResponse>('/skills', {
    method: 'POST',
    body: JSON.stringify(skill),
  });
};

export const updateSkill = (skillId: string, updates: SkillUpdate) => {
  return request<SkillResponse>(`/skills/${skillId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
};

export const deleteSkill = (skillId: string) => {
  return request<void>(`/skills/${skillId}`, {
    method: 'DELETE',
  });
};

export const syncSkillsFromFilesystem = () => {
  return request<{ synced: number; skipped: number; errors: number; message: string }>('/skills/sync', {
    method: 'POST',
  });
};

// ===== Agent Config API =====

export const listAgentConfigs = (params?: {
  user_id?: string;
  search?: string;
  status?: string;
  skip?: number;
  limit?: number;
  include_total?: boolean;
}) => {
  return request<AgentConfigResponse[] | PaginatedResponse<AgentConfigResponse>>('/agent-configs', {
    method: 'GET',
    query: params,
  });
};

export const getAgentConfig = (agentId: string) => {
  return request<AgentConfigDetail>(`/agent-configs/${agentId}`, {
    method: 'GET',
  });
};

export const createAgentConfig = (config: AgentConfigCreate) => {
  return request<AgentConfigResponse>('/agent-configs', {
    method: 'POST',
    body: JSON.stringify(config),
  });
};

export const updateAgentConfig = (agentId: string, updates: AgentConfigUpdate) => {
  return request<AgentConfigResponse>(`/agent-configs/${agentId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
};

export const deleteAgentConfig = (agentId: string) => {
  return request<void>(`/agent-configs/${agentId}`, {
    method: 'DELETE',
  });
};

export const assignSkillsToAgent = (agentId: string, skillIds: string[], replace: boolean = false) => {
  return request<{ success: boolean }>(`/agent-configs/${agentId}/skills`, {
    method: 'POST',
    body: JSON.stringify(skillIds),
    query: { replace },
  });
};

export const removeSkillFromAgent = (agentId: string, skillId: string) => {
  return request<void>(`/agent-configs/${agentId}/skills/${skillId}`, {
    method: 'DELETE',
  });
};

export const assignToolsToAgent = (agentId: string, toolIds: string[], replace: boolean = false) => {
  return request<{ success: boolean }>(`/agent-configs/${agentId}/tools`, {
    method: 'POST',
    body: JSON.stringify(toolIds),
    query: { replace },
  });
};

// ===== Tools API =====

export const listTools = (params?: {
  tool_type?: string;
  category?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
  include_total?: boolean;
}) => {
  return request<ToolResponse[] | PaginatedResponse<ToolResponse>>('/tools', {
    method: 'GET',
    query: params,
  });
};

export const getTool = (toolId: string) => {
  return request<ToolResponse>(`/tools/${toolId}`, {
    method: 'GET',
  });
};

export const createTool = (tool: ToolCreate) => {
  return request<ToolResponse>('/tools', {
    method: 'POST',
    body: JSON.stringify(tool),
  });
};

export const updateTool = (toolId: string, updates: ToolUpdate) => {
  return request<ToolResponse>(`/tools/${toolId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
};

export const deleteTool = (toolId: string) => {
  return request<void>(`/tools/${toolId}`, {
    method: 'DELETE',
  });
};

export const discoverMcpTools = () => {
  return request<{ discovered: number; skipped: number; errors: number; message: string }>('/tools/discover', {
    method: 'POST',
  });
};

export const seedDemoData = () => {
  return request<{
    created: { skills: string[]; tools: string[]; agents: string[] };
    skipped: { skills: string[]; tools: string[]; agents: string[] };
  }>('/dev/seed-demo', {
    method: 'POST',
  });
};

// ===== Runtime Monitor API =====

export const getActiveSkills = (sessionId?: string) => {
  return request<ActiveSkill[]>('/runtime/skills/active', {
    method: 'GET',
    query: sessionId ? { session_id: sessionId } : undefined,
  });
};

export const getAgentStats = (agentId: string, days: number = 7) => {
  return request<AgentStats>(`/runtime/agents/${agentId}/stats`, {
    method: 'GET',
    query: { days },
  });
};

export const getSkillActivationLogs = (skillId: string, limit: number = 50) => {
  return request<SkillActivationLog[]>(`/runtime/skills/${skillId}/logs`, {
    method: 'GET',
    query: { limit },
  });
};

// ===== Export all API methods =====
export const agentSkillsApi = {
  // Skills
  listSkills,
  getSkill,
  getPopularSkills,
  createSkill,
  updateSkill,
  deleteSkill,
  syncSkillsFromFilesystem,
  // Agent Configs
  listAgentConfigs,
  getAgentConfig,
  createAgentConfig,
  updateAgentConfig,
  deleteAgentConfig,
  assignSkillsToAgent,
  removeSkillFromAgent,
  assignToolsToAgent,
  // Tools
  listTools,
  getTool,
  createTool,
  updateTool,
  deleteTool,
  discoverMcpTools,
  seedDemoData,
  // Runtime
  getActiveSkills,
  getAgentStats,
  getSkillActivationLogs,
};
