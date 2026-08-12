export function shouldApplyHomeSessionState(routePath: string): boolean {
  return routePath === '/home'
}

export type HomeSessionState =
  | { kind: 'session'; sessionId: string; syncRoute: boolean }
  | { kind: 'draft'; clearRoute: boolean }

export function resolveHomeSessionState(
  routeSessionId: string,
  sessionIds: string[],
  persistedSessionId: string | null,
): HomeSessionState {
  if (routeSessionId) {
    return sessionIds.includes(routeSessionId)
      ? { kind: 'session', sessionId: routeSessionId, syncRoute: false }
      : { kind: 'draft', clearRoute: true }
  }
  if (persistedSessionId && sessionIds.includes(persistedSessionId)) {
    return { kind: 'session', sessionId: persistedSessionId, syncRoute: true }
  }
  return { kind: 'draft', clearRoute: false }
}
