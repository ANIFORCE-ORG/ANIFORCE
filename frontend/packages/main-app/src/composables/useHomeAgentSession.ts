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
import { useAgentStore } from '@/store/agent'

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

export interface AgentExecutionTodo {
  id: string
  title: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
}

export interface AgentExecutionTool {
  id: string
  name: string
  status: 'running' | 'completed' | 'error'
  arguments?: Record<string, unknown>
  result?: unknown
}

export interface AgentTimelineMeta {
  runId?: string
  messageId: string
  parentMessageId?: string
  toolCallId?: string
  activityType?: 'TOOL_CALL' | 'PLAN' | 'BUSINESS_RESULT'
  createdAt: number
  updatedAt: number
}

export type AgentTimelineBlock =
  | (AgentTimelineMeta & {
      type: 'tool_activity'
      id: string
      toolName: string
      status: 'running' | 'completed' | 'error'
      title: string
      description?: string
      summary?: string
      arguments?: Record<string, unknown>
      result?: unknown
    })
  | (AgentTimelineMeta & {
      type: 'project_list'
      id: string
      summary: string
      projects: Record<string, unknown>[]
      sourceToolCallId?: string
      surfaceId: string
    })
  | (AgentTimelineMeta & {
      type: 'plan'
      id: string
      todos: AgentExecutionTodo[]
    })

