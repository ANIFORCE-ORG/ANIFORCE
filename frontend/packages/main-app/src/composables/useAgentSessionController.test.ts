import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { getAgentSessionSnapshot } = vi.hoisted(() => ({
  getAgentSessionSnapshot: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/home?session_id=session-a', params: {} }),
}))

vi.mock('@/api/agent', async importOriginal => {
  const original = await importOriginal<typeof import('@/api/agent')>()
  return { ...original, getAgentSessionSnapshot }
})

import { useAgentSessionController } from './useAgentSessionController'
import { useAgentStore } from '@/store/agent'

describe('agent session controller run isolation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getAgentSessionSnapshot.mockReset()
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
  })

  it('does not replace live state when selecting the session that owns the active run', async () => {
    const store = useAgentStore()
    const session = { id: 'session-a', title: 'A' } as typeof store.sessions[number]
    store.sessions = [session]
    store.activeSessionId = 'session-a'
    store.setMessages('session-a', [{ id: 'live-message', role: 'assistant', content: 'live' } as any])
    store.agentRunning = true
    store.resetStreamRuntime('session-a', 'run-a')
    getAgentSessionSnapshot.mockResolvedValue({ messages: [] })

    const controller = useAgentSessionController()
    await controller.selectSession(session)

    expect(getAgentSessionSnapshot).not.toHaveBeenCalled()
    expect(store.messages.map(message => message.id)).toEqual(['live-message'])
  })
})
