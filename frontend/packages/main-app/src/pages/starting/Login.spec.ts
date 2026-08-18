import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Login.vue', import.meta.url), 'utf8')

describe('Notion-style login page', () => {
  it('uses a compact semantic login surface', () => {
    expect(source).toContain('class="login-page"')
    expect(source).toContain('class="login-card"')
    expect(source).toContain('class="login-form"')
    expect(source).toContain('class="login-field"')
    expect(source).toContain('class="login-submit"')
  })

  it('uses the shared Notion palette and restrained card treatment', () => {
    expect(source).toContain('--login-canvas: var(--workspace-canvas, #ffffff);')
    expect(source).toContain('border: 1px solid var(--login-line);')
    expect(source).toContain('border-radius: 12px;')
    expect(source).toContain('box-shadow: rgba(15, 15, 15, 0.08) 0 12px 36px;')
    expect(source).not.toContain('bg-gradient-to')
    expect(source).not.toContain('shadow-2xl')
    expect(source).not.toContain('border-2')
  })

  it('keeps compact controls and responsive spacing', () => {
    expect(source).toContain('min-height: 40px;')
    expect(source).toContain('@media (max-width: 560px)')
    expect(source).toContain('padding: 20px 16px;')
  })

  it('preserves the existing authentication interactions', () => {
    expect(source).toContain('@submit.prevent="handleLogin"')
    expect(source).toContain('v-model="email"')
    expect(source).toContain('v-model="password"')
    expect(source).toContain('@click="handleForgotPassword"')
    expect(source).toContain("@click=\"router.push('/')\"")
  })
})
