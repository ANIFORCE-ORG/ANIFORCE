export interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
  timestamp: number
}

export interface UserInfo {
  id: string
  email: string
  name: string
}

export interface GameInfo {
  name: string
  type: string
  target_market: string[]
  target_audience: string
}

export interface Trend {
  id: string
  name: string
  growth: number
  description: string
}

export interface Recommendation {
  id: string
  direction: string
  ctr_estimate: number
  tags: string[]
  description: string
}

export interface Material {
  id: string
  type: 'a_segment' | 'b_segment' | 'c_segment' | 'full_video'
  url: string
  thumbnail_url?: string
  duration?: number
  ctr: number
  tags: string[]
}

export interface CampaignConfig {
  budget: number
  platforms: Array<{
    name: string
    budget: number
    strategy: string
  }>
  duration: number
  target_roi: number
}
