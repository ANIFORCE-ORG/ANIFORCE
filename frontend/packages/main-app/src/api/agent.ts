export interface AgentSession {
  id: string
  session_id?: string
  title: string
  status?: string
  created_at: string
  updated_at?: string
  archived_at?: string | null
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

export interface AgentContextSnapshot {
  route: string
  activePanel?: 'context' | 'creative' | 'analysis' | 'budget' | 'audit'
  activeProjectId?: string | null
  activeCampaignId?: string | null
  selectedEntities?: Array<{ type: 'project' | 'campaign' | 'material'; id: string; name?: string }>
  draftEdits?: Record<string, unknown>
}

export interface SideEffectEvent {
  id?: string
  type: 'entity_changed' | 'content_ready' | 'data_ready' | 'action_required' | 'run_status' | string
  domain?: string | null
  action?: string | null
  message?: string
  affected_entities?: Array<{ type?: string; id?: string; name?: string }>
  refresh_panels?: Array<'context' | 'creative' | 'analysis' | 'budget' | 'audit' | string>
  created_at?: string
}

function normalizeAgentSession(raw: any): AgentSession {
  const id = String(raw?.id || raw?.session_id || '')
  return {
    ...raw,
    id,
    session_id: raw?.session_id || id,
    title: raw?.title || id || '新对话',
    created_at: raw?.created_at || new Date().toISOString(),
    updated_at: raw?.updated_at,
  }
}

async function agentJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('animagus_token')
  const response = await fetch(`/api/v1/agent${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `Agent request failed: ${response.status}`)
  }

  return response.json()
}

export async function createAgentSession(payload: { title?: string } = {}): Promise<AgentSession> {
  const session = await agentJson<any>('/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return normalizeAgentSession(session)
}

export async function listAgentSessions(): Promise<AgentSession[]> {
  const sessions = await agentJson<any[]>('/sessions')
  return sessions.map(normalizeAgentSession)
}

export async function getAgentSession(sessionId: string): Promise<{ session: AgentSession; messages: AgentMessage[] }> {
  const sessions = await listAgentSessions()
  const session = sessions.find(item => item.id === sessionId) || normalizeAgentSession({ session_id: sessionId, title: sessionId })
  return { session, messages: [] }
}

export async function listAgentModels(): Promise<{ models: AgentModel[] }> {
  const health = await agentJson<{ provider?: string; model: string }>('/health')
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

export async function* streamAgentMessage(sessionId: string, message: string, taskType = 'conversation', contextSnapshot?: AgentContextSnapshot): AsyncGenerator<AgentStreamEvent, void, unknown> {
  const token = localStorage.getItem('animagus_token')
  const response = await fetch('/api/v1/agent/runs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ prompt: message, session_id: sessionId, task_type: taskType, context_snapshot: contextSnapshot }),
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
