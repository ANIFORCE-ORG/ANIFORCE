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
export interface ThinkingContentBlock { type: 'thinking'; thinking: string }
export type AgentContentBlock = TextContentBlock | ImageContentBlock | ThinkingContentBlock | Record<string, unknown>

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

function clearInvalidAuth(): void {
  localStorage.removeItem('animagus_token')
  localStorage.removeItem('animagus_auth')
  localStorage.removeItem('animagus_user')
}

function redirectToLogin(): void {
  if (window.location.pathname !== '/login') window.location.href = '/login'
}

function isTokenExpired(token: string): boolean {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return true
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(decodeURIComponent(atob(base64).split('').map(char => `%${(`00${char.charCodeAt(0).toString(16)}`).slice(-2)}`).join('')))
    return !payload.exp || Date.now() >= Number(payload.exp) * 1000
  } catch {
    return true
  }
}

function stringifyErrorPayload(payload: unknown, fallback: string): string {
  if (!payload) return fallback
  if (typeof payload === 'string') return payload
  if (typeof payload !== 'object') return String(payload)
  const record = payload as Record<string, unknown>
  return stringifyErrorPayload(record.detail || record.error || record.message || record.code, fallback)
}

function parseErrorMessage(text: string, fallback: string): string {
  if (!text) return fallback
  try {
    return stringifyErrorPayload(JSON.parse(text), fallback)
  } catch {
    return text
  }
}

async function throwAgentError(response: Response, fallback: string): Promise<never> {
  const text = await response.text().catch(() => '')
  const message = parseErrorMessage(text, fallback)
  if (response.status === 401) {
    clearInvalidAuth()
    redirectToLogin()
  }
  throw new Error(message)
}

function getValidAgentToken(): string | null {
  const token = localStorage.getItem('animagus_token')
  if (token && isTokenExpired(token)) {
    clearInvalidAuth()
    redirectToLogin()
    throw new Error('登录已过期，请重新登录')
  }
  return token
}

async function agentJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getValidAgentToken()
  const response = await fetch(`/api/v1/agent${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    await throwAgentError(response, `Agent request failed: ${response.status}`)
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
  const detail = await agentJson<any>(`/sessions/${encodeURIComponent(sessionId)}`)
  const session = normalizeAgentSession(detail)
  const messages = Array.isArray(detail.messages) ? detail.messages as AgentMessage[] : []
  return { session, messages }
}

export async function updateAgentSession(sessionId: string, payload: { title: string }): Promise<AgentSession> {
  const session = await agentJson<any>(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
  return normalizeAgentSession(session)
}

export async function deleteAgentSession(sessionId: string): Promise<void> {
  await agentJson(`/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
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

export async function cancelAgentTask(taskId: string, sessionId?: string): Promise<void> {
  await agentJson(`/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export interface AgentRunStart {
  run_id: string
  session_id: string
  status: string
}

export async function startAgentRun(sessionId: string, message: string, taskType = 'conversation', contextSnapshot?: AgentContextSnapshot, signal?: AbortSignal): Promise<AgentRunStart> {
  const token = getValidAgentToken()
  const response = await fetch('/api/v1/agent/runs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ prompt: message, session_id: sessionId, task_type: taskType, context_snapshot: contextSnapshot }),
    signal,
  })
  if (!response.ok) {
    await throwAgentError(response, `Agent run failed: ${response.status}`)
  }
  return response.json()
}

export async function* streamAgentRunEvents(runId: string, afterSequence = 0, signal?: AbortSignal): AsyncGenerator<AgentStreamEvent, void, unknown> {
  const token = getValidAgentToken()
  const response = await fetch(`/api/v1/agent/runs/${encodeURIComponent(runId)}/events?after_sequence=${afterSequence}`, {
    method: 'GET',
    headers: {
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
  })

  if (!response.ok) {
    await throwAgentError(response, `Agent event stream failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('Agent event stream response is not readable')

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

export async function* streamAgentMessage(sessionId: string, message: string, taskType = 'conversation', contextSnapshot?: AgentContextSnapshot, signal?: AbortSignal): AsyncGenerator<AgentStreamEvent, void, unknown> {
  const run = await startAgentRun(sessionId, message, taskType, contextSnapshot, signal)
  yield { event: 'runtime.started', data: { run_id: run.run_id, task_id: run.run_id, session_id: run.session_id } }
  let lastSequence = 0
  for await (const event of streamAgentRunEvents(run.run_id, lastSequence, signal)) {
    const sequence = Number((event.data as any)?.sequence || 0)
    if (sequence > lastSequence) lastSequence = sequence
    yield event
  }
}

function parseSseEvent(raw: string): AgentStreamEvent | null {
  const lines = raw.split('\n')
  let event = 'message'
  let id: number | null = null
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith('id:')) id = Number(line.slice(3).trim()) || null
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
  }
  if (!dataLines.length) return null
  try {
    const data = JSON.parse(dataLines.join('\n'))
    if (id !== null && data && typeof data === 'object') data.sequence = id
    return { event, data }
  } catch {
    return { event, data: { text: dataLines.join('\n'), ...(id !== null ? { sequence: id } : {}) } }
  }
}
