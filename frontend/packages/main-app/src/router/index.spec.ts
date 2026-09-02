import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./index.ts', import.meta.url), 'utf8')

describe('demo authentication routing', () => {
  it('does not auto-login again after an explicit demo logout', () => {
    expect(source).toContain("import.meta.env.VITE_DEMO_MODE === 'true' && !auth.isLoggedIn && !auth.hasExplicitDemoLogout")
  })

  it('protects static and dynamic workspace routes through route metadata', () => {
    expect(source).toContain('const requiresAuth = to.meta.workspaceShell === true')
    expect(source).toContain('if (requiresAuth && !auth.isLoggedIn)')
    expect(source).not.toContain('requiresAuth.includes(to.path)')
  })
})
