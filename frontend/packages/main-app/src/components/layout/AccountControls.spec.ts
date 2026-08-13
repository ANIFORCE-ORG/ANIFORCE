import { existsSync, readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const componentUrl = new URL('./AccountControls.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

describe('shared account controls', () => {
  it('provides header and sidebar variants without duplicating store behavior', () => {
    expect(existsSync(componentUrl)).toBe(true)
    expect(source).toContain("variant: 'header' | 'sidebar'")
    expect(source).toContain('collapsed: false')
    expect(source).toContain('useAuthStore()')
    expect(source).toContain('useLanguage()')
    expect(source).toContain('auth.logout()')
  })

  it('keeps the account menu accessible and dismissible', () => {
    expect(source).toContain('aria-haspopup="menu"')
    expect(source).toContain(':aria-expanded="showMenu"')
    expect(source).toContain("event.key === 'Escape'")
    expect(source).toContain('!rootElement.value?.contains')
    expect(source).toContain('.account-trigger:focus-visible')
  })

  it('opens the collapsed sidebar account popover to the right', () => {
    expect(source).toContain("'account-popover--sidebar': isSidebar")
    expect(source).toContain('left: calc(100% + 8px);')
    expect(source).toContain('bottom: 8px;')
    expect(source).toContain('aria-label="账户与偏好设置"')
    expect(source).toContain('{{ auth.user?.name?.charAt(0) }}')
    expect(source).toContain('v-if="!collapsed" class="sidebar-account-name"')
  })

  it('preserves notification, language, and logout controls', () => {
    expect(source).toContain('notifications')
    expect(source).toContain('class="language-switcher"')
    expect(source).toContain('中文')
    expect(source).toContain('EN')
    expect(source).toContain('logout')
  })
})