export function useHomeAgentSession() {
  const store = useAgentStore()
  
  // 从 store 读取全局状态（这些是 computed，只读）
  const sessions = computed(() => store.sessions)
  const activeSession = computed(() => store.activeSession)
  const messages = computed(() => store.messages)
  const timelineBlocks = computed(() => store.timelineBlocks)
  const workspaceToolResults = computed(() => store.workspaceToolResults)
  const models = computed(() => store.models)
  const selectedModel = computed(() => store.selectedModel)
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  const agentRunning = computed(() => store.agentRunning)
  const agentPhase = computed(() => store.agentPhase)
  const streamingMessage = computed(() => store.streamingMessage)
  
  // 本地临时状态（不需要跨页面持久化）
  const executionPlan = ref<{ id: string; todos: AgentExecutionTodo[] } | null>(null)
  const executionTools = ref<AgentExecutionTool[]>([])
  const retryInfo = ref<null>(null)
  const commandStatus = ref<string | null>(null)
  const contextUsage = ref<ContextUsage | null>(null)
  const currentTask = ref<AgentCurrentTask | null>(null)
  
  let currentRunId: string | undefined
  let currentAssistantMessageId: string | undefined
  let typewriterTimer: number | null = null
  let typewriterBuffer = ''

  function restoreTimelineFromCache(): void {
    if (!activeSession.value) return
    store.restoreFromLocalStorage(activeSession.value.id)
  }

  function persistTimelineToCache(): void {
    if (!activeSession.value) return
    store.persistToLocalStorage(activeSession.value.id)
  }

  function restoreWorkspaceFromCache(): void {
    if (!activeSession.value) return
    store.restoreFromLocalStorage(activeSession.value.id)
  }

  function persistWorkspaceToCache(): void {
    if (!activeSession.value) return
    store.persistToLocalStorage(activeSession.value.id)
  }

  const visibleMessages = computed(() => messages.value.filter(message => message.role === 'user' || message.role === 'assistant' || message.role === 'activity'))
  const modelNames = computed(() => Object.fromEntries(models.value.map(model => [`${model.provider}:${model.id}`, model.name])))
  const sessionStats = computed<SessionStats | null>(() => {
    const totals = messages.value.reduce(
      (acc, message) => {
        const usage = message.usage
        if (!usage) return acc
        acc.input += usage.input || 0
        acc.output += usage.output || 0
        acc.cacheRead += usage.cacheRead || 0
        acc.cacheWrite += usage.cacheWrite || 0
        acc.cost += usage.cost?.total || 0
        return acc
      },
      { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0 },
    )
    if (!totals.input && !totals.output && !totals.cacheRead && !totals.cacheWrite && !totals.cost) return null
    return {
      tokens: {
        input: totals.input,
        output: totals.output,
        cacheRead: totals.cacheRead,
        cacheWrite: totals.cacheWrite,
      },
      cost: totals.cost,
    }
  })

  async function refreshModels(): Promise<void> {
    const res = await listAgentModels()
    store.models = res.models
    if (!selectedModel.value && res.models.length) {
      store.selectedModel = { provider: res.models[0].provider, modelId: res.models[0].id }
    }
  }

  async function refreshSessions(): Promise<void> {
    store.sessions = await listAgentSessions()
  }

  async function createSession(route?: AgentRouteContext | Event): Promise<void> {
    store.loading = true
    store.error = null
    try {
      const normalizedRoute = route instanceof Event ? undefined : route
      const session = await createAgentSession({ title: normalizedRoute?.title || `Agent Session ${sessions.value.length + 1}` })
      store.sessions = [session, ...sessions.value.filter(item => item.id !== session.id)]
      await selectSession(session)
    } finally {
      store.loading = false
    }
  }

  async function selectSession(session: AgentSession): Promise<void> {
    store.activeSessionId = session.id
    localStorage.setItem('aniforce.activeSessionId', session.id)
    store.loading = true
    store.error = null
    store.streamingMessage = null
    store.agentRunning = false
    executionPlan.value = null
    executionTools.value = []
    currentRunId = undefined
    currentAssistantMessageId = undefined
    try {
      const detail = await getAgentSession(session.id)
      store.setMessages(session.id, detail.messages)
      restoreTimelineFromCache()
      restoreWorkspaceFromCache()
    } catch (err: any) {
      store.error = err?.message || '加载 Agent 会话失败'
    } finally {
      store.loading = false
    }
  }

  async function renameSession(sessionId: string, title: string): Promise<void> {
    store.sessions = sessions.value.map(item => item.id === sessionId ? { ...item, title } : item)
  }

  async function deleteSession(sessionId: string): Promise<void> {
    store.sessions = sessions.value.filter(item => item.id !== sessionId)
    if (store.activeSessionId === sessionId) {
      store.activeSessionId = null
      if (sessions.value.length) await selectSession(sessions.value[0])
      else await createSession()
    }
  }

  async function send(message: string, _images?: unknown, _route?: AgentRouteContext): Promise<void> {
    const text = message.trim()
    if (!text || agentRunning.value) return
    if (!activeSession.value) await createSession()
    if (!activeSession.value) return

    const sessionId = activeSession.value.id
    store.error = null
    store.agentRunning = true
    store.agentPhase = { kind: 'waiting_model' }
    executionPlan.value = null
    executionTools.value = []
    currentRunId = `run_${Date.now()}`
    currentAssistantMessageId = undefined
    stopTypewriter()
    typewriterBuffer = ''

    store.appendMessage(sessionId, {
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
    store.streamingMessage = assistant

    try {
      for await (const event of streamAgentMessage(sessionId, text, _route?.task_type || 'conversation')) {
        if (event.event === 'runtime.started') {
          currentRunId = String(event.data.task_id || event.data.run_id || `run_${Date.now()}`)
          store.agentPhase = { kind: 'waiting_model' }
        }

        if (event.event === 'message.updated') {
          if (!currentAssistantMessageId) {
            assistant.id = `msg_${Date.now()}`
            currentAssistantMessageId = assistant.id
            attachCurrentRunTimelineBlocks(assistant.id)
          }
          const delta = event.data.delta
          if (typeof delta === 'string') enqueueTypewriter(delta)
        }

        if (event.event === 'message.completed') {
          drainTypewriter()
          const content = event.data.content
          if (typeof content === 'string' && content.trim()) assistant.content = content
          const usage = event.data.usage
          if (usage && typeof usage === 'object') assistant.usage = usage as any
          currentAssistantMessageId = assistant.id
          attachCurrentRunTimelineBlocks(assistant.id)
        }

        if (event.event === 'tool_call.started') {
          const toolName = String(event.data.tool_name || 'tool')
          const toolId = String(event.data.tool_call_id || `${toolName}_${Date.now()}`)
          const args = normalizeRecord(event.data.arguments)
          const tool: AgentExecutionTool = {
            id: toolId,
            name: toolName,
            status: 'running',
            arguments: args,
          }
          executionTools.value = [...executionTools.value, tool].slice(-8)
          upsertTimelineTool({ id: toolId, toolName, status: 'running', arguments: args })
          store.agentPhase = {
            kind: 'running_tools',
            tools: executionTools.value
              .filter(item => item.status === 'running')
              .map(item => ({ id: item.id, name: item.name })),
          }
        }

        if (event.event === 'tool_call.completed') {
          const toolId = String(event.data.tool_call_id || '')
          const result = event.data.result
          let toolName = String(event.data.tool_name || '')
          const index = executionTools.value.findIndex(t => t.id === toolId)
          if (index >= 0) {
            toolName = toolName || executionTools.value[index].name
            executionTools.value[index] = {
              ...executionTools.value[index],
              status: 'completed',
              result,
            }
            executionTools.value = [...executionTools.value]
          }
          if (toolName) {
            upsertTimelineTool({ id: toolId || `${toolName}_${Date.now()}`, toolName, status: 'completed', result })
            appendBusinessResultBlock(toolId, toolName, result)
          }
          const running = executionTools.value.filter(item => item.status === 'running')
          store.agentPhase = running.length
            ? { kind: 'running_tools', tools: running.map(item => ({ id: item.id, name: item.name })) }
            : { kind: 'waiting_model' }
        }

        if (event.event === 'plan.created' || event.event === 'plan.updated' || event.event.startsWith('todo.')) {
          handleCustomEvent({ subtype: event.event, ...event.data })
        }

        if (event.event === 'runtime.completed') {
          markRunningToolsCompleted()
        }

        if (event.event === 'runtime.error' || event.event === 'error') {
          throw new Error(String(event.data.message || 'Agent 流式响应错误'))
        }
      }
      drainTypewriter()
      store.appendMessage(sessionId, { ...assistant })
      store.streamingMessage = null
    } catch (err: any) {
      store.error = err?.message || 'Agent 流式响应失败'
      if (streamingMessage.value && !String(streamingMessage.value.content || '').trim()) {
        streamingMessage.value.content = '抱歉，Agent 流式响应失败，请稍后重试。'
      }
    } finally {
      stopTypewriter()
      typewriterBuffer = ''
      store.agentRunning = false
      store.agentPhase = null
      markRunningToolsCompleted()
    }
  }

  function abort(): void {
    store.error = '当前最小版本暂未接入取消；刷新页面可停止前端等待。'
  }

  function changeModel(provider: string, modelId: string): void {
    store.selectedModel = { provider, modelId }
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

  function normalizeRecord(value: unknown): Record<string, unknown> | undefined {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : undefined
  }

  function handleCustomEvent(data: Record<string, unknown>): void {
    const payload = readEventPayload(data)
    const subtype = String(payload.subtype || '')
    if (subtype === 'plan.created') {
      const todos = Array.isArray(payload.todos) ? payload.todos : []
      executionPlan.value = {
        id: String(payload.plan_id || `plan_${Date.now()}`),
        todos: todos.map((todo, index) => {
          const record = todo && typeof todo === 'object' ? todo as Record<string, unknown> : {}
          return {
            id: String(record.id || `todo_${index + 1}`),
            title: String(record.title || `步骤 ${index + 1}`),
            description: record.description ? String(record.description) : undefined,
            status: normalizeTodoStatus(record.status),
          }
        }),
      }
      upsertPlanBlock()
      return
    }

    if (subtype.startsWith('todo.') && executionPlan.value) {
      const todoId = String(payload.todo_id || '')
      const nextStatus = normalizeTodoStatus(subtype.replace('todo.', ''))
      executionPlan.value = {
        ...executionPlan.value,
        todos: executionPlan.value.todos.map(todo =>
          todo.id === todoId ? { ...todo, status: nextStatus } : todo
        ),
      }
      upsertPlanBlock()
    }
  }

  function upsertPlanBlock(): void {
    if (!executionPlan.value) return
    const blockId = executionPlan.value.id
    const existing = timelineBlocks.value.find(item => item.type === 'plan' && item.id === blockId)
    const now = Date.now()
    const block: AgentTimelineBlock = {
      ...timelineMeta({ id: blockId, existing, activityType: 'PLAN', now }),
      type: 'plan',
      id: blockId,
      todos: executionPlan.value.todos,
    }
    if (!activeSession.value) return
    store.upsertTimelineBlock(activeSession.value.id, block)
  }

  function upsertTimelineTool(input: {
    id: string
    toolName: string
    status: 'running' | 'completed' | 'error'
    arguments?: Record<string, unknown>
    result?: unknown
  }): void {
    if (isInvisibleTool(input.toolName, input.arguments)) return
    const presentation = toolPresentation(input.toolName, input.arguments, input.result, input.status)
    const existing = timelineBlocks.value.find(item => item.type === 'tool_activity' && item.toolCallId === input.id)
    const now = Date.now()
    const block: AgentTimelineBlock = {
      ...timelineMeta({ id: `activity_tool_${input.id}`, existing, toolCallId: input.id, activityType: 'TOOL_CALL', now }),
      type: 'tool_activity',
      id: `activity_tool_${input.id}`,
      toolName: input.toolName,
      status: input.status,
      title: presentation.title,
      description: presentation.description,
      summary: presentation.summary,
      arguments: input.arguments || (existing?.type === 'tool_activity' ? existing.arguments : undefined),
      result: input.result,
    }
    if (!activeSession.value) return
    store.upsertTimelineBlock(activeSession.value.id, block)
  }

  function isInvisibleTool(toolName: string, args?: Record<string, unknown>): boolean {
    return toolName === 'unknown' && (!args || Object.keys(args).length === 0)
  }

  function toolPresentation(
    toolName: string,
    args: Record<string, unknown> | undefined,
    result: unknown,
    status: 'running' | 'completed' | 'error'
  ): { title: string; description?: string; summary?: string } {
    if (toolName === 'list_projects') {
      const limit = args?.limit ? `最多 ${args.limit} 个` : '默认数量'
      const statusText = args?.status ? `状态 ${args.status}` : '全部状态'
      return {
        title: status === 'running' ? '正在查询项目列表' : status === 'error' ? '项目列表查询失败' : '项目列表查询完成',
        description: `从 ANIFORCE 项目库读取当前账号可访问项目（${statusText} · ${limit}）`,
        summary: status === 'completed' ? summarizeProjectResult(result) : undefined,
      }
    }
    if (toolName === 'get_project_detail') {
      return {
        title: status === 'running' ? '正在读取项目详情' : status === 'error' ? '项目详情读取失败' : '项目详情读取完成',
        description: args?.project_id ? `项目 ID：${args.project_id}` : undefined,
      }
    }
    if (toolName === 'create_project') {
      return {
        title: status === 'running' ? '正在创建项目' : status === 'error' ? '项目创建失败' : '项目创建完成',
        description: args?.name ? `项目：${args.name}` : undefined,
      }
    }
    return {
      title: status === 'running' ? '正在执行 Agent 操作' : status === 'error' ? 'Agent 操作失败' : 'Agent 操作完成',
      description: toolName,
    }
  }

  function appendBusinessResultBlock(toolCallId: string, toolName: string, result: unknown): void {
    if (toolName !== 'list_projects') return
    const projects = extractProjects(result)
    if (!projects) return
    const blockId = `surface_project_list_${toolCallId}`
    const existing = timelineBlocks.value.find(item => item.id === blockId)
    const now = Date.now()
    const block: AgentTimelineBlock = {
      ...timelineMeta({ id: blockId, existing, toolCallId, activityType: 'BUSINESS_RESULT', now }),
      type: 'project_list',
      id: blockId,
      summary: `共 ${projects.length} 个项目`,
      projects,
      sourceToolCallId: toolCallId,
      surfaceId: `project-list-${toolCallId}`,
    }
    if (!activeSession.value) return
    const sessionId = activeSession.value.id
    store.upsertTimelineBlock(sessionId, block)
    store.setWorkspace(sessionId, [{
      id: `workspace_${blockId}`,
      name: 'project_list',
      result: {
        type: 'project_list',
        projects,
        summary: block.summary,
      },
    }])
  }

  function summarizeProjectResult(result: unknown): string {
    const projects = extractProjects(result)
    if (projects) return `找到 ${projects.length} 个项目`
    const text = typeof result === 'string' ? result : ''
    const match = /找到\s*(\d+)\s*个项目/.exec(text)
    return match ? `找到 ${match[1]} 个项目` : '已获得查询结果'
  }

  function extractProjects(result: unknown): Record<string, unknown>[] | null {
    if (!result) return null
    if (typeof result === 'object') {
      const record = result as Record<string, unknown>
      const candidates = [record.projects, record.items, record.list]
      for (const candidate of candidates) {
        if (Array.isArray(candidate)) return candidate.filter(isRecord)
      }
      if (typeof record.text === 'string') return extractProjects(record.text)
    }
    if (typeof result !== 'string') return null
    const projects: Record<string, unknown>[] = []
    const chunks = result.split(/\n(?=\d+\.\s+\*\*)/g)
    for (const chunk of chunks) {
      const nameMatch = /\d+\.\s+\*\*(.*?)\*\*/.exec(chunk)
      const idMatch = /ID:\s*([^\n]+)/.exec(chunk)
      if (!nameMatch || !idMatch) continue
      const budgetMatch = /预算:\s*[¥￥]?([\d,\.]+)/.exec(chunk)
      const statusMatch = /状态:\s*([^\n]+)/.exec(chunk)
      const descriptionMatch = /描述:\s*([^\n]+)/.exec(chunk)
      projects.push({
        id: idMatch[1].trim(),
        name: nameMatch[1].trim(),
        total_budget: budgetMatch ? Number(budgetMatch[1].replace(/,/g, '')) : 0,
        spent: 0,
        status: statusMatch ? statusMatch[1].trim() : undefined,
        description: descriptionMatch ? descriptionMatch[1].trim() : undefined,
        game_type: '',
        target_market: '',
        tags: [],
      })
    }
    return projects.length ? projects : null
  }

  function isRecord(value: unknown): value is Record<string, unknown> {
    return Boolean(value && typeof value === 'object' && !Array.isArray(value))
  }

  function reparentTimelineBlocks(previousParentId: string | undefined, nextParentId: string | undefined): void {
    if (!previousParentId || !nextParentId || previousParentId === nextParentId) return
    if (!activeSession.value) return
    const sessionId = activeSession.value.id
    let changed = false
    const current = store.timelineBySession.get(sessionId) || []
    const updated = current.map(block => {
      if (block.parentMessageId !== previousParentId) return block
      changed = true
      return { ...block, parentMessageId: nextParentId, updatedAt: Date.now() }
    })
    if (changed) {
      store.timelineBySession.set(sessionId, updated)
      store.persistToLocalStorage(sessionId)
    }
  }

  function attachCurrentRunTimelineBlocks(parentMessageId: string | undefined): void {
    if (!parentMessageId || !currentRunId) return
    if (!activeSession.value) return
    const sessionId = activeSession.value.id
    let changed = false
    const current = store.timelineBySession.get(sessionId) || []
    const updated = current.map(block => {
      if (block.parentMessageId || block.runId !== currentRunId) return block
      changed = true
      return { ...block, parentMessageId, updatedAt: Date.now() }
    })
    if (changed) {
      store.timelineBySession.set(sessionId, updated)
      store.persistToLocalStorage(sessionId)
    }
  }

  function timelineMeta(input: {
    id: string
    existing?: AgentTimelineBlock
    toolCallId?: string
    activityType: AgentTimelineMeta['activityType']
    now: number
  }): AgentTimelineMeta {
    return {
      runId: input.existing?.runId || currentRunId,
      messageId: input.existing?.messageId || input.id,
      parentMessageId: input.existing?.parentMessageId || currentAssistantMessageId,
      toolCallId: input.existing?.toolCallId || input.toolCallId,
      activityType: input.activityType,
      createdAt: input.existing?.createdAt || input.now,
      updatedAt: input.now,
    }
  }

  function handleTimelineAction(action: string, payload: Record<string, unknown>): void {
    if (action === 'open_project' && payload.projectId) {
      window.location.href = `/projects/${encodeURIComponent(String(payload.projectId))}`
      return
    }
    if (action === 'create_campaign' && payload.projectId) {
      window.location.href = `/campaign/create?project_id=${encodeURIComponent(String(payload.projectId))}`
      return
    }
    if (action === 'open_in_workspace' && payload.type === 'project_list') {
      if (!activeSession.value) return
      const projects = Array.isArray(payload.projects) ? payload.projects : []
      store.setWorkspace(activeSession.value.id, [{
        id: `workspace_${Date.now()}`,
        name: 'project_list',
        result: {
          type: 'project_list',
          projects,
          summary: payload.summary || `共 ${projects.length} 个项目`
        }
      }])
    }
  }

  function normalizeTodoStatus(value: unknown): AgentExecutionTodo['status'] {
    if (value === 'running' || value === 'completed' || value === 'failed' || value === 'skipped') return value
    return 'pending'
  }

  function findLatestToolIndex(toolName: string): number {
    for (let index = executionTools.value.length - 1; index >= 0; index -= 1) {
      if (executionTools.value[index]?.name === toolName && executionTools.value[index]?.status === 'running') return index
    }
    for (let index = executionTools.value.length - 1; index >= 0; index -= 1) {
      if (executionTools.value[index]?.name === toolName) return index
    }
    return -1
  }

  function markRunningToolsCompleted(): void {
    let changed = false
    executionTools.value = executionTools.value.map(tool => {
      if (tool.status !== 'running') return tool
      changed = true
      return { ...tool, status: 'completed' }
    })
    if (changed) executionTools.value = [...executionTools.value]
    
    if (!activeSession.value) return
    const sessionId = activeSession.value.id
    const current = store.timelineBySession.get(sessionId) || []
    const updated = current.map(block => {
      if (block.type !== 'tool_activity' || block.status !== 'running') return block
      return { ...block, status: 'completed' as const, title: toolPresentation(block.toolName, block.arguments, block.result, 'completed').title, updatedAt: Date.now() }
    })
    store.timelineBySession.set(sessionId, updated)
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
    executionPlan,
    executionTools,
    timelineBlocks,
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
    handleTimelineAction,
  }
}
