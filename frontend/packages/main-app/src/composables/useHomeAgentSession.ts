import { computed, onUnmounted, ref } from 'vue'
import {
  createAgentSession,
  getAgentSession,
  listAgentModels,
  listAgentSessions,
  streamAgentMessage,
  type AgentMessage,
  type AgentModel,
  type AgentSession,
} from '@/api/agent'

export type AgentPhase =
  | { kind: 'queued' }
  | { kind: 'waiting_model' }
  | { kind: 'running_tools'; tools: { id: string; name: string }[] }
  | null

export interface SessionStats {
  tokens: { input: number; output: number; cacheRead: number; cacheWrite: number }
  cost: number
}

export interface ContextUsage {
  percent: number | null
  contextWindow: number
  tokens: number | null
}

export interface AgentRouteContext {
  task_type?: string | null
  workspace_type?: string | null
  intent?: string | null
  title?: string
}

export interface AgentCurrentTask {
  id: string
  session_id: string
  title: string
  task_type?: string | null
  status: string
  phase?: string | null
  summary?: string | null
  goal?: string | null
  task_definition?: {
    label?: string
    phases?: Array<{ key: string; label: string }>
  } | null
  pending_actions?: Array<{
    id: string
    action_type: string
    status: string
    title: string
    options?: Array<{ value?: string; label?: string }>
  }>
  artifacts?: Array<Record<string, unknown>>
}

