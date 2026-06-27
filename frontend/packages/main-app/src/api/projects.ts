/**
 * 项目管理 API
 */

import { http } from './http'

export interface Project {
  id: string
  name: string
  product?: string
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
  product?: string
  target_market?: string
  status?: string
  start_date?: string
  end_date?: string
  total_budget?: number
  manager?: string
  game_type?: string
  tags?: string[]
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
    product?: string
    target_market?: string
    status?: string
    start_date?: string
    end_date?: string
    total_budget?: number
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
