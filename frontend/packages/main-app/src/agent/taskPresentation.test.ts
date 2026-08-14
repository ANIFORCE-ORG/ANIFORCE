import { describe, expect, it } from 'vitest'

import { normalizeTaskPanelStatus, taskStatusPresentation } from './taskPresentation'

describe('task presentation', () => {
  it.each([
    ['created', 'created'],
    ['running', 'running'],
    ['waiting_user_input', 'waiting_user_input'],
    ['waiting_approval', 'waiting_approval'],
    ['applying', 'applying'],
    ['completed', 'completed'],
    ['failed', 'failed'],
    ['canceled', 'canceled'],
  ] as const)('preserves persisted status %s', (persisted, expected) => {
    expect(normalizeTaskPanelStatus(persisted)).toBe(expected)
  })

  it('falls back to running for an unknown active status', () => {
    expect(normalizeTaskPanelStatus('dispatching')).toBe('running')
  })

  it('presents approval as a user-visible waiting state', () => {
    expect(taskStatusPresentation.waiting_approval).toEqual({
      label: '等待确认',
      icon: 'approval_delegation',
    })
  })
})
