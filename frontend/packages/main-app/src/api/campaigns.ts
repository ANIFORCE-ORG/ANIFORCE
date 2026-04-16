/**
 * 广告投放 API
 */
import { http } from './http'

export interface Campaign {
  id: string
  project_id: string
  project_name: string
  name: string
  description?: string
  platform: string
  budget: number
  spent: number
  status: string
  material_ids: string[]
  start_date: string
  end_date?: string
  config?: any
  created_at: string
  updated_at: string
  // 新增字段
  installs?: number
  cpi?: number
  roi?: number
  target_cpa?: number
  pipeline_step?: string
  learning_phase?: string
  auto_optimize_enabled?: boolean
  optimization_rules?: any
}

export interface CampaignsResponse {
  campaigns: Campaign[]
}

export interface CampaignDetailResponse extends Campaign {}

/**
 * 获取广告投放列表
 */
export async function getCampaigns(params?: {
  project_id?: string
  status?: string
  limit?: number
}): Promise<Campaign[]> {
  const queryParams = new URLSearchParams()
  if (params?.project_id) queryParams.append('project_id', params.project_id)
  if (params?.status) queryParams.append('status', params.status)
  if (params?.limit) queryParams.append('limit', params.limit.toString())

  const query = queryParams.toString()
  const endpoint = `/campaigns${query ? `?${query}` : ''}`

  const response = await http.get<CampaignsResponse>(endpoint)
  return response.campaigns
}

/**
 * 获取广告投放详情
 */
export async function getCampaignDetail(campaignId: string): Promise<Campaign> {
  return http.get<Campaign>(`/campaigns/${campaignId}`)
}

/**
 * 获取广告投放关联的素材
 */
export async function getCampaignMaterials(campaignId: string): Promise<any[]> {
  const response = await http.get<{ materials: any[] }>(`/campaigns/${campaignId}/materials`)
  return response.materials
}

/**
 * 创建广告投放
 */
export async function createCampaign(data: {
  project_id: string
  name: string
  platform: string
  budget: number
  status?: string
  material_ids?: string[]
}): Promise<Campaign> {
  return http.post<Campaign>('/campaigns', data)
}

/**
 * 更新广告投放状态
 */
export async function updateCampaignStatus(
  campaignId: string,
  status: string
): Promise<{ message: string }> {
  return http.put(`/campaigns/${campaignId}/status`, { status })
}

/**
 * 删除广告投放
 */
export async function deleteCampaign(campaignId: string): Promise<void> {
  return http.delete<void>(`/campaigns/${campaignId}`)
}
