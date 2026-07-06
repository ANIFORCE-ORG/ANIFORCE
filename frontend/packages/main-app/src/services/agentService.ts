import type {
  AGUIEvent,
  ExecutionPlan,
  ToolCall,
  HITLConfirmationRequest,
  SharedState,
} from '@/types/agui'
import {
  AGUIEventType,
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

function readSdkTextDelta(event: AgentStreamEvent): string {
  const data = event.data.data
  if (event.event !== 'raw_response_event' || event.data.type !== 'raw_response_event' || !data || typeof data !== 'object') return ''
  const record = data as Record<string, any>
  return record.type === 'response.output_text.delta' ? String(record.delta || '') : ''
}

function sdkToolEventToTool(event: AgentStreamEvent): ToolCall | null {
  if (event.event !== 'run_item_stream_event' || event.data.type !== 'run_item_stream_event') return null
  const item = event.data.item && typeof event.data.item === 'object' ? event.data.item as Record<string, any> : {}
  const raw = item.raw_item && typeof item.raw_item === 'object' ? item.raw_item as Record<string, any> : {}
  if (event.data.name === 'tool_called') {
    return {
      tool_name: String(item.tool_name || raw.name || item.name || 'tool'),
      tool_args: raw.arguments || item.arguments || {},
      started_at: new Date().toISOString(),
    }
  }
  if (event.data.name === 'tool_output') {
    return {
      tool_name: String(item.tool_name || raw.name || item.name || 'tool'),
      tool_result: 'output' in item ? item.output : raw.output || raw.content,
      completed_at: new Date().toISOString(),
    }
  }
  return null
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
      text += readSdkTextDelta(event)
      if (event.event === 'runtime.completed') {
        text = String(event.data.final_output || text)
        timestamp = String(event.data.created_at || timestamp)
      }
    }
    return { session_id: sessionId, message: text, timestamp }
  }

  async *chatStream(sessionId: string, message: string): AsyncGenerator<string, void, unknown> {
    for await (const event of this.streamChat(sessionId, message)) {
      const delta = readSdkTextDelta(event)
      if (delta) yield delta
      if (event.event === 'runtime.error' || event.event === 'error') {
        throw new Error(String(event.data.message || 'Agent stream error'))
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

  async *streamChatWithHandlers(
    sessionId: string,
    message: string,
    handlers: AGUIEventHandlers
  ): AsyncGenerator<AGUIEvent, void, unknown> {
    for await (const event of this.streamChat(sessionId, message)) {
      const aguiEvent: AGUIEvent = event as AGUIEvent

      try {
        const content = readSdkTextDelta(event)
        if (content) handlers.onTextMessage?.(content)

        if (event.event === 'runtime.completed') {
          handlers.onMessageCompleted?.(String(event.data.final_output || ''))
        }

        const tool = sdkToolEventToTool(event)
        if (tool) handlers.onToolCall?.(tool)

        if (event.event === AGUIEventType.STATE_SNAPSHOT) {
          handlers.onStateUpdate?.(event.data.state || event.data)
        }

        if (event.event === AGUIEventType.RUNTIME_ERROR || event.event === 'error') {
          handlers.onError?.(event.data)
        }

        yield aguiEvent
      } catch (error) {
        console.error('AG-UI event handling error:', error)
        handlers.onError?.({ message: 'Event handling failed', error })
      }
    }
  }

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
}

export const agentService = new AgentService()
