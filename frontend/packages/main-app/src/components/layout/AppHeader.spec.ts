import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./AppHeader.vue', import.meta.url), 'utf8')

describe('AppHeader visual contract', () => {
  it('preserves the existing ANIFORCE Logo rendering contract', () => {
    expect(source).toContain(
      '<img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />',
    )
    expect(source).toContain(
      'filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);',
    )
  })

  it('uses the approved Notion-balanced header treatment', () => {
    expect(source).toContain('<header class="app-header">')
    expect(source).toContain('class="header-user"')
    expect(source).toContain('class="header-avatar"')
    expect(source).toContain('class="header-icon-button"')
    expect(source).toContain('class="language-switcher"')
    expect(source).toContain('border-bottom: 1px solid #e9e9e7;')
    expect(source).toContain(':global(.dark) .app-header')
    expect(source).toContain('.header-user:focus-visible')
    expect(source).not.toContain('backdrop-blur-md')
    expect(source).not.toContain('bg-primary/10')
    expect(source).not.toContain('border-2 border-primary/30')
  })

  it('fits narrow screens without moving or resizing the Logo', () => {
    expect(source).toContain('@media (max-width: 520px)')
    expect(source).toContain('  .header-user {\n    gap: 4px;')
    expect(source).toContain('  .header-user-email {\n    max-width: 88px;')
    expect(source).toContain('  .language-option {\n    padding-right: 4px;\n    padding-left: 4px;')
    expect(source).not.toContain('max-width: 112px;')
  })
})
