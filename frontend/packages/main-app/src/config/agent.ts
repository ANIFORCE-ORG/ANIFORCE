/**
 * Agent API 配置
 * 用于配置AD Agent后端服务的API地址
 */

export type ChatMode = 'stream' | 'normal'

export interface AgentConfig {
  baseUrl: string
  chatMode: ChatMode
  endpoints: {
    health: string
    chat: string
    chatStream: string
    websocket: string
    sessions: string
    sessionDetail: (sessionId: string) => string
  }
}

// 从环境变量读取,如果没有则使用默认值
const AGENT_BASE_URL = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8000'
const AGENT_CHAT_MODE = (import.meta.env.VITE_AGENT_CHAT_MODE || 'stream') as ChatMode

export const agentConfig: AgentConfig = {
  baseUrl: AGENT_BASE_URL,
  chatMode: AGENT_CHAT_MODE,
  endpoints: {
    health: '/health',
    chat: '/chat',
    chatStream: '/chat/stream',
    websocket: '/ws/chat',
    sessions: '/sessions',
    sessionDetail: (sessionId: string) => `/sessions/${sessionId}`
  }
}

// 获取完整的API URL
export function getAgentApiUrl(endpoint: string): string {
  return `${agentConfig.baseUrl}${endpoint}`
}

// 获取WebSocket URL
export function getAgentWsUrl(sessionId: string): string {
  const wsProtocol = agentConfig.baseUrl.startsWith('https') ? 'wss' : 'ws'
  const baseUrl = agentConfig.baseUrl.replace(/^https?:\/\//, '')
  return `${wsProtocol}://${baseUrl}${agentConfig.endpoints.websocket}/${sessionId}`
}
