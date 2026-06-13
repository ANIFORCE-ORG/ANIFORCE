import type {
  AGUIEvent,
  AGUIEventHandler,
  EnhancedMessage,
  ExecutionPlan,
  ToolCall,
  HITLConfirmationRequest,
  SharedState,
} from '@/types/agui'
import {
  isTextMessageEvent,
  isMessageCompletedEvent,
  isToolCallEvent,
  isCustomEvent,
  getCustomEventSubtype,
  AGUIEventType,
  CustomEventSubtype,
} from '@/types/agui'

export interface AgentChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface AgentChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface AgentStreamEvent {
  event: string
  data: Record<string, any>
}

// AG-UI 增强事件处理器
export interface AGUIEventHandlers {
  onTextMessage?: (content: string) => void
  onMessageCompleted?: (content: string) => void
  onToolCall?: (tool: ToolCall) => void
  onPlanCreated?: (plan: ExecutionPlan) => void
  onTodoUpdated?: (todoId: string, status: string) => void
  onHITLRequest?: (request: HITLConfirmationRequest) => void
  onStateUpdate?: (state: SharedState) => void
  onError?: (error: any) => void
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('animagus_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export class AgentService {
  generateSessionId(prefix: string = 'chat'): string {
    const timestamp = Date.now()
    const random = Math.random().toString(36).slice(2, 9)
    return `${prefix}_${timestamp}_${random}`
  }

  async healthCheck(): Promise<{ status: string; provider: string; model: string; streaming: boolean }> {
    const response = await fetch(apiUrl('/agent/health'), {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`Agent health failed: ${response.status}`)
    return response.json()
  }

  async createChatSession(title = '新对话'): Promise<AgentChatSession> {
    const response = await fetch(apiUrl('/agent/chat/sessions'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({ title }),
    })
    if (!response.ok) throw new Error(`Create chat session failed: ${response.status}`)
    return response.json()
  }

  async getChatSession(sessionId: string): Promise<{ session: AgentChatSession; messages: AgentChatMessage[] }> {
    const response = await fetch(apiUrl(`/agent/chat/sessions/${encodeURIComponent(sessionId)}`), {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`Get chat session failed: ${response.status}`)
    return response.json()
  }

  async getSessionDetail(sessionId: string): Promise<{ session_id: string; messages: AgentChatMessage[]; message_count: number; created_at: string; updated_at: string }> {
    const detail = await this.getChatSession(sessionId)
    return {
      session_id: detail.session.id,
      messages: detail.messages,
      message_count: detail.messages.length,
      created_at: detail.session.created_at,
      updated_at: detail.session.updated_at,
    }
  }

  async chat(sessionId: string, message: string): Promise<{ session_id: string; message: string; timestamp: string }> {
    let text = ''
    let timestamp = new Date().toISOString()
    for await (const event of this.streamChat(sessionId, message)) {
      const payload = readEventPayload(event.data)
      if (event.event === 'message_delta' || event.event === 'message.updated') text += String(payload.delta || '')
      if (event.event === 'message_completed' || event.event === 'message.completed') {
        text = String(payload.content || text)
        timestamp = String(event.data.created_at || timestamp)
      }
    }
    return { session_id: sessionId, message: text, timestamp }
  }

  async *chatStream(sessionId: string, message: string): AsyncGenerator<string, void, unknown> {
    for await (const event of this.streamChat(sessionId, message)) {
      const payload = readEventPayload(event.data)
      if (event.event === 'message_delta' || event.event === 'message.updated') yield String(payload.delta || '')
      if (event.event === 'runtime.error' || event.event === 'error') {
        throw new Error(String(payload.message || event.data.message || 'Agent stream error'))
      }
    }
  }

  async *streamChat(sessionId: string, message: string): AsyncGenerator<AgentStreamEvent, void, unknown> {
    const response = await fetch(apiUrl(`/agent/chat/sessions/${encodeURIComponent(sessionId)}/stream`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...authHeaders(),
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => '')
      throw new Error(errorText || `Stream chat failed: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('Stream response body is not readable')

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let boundaryIndex = buffer.indexOf('\n\n')
        while (boundaryIndex >= 0) {
          const rawEvent = buffer.slice(0, boundaryIndex)
          buffer = buffer.slice(boundaryIndex + 2)
          const parsed = parseSseEvent(rawEvent)
          if (parsed) yield parsed
          boundaryIndex = buffer.indexOf('\n\n')
        }
      }
    } finally {
      reader.releaseLock()
    }
  }
}

function readEventPayload(data: Record<string, any>): Record<string, any> {
  const payload = data.payload
  return payload && typeof payload === 'object' ? payload : data
}

function parseSseEvent(rawEvent: string): AgentStreamEvent | null {
  const lines = rawEvent.split('\n')
  let event = 'message'
  const dataLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
  }

  if (!dataLines.length) return null

  try {
    return { event, data: JSON.parse(dataLines.join('\n')) }
  } catch {
    return { event, data: { text: dataLines.join('\n') } }
  }
}

export const agentService = new AgentService()

  /**
   * AG-UI 增强的流式对话
   * 支持所有 AG-UI 协议事件
   */
  async *streamChatWithHandlers(
    sessionId: string,
    message: string,
    handlers: AGUIEventHandlers
  ): AsyncGenerator<AGUIEvent, void, unknown> {
    for await (const event of this.streamChat(sessionId, message)) {
      const aguiEvent: AGUIEvent = event as AGUIEvent
      const eventType = aguiEvent.event
      const payload = aguiEvent.data.payload || aguiEvent.data

      try {
        // 文本消息事件
        if (isTextMessageEvent(eventType)) {
          const content = String(payload.delta || payload.content || '')
          if (content && handlers.onTextMessage) {
            handlers.onTextMessage(content)
          }
        }

        // 消息完成事件
        if (isMessageCompletedEvent(eventType)) {
          const content = String(payload.content || payload.text || '')
          if (handlers.onMessageCompleted) {
            handlers.onMessageCompleted(content)
          }
        }

        // 工具调用事件
        if (isToolCallEvent(eventType)) {
          if (eventType === AGUIEventType.TOOL_CALL_START) {
            const tool: ToolCall = {
              tool_name: String(payload.tool_name || ''),
              started_at: new Date().toISOString(),
            }
            if (handlers.onToolCall) {
              handlers.onToolCall(tool)
            }
          } else if (eventType === AGUIEventType.TOOL_CALL_ARGS) {
            const tool: ToolCall = {
              tool_name: String(payload.tool_name || ''),
              tool_args: payload.tool_args || payload.args,
            }
            if (handlers.onToolCall) {
              handlers.onToolCall(tool)
            }
          } else if (eventType === AGUIEventType.TOOL_CALL_END) {
            const tool: ToolCall = {
              tool_name: String(payload.tool_name || ''),
              tool_result: payload.tool_result || payload.result,
              completed_at: new Date().toISOString(),
            }
            if (handlers.onToolCall) {
              handlers.onToolCall(tool)
            }
          }
        }

        // 自定义事件（Plan/Todo/HITL）
        if (isCustomEvent(eventType)) {
          const subtype = getCustomEventSubtype(aguiEvent)

          if (subtype === CustomEventSubtype.PLAN_CREATED) {
            const plan: ExecutionPlan = {
              plan_id: String(payload.plan_id || ''),
              task_id: sessionId,
              todos: payload.todos || [],
            }
            if (handlers.onPlanCreated) {
              handlers.onPlanCreated(plan)
            }
          } else if (
            subtype === CustomEventSubtype.TODO_STARTED ||
            subtype === CustomEventSubtype.TODO_COMPLETED ||
            subtype === CustomEventSubtype.TODO_FAILED ||
            subtype === CustomEventSubtype.TODO_SKIPPED
          ) {
            const todoId = String(payload.todo_id || '')
            const status = subtype.replace('todo.', '')
            if (handlers.onTodoUpdated) {
              handlers.onTodoUpdated(todoId, status)
            }
          } else if (subtype === CustomEventSubtype.HITL_CONFIRMATION_REQUEST) {
            const request: HITLConfirmationRequest = {
              request_id: String(payload.request_id || ''),
              operation: String(payload.operation || ''),
              description: String(payload.description || ''),
              risk_level: payload.risk_level || 'medium',
              details: payload.details,
            }
            if (handlers.onHITLRequest) {
              handlers.onHITLRequest(request)
            }
          }
        }

        // 共享状态事件
        if (eventType === AGUIEventType.STATE_SNAPSHOT) {
          const state: SharedState = payload.state || payload
          if (handlers.onStateUpdate) {
            handlers.onStateUpdate(state)
          }
        }

        // 错误事件
        if (eventType === AGUIEventType.RUNTIME_ERROR || eventType === 'error') {
          if (handlers.onError) {
            handlers.onError(payload)
          }
        }

        yield aguiEvent
      } catch (error) {
        console.error('AG-UI event handling error:', error)
        if (handlers.onError) {
          handlers.onError({ message: 'Event handling failed', error })
        }
      }
    }
  }

  /**
   * 发送 HITL 确认响应
   */
  async sendHITLResponse(
    sessionId: string,
    requestId: string,
    confirmed: boolean,
    feedback?: string
  ): Promise<void> {
    const response = await fetch(apiUrl(`/agent/chat/sessions/${encodeURIComponent(sessionId)}/hitl`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({
        request_id: requestId,
        confirmed,
        user_feedback: feedback,
      }),
    })

    if (!response.ok) {
      throw new Error(`Send HITL response failed: ${response.status}`)
    }
  }
