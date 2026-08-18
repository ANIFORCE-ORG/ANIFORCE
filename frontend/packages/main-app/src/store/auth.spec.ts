import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

class MemoryStorage implements Storage {
  private values = new Map<string, string>()

  get length() {
    return this.values.size
  }

  clear() {
    this.values.clear()
  }

  getItem(key: string) {
    return this.values.get(key) ?? null
  }

  key(index: number) {
    return Array.from(this.values.keys())[index] ?? null
  }

  removeItem(key: string) {
    this.values.delete(key)
  }

  setItem(key: string, value: string) {
    this.values.set(key, value)
  }
}

describe('demo authentication session', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_DEMO_MODE', 'true')
    vi.stubGlobal('localStorage', new MemoryStorage())
    vi.stubGlobal('sessionStorage', new MemoryStorage())
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('remembers an explicit logout for the current demo browser session', async () => {
    const { useAuthStore } = await import('./auth')
    const auth = useAuthStore()

    auth.fakeLogin()
    auth.logout()

    expect(auth.isLoggedIn).toBe(false)
    expect(auth.hasExplicitDemoLogout).toBe(true)
    expect(sessionStorage.getItem('aniforce_demo_logged_out')).toBe('true')

    setActivePinia(createPinia())
    expect(useAuthStore().hasExplicitDemoLogout).toBe(true)
  })

  it('clears the explicit logout marker after a new demo login', async () => {
    sessionStorage.setItem('aniforce_demo_logged_out', 'true')
    const { useAuthStore } = await import('./auth')
    const auth = useAuthStore()

    auth.fakeLogin()

    expect(auth.hasExplicitDemoLogout).toBe(false)
    expect(sessionStorage.getItem('aniforce_demo_logged_out')).toBe(null)
  })
})
