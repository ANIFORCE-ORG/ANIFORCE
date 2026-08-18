import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentSession, AgentMessage, AgentModel, AgentContentBlock, SideEffectEvent } from '@/api/agent'
import type { AgentCurrentTask, AgentTimelineBlock, AgentPhase } from '@/composables/useAgentSessionController'

export const useAgentStore = defineStore('agent', () => {
  // 核心状态 - 使用 ref 而不是 reactive，确保可以直接赋值
  const sessions = ref<AgentSession[]>([])
  const activeSessionId = ref<string | null>(null)
  const messagesBySession = ref<Map<string, AgentMessage[]>>(new Map())
  const timelineBySession = ref<Map<string, AgentTimelineBlock[]>>(new Map())
  const workspaceBySession = ref<Map<string, Array<{ id: string; name: string; result?: unknown }>>>(new Map())
  const sideEffectsBySession = ref<Map<string, SideEffectEvent[]>>(new Map())
  const stalePanelsBySession = ref<Map<string, Set<string>>>(new Map())
  
  // UI 状态
  const models = ref<AgentModel[]>([])
  const selectedModel = ref<{ provider: string; modelId: string } | null>(null)
  const loading = ref(false)
  const errorsBySession = ref<Map<string, string | null>>(new Map())
  const commandStatusBySession = ref<Map<string, string | null>>(new Map())
  const currentTaskBySession = ref<Map<string, AgentCurrentTask | null>>(new Map())
  const unscopedError = ref<string | null>(null)
  const error = computed(() => activeSessionId.value
    ? errorsBySession.value.get(activeSessionId.value) || null
    : unscopedError.value)
  const commandStatus = computed(() => activeSessionId.value
    ? commandStatusBySession.value.get(activeSessionId.value) || null
    : null)
  const currentTask = computed(() => activeSessionId.value
    ? currentTaskBySession.value.get(activeSessionId.value) || null
    : null)
  const agentRunning = ref(false)
  const agentPhase = ref<AgentPhase>(null)
  const streamingMessage = ref<AgentMessage | null>(null)

  // 流式运行时状态（全局唯一，不随页面组件销毁）
  const activeRunSessionId = ref<string | null>(null) // 当前正在运行的 session，保证只有一条流
  const currentRunId = ref<string | null>(null) // 真实 task_id（runtime.started 后才有值）
  const currentRunLastSequence = ref(0)
  const currentAssistantMessageId = ref<string | undefined>(undefined)
  const executionTools = ref<Array<{ id: string; name: string; status: 'running' | 'completed' | 'error'; arguments?: Record<string, unknown>; result?: unknown }>>([])
  let currentAbortController: AbortController | null = null
  let typewriterTimer: number | null = null
  let typewriterTick: (() => void) | null = null
  let typewriterBuffer = ''
  let typewriterPaused = false
  let deferredStreamFinalizer: (() => void) | null = null
  
  // 计算属性
  const activeSession = computed(() => {
    if (!activeSessionId.value) return null
    return sessions.value.find(s => s.id === activeSessionId.value) || null
  })
  
  const messages = computed(() => {
    if (!activeSessionId.value) return []
    return messagesBySession.value.get(activeSessionId.value) || []
  })
  
  const timelineBlocks = computed(() => {
    if (!activeSessionId.value) return []
    return timelineBySession.value.get(activeSessionId.value) || []
  })
  
  const workspaceToolResults = computed(() => {
    if (!activeSessionId.value) return []
    return workspaceBySession.value.get(activeSessionId.value) || []
  })

  const sideEffects = computed(() => {
    if (!activeSessionId.value) return []
    return sideEffectsBySession.value.get(activeSessionId.value) || []
  })

  const stalePanels = computed(() => {
    if (!activeSessionId.value) return []
    return Array.from(stalePanelsBySession.value.get(activeSessionId.value) || new Set())
  })
  
  // 持久化
  function restoreFromLocalStorage(sessionId: string): void {
    try {
      const messagesKey = `aniforce_messages_${sessionId}`
      const timelineKey = `aniforce_timeline_${sessionId}`
      const workspaceKey = `aniforce_workspace_${sessionId}`

      const cachedMessages = localStorage.getItem(messagesKey)
      if (cachedMessages) {
        const parsedMessages = JSON.parse(cachedMessages)
        if (Array.isArray(parsedMessages)) messagesBySession.value.set(sessionId, parsedMessages)
      }
      
      const cachedTimeline = localStorage.getItem(timelineKey)
      if (cachedTimeline) {
        timelineBySession.value.set(sessionId, JSON.parse(cachedTimeline))
      }
      
      const cachedWorkspace = localStorage.getItem(workspaceKey)
      if (cachedWorkspace) {
        workspaceBySession.value.set(sessionId, JSON.parse(cachedWorkspace))
      }
    } catch (e) {
      console.warn('[agent-store] restore failed', e)
    }
  }
  
  function persistToLocalStorage(sessionId: string): void {
    try {
      const messages = messagesBySession.value.get(sessionId)
      if (messages && messages.length) {
        localStorage.setItem(`aniforce_messages_${sessionId}`, JSON.stringify(messages))
      }

      const timeline = timelineBySession.value.get(sessionId)
      if (timeline && timeline.length) {
        localStorage.setItem(`aniforce_timeline_${sessionId}`, JSON.stringify(timeline))
      }
      
      const workspace = workspaceBySession.value.get(sessionId)
      if (workspace && workspace.length) {
        localStorage.setItem(`aniforce_workspace_${sessionId}`, JSON.stringify(workspace))
      }
    } catch (e) {
      console.warn('[agent-store] persist failed', e)
    }
  }

  function removeSessionCache(sessionId: string): void {
    messagesBySession.value.delete(sessionId)
    timelineBySession.value.delete(sessionId)
    workspaceBySession.value.delete(sessionId)
    sideEffectsBySession.value.delete(sessionId)
    stalePanelsBySession.value.delete(sessionId)
    errorsBySession.value.delete(sessionId)
    commandStatusBySession.value.delete(sessionId)
    currentTaskBySession.value.delete(sessionId)
    localStorage.removeItem(`aniforce_messages_${sessionId}`)
    localStorage.removeItem(`aniforce_timeline_${sessionId}`)
    localStorage.removeItem(`aniforce_workspace_${sessionId}`)
  }
  
  // Actions
  function setError(sessionId: string | null, message: string | null): void {
    if (sessionId) errorsBySession.value.set(sessionId, message)
    else unscopedError.value = message
  }

  function setCommandStatus(sessionId: string, status: string | null): void {
    commandStatusBySession.value.set(sessionId, status)
  }

  function setCurrentTask(sessionId: string, task: AgentCurrentTask | null): void {
    currentTaskBySession.value.set(sessionId, task)
  }

  function setMessages(sessionId: string, msgs: AgentMessage[]): void {
    messagesBySession.value.set(sessionId, msgs)
    persistToLocalStorage(sessionId)
  }
  
  function appendMessage(sessionId: string, msg: AgentMessage): void {
    const current = messagesBySession.value.get(sessionId) || []
    messagesBySession.value.set(sessionId, [...current, msg])
    persistToLocalStorage(sessionId)
  }
  
  // AG-UI: 插入或更新 activity 消息
  function upsertActivityMessage(sessionId: string, msg: AgentMessage): void {
    const current = messagesBySession.value.get(sessionId) || []
    const index = current.findIndex(m => m.id === msg.id)
    if (index >= 0) {
      // 更新现有 activity（例如 running → completed）
      current[index] = msg
      messagesBySession.value.set(sessionId, [...current])
    } else {
      // 插入新 activity
      messagesBySession.value.set(sessionId, [...current, msg])
    }
    persistToLocalStorage(sessionId)
  }
  
  function upsertTimelineBlock(sessionId: string, block: AgentTimelineBlock): void {
    const current = timelineBySession.value.get(sessionId) || []
    const index = current.findIndex(b => b.id === block.id)
    if (index >= 0) {
      current[index] = block
      timelineBySession.value.set(sessionId, [...current])
    } else {
      timelineBySession.value.set(sessionId, [...current, block])
    }
    persistToLocalStorage(sessionId)
  }
  
  function setWorkspace(sessionId: string, results: Array<{ id: string; name: string; result?: unknown }>): void {
    workspaceBySession.value.set(sessionId, results)
    persistToLocalStorage(sessionId)
  }

  function recordSideEffect(sessionId: string, event: SideEffectEvent): void {
    const current = sideEffectsBySession.value.get(sessionId) || []
    sideEffectsBySession.value.set(sessionId, [...current, event].slice(-100))
    const panels = stalePanelsBySession.value.get(sessionId) || new Set<string>()
    for (const panel of event.refresh_panels || []) panels.add(String(panel))
    stalePanelsBySession.value.set(sessionId, panels)
  }

  function clearStalePanel(sessionId: string, panel: string): void {
    const panels = stalePanelsBySession.value.get(sessionId)
    if (!panels) return
    panels.delete(panel)
    stalePanelsBySession.value.set(sessionId, new Set(panels))
  }

  // ==================== 流式运行时操作 ====================
  // 这些状态在 store 层管理，保证页面切换不会丢失或重复创建

  function getAbortController(): AbortController | null {
    return currentAbortController
  }

  function setAbortController(controller: AbortController | null): void {
    currentAbortController = controller
  }

  function resetStreamRuntime(sessionId: string, runId: string): void {
    activeRunSessionId.value = sessionId
    currentRunId.value = runId
    currentRunLastSequence.value = 0
    currentAssistantMessageId.value = undefined
    typewriterBuffer = ''
    stopTypewriter()
  }

  function clearStreamRuntime(): void {
    activeRunSessionId.value = null
    currentRunId.value = null
    currentRunLastSequence.value = 0
    currentAssistantMessageId.value = undefined
    typewriterBuffer = ''
    typewriterTick = null
    typewriterPaused = false
    deferredStreamFinalizer = null
    stopTypewriter()
    currentAbortController = null
  }

  // Typewriter 控制（全局唯一 timer）
  function setTypewriterTick(tick: () => void): void {
    typewriterTick = tick
    if (typewriterTimer || typewriterPaused) return
    typewriterTimer = window.setInterval(tick, 24)
  }

  function stopTypewriter(): void {
    if (typewriterTimer) window.clearInterval(typewriterTimer)
    typewriterTimer = null
  }

  function pauseTypewriter(): void {
    typewriterPaused = true
    stopTypewriter()
  }

  function resumeTypewriter(): void {
    typewriterPaused = false
    if (!typewriterTimer && typewriterTick && typewriterBuffer) {
      typewriterTimer = window.setInterval(typewriterTick, 24)
      return
    }
    if (!typewriterBuffer && deferredStreamFinalizer) {
      const finalize = deferredStreamFinalizer
      deferredStreamFinalizer = null
      finalize()
    }
  }

  function isTypewriterPaused(): boolean {
    return typewriterPaused
  }

  function getTypewriterBuffer(): string {
    return typewriterBuffer
  }

  function setTypewriterBuffer(buffer: string): void {
    typewriterBuffer = buffer
  }

  function appendTypewriterBuffer(delta: string): void {
    typewriterBuffer += delta
  }

  function hasTypewriterTimer(): boolean {
    return typewriterTimer !== null
  }

  function setDeferredStreamFinalizer(finalizer: (() => void) | null): void {
    deferredStreamFinalizer = finalizer
  }

  function runDeferredStreamFinalizer(): void {
    if (!deferredStreamFinalizer || typewriterPaused || typewriterBuffer) return
    const finalize = deferredStreamFinalizer
    deferredStreamFinalizer = null
    finalize()
  }

  function ensureStreamingContentBlocks(): AgentContentBlock[] | null {
    const msg = streamingMessage.value
    if (!msg) return null
    if (Array.isArray(msg.content)) return msg.content as AgentContentBlock[]
    const existingText = typeof msg.content === 'string' ? msg.content : ''
    const blocks: AgentContentBlock[] = existingText ? [{ type: 'text', text: existingText }] : []
    msg.content = blocks
    return blocks
  }

  // streamingMessage content 操作（统一入口，避免多处直接改）
  function appendDeltaToStreaming(blockType: 'text' | 'thinking', field: 'text' | 'thinking', delta: string): void {
    const msg = streamingMessage.value
    if (!msg || !delta) return
    const blocks = ensureStreamingContentBlocks()
    if (!blocks) return
    // 累积到最后一个同类型 block（不是第一个！修复多轮 thinking 的 bug）
    let last = blocks[blocks.length - 1]
    if (!last || typeof last !== 'object' || !('type' in last) || last.type !== blockType) {
      last = { type: blockType, [field]: '' } as AgentContentBlock
      blocks.push(last)
    }
    ;(last as Record<string, unknown>)[field] = String((last as Record<string, unknown>)[field] || '') + delta
    msg.content = [...blocks]
  }

  function appendToolCallToStreaming(tool: { id: string; name: string; arguments?: Record<string, unknown>; result?: unknown }): void {
    const msg = streamingMessage.value
    if (!msg) return
    const blocks = ensureStreamingContentBlocks()
    if (!blocks) return
    const existing = blocks.find(
      (b): b is Record<string, unknown> => b && typeof b === 'object' && b.type === 'toolCall' && (b.toolCallId === tool.id || b.id === tool.id)
    )
    if (existing) {
      existing.result = tool.result
      existing.toolName = existing.toolName || tool.name
      existing.input = existing.input || tool.arguments || {}
    } else {
      blocks.push({
        type: 'toolCall',
        toolCallId: tool.id,
        toolName: tool.name,
        input: tool.arguments || {},
        result: tool.result,
      } as AgentContentBlock)
    }
    msg.content = [...blocks]
  }

  function appendApprovalToStreaming(approval: { runId: string; checkpointId: string; interruptions?: Array<Record<string, unknown>> }): void {
    const msg = streamingMessage.value
    if (!msg) return
    const blocks = ensureStreamingContentBlocks()
    if (!blocks) return
    const existing = blocks.find(
      (b): b is Record<string, unknown> => b && typeof b === 'object' && b.type === 'approval' && b.checkpointId === approval.checkpointId
    )
    if (existing) {
      existing.status = 'pending'
      existing.interruptions = approval.interruptions || []
    } else {
      blocks.push({
        type: 'approval',
        runId: approval.runId,
        checkpointId: approval.checkpointId,
        status: 'pending',
        interruptions: approval.interruptions || [],
      } as AgentContentBlock)
    }
    msg.content = [...blocks]
  }

  function updateApprovalStatus(checkpointId: string, status: 'pending' | 'approved' | 'rejected' | 'running'): void {
    const allMessages = [...messagesBySession.value.values()].flat()
    const candidates = streamingMessage.value ? [streamingMessage.value, ...allMessages] : allMessages
    for (const msg of candidates) {
      if (!Array.isArray(msg.content)) continue
      let changed = false
      for (const block of msg.content as AgentContentBlock[]) {
        if (block && typeof block === 'object' && block.type === 'approval' && block.checkpointId === checkpointId) {
          ;(block as Record<string, unknown>).status = status
          changed = true
        }
      }
      if (changed) msg.content = [...(msg.content as AgentContentBlock[])]
    }
  }

  function updateToolCallResultInStreaming(toolId: string, result: unknown): void {
    const msg = streamingMessage.value
    if (!msg || !Array.isArray(msg.content)) return
    const blocks = msg.content as AgentContentBlock[]
    let changed = false
    for (const block of blocks) {
      if (block && typeof block === 'object' && block.type === 'toolCall' && (block.toolCallId === toolId || block.id === toolId)) {
        ;(block as Record<string, unknown>).result = result
        changed = true
        break
      }
    }
    if (changed) msg.content = [...blocks]
  }
  
  return {
    // State (直接暴露 ref，外部可以直接修改)
    sessions,
    activeSessionId,
    messagesBySession,
    timelineBySession,
    workspaceBySession,
    sideEffectsBySession,
    stalePanelsBySession,
    models,
    selectedModel,
    loading,
    errorsBySession,
    commandStatusBySession,
    currentTaskBySession,
    error,
    commandStatus,
    currentTask,
    agentRunning,
    agentPhase,
    streamingMessage,
    activeRunSessionId,
    currentRunId,
    currentRunLastSequence,
    currentAssistantMessageId,
    executionTools,
    
    // Computed
    activeSession,
    messages,
    timelineBlocks,
    workspaceToolResults,
    sideEffects,
    stalePanels,
    
    // Actions
    restoreFromLocalStorage,
    persistToLocalStorage,
    removeSessionCache,
    setError,
    setCommandStatus,
    setCurrentTask,
    setMessages,
    appendMessage,
    upsertActivityMessage,  // AG-UI: activity 消息插入/更新
    upsertTimelineBlock,
    setWorkspace,
    recordSideEffect,
    clearStalePanel,
    // 流式运行时
    getAbortController,
    setAbortController,
    resetStreamRuntime,
    clearStreamRuntime,
    setTypewriterTick,
    stopTypewriter,
    pauseTypewriter,
    resumeTypewriter,
    isTypewriterPaused,
    getTypewriterBuffer,
    setTypewriterBuffer,
    appendTypewriterBuffer,
    hasTypewriterTimer,
    setDeferredStreamFinalizer,
    runDeferredStreamFinalizer,
    appendDeltaToStreaming,
    appendToolCallToStreaming,
    appendApprovalToStreaming,
    updateApprovalStatus,
    updateToolCallResultInStreaming,
  }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAgentStore, import.meta.hot))
}
