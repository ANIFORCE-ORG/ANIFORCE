import { http } from './http'

export interface AgentSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface AgentUsage {
  input?: number
  output?: number
  cacheRead?: number
  cacheWrite?: number
  totalTokens?: number
  cost?: { total?: number; input?: number; output?: number; cacheRead?: number; cacheWrite?: number }
}

export interface TextContentBlock { type: 'text'; text: string }
export interface ImageContentBlock { type: 'image'; data?: string; mimeType?: string; source?: Record<string, unknown> }
export type AgentContentBlock = TextContentBlock | ImageContentBlock | Record<string, unknown>

export interface AgentMessage {
  id?: string
  role: 'user' | 'assistant' | 'system' | 'toolResult' | 'bashExecution' | 'custom' | 'branchSummary' | 'compactionSummary' | 'activity'
  content?: string | AgentContentBlock[] | ActivityContent
  sequence?: number
  created_at?: string
  timestamp?: number | string
  provider?: string
  model?: string
  usage?: AgentUsage
  toolCallId?: string
  toolName?: string
  isError?: boolean
  [key: string]: unknown
}

export interface ActivityContent {
  activityType: string
  toolName: string
  status: 'running' | 'completed' | 'error'
  title: string
  arguments?: Record<string, unknown>
}

export interface AgentModel {
  id: string
  name: string
  provider: string
  input?: string[]
}

export interface AgentStreamEvent {
  event: string
  data: Record<string, unknown>
}

export async function createAgentSession(payload: { title?: string } = {}): Promise<AgentSession> {
  return http.post<AgentSession>('/agent/chat/sessions', payload)
}

export async function listAgentSessions(): Promise<AgentSession[]> {
  return http.get<AgentSession[]>('/agent/chat/sessions')
}

export async function getAgentSession(sessionId: string): Promise<{ session: AgentSession; messages: AgentMessage[] }> {
  return http.get(`/agent/chat/sessions/${encodeURIComponent(sessionId)}`)
}

export async function listAgentModels(): Promise<{ models: AgentModel[] }> {
  const health = await http.get<{ provider: string; model: string }>('/agent/health')
  return {
    models: [
      {
        id: health.model,
        name: health.model,
        provider: health.provider || 'openai-compatible',
        input: ['text'],
      },
    ],
  }
}

export async function* streamAgentMessage(sessionId: string, message: string): AsyncGenerator<AgentStreamEvent, void, unknown> {
  const token = localStorage.getItem('animagus_token')
  const response = await fetch(`/api/v1/agent/chat/sessions/${encodeURIComponent(sessionId)}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message }),
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `Agent stream failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('Agent stream response is not readable')

  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const raw = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const event = parseSseEvent(raw)
        if (event) yield event
        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}

function parseSseEvent(raw: string): AgentStreamEvent | null {
  const lines = raw.split('\n')
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
