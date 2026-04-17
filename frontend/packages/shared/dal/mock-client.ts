import type { ApiResponse } from '../types'
import type { IChatClient, IMaterialClient, ICampaignClient, IMonitorClient, IAuthClient } from './interfaces'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const MOCK_TRENDS = [
  { id: '1', name: 'Boss挑战', growth: 45, description: 'RPG玩家喜欢高难度Boss战展示' },
  { id: '2', name: '装备展示', growth: 38, description: '稀有装备获取瞬间' },
  { id: '3', name: 'PVP对决', growth: 32, description: '实时PVP高光时刻' },
]

const MOCK_RECOMMENDATIONS = [
  { id: '1', direction: 'Boss战+夸张奖励', ctr_estimate: 3.2, tags: ['Boss挑战', '高奖励', '视觉冲击'], description: '开场3秒Boss战高光时刻' },
  { id: '2', direction: '装备收集+稀有掉落', ctr_estimate: 2.8, tags: ['装备展示', '稀有掉落', '收集欲'], description: '展示稀有装备获取过程' },
]

const MOCK_MATERIALS = [
  { id: '1', type: 'a_segment' as const, url: '', thumbnail_url: '', duration: 5, ctr: 3.2, tags: ['Boss战', '高光'] },
  { id: '2', type: 'b_segment' as const, url: '', thumbnail_url: '', duration: 10, ctr: 2.8, tags: ['装备', '稀有'] },
  { id: '3', type: 'c_segment' as const, url: '', thumbnail_url: '', duration: 5, ctr: 2.5, tags: ['CTA', '下载'] },
]

function ok<T>(data: T): ApiResponse<T> {
  return { success: true, data, message: '操作成功', timestamp: Date.now() }
}

export class MockChatClient implements IChatClient {
  async analyzeGame(gameDescription: string, gameType: string) {
    await delay(2000)
    return ok({
      session_id: 'mock-session-' + Date.now(),
      message: { role: 'ai', content: `已分析「${gameDescription}」，这是一款${gameType}类型的游戏。以下是市场热点和推荐方向：` },
      analysis: { trends: MOCK_TRENDS, recommendations: MOCK_RECOMMENDATIONS },
    })
  }

  async sendMessage(_sessionId: string, content: string) {
    await delay(1000)
    return ok({ message: { role: 'ai', content: `收到您的消息：「${content}」，正在为您处理...` } })
  }

  async getHistory(_sessionId: string) {
    await delay(500)
    return ok({ messages: [{ role: 'ai', content: '欢迎使用ANIMAGUS智能投放平台！', timestamp: Date.now() }] })
  }
}

export class MockMaterialClient implements IMaterialClient {
  async generateMaterials(_sessionId: string, _direction: string) {
    await delay(4000)
    return ok({ task_id: 'mock-task-' + Date.now(), materials: MOCK_MATERIALS })
  }

  async getMaterials(_taskId: string) {
    await delay(500)
    return ok({ materials: MOCK_MATERIALS, status: 'completed' })
  }
}

export class MockCampaignClient implements ICampaignClient {
  async createPlan(config: any) {
    await delay(2000)
    return ok({
      campaign_id: 'mock-campaign-' + Date.now(),
      plan: {
        platforms: [
          { name: 'Meta Ads', budget: config.budget * 0.6, strategy: 'Nobid + AEO' },
          { name: 'Google Ads', budget: config.budget * 0.4, strategy: 'tCPA' },
        ],
        estimated_roi: 2.5,
      },
    })
  }

  async getCampaign(campaignId: string) {
    await delay(500)
    return ok({
      id: campaignId,
      status: 'active',
      config: { budget: 10000, platforms: [], duration: 7, target_roi: 2.0 },
    })
  }
}

export class MockMonitorClient implements IMonitorClient {
  async getMetrics(_campaignId: string) {
    await delay(500)
    return ok({
      impressions: 125000, clicks: 3750, conversions: 450,
      spend: 4500, revenue: 11250, ctr: 3.0, cvr: 12.0, roi: 2.5,
    })
  }
}

export class MockAuthClient implements IAuthClient {
  async login(email: string, _password: string) {
    await delay(500)
    return ok({
      user: { id: 'demo-user-001', email, name: 'Demo User' },
      access_token: 'mock-token-' + Date.now(),
      refresh_token: 'mock-refresh-' + Date.now(),
    })
  }

  async register(email: string, _password: string, name: string) {
    await delay(500)
    return ok({
      user: { id: 'demo-user-001', email, name },
      access_token: 'mock-token-' + Date.now(),
      refresh_token: 'mock-refresh-' + Date.now(),
    })
  }
}
