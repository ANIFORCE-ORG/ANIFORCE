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
  connection_id?: string
  account_id?: string
  objective?: string
  buying_type?: string
  special_ad_categories?: string
  special_ad_category_country?: string
  promoted_object?: string
  ab_test?: string
  campaign_budget_optimization?: string
  budget_type?: string
  budget: number
  budget_schedule_specs?: string
  pacing_type?: string
  bid_strategy?: string
  spend_limit?: number
  spent: number
  status: string
  material_ids: string[]
  start_date: string
  end_date?: string
  config?: any
  created_at: string
  updated_at: string
}

export interface CampaignsResponse {
  campaigns: Campaign[]
}

export interface CampaignDetailResponse extends Campaign {}

export interface AdSetPerformance {
  id: string
  name: string
  status: string
  daily_budget: number
  spent: number
  audience?: string
  placements?: string
  optimization_goal?: string
  bid_strategy?: string
  data_available: boolean
  sample_count: number
  latest?: {
    timestamp: string
    impressions: number
    clicks: number
    conversions: number
    installs: number
    spend: number
    revenue: number
    ctr: number
    cvr: number
    cpa: number
    cpi: number
    roi: number
  } | null
}

export interface CampaignPerformance {
  data_available: boolean
  ad_set_breakdown: AdSetPerformance[]
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
 * 获取广告投放表现及其广告单元明细
 */
export async function getCampaignPerformance(
  campaignId: string,
  hours = 168
): Promise<CampaignPerformance> {
  return http.get<CampaignPerformance>(`/campaigns/${campaignId}/performance?hours=${hours}`)
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
  account_id?: string
  objective?: string
  buying_type?: string
  special_ad_categories?: string
  ab_test?: string
  campaign_budget_optimization?: string
  status?: string
  budget_type?: string
  budget: number
  bid_strategy?: string
  spend_limit?: string
  material_ids?: string[]
}): Promise<Campaign> {
  return http.post<Campaign>('/campaigns', data)
}

/**
 * 应用信息接口
 */
export interface Application {
  id: string
  name: string
  namespace?: string
  object_store_urls?: {
    ios_url?: string
    itunes?: string
    android_url?: string
    google_play?: string
    amazon_app_store?: string
    windows_phone_app_store?: string
  }
  supported_platforms?: string[]
  app_type?: string
  link?: string
}

/**
 * 获取 Meta 广告账户的应用列表
 */
export async function getMetaApplications(
  connectionId: string,
  adAccountId: string
): Promise<Application[]> {
  return http.get<Application[]>(
    `/platform-auth/meta/${connectionId}/adaccounts/${adAccountId}/applications`
  )
}

/**
 * Facebook Page 信息接口
 */
export interface FacebookPage {
  id: string
  name: string
  category?: string
  tasks?: string[]
  instagram_business_account?: {
    id: string
  }
  has_advertise_permission: boolean
}

/**
 * 获取用户可管理的 Facebook Pages
 */
export async function getMetaPages(connectionId: string): Promise<FacebookPage[]> {
  return http.get<FacebookPage[]>(`/platform-auth/meta/${connectionId}/pages`)
}

/**
 * Meta 广告图片信息接口
 */
export interface AdImage {
  id: string
  name?: string
  hash: string
  url?: string
  url_128?: string
  height?: number
  width?: number
  status?: string
  created_time?: string
}

/**
 * 获取 Meta 广告账户的图片素材列表
 */
export async function getMetaAdImages(
  connectionId: string,
  adAccountId: string
): Promise<AdImage[]> {
  return http.get<AdImage[]>(
    `/platform-auth/meta/${connectionId}/adaccounts/${adAccountId}/images`
  )
}

/**
 * Meta 广告视频信息接口
 */
export interface AdVideo {
  id: string
  title?: string
  description?: string
  length?: number
  picture?: string
  source?: string
  status?: string
  created_time?: string
}

/**
 * 获取 Meta 广告账户的视频素材列表
 */
export async function getMetaAdVideos(
  connectionId: string,
  adAccountId: string
): Promise<AdVideo[]> {
  return http.get<AdVideo[]>(
    `/platform-auth/meta/${connectionId}/adaccounts/${adAccountId}/videos`
  )
}

/**
 * 更新广告投放
 */
export async function updateCampaign(
  campaignId: string,
  data: {
    name?: string
    platform?: string
    account_id?: string
    objective?: string
    buying_type?: string
    special_ad_categories?: string
    ab_test?: string
    campaign_budget_optimization?: string
    status?: string
    budget_type?: string
    budget?: number
    bid_strategy?: string
    spend_limit?: number
    start_date?: string
    end_date?: string
    material_ids?: string[]
  }
): Promise<Campaign> {
  return http.put<Campaign>(`/campaigns/${campaignId}`, data)
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
