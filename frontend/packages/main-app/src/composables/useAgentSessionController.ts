import { computed, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  createAgentSession,
  getAgentSessionSnapshot,
  listAgentModels,
  listAgentSessions,
  startAgentRun,
  streamAgentRunEvents,
  resolveAgentRunApproval,
  cancelAgentRun,
  updateAgentSession,
  deleteAgentSession,
  type AgentMessage,
  type AgentModel,
  type AgentSession,
  type AgentContextSnapshot,
  type AgentContentBlock,
  type AgentSdkStreamEvent,
  type SideEffectEvent,
} from '@/api/agent'
import { useAgentStore } from '@/store/agent'
import { useWorkspaceStore, workspaceResultProjectionRegistry, type WorkspaceSurface } from '@/store/workspace'
import { parseAgentSdkEvent } from '@/agent/protocol/parser'
import { connectPersistedRun } from '@/services/runConnectionManager'
import { hydrateWorkspaceSnapshot } from '@/services/workspaceArtifactStore'

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

export function useAgentSessionController() {
  const store = useAgentStore()
  const workspace = useWorkspaceStore()
  const route = useRoute()
  
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
  const showingActiveRun = computed(() => Boolean(store.agentRunning && activeSession.value?.id === store.activeRunSessionId))
  const agentRunning = computed(() => showingActiveRun.value)
  const agentPhase = computed(() => showingActiveRun.value ? store.agentPhase : null)
  const streamingMessage = computed(() => showingActiveRun.value ? store.streamingMessage : null)
  
  // 本地临时状态（不需要跨页面持久化）
  const executionPlan = ref<{ id: string; todos: AgentExecutionTodo[] } | null>(null)
  const executionTools = ref<AgentExecutionTool[]>([])
  const retryInfo = ref<null>(null)
  const commandStatus = ref<string | null>(null)
  const contextUsage = ref<ContextUsage | null>(null)
  const currentTask = ref<AgentCurrentTask | null>(null)
  const pendingWorkspaceProjectionRequests = ref<Array<{ runId?: string; surface: WorkspaceSurface; reason?: string }>>([])
  const recentWorkspaceToolOutputs = ref<Array<{ id: string; runId?: string; toolName: string; surface: WorkspaceSurface; payload: Record<string, unknown>; mode: 'readonly' }>>([])

  // 流式运行时状态全部从 store 读写（不再用闭包变量）
  // currentRunId / currentAbortController / typewriter 都在 store

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

  function isDefaultSessionTitle(title?: string): boolean {
    if (!title) return true
    return title === '新对话'
      || title.startsWith('Agent Session ')
      || /^日常对话\s*\d*$/.test(title)
      || /^项目管理\s*\d*$/.test(title)
  }

  function titleFromMessage(message: string): string {
    const normalized = message.replace(/\s+/g, ' ').trim()
    return normalized.length > 50 ? `${normalized.slice(0, 50)}…` : normalized
  }

  async function createSession(route?: AgentRouteContext | Event): Promise<void> {
    store.loading = true
    store.error = null
    try {
      const normalizedRoute = route instanceof Event ? undefined : route
      const session = await createAgentSession({ title: normalizedRoute?.title || '新对话' })
      store.sessions = [session, ...sessions.value.filter(item => item.id !== session.id)]
      store.setMessages(session.id, [])
      await selectSession(session)
    } finally {
      store.loading = false
    }
  }

  async function selectSession(session: AgentSession): Promise<void> {
    const selectingActiveRun = store.agentRunning && store.activeRunSessionId === session.id
    store.activeSessionId = session.id
    localStorage.setItem('aniforce.activeSessionId', session.id)
    store.loading = true
    store.error = null
    if (!selectingActiveRun && !store.agentRunning) {
      store.streamingMessage = null
      store.agentRunning = false
      executionPlan.value = null
      executionTools.value = []
      store.clearStreamRuntime()
      // 清理 Workspace projection 状态
      pendingWorkspaceProjectionRequests.value = []
      recentWorkspaceToolOutputs.value = []
    }
    try {
      if (!selectingActiveRun) {
        const snapshot = await getAgentSessionSnapshot(session.id)
        store.setMessages(session.id, snapshot.messages)
        restoreTimelineFromCache()
        restoreWorkspaceFromCache()
        hydrateWorkspaceSnapshot(workspace, session.id, snapshot)
        if (snapshot.latest_run && ['queued', 'resume_queued', 'running', 'cancel_requested'].includes(String(snapshot.latest_run.status))) {
          const runId = String(snapshot.latest_run.run_id)
          commandStatus.value = '任务正在后台执行'
          store.agentRunning = true
          store.agentPhase = { kind: 'waiting_model' }
          store.resetStreamRuntime(session.id, runId)
          store.currentRunLastSequence = snapshot.last_persisted_sequence
          const controller = new AbortController()
          store.setAbortController(controller)
          void connectPersistedRun(
            runId,
            snapshot.last_persisted_sequence,
            controller.signal,
          ).then(async result => {
            store.currentRunLastSequence = result.lastSequence
            const refreshed = await getAgentSessionSnapshot(session.id)
            store.setMessages(session.id, refreshed.messages)
            hydrateWorkspaceSnapshot(workspace, session.id, refreshed)
            store.agentRunning = false
            store.agentPhase = null
            store.streamingMessage = null
            store.clearStreamRuntime()
            commandStatus.value = null
          }).catch(err => {
            if (err?.name !== 'AbortError') store.error = err?.message || '恢复 Agent 任务连接失败'
          })
        }
      }
    } catch (err: any) {
      store.error = err?.message || '加载 Agent 会话失败'
    } finally {
      store.loading = false
    }
  }

  async function renameSession(sessionId: string, title: string): Promise<void> {
    const normalizedTitle = title.trim()
    if (!normalizedTitle) return
    const updated = await updateAgentSession(sessionId, { title: normalizedTitle })
    store.sessions = sessions.value.map(item => item.id === sessionId ? { ...item, title: updated.title } : item)
  }

  async function deleteSession(sessionId: string): Promise<void> {
    await deleteAgentSession(sessionId)
    store.sessions = sessions.value.filter(item => item.id !== sessionId)
    store.removeSessionCache(sessionId)
    if (store.activeSessionId === sessionId) {
      store.activeSessionId = null
      const nextSession = store.sessions[0]
      if (nextSession) await selectSession(nextSession)
      else await createSession()
    }
  }

  async function send(message: string, _images?: unknown, _route?: AgentRouteContext): Promise<void> {
    const text = message.trim()
    if (!text || store.agentRunning) return
    if (!activeSession.value) await createSession()
    if (!activeSession.value) return

    const perfStart = performance.now()
    let firstSseEventLogged = false
    let firstRuntimeStartedLogged = false
    let firstThinkingDeltaLogged = false
    let firstMessageDeltaLogged = false
    const perfMs = () => Math.round(performance.now() - perfStart)

    const sessionId = activeSession.value.id
    const shouldAutoTitle = isDefaultSessionTitle(activeSession.value.title) && messages.value.length === 0
    if (shouldAutoTitle) {
      const title = titleFromMessage(text)
      store.sessions = sessions.value.map(item => item.id === sessionId ? { ...item, title } : item)
      updateAgentSession(sessionId, { title }).catch(err => {
        console.warn('[agent] failed to auto-title session', err)
      })
    }
    store.error = null
    store.agentRunning = true
    store.agentPhase = { kind: 'waiting_model' }
    executionPlan.value = null
    executionTools.value = []
    pendingWorkspaceProjectionRequests.value = []
    recentWorkspaceToolOutputs.value = []
    // 初始用临时 runId，后续替换为 backend-owned run_id
    const tempRunId = `run_${Date.now()}`
    store.resetStreamRuntime(sessionId, tempRunId)
    store.getAbortController()?.abort()
    store.setAbortController(new AbortController())

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

    let streamCompletedSuccessfully = false
    let completedAssistantContent = ''

    try {
      const contextSnapshot = collectContextSnapshot(_route)
      console.info('[PERF][agent_first_token][frontend] send_start', {
        sessionId,
        promptChars: text.length,
        route: contextSnapshot.route,
      })
      const run = await startAgentRun(sessionId, text, _route?.task_type || 'conversation', contextSnapshot, store.getAbortController()?.signal)
      store.currentRunId = run.run_id
      store.currentRunLastSequence = 0
      for await (const event of streamAgentRunEvents(run.run_id, store.currentRunLastSequence, store.getAbortController()?.signal)) {
        const sequence = Number(event.data.sequence || 0)
        if (sequence > store.currentRunLastSequence) store.currentRunLastSequence = sequence
        if (!firstSseEventLogged) {
          firstSseEventLogged = true
          console.info('[PERF][agent_first_token][frontend] first_sse_event', {
            elapsedMs: perfMs(),
            event: event.event,
            sessionId,
          })
        }

        if (event.event === 'runtime.started') {
          store.currentRunId = run.run_id
          store.agentPhase = { kind: 'waiting_model' }
          if (!firstRuntimeStartedLogged) {
            firstRuntimeStartedLogged = true
            console.info('[PERF][agent_first_token][frontend] runtime_started', {
              elapsedMs: perfMs(),
              runId: store.currentRunId,
              taskId: event.data.task_id,
              sessionId,
            })
          }
        }

        if (event.event === 'raw_response_event' || event.event === 'run_item_stream_event' || event.event === 'agent_updated_stream_event') {
          handleSdkRawEvent(event.data as unknown as AgentSdkStreamEvent, sessionId, {
            assistant,
            perfMs,
            markFirstMessageDelta(deltaChars) {
              if (firstMessageDeltaLogged) return
              firstMessageDeltaLogged = true
              console.info('[PERF][agent_first_token][frontend] first_message_delta', {
                elapsedMs: perfMs(),
                runId: store.currentRunId,
                sessionId,
                deltaChars,
              })
            },
            markFirstThinkingDelta(deltaChars) {
              if (firstThinkingDeltaLogged) return
              firstThinkingDeltaLogged = true
              console.info('[PERF][agent_first_token][frontend] first_thinking_delta', {
                elapsedMs: perfMs(),
                runId: store.currentRunId,
                sessionId,
                deltaChars,
              })
            },
          })
        }

        if (event.event === 'side_effect') {
          handleSideEffect(event.data as unknown as SideEffectEvent, sessionId)
        }

        if (event.event === 'runtime.completed') {
          const finalOutput = event.data.final_output
          if (typeof finalOutput === 'string') completedAssistantContent = finalOutput
          const usage = event.data.usage
          if (usage && typeof usage === 'object') assistant.usage = usage as any
          markRunningToolsCompleted()
        }

        if (event.event === 'runtime.requires_action') {
          drainTypewriter(false)
          ensureAssistantMessage(assistant)
          const checkpointId = String(event.data.checkpoint_id || '')
          const runIdStr = String(event.data.run_id || run.run_id)
          const interruptions = Array.isArray(event.data.interruptions) ? event.data.interruptions as any : []
          // Workspace 投影：高风险工具产生可编辑审批草稿 + review projection
          const sessionId = activeSession.value?.id
          if (sessionId) {
            for (const interruption of interruptions) {
              const toolName = String(interruption?.tool_name || '')
              let originalArgs: Record<string, unknown> = {}
              const rawArgs = interruption?.arguments
              if (typeof rawArgs === 'string') {
                try { originalArgs = JSON.parse(rawArgs) } catch { originalArgs = { raw: rawArgs } }
              } else if (rawArgs && typeof rawArgs === 'object') {
                originalArgs = rawArgs as Record<string, unknown>
              }
              workspace.createApprovalDraft(checkpointId, runIdStr, toolName, 'approval.review', originalArgs)
              workspace.upsertProjection(sessionId, {
                id: `proj_approval_${checkpointId}`,
                sessionId,
                runId: runIdStr,
                surface: 'approval.review',
                sourceToolName: toolName,
                mode: 'review',
                payload: { originalArguments: originalArgs },
                approval: { runId: runIdStr, checkpointId, decisionStatus: 'pending' },
                updatedAt: Date.now(),
              })
            }
          }
          store.agentPhase = null
          // 重要：requires_action 时流已结束，必须清理 agentRunning，否则 resolveApproval 会 early return
          streamCompletedSuccessfully = true
        }

        if (event.event === 'runtime.error' || event.event === 'error') {
          throw new Error(String(event.data.message || 'Agent 流式响应错误'))
        }
      }
      streamCompletedSuccessfully = true
    } catch (err: any) {
      const aborted = err?.name === 'AbortError'
      if (aborted) {
        drainTypewriter()
        if (streamingMessage.value) {
          store.appendMessage(sessionId, { ...streamingMessage.value })
          store.streamingMessage = null
        }
      } else {
        store.error = err?.message || 'Agent 流式响应失败'
        if (streamingMessage.value && !hasMessageContent(streamingMessage.value)) {
          streamingMessage.value.content = '抱歉，Agent 流式响应失败，请稍后重试。'
        }
      }
    } finally {
      const finishSuccess = () => {
        drainTypewriter(false)
        if (completedAssistantContent && store.streamingMessage && !hasTextContent(store.streamingMessage)) {
          store.appendDeltaToStreaming('text', 'text', completedAssistantContent)
        }
        console.info('[PERF][agent_first_token][frontend] stream_completed', {
          elapsedMs: perfMs(),
          runId: store.currentRunId,
          sessionId,
          firstDeltaSeen: firstMessageDeltaLogged,
        })
        if (store.streamingMessage) {
          store.appendMessage(sessionId, { ...store.streamingMessage })
          store.streamingMessage = null
        }
      }
      const cleanup = () => {
        store.setAbortController(null)
        store.stopTypewriter()
        store.setTypewriterBuffer('')
        store.agentRunning = false
        store.agentPhase = null
        store.clearStreamRuntime()
        markRunningToolsCompleted()
      }
      if (store.isTypewriterPaused() && store.streamingMessage) {
        store.setDeferredStreamFinalizer(() => {
          if (streamCompletedSuccessfully) finishSuccess()
          cleanup()
        })
      } else {
        if (streamCompletedSuccessfully) finishSuccess()
        cleanup()
      }
    }
  }

  function collectContextSnapshot(routeContext?: AgentRouteContext): AgentContextSnapshot {
    const activePanel = routeContext?.workspace_type || new URLSearchParams(window.location.search).get('panel') || undefined
    const sessionId = activeSession.value?.id || ''
    return {
      route: route.fullPath,
      activePanel: isAgentPanel(activePanel) ? activePanel : undefined,
      activeProjectId: readRouteParam('projectId') || readRouteParam('id'),
      activeCampaignId: readRouteParam('campaignId'),
      selectedEntities: workspace.getSelectedEntities(sessionId),
      draftEdits: workspace.getDraftSummaries(sessionId),
      pendingApprovals: workspace.getPendingApprovalSummaries(sessionId),
      recentInteractions: workspace.getRecentInteractions(sessionId, 10).map(e => ({
        type: e.type,
        surface: e.surface,
        field: e.field,
        at: e.createdAt,
      })),
      workspaceProjection: summarizeWorkspaceProjection(sessionId),
    }
  }

  function summarizeWorkspaceProjection(sessionId: string): AgentContextSnapshot['workspaceProjection'] | undefined {
    const projection = workspace.getActiveProjection(sessionId)
    if (!projection) return undefined
    const payload = projection.payload || {}
    let itemCount: number | undefined
    if (Array.isArray(payload.projects)) itemCount = payload.projects.length
    else if (Array.isArray(payload.campaigns)) itemCount = payload.campaigns.length
    else if (Array.isArray(payload.materials)) itemCount = payload.materials.length
    return {
      surface: projection.surface,
      mode: projection.mode,
      sourceToolName: projection.sourceToolName,
      itemCount,
      alreadyVisible: projection.mode !== 'loading',
    }
  }

  function handleSideEffect(event: SideEffectEvent, targetSessionId = activeSession.value?.id): void {
    if (!targetSessionId) return
    store.recordSideEffect(targetSessionId, event)
    if (activeSession.value?.id === targetSessionId) {
      const panels = event.refresh_panels?.length ? event.refresh_panels.join(', ') : 'workspace'
      commandStatus.value = event.message || `业务数据已更新，待刷新：${panels}`
    }
  }

  function isAgentPanel(value: unknown): value is AgentContextSnapshot['activePanel'] {
    return value === 'context' || value === 'creative' || value === 'analysis' || value === 'budget' || value === 'audit'
  }

  function readRouteParam(key: string): string | null {
    const value = route.params[key]
    if (Array.isArray(value)) return value[0] || null
    return typeof value === 'string' ? value : null
  }

  async function abort(): Promise<void> {
    if (!store.agentRunning) return
    const sessionId = activeSession.value?.id
    const runId = store.currentRunId
    store.getAbortController()?.abort()
    if (runId) {
      await cancelAgentRun(runId).catch((err) => {
        console.warn('[agent] cancel run failed', err)
      })
    }
    drainTypewriter()
    if (streamingMessage.value) {
      if (sessionId && hasMessageContent(streamingMessage.value)) {
        store.appendMessage(sessionId, { ...streamingMessage.value })
      }
      store.streamingMessage = null
    }
    store.agentRunning = false
    store.agentPhase = null
    store.error = null
    store.clearStreamRuntime()
  }

  function changeModel(provider: string, modelId: string): void {
    store.selectedModel = { provider, modelId }
  }

  function normalizeRecord(value: unknown): Record<string, unknown> | undefined {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : undefined
  }

  function hasTextContent(message: AgentMessage): boolean {
    const content = message.content
    if (typeof content === 'string') return content.trim().length > 0
    if (!Array.isArray(content)) return false
    return content.some(block => block && typeof block === 'object' && block.type === 'text' && String(block.text || '').trim().length > 0)
  }

  function hasMessageContent(message: AgentMessage): boolean {
    const content = message.content
    if (typeof content === 'string') return content.trim().length > 0
    if (!Array.isArray(content)) return false
    return content.some(block => {
      if (!block || typeof block !== 'object') return false
      if (block.type === 'text') return String(block.text || '').trim().length > 0
      if (block.type === 'thinking') return String(block.thinking || '').trim().length > 0
      if (block.type === 'toolCall') return true
      if (block.type === 'approval') return true
      return false
    })
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
    store.upsertTimelineBlock(activeSession.value.id, block)
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
    if (!parentMessageId || !store.currentRunId) return
    if (!activeSession.value) return
    const sessionId = activeSession.value.id
    let changed = false
    const current = store.timelineBySession.get(sessionId) || []
    const updated = current.map(block => {
      if (block.parentMessageId || block.runId !== store.currentRunId) return block
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
      runId: input.existing?.runId || store.currentRunId || undefined,
      messageId: input.existing?.messageId || input.id,
      parentMessageId: input.existing?.parentMessageId || store.currentAssistantMessageId,
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
    if (action === 'open_in_workspace') {
      // Workspace 投影统一由 Agent 调用 request_workspace_projection 触发。
      return
    }
  }

  function handleSdkRawEvent(event: AgentSdkStreamEvent, sessionId: string, options: {
    assistant: AgentMessage
    perfMs: () => number
    markFirstMessageDelta: (deltaChars: number) => void
    markFirstThinkingDelta: (deltaChars: number) => void
  }): void {
    const parsed = parseAgentSdkEvent(event)
    if (parsed.kind === 'text') {
      ensureAssistantMessage(options.assistant)
      options.markFirstMessageDelta(parsed.delta.length)
      store.appendDeltaToStreaming('text', 'text', parsed.delta)
      return
    }
    if (parsed.kind === 'reasoning') {
      drainTypewriter(false)
      if (!streamingMessage.value) return
      ensureAssistantMessage(streamingMessage.value)
      options.markFirstThinkingDelta(parsed.delta.length)
      store.appendDeltaToStreaming('thinking', 'thinking', parsed.delta)
      return
    }
    if (parsed.kind === 'tool_called') {
      drainTypewriter(false)
      const { id, name, arguments: args } = parsed
      const tool: AgentExecutionTool = {
        id,
        name,
        status: 'running',
        arguments: args,
      }
      executionTools.value = [...executionTools.value, tool].slice(-8)
      store.appendToolCallToStreaming({ id, name, arguments: args })
      upsertTimelineTool({ id, toolName: name, status: 'running', arguments: args })
      store.agentPhase = {
        kind: 'running_tools',
        tools: executionTools.value
          .filter(item => item.status === 'running')
          .map(item => ({ id: item.id, name: item.name })),
      }
    } else if (parsed.kind === 'tool_output') {
      const { id, output: result } = parsed
      let toolName = ''
      const index = executionTools.value.findIndex(t => t.id === id)
      if (index >= 0) {
        toolName = executionTools.value[index].name
        executionTools.value[index] = {
          ...executionTools.value[index],
          status: 'completed',
          result,
        }
        executionTools.value = [...executionTools.value]
      }
      if (toolName) {
        if (id) store.updateToolCallResultInStreaming(id, result)
        upsertTimelineTool({ id: id || `${toolName}_${Date.now()}`, toolName, status: 'completed', result })
        appendBusinessResultBlock(id, toolName, result)
        const sessionId = activeSession.value?.id
        if (sessionId) {
          handleWorkspaceProjectionToolOutput(sessionId, id, toolName, result)
        }
      }
      const running = executionTools.value.filter(item => item.status === 'running')
      store.agentPhase = running.length
        ? { kind: 'running_tools', tools: running.map(item => ({ id: item.id, name: item.name })) }
        : { kind: 'waiting_model' }
    }
  }

  function ensureAssistantMessage(message: AgentMessage): void {
    if (store.currentAssistantMessageId) return
    message.id = `msg_${Date.now()}`
    store.currentAssistantMessageId = message.id
    attachCurrentRunTimelineBlocks(message.id)
  }

  function handleWorkspaceProjectionToolOutput(sessionId: string, toolCallId: string, toolName: string, result: unknown): void {
    if (toolName === 'request_workspace_projection') {
      const request = parseWorkspaceProjectionRequest(result)
      if (!request) return
      pendingWorkspaceProjectionRequests.value = [...pendingWorkspaceProjectionRequests.value, { runId: store.currentRunId || undefined, ...request }].slice(-8)
      projectRecentWorkspaceToolOutput(sessionId, request.surface)
      return
    }

    const config = workspaceResultProjectionRegistry[toolName]
    if (!config) return
    const payload = config.resultToPayload(result)
    recentWorkspaceToolOutputs.value = [
      ...recentWorkspaceToolOutputs.value,
      {
        id: toolCallId || `${toolName}_${Date.now()}`,
        runId: store.currentRunId || undefined,
        toolName,
        surface: config.surface,
        payload,
        mode: config.mode,
      },
    ].slice(-12)
    projectRecentWorkspaceToolOutput(sessionId, config.surface)
  }

  function parseWorkspaceProjectionRequest(result: unknown): { surface: WorkspaceSurface; reason?: string } | null {
    const parsed = typeof result === 'string' ? parseJsonString(result) : result
    const record = normalizeRecord(parsed)
    if (!record || record.accepted !== true || typeof record.surface !== 'string') return null
    if (!isWorkspaceSurface(record.surface)) return null
    return { surface: record.surface, reason: typeof record.reason === 'string' ? record.reason : undefined }
  }

  function parseJsonString(value: string): unknown {
    try {
      return JSON.parse(value)
    } catch {
      return null
    }
  }

  function isWorkspaceSurface(value: string): value is WorkspaceSurface {
    return value === 'project.list'
      || value === 'project.detail'
      || value === 'campaign.list'
      || value === 'campaign.detail'
      || value === 'campaign.materials'
      || value === 'material.list'
      || value === 'material.detail'
      || value === 'material.image'
  }

  function projectRecentWorkspaceToolOutput(sessionId: string, surface: WorkspaceSurface): void {
    const requestIndex = [...pendingWorkspaceProjectionRequests.value]
      .reverse()
      .findIndex(request => request.surface === surface && (!request.runId || request.runId === store.currentRunId))
    if (requestIndex < 0) return
    const output = [...recentWorkspaceToolOutputs.value]
      .reverse()
      .find(item => item.surface === surface && (!item.runId || item.runId === store.currentRunId))
    if (!output) return
    workspace.upsertProjection(sessionId, {
      id: `proj_${output.id}`,
      sessionId,
      runId: store.currentRunId || '',
      surface: output.surface,
      mode: output.mode,
      sourceToolName: output.toolName,
      sourceToolCallId: output.id,
      payload: output.payload,
      updatedAt: Date.now(),
    })
    const actualIndex = pendingWorkspaceProjectionRequests.value.length - 1 - requestIndex
    pendingWorkspaceProjectionRequests.value = pendingWorkspaceProjectionRequests.value.filter((_, index) => index !== actualIndex)
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

  function appendTextToStreamMessage(text: string): void {
    const msg = streamingMessage.value
    if (!msg || !text) return
    if (Array.isArray(msg.content)) {
      // 找最后一个 text block，或新建一个
      const blocks = msg.content as AgentContentBlock[]
      let last = blocks[blocks.length - 1]
      if (!last || typeof last !== 'object' || !('type' in last) || last.type !== 'text') {
        last = { type: 'text', text: '' }
        blocks.push(last)
      }
      ;(last as { type: 'text'; text: string }).text += text
      msg.content = [...blocks]
    } else {
      msg.content = `${typeof msg.content === 'string' ? msg.content : ''}${text}`
    }
  }

  function drainTypewriter(runDeferredFinalizer = true): void {
    const buffer = store.getTypewriterBuffer()
    if (buffer && streamingMessage.value) {
      appendTextToStreamMessage(buffer)
    }
    store.setTypewriterBuffer('')
    store.stopTypewriter()
    if (runDeferredFinalizer) store.runDeferredStreamFinalizer()
  }

  async function resolveApproval(
    runId: string,
    checkpointId: string,
    decision: 'approve' | 'reject',
    editedArguments?: Record<string, unknown>,
    argumentDiff?: Array<{ field: string; before: unknown; after: unknown }>,
  ): Promise<void> {
    if (!activeSession.value) return
    const sessionId = activeSession.value.id

    drainTypewriter(false)
    store.stopTypewriter()
    store.setTypewriterBuffer('')
    store.setDeferredStreamFinalizer(null)
    
    // 保存并清空当前流式消息（含审批卡片）
    if (store.streamingMessage && hasMessageContent(store.streamingMessage)) {
      store.appendMessage(sessionId, { ...store.streamingMessage })
    }
    store.streamingMessage = null
    
    store.agentRunning = true
    store.agentPhase = { kind: 'waiting_model' }
    store.updateApprovalStatus(checkpointId, decision === 'approve' ? 'approved' : 'rejected')
    workspace.setApprovalDraftStatus(checkpointId, decision === 'approve' ? 'executing' : 'rejected')
    if (decision === 'approve' && editedArguments) {
      workspace.recordInteraction(sessionId, {
        type: 'approval.confirmed',
        surface: workspace.getApprovalDraft(checkpointId)?.surface || '',
        field: checkpointId,
        after: editedArguments,
      })
    } else if (decision === 'reject') {
      workspace.recordInteraction(sessionId, {
        type: 'approval.rejected',
        surface: workspace.getApprovalDraft(checkpointId)?.surface || '',
        field: checkpointId,
      })
    }
    // Resume 流也必须绑定 activeRunSessionId，否则 streamingMessage computed 不会渲染。
    store.resetStreamRuntime(sessionId, runId)

    // 为 approval resume 创建独立的 AbortController
    const approvalAbortController = new AbortController()
    store.setAbortController(approvalAbortController)

    const assistant: AgentMessage = {
      id: `local_assistant_resume_${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      provider: selectedModel.value?.provider,
      model: selectedModel.value?.modelId,
    }
    store.streamingMessage = assistant
    let completedAssistantContent = ''
    try {
      for await (const event of resolveAgentRunApproval(runId, checkpointId, decision, undefined, approvalAbortController.signal, editedArguments, argumentDiff)) {
        // approval resume 流返回的是 SDK 原生事件，event.event 是 type（如 'tool_called'、'tool_output'）
        const eventType = event.event
        const raw = event.data as unknown as AgentSdkStreamEvent

        // SDK 原生事件：处理对话消息
        if (eventType === 'raw_response_event' || eventType === 'run_item_stream_event' || eventType === 'agent_updated_stream_event') {
          handleSdkRawEvent(raw, sessionId, {
            assistant,
            perfMs: () => 0,
            markFirstMessageDelta() {},
            markFirstThinkingDelta() {},
          })
        }

        // SDK 原生事件：处理 Workspace 投影
        if (eventType === 'tool_called' && raw.data?.tool_name) {
          const toolName = String(raw.data.tool_name)
          workspace.upsertProjection(sessionId, {
            id: `proj_approval_${checkpointId}`,
            runId,
            sessionId,
            surface: 'approval.review',
            mode: 'executing',
            sourceToolName: toolName,
            sourceToolCallId: String(raw.data.tool_call_id || ''),
            payload: (raw.data.arguments || {}) as Record<string, unknown>,
            approval: { runId, checkpointId, decisionStatus: 'approved' },
            updatedAt: Date.now(),
          })
          // 同时调用 handleSdkRawEvent 处理对话消息
          handleSdkRawEvent(raw, sessionId, {
            assistant,
            perfMs: () => 0,
            markFirstMessageDelta() {},
            markFirstThinkingDelta() {},
          })
        }

        if (eventType === 'tool_output' && raw.data?.tool_call_id) {
          const result = (raw.data.output || {}) as Record<string, unknown>
          workspace.setProjectionReady(sessionId, String(raw.data.tool_call_id), result, 'completed')
          // 同时调用 handleSdkRawEvent 处理对话消息
          handleSdkRawEvent(raw, sessionId, {
            assistant,
            perfMs: () => 0,
            markFirstMessageDelta() {},
            markFirstThinkingDelta() {},
          })
        }
        if (eventType === 'runtime.completed') {
          const finalOutput = event.data.final_output
          if (typeof finalOutput === 'string') completedAssistantContent = finalOutput
          const usage = event.data.usage
          if (usage && typeof usage === 'object') assistant.usage = usage as any
          markRunningToolsCompleted()
          // 标记当前 approval draft 为 completed
          workspace.setApprovalDraftStatus(checkpointId, 'completed')
        }
        if (event.event === 'runtime.requires_action') {
          drainTypewriter(false)
          ensureAssistantMessage(assistant)
        }
        if (event.event === 'runtime.error' || event.event === 'error') {
          throw new Error(String(event.data.message || '审批恢复失败'))
        }
      }
      drainTypewriter(false)
      if (completedAssistantContent && store.streamingMessage && !hasTextContent(store.streamingMessage)) {
        store.appendDeltaToStreaming('text', 'text', completedAssistantContent)
      }
      if (store.streamingMessage) {
        if (hasMessageContent(store.streamingMessage)) store.appendMessage(sessionId, { ...store.streamingMessage })
        store.streamingMessage = null
      }
      workspace.setApprovalDraftStatus(checkpointId, decision === 'approve' ? 'completed' : 'rejected')
    } catch (err: any) {
      store.error = err?.message || '审批恢复失败'
      store.updateApprovalStatus(checkpointId, 'pending')
      workspace.setApprovalDraftStatus(checkpointId, decision === 'approve' ? 'pending' : 'rejected')
    } finally {
      store.agentRunning = false
      store.agentPhase = null
      store.clearStreamRuntime()
      markRunningToolsCompleted()
    }
  }

  // 注意：不再在 onUnmounted 里 abort。
  // 流式状态现在在 store，切页面不丢；用户主动点“停止”才取消。

  // Workspace 投影状态
  const workspaceProjection = computed(() => {
    const sessionId = activeSession.value?.id || ''
    return workspace.getActiveProjection(sessionId)
  })
  const workspaceSelectedEntities = computed(() => {
    const sessionId = activeSession.value?.id
    return sessionId ? workspace.getSelectedEntities(sessionId) : []
  })

  const workspaceApprovalDraft = computed(() => {
    const projection = workspaceProjection.value
    if (projection?.approval) {
      return workspace.getApprovalDraft(projection.approval.checkpointId) || null
    }
    const drafts = Array.from(workspace.approvalDrafts.values())
    return drafts.find(draft => draft.status === 'pending' || draft.status === 'executing')
      || drafts.find(draft => draft.status === 'completed')
      || null
  })

  function updateApprovalDraftForm(checkpointId: string, formModel: import('@/components/projects/projectFormModel').ProjectFormModel): void {
    workspace.updateApprovalDraftForm(checkpointId, formModel)
  }

  function resolveWorkspaceApproval(payload: {
    checkpointId: string
    runId: string
    editedArguments: Record<string, unknown>
    argumentDiff: Array<{ field: string; before: unknown; after: unknown }>
  }): Promise<void> {
    return resolveApproval(payload.runId, payload.checkpointId, 'approve', payload.editedArguments, payload.argumentDiff)
  }

  function rejectWorkspaceApproval(checkpointId: string, runId: string): Promise<void> {
    return resolveApproval(runId, checkpointId, 'reject')
  }

  function selectWorkspaceEntity(entity: { type: 'project' | 'campaign' | 'material'; id: string; name?: string }): void {
    const sessionId = activeSession.value?.id
    if (!sessionId) return
    workspace.selectEntity(sessionId, entity)
  }

  function unselectWorkspaceEntity(entity: { type: 'project' | 'campaign' | 'material'; id: string; name?: string }): void {
    const sessionId = activeSession.value?.id
    if (!sessionId) return
    workspace.unselectEntity(sessionId, entity)
  }

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
    workspaceProjection,
    workspaceSelectedEntities,
    workspaceApprovalDraft,
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
    resolveApproval,
    resolveWorkspaceApproval,
    rejectWorkspaceApproval,
    updateApprovalDraftForm,
    selectWorkspaceEntity,
    unselectWorkspaceEntity,
    abort,
    pauseTypewriter: store.pauseTypewriter,
    resumeTypewriter: store.resumeTypewriter,
    changeModel,
    handleTimelineAction,
  }
}
