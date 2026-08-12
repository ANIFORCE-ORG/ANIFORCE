import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAgentStore } from './agent'

describe('agent store session errors', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows only the active session error', () => {
    const store = useAgentStore()
    store.sessions = [
      { id: 'session-a', title: 'A' },
      { id: 'session-b', title: 'B' },
    ] as typeof store.sessions

    store.setError('session-a', 'A failed')
    store.setError('session-b', 'B failed')

    store.activeSessionId = 'session-a'
    expect(store.error).toBe('A failed')

    store.activeSessionId = 'session-b'
    expect(store.error).toBe('B failed')

    store.activeSessionId = null
    expect(store.error).toBeNull()
  })

  it('keeps task and recovery status scoped across controller instances', () => {
    const store = useAgentStore()
    store.sessions = [
      { id: 'session-a', title: 'A' },
      { id: 'session-b', title: 'B' },
    ] as typeof store.sessions
    store.setCurrentTask('session-a', { id: 'task-a', session_id: 'session-a', title: 'Task A', status: 'running' })
    store.setCurrentTask('session-b', { id: 'task-b', session_id: 'session-b', title: 'Task B', status: 'completed' })
    store.setCommandStatus('session-a', '任务正在后台执行')

    store.activeSessionId = 'session-a'
    expect(store.currentTask?.id).toBe('task-a')
    expect(store.commandStatus).toBe('任务正在后台执行')

    store.activeSessionId = 'session-b'
    expect(store.currentTask?.id).toBe('task-b')
    expect(store.commandStatus).toBeNull()
  })
})
