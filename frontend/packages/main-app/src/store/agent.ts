import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentSession, AgentMessage, AgentModel, SideEffectEvent } from '@/api/agent'
import type { AgentTimelineBlock, AgentPhase } from '@/composables/useHomeAgentSession'

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
  const error = ref<string | null>(null)
  const agentRunning = ref(false)
  const agentPhase = ref<AgentPhase>(null)
  const streamingMessage = ref<AgentMessage | null>(null)
  
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
      const timelineKey = `aniforce_timeline_${sessionId}`
      const workspaceKey = `aniforce_workspace_${sessionId}`
      
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
  
  // Actions
  function setMessages(sessionId: string, msgs: AgentMessage[]): void {
    messagesBySession.value.set(sessionId, msgs)
  }
  
  function appendMessage(sessionId: string, msg: AgentMessage): void {
    const current = messagesBySession.value.get(sessionId) || []
    messagesBySession.value.set(sessionId, [...current, msg])
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
    error,
    agentRunning,
    agentPhase,
    streamingMessage,
    
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
    setMessages,
    appendMessage,
    upsertActivityMessage,  // AG-UI: activity 消息插入/更新
    upsertTimelineBlock,
    setWorkspace,
    recordSideEffect,
    clearStalePanel,
  }
})
