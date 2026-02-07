import type { ApiResponse, Trend, Recommendation, Material, CampaignConfig } from '../types'

export interface IChatClient {
  analyzeGame(gameDescription: string, gameType: string): Promise<ApiResponse<{
    session_id: string
    message: { role: string; content: string }
    analysis: {
      trends: Trend[]
      recommendations: Recommendation[]
    }
  }>>
  sendMessage(sessionId: string, content: string): Promise<ApiResponse<{
    message: { role: string; content: string }
  }>>
  getHistory(sessionId: string): Promise<ApiResponse<{
    messages: Array<{ role: string; content: string; timestamp: number }>
  }>>
}

export interface IMaterialClient {
  generateMaterials(sessionId: string, direction: string): Promise<ApiResponse<{
    task_id: string
    materials: Material[]
  }>>
  getMaterials(taskId: string): Promise<ApiResponse<{
    materials: Material[]
    status: string
  }>>
}

export interface ICampaignClient {
  createPlan(config: CampaignConfig): Promise<ApiResponse<{
    campaign_id: string
    plan: {
      platforms: Array<{ name: string; budget: number; strategy: string }>
      estimated_roi: number
    }
  }>>
  getCampaign(campaignId: string): Promise<ApiResponse<{
    id: string
    status: string
    config: CampaignConfig
  }>>
}

export interface IMonitorClient {
  getMetrics(campaignId: string): Promise<ApiResponse<{
    impressions: number
    clicks: number
    conversions: number
    spend: number
    revenue: number
    ctr: number
    cvr: number
    roi: number
  }>>
}

export interface IAuthClient {
  login(email: string, password: string): Promise<ApiResponse<{
    user: { id: string; email: string; name: string }
    access_token: string
    refresh_token: string
  }>>
  register(email: string, password: string, name: string): Promise<ApiResponse<{
    user: { id: string; email: string; name: string }
    access_token: string
    refresh_token: string
  }>>
}
