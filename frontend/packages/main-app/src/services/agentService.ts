/**
 * AD Agent 服务封装
 * 提供与AD Agent后端的交互接口
 */

import axios from 'axios'
import { getAgentApiUrl } from '@/config/agent'

export interface Message {
  role: 'system' | 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  session_id: string
  message: string
}

export interface ChatResponse {
  session_id: string
  message: string
  timestamp: string
}

export interface SessionInfo {
  session_id: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface SessionDetail {
  session_id: string
  messages: Message[]
  message_count: number
  created_at: string
  updated_at: string
}

export class AgentService {
  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await axios.get(getAgentApiUrl('/health'))
    return response.data
  }

  /**
   * 非流式对话
   */
  async chat(sessionId: string, message: string): Promise<ChatResponse> {
    const response = await axios.post<ChatResponse>(
      getAgentApiUrl('/chat'),
      {
        session_id: sessionId,
        message: message
      }
    )
    return response.data
  }

  /**
   * 流式对话
   * 使用异步生成器逐步返回内容片段
   */
  async *chatStream(sessionId: string, message: string): AsyncGenerator<string, void, unknown> {
    const response = await fetch(getAgentApiUrl('/chat/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: message
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Response body is not readable')
    }

    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6)
            if (content === '[DONE]') {
              return
            }
            if (content.trim()) {
              yield content
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  /**
   * 获取会话列表
   */
  async getSessions(): Promise<{ sessions: SessionInfo[]; count: number }> {
    const response = await axios.get(getAgentApiUrl('/sessions'))
    return response.data
  }

  /**
   * 获取会话详情
   */
  async getSessionDetail(sessionId: string): Promise<SessionDetail> {
    const response = await axios.get(getAgentApiUrl(`/sessions/${sessionId}`))
    return response.data
  }

  /**
   * 生成唯一的会话ID
   */
  generateSessionId(prefix: string = 'session'): string {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 9)
    return `${prefix}-${timestamp}-${random}`
  }
}

// 导出单例
export const agentService = new AgentService()
