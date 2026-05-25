import { computed, ref } from 'vue'

export interface WorkspaceSession {
  id: string
  name: string
  active: boolean
}

const STORAGE_KEY = 'aniforce_agent_sessions'

const defaultSessions: WorkspaceSession[] = [
  { id: 'agent-onboarding', name: '首次广告配置', active: true },
  { id: 'agent-performance', name: '投放表现复盘', active: false },
  { id: 'agent-creative', name: '素材优化建议', active: false },
  { id: 'agent-account', name: '广告账户授权', active: false },
]

function loadSessions() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return JSON.parse(stored) as WorkspaceSession[]
  } catch {
    // Fall back to defaults if local storage is unavailable or corrupted.
  }
  return [...defaultSessions]
}

const agentSessions = ref<WorkspaceSession[]>(loadSessions())

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(agentSessions.value))
}

export function useWorkspaceSessions(_panelId?: string) {
  const sessions = computed(() => agentSessions.value)
  const activeSessionId = computed(() =>
    sessions.value.find(session => session.active)?.id || sessions.value[0]?.id || 'agent-onboarding'
  )

  const switchSession = (session: WorkspaceSession) => {
    agentSessions.value = sessions.value.map(item => ({
      ...item,
      active: item.id === session.id,
    }))
    persist()
  }

  return {
    sessions,
    activeSessionId,
    switchSession,
  }
}
