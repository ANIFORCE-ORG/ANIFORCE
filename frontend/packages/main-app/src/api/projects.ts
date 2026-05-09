/**
 * 项目管理 API
 */

import { http } from './http'
import type { PlatformAccount } from './platformAccounts'

export interface Project {
  id: string
  name: string
  description?: string
  game_type: string
  target_market: string
  tags: string[]
  total_budget: number
  spent: number
  status: string
  manager: string
  start_date: string
  end_date: string
  created_at: string
  updated_at: string
  product_type?: string
  region?: string | string[]
  target_roi?: number
  current_roi?: number
  installs?: number
  campaign_count?: number
}

export interface ProjectPlatformAccount {
  id: string
  project_id: string
  platform_account_id: string
  role: string
  status: string
  spend_cap?: number
  daily_cap?: number
  note?: string
  account?: PlatformAccount
}

export interface AgentAction {
  id: string
  project_id: string
  platform_account_id?: string
  campaign_id?: string
  action_type: string
  risk_level: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  status: string
  title: string
  summary?: string
  evidence: Record<string, any>
  payload: Record<string, any>
  expected_impact: Record<string, any>
  created_at: string
}

interface ProjectsResponse {
  projects: Project[]
}

/**
 * 获取项目列表
 */
export async function getProjects(params?: {
  status?: string
  limit?: number
}): Promise<Project[]> {
  const queryParams = new URLSearchParams()
  if (params?.status) queryParams.append('status', params.status)
  if (params?.limit) queryParams.append('limit', params.limit.toString())

  const query = queryParams.toString()
  const endpoint = `/projects${query ? `?${query}` : ''}`

  const response = await http.get<ProjectsResponse>(endpoint)
  return response.projects
}

/**
 * 获取项目详情
 */
export async function getProjectDetail(projectId: string): Promise<Project> {
  return http.get<Project>(`/projects/${projectId}`)
}

/**
 * 创建项目
 */
export async function createProject(data: {
  name: string
  game_type: string
  target_market: string
  total_budget: number
  tags?: string[]
  manager?: string
}): Promise<Project> {
  return http.post<Project>('/projects', data)
}

/**
 * 更新项目
 */
export async function updateProject(
  projectId: string,
  data: {
    name?: string
    total_budget?: number
    status?: string
    product_type?: string
    region?: string[]
    target_roi?: number
  }
): Promise<Project> {
  return http.put<Project>(`/projects/${projectId}`, data)
}

/**
 * 删除项目
 */
export async function deleteProject(projectId: string): Promise<void> {
  return http.delete<void>(`/projects/${projectId}`)
}

/**
 * 获取项目关联的广告投放
 */
export async function getProjectCampaigns(projectId: string): Promise<any[]> {
  const response = await http.get<{ campaigns: any[] }>(`/campaigns?project_id=${projectId}`)
  return response.campaigns
}

export async function getProjectPlatformAccounts(projectId: string): Promise<ProjectPlatformAccount[]> {
  return http.get<ProjectPlatformAccount[]>(`/projects/${projectId}/platform-accounts`)
}

export async function bindProjectPlatformAccount(
  projectId: string,
  data: {
    platform_account_id: string
    role?: string
    spend_cap?: number
    daily_cap?: number
    note?: string
  }
): Promise<ProjectPlatformAccount> {
  return http.post<ProjectPlatformAccount>(`/projects/${projectId}/platform-accounts`, data)
}

export async function unbindProjectPlatformAccount(
  projectId: string,
  platformAccountId: string
): Promise<{ message: string }> {
  return http.delete(`/projects/${projectId}/platform-accounts/${platformAccountId}`)
}

export async function getProjectAgentActions(projectId: string): Promise<AgentAction[]> {
  return http.get<AgentAction[]>(`/projects/${projectId}/agent-actions`)
}

export async function generateProjectAgentActions(projectId: string): Promise<{ actions: AgentAction[] }> {
  return http.post<{ actions: AgentAction[] }>(`/projects/${projectId}/agent-actions/generate`)
}

export async function confirmProjectAgentAction(projectId: string, actionId: string): Promise<AgentAction> {
  return http.post<AgentAction>(`/projects/${projectId}/agent-actions/${actionId}/confirm`)
}

export async function rejectProjectAgentAction(projectId: string, actionId: string): Promise<AgentAction> {
  return http.post<AgentAction>(`/projects/${projectId}/agent-actions/${actionId}/reject`)
}