export function useHomeAgentSession() {
  const sessions = ref<AgentSession[]>([])
  const activeSession = ref<AgentSession | null>(null)
  const messages = ref<AgentMessage[]>([])
  const streamingMessage = ref<AgentMessage | null>(null)
  const agentRunning = ref(false)
  const agentPhase = ref<AgentPhase>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const models = ref<AgentModel[]>([])
  const selectedModel = ref<{ provider: string; modelId: string } | null>(null)
  const retryInfo = ref<null>(null)
  const commandStatus = ref<string | null>(null)
  const contextUsage = ref<ContextUsage | null>(null)
  const currentTask = ref<AgentCurrentTask | null>(null)
  const workspaceToolResults = ref<Array<{ id: string; name: string; result?: unknown; isError?: boolean }>>([])
  let typewriterTimer: number | null = null
  let typewriterBuffer = ''

  const visibleMessages = computed(() => messages.value.filter(message => message.role === 'user' || message.role === 'assistant'))
  const modelNames = computed(() => Object.fromEntries(models.value.map(model => [`${model.provider}:${model.id}`, model.name])))
  const sessionStats = computed<SessionStats | null>(() => null)

  async function refreshModels(): Promise<void> {
    const res = await listAgentModels()
    models.value = res.models
    if (!selectedModel.value && res.models.length) {
      selectedModel.value = { provider: res.models[0].provider, modelId: res.models[0].id }
    }
  }

  async function refreshSessions(): Promise<void> {
    sessions.value = await listAgentSessions()
  }

  async function createSession(route?: AgentRouteContext | Event): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const normalizedRoute = route instanceof Event ? undefined : route
      const session = await createAgentSession({ title: normalizedRoute?.title || `Agent Session ${sessions.value.length + 1}` })
      sessions.value = [session, ...sessions.value.filter(item => item.id !== session.id)]
      await selectSession(session)
    } finally {
      loading.value = false
    }
  }

  async function selectSession(session: AgentSession): Promise<void> {
    activeSession.value = session
    loading.value = true
    error.value = null
    streamingMessage.value = null
    agentRunning.value = false
    try {
      const detail = await getAgentSession(session.id)
      messages.value = detail.messages
    } catch (err: any) {
      error.value = err?.message || '加载 Agent 会话失败'
    } finally {
      loading.value = false
    }
  }

  async function renameSession(sessionId: string, title: string): Promise<void> {
    sessions.value = sessions.value.map(item => item.id === sessionId ? { ...item, title } : item)
    if (activeSession.value?.id === sessionId) activeSession.value = { ...activeSession.value, title }
  }

  async function deleteSession(sessionId: string): Promise<void> {
    sessions.value = sessions.value.filter(item => item.id !== sessionId)
    if (activeSession.value?.id === sessionId) {
      activeSession.value = null
      messages.value = []
      if (sessions.value.length) await selectSession(sessions.value[0])
      else await createSession()
    }
  }

  async function send(message: string, _images?: unknown, _route?: AgentRouteContext): Promise<void> {
    const text = message.trim()
    if (!text || agentRunning.value) return
    if (!activeSession.value) await createSession()
    if (!activeSession.value) return

    error.value = null
    agentRunning.value = true
    agentPhase.value = { kind: 'waiting_model' }
    stopTypewriter()
    typewriterBuffer = ''

    messages.value.push({
      id: `local_user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    })

    const assistant: AgentMessage = {
      id: `local_assistant_${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      provider: selectedModel.value?.provider,
      model: selectedModel.value?.modelId,
    }
    streamingMessage.value = assistant

    try {
      for await (const event of streamAgentMessage(activeSession.value.id, text)) {
        if (event.event === 'runtime.started') {
          agentPhase.value = { kind: 'waiting_model' }
        }
        if (event.event === 'message.started') {
          const started = readAssistantEvent(event.data)
          assistant.id = started.id || assistant.id
          assistant.provider = started.provider || assistant.provider
          assistant.model = started.model || assistant.model
          assistant.created_at = started.created_at || assistant.created_at
        }
        if (event.event === 'message.updated') {
          const updated = readAssistantEvent(event.data)
          if (updated.provider) assistant.provider = updated.provider
          if (updated.model) assistant.model = updated.model
          enqueueTypewriter(String(updated.delta || ''))
        }
        if (event.event === 'message.completed') {
          const completed = readAssistantEvent(event.data)
          drainTypewriter()
          assistant.id = completed.id || assistant.id
          assistant.content = completed.content || assistant.content || ''
          assistant.created_at = completed.created_at || assistant.created_at
          assistant.provider = completed.provider || assistant.provider
          assistant.model = completed.model || assistant.model
          assistant.usage = completed.usage || readUsage(event.data) || assistant.usage
        }
        if (event.event === 'runtime.completed') {
          const usage = readUsage(event.data)
          if (usage) assistant.usage = usage
        }
        if (event.event === 'runtime.error') {
          const payload = readEventPayload(event.data)
          throw new Error(String(payload.message || event.data.message || 'Agent stream error'))
        }
      }
      drainTypewriter()
      messages.value.push({ ...assistant })
      streamingMessage.value = null
    } catch (err: any) {
      error.value = err?.message || 'Agent 流式响应失败'
      if (streamingMessage.value && !String(streamingMessage.value.content || '').trim()) {
        streamingMessage.value.content = '抱歉，Agent 流式响应失败，请稍后重试。'
      }
    } finally {
      stopTypewriter()
      typewriterBuffer = ''
      agentRunning.value = false
      agentPhase.value = null
    }
  }

  function abort(): void {
    error.value = '当前最小版本暂未接入取消；刷新页面可停止前端等待。'
  }

  function changeModel(provider: string, modelId: string): void {
    selectedModel.value = { provider, modelId }
  }

  function readEventPayload(data: Record<string, unknown>): Record<string, unknown> {
    const payload = data.payload
    return payload && typeof payload === 'object' ? payload as Record<string, unknown> : data
  }

  function readAssistantEvent(data: Record<string, unknown>): AgentMessage & { delta?: string } {
    const payload = readEventPayload(data)
    const value = payload.assistantMessageEvent
    if (value && typeof value === 'object') return value as AgentMessage & { delta?: string }
    return payload as AgentMessage & { delta?: string }
  }

  function readUsage(data: Record<string, unknown>): AgentMessage['usage'] | undefined {
    const payload = readEventPayload(data)
    const usage = payload.usage
    if (usage && typeof usage === 'object') return usage as AgentMessage['usage']
    return undefined
  }

  function enqueueTypewriter(delta: string): void {
    if (!delta) return
    typewriterBuffer += delta
    if (typewriterTimer) return
    typewriterTimer = window.setInterval(() => {
      if (!streamingMessage.value) return drainTypewriter()
      const chunkSize = typewriterBuffer.length > 80 ? 6 : typewriterBuffer.length > 24 ? 3 : 1
      const chunk = typewriterBuffer.slice(0, chunkSize)
      typewriterBuffer = typewriterBuffer.slice(chunkSize)
      streamingMessage.value.content = `${typeof streamingMessage.value.content === 'string' ? streamingMessage.value.content : ''}${chunk}`
      if (!typewriterBuffer) stopTypewriter()
    }, 24)
  }

  function drainTypewriter(): void {
    if (typewriterBuffer && streamingMessage.value) {
      streamingMessage.value.content = `${typeof streamingMessage.value.content === 'string' ? streamingMessage.value.content : ''}${typewriterBuffer}`
    }
    typewriterBuffer = ''
    stopTypewriter()
  }

  function stopTypewriter(): void {
    if (typewriterTimer) window.clearInterval(typewriterTimer)
    typewriterTimer = null
  }

  onUnmounted(() => stopTypewriter())

  return {
    sessions,
    activeSession,
    messages,
    streamingMessage,
    agentRunning,
    agentPhase,
    loading,
    error,
    models,
    selectedModel,
    modelNames,
    retryInfo,
    commandStatus,
    contextUsage,
    currentTask,
    workspaceToolResults,
    visibleMessages,
    sessionStats,
    refreshModels,
    refreshSessions,
    createSession,
    selectSession,
    renameSession,
    deleteSession,
    send,
    abort,
    changeModel,
  }
}
