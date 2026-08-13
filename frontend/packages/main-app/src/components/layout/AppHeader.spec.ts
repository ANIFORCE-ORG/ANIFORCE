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

  it('delegates account controls outside workspace routes', () => {
    expect(source).toContain("<header :class=\"['app-header', { 'app-header--workspace': isWorkspaceShell }]\">")
    expect(source).toContain("import AccountControls from '@/components/layout/AccountControls.vue'")
    expect(source).toContain('<AccountControls v-if="!isWorkspaceShell" variant="header" />')
    expect(source).toContain('v-if="!isWorkspaceShell"')
    expect(source).toContain('border-bottom: 1px solid #e9e9e7;')
    expect(source).toContain('min-height: 57px;')
    expect(source).toContain(':global(.dark) .app-header')
    expect(source).not.toContain('backdrop-blur-md')
    expect(source).not.toContain('bg-primary/10')
    expect(source).not.toContain('border-2 border-primary/30')
  })

  it('does not move or resize the public Logo', () => {
    expect(source).not.toContain('max-width: 112px;')
  })
})
