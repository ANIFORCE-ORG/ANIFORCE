import { describe, expect, it, vi } from 'vitest'

import {
  setCompatibleCommandStatus,
  setCompatibleCurrentTask,
  setCompatibleError,
} from './agentStoreCompatibility'

describe('agent store HMR compatibility', () => {
  it('does not crash when a legacy store lacks new session actions', () => {
    const legacyStore: Record<string, unknown> = { error: null }
    const taskFallback = new Map<string, unknown>()
    const commandFallback = new Map<string, string | null>()

    expect(() => setCompatibleCurrentTask(legacyStore, taskFallback, 'session-a', { id: 'task-a' })).not.toThrow()
    expect(() => setCompatibleCommandStatus(legacyStore, commandFallback, 'session-a', 'running')).not.toThrow()
    expect(() => setCompatibleError(legacyStore, 'session-a', 'failed')).not.toThrow()

    expect(taskFallback.get('session-a')).toEqual({ id: 'task-a' })
    expect(commandFallback.get('session-a')).toBe('running')
    expect(legacyStore.error).toBe('failed')
  })

  it('uses current store actions when they are available', () => {
    const store = {
      setCurrentTask: vi.fn(),
      setCommandStatus: vi.fn(),
      setError: vi.fn(),
    }

    setCompatibleCurrentTask(store, new Map(), 'session-a', { id: 'task-a' })
    setCompatibleCommandStatus(store, new Map(), 'session-a', 'running')
    setCompatibleError(store, 'session-a', 'failed')

    expect(store.setCurrentTask).toHaveBeenCalledWith('session-a', { id: 'task-a' })
    expect(store.setCommandStatus).toHaveBeenCalledWith('session-a', 'running')
    expect(store.setError).toHaveBeenCalledWith('session-a', 'failed')
  })
})
