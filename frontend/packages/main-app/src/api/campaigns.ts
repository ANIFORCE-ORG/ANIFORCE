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
  platform_account_id?: string
  external_campaign_id?: string
  external_status?: string
  objective?: string
  budget_type?: 'daily' | 'total' | 'lifetime'
  daily_budget?: number
  lifetime_budget?: number
  bid_strategy?: string
  last_synced_at?: string
  last_sync_error?: string
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
  budget_type?: 'daily' | 'total' | 'lifetime'
  budget_remaining?: number
  budget_usage_rate?: number
  elapsed_rate?: number
  pacing_status?: 'fast' | 'slow' | 'normal'
  ctr?: number
  cvr?: number
  last_spend?: number
  last_revenue?: number
  project_budget?: {
    project_total_budget: number
    project_spent: number
    project_remaining_budget: number
    project_allocated_budget: number
    project_unallocated_budget: number
    project_allocation_rate: number
    project_spend_rate: number
  }
  agent_action?: {
    level: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
    label: string
    reason: string
  }
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
 * 添加素材到广告投放
 */
export async function addMaterialToCampaign(
  campaignId: string,
  materialId: string
): Promise<{ message: string }> {
  return http.post(`/campaigns/${campaignId}/materials/${materialId}`)
}

/**
 * 从广告投放移除素材
 */
export async function removeMaterialFromCampaign(
  campaignId: string,
  materialId: string
): Promise<{ message: string }> {
  return http.delete(`/campaigns/${campaignId}/materials/${materialId}`)
}

/**
 * 创建广告投放
 */
export async function createCampaign(data: {
  project_id: string
  name: string
  platform: string
  platform_account_id?: string
  budget: number
  budget_type?: 'daily' | 'total'
  status?: string
  objective?: string
  bidding_strategy?: string
  target_cpa?: number
  start_date?: string
  end_date?: string
  target_regions?: string[]
  age_range?: { min: number; max: number }
  gender?: string
  target_interests?: string[]
  material_ids?: string[]
  auto_optimize_enabled?: boolean
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
