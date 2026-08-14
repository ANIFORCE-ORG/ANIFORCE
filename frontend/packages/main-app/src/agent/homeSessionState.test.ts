import { describe, expect, it } from 'vitest'

import { resolveHomeSessionState, shouldApplyHomeSessionState } from './homeSessionState'

const sessionIds = ['session-a', 'session-b']

describe('home session state', () => {
  it('never intercepts navigation away from Home', () => {
    expect(shouldApplyHomeSessionState('/home')).toBe(true)
    expect(shouldApplyHomeSessionState('/material')).toBe(false)
    expect(shouldApplyHomeSessionState('/projects/project-1')).toBe(false)
  })

  it('selects the session named by a valid route', () => {
    expect(resolveHomeSessionState('session-b', sessionIds, 'session-a')).toEqual({
      kind: 'session',
      sessionId: 'session-b',
      syncRoute: false,
    })
  })

  it('restores the persisted active session when the route has no session', () => {
    expect(resolveHomeSessionState('', sessionIds, 'session-a')).toEqual({
      kind: 'session',
      sessionId: 'session-a',
      syncRoute: true,
    })
  })

  it('opens an explicit draft for an invalid route session', () => {
    expect(resolveHomeSessionState('missing', sessionIds, 'session-a')).toEqual({
      kind: 'draft',
      clearRoute: true,
    })
  })

  it('opens a draft when there is no restorable session', () => {
    expect(resolveHomeSessionState('', sessionIds, null)).toEqual({
      kind: 'draft',
      clearRoute: false,
    })
  })
})
