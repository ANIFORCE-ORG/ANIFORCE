import type { ApiResponse, Material, CampaignConfig, Trend, Recommendation } from '../types'
import type { IChatClient, IMaterialClient, ICampaignClient, IMonitorClient, IAuthClient } from './interfaces'

class HttpBase {
  protected baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  protected async request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> || {}),
    }

    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(error.error?.message || error.message || '请求失败')
    }
    return response.json()
  }

  protected post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: 'POST', body: JSON.stringify(body) })
  }

  protected get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: 'GET' })
  }
}

export class HttpChatClient extends HttpBase implements IChatClient {
  analyzeGame(gameDescription: string, gameType: string) {
    return this.post<{ session_id: string; message: { role: string; content: string }; analysis: { trends: Trend[]; recommendations: Recommendation[] } }>('/chat/analyze', { game_description: gameDescription, game_type: gameType })
  }

  sendMessage(sessionId: string, content: string) {
    return this.post<{ message: { role: string; content: string } }>(`/chat/${sessionId}/message`, { content })
  }

  getHistory(sessionId: string) {
    return this.get<{ messages: Array<{ role: string; content: string; timestamp: number }> }>(`/chat/${sessionId}/history`)
  }
}

export class HttpMaterialClient extends HttpBase implements IMaterialClient {
  generateMaterials(sessionId: string, direction: string) {
    return this.post<{ task_id: string; materials: Material[] }>('/materials/generate', { session_id: sessionId, direction })
  }

  getMaterials(taskId: string) {
    return this.get<{ materials: Material[]; status: string }>(`/materials/${taskId}`)
  }
}

export class HttpCampaignClient extends HttpBase implements ICampaignClient {
  createPlan(config: CampaignConfig) {
    return this.post<{ campaign_id: string; plan: { platforms: Array<{ name: string; budget: number; strategy: string }>; estimated_roi: number } }>('/campaigns', config)
  }

  getCampaign(campaignId: string) {
    return this.get<{ id: string; status: string; config: CampaignConfig }>(`/campaigns/${campaignId}`)
  }
}

export class HttpMonitorClient extends HttpBase implements IMonitorClient {
  getMetrics(campaignId: string) {
    return this.get<{ impressions: number; clicks: number; conversions: number; spend: number; revenue: number; ctr: number; cvr: number; roi: number }>(`/monitor/${campaignId}/metrics`)
  }
}

export class HttpAuthClient extends HttpBase implements IAuthClient {
  login(email: string, password: string) {
    return this.post<{ user: { id: string; email: string; name: string }; access_token: string; refresh_token: string }>('/auth/login', { email, password })
  }

  register(email: string, password: string, name: string) {
    return this.post<{ user: { id: string; email: string; name: string }; access_token: string; refresh_token: string }>('/auth/register', { email, password, name })
  }
}
