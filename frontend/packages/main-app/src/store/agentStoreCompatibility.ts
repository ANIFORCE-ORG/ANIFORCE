type CompatibilityStore = Record<string, any>

export function setCompatibleCurrentTask<T>(
  store: CompatibilityStore,
  fallback: Map<string, T | null>,
  sessionId: string,
  task: T | null,
): void {
  if (typeof store.setCurrentTask === 'function') {
    store.setCurrentTask(sessionId, task)
    return
  }
  fallback.set(sessionId, task)
}

export function setCompatibleCommandStatus(
  store: CompatibilityStore,
  fallback: Map<string, string | null>,
  sessionId: string,
  status: string | null,
): void {
  if (typeof store.setCommandStatus === 'function') {
    store.setCommandStatus(sessionId, status)
    return
  }
  fallback.set(sessionId, status)
}

export function setCompatibleError(
  store: CompatibilityStore,
  sessionId: string | null,
  message: string | null,
): void {
  if (typeof store.setError === 'function') {
    store.setError(sessionId, message)
    return
  }
  if (sessionId && store.errorsBySession instanceof Map) {
    store.errorsBySession.set(sessionId, message)
    return
  }
  store.error = message
}
