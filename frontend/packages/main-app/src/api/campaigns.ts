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

export interface CampaignMaterialBindingInput {
  material_id: string
  title?: string
  description?: string
  copy?: string
  source?: 'manual' | 'upload' | 'ai' | 'copied'
  sort_order?: number
  status?: 'draft' | 'ready' | 'disabled'
}

export interface CampaignMaterialBinding {
  id: string
  campaign_id: string
  material_id: string
  title?: string
  description?: string
  copy?: string
  source?: string
  sort_order: number
  status: string
  created_by?: string
  created_at: string
  updated_at: string
  material?: any
}

export interface BatchCampaignCreateRequest {
  plan_count: number
  name_template: string
  platform: string
  platform_account_id?: string
  objective?: string
  budget_type?: 'daily' | 'total' | 'lifetime'
  budget: number
  target_cpa?: number
  bidding_strategy?: string
  start_date?: string
  end_date?: string
  targeting?: {
    regions: string[]
    age_range: { min: number; max: number }
    gender: string
    interests: string[]
  }
  materials?: CampaignMaterialBindingInput[]
  status?: string
  auto_optimize_enabled?: boolean
}

export interface BatchCampaignCreateResponse {
  campaigns: Campaign[]
  material_bindings: CampaignMaterialBinding[]
  plan_count: number
  skipped: boolean
  message?: string
}

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
export async function getCampaignMaterials(campaignId: string): Promise<CampaignMaterialBinding[]> {
  const response = await http.get<{ materials: CampaignMaterialBinding[] }>(`/campaigns/${campaignId}/materials`)
  return response.materials
}

export async function createCampaignMaterialBinding(
  campaignId: string,
  data: CampaignMaterialBindingInput
): Promise<CampaignMaterialBinding> {
  return http.post<CampaignMaterialBinding>(`/campaigns/${campaignId}/materials`, data)
}

export async function updateCampaignMaterialBinding(
  campaignId: string,
  bindingId: string,
  data: Partial<CampaignMaterialBindingInput>
): Promise<CampaignMaterialBinding> {
  return http.put<CampaignMaterialBinding>(`/campaigns/${campaignId}/materials/${bindingId}`, data)
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

export async function batchCreateProjectCampaigns(
  projectId: string,
  data: BatchCampaignCreateRequest
): Promise<BatchCampaignCreateResponse> {
  return http.post<BatchCampaignCreateResponse>(`/projects/${projectId}/campaigns/batch`, data)
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
