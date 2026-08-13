import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const readSource = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8')

describe('Codex-inspired workspace shell', () => {
  const routerSource = readSource('../../router/index.ts')
  const headerSource = readSource('./AppHeader.vue')
  const sidebarSource = readSource('./SidebarNav.vue')
  const footerSource = readSource('./AppFooter.vue')

  it('opts the fifteen SidebarNav routes into the workspace shell', () => {
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
    expect(routerSource).toMatch(/name: 'market-analysis',\s+component: \(\) => import\('@\/pages\/MarketAnalysis\.vue'\),\s+\},/)
  })

  it('keeps the public header Logo and applies only workspace hairline behavior', () => {
    expect(headerSource).toContain('const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)')
    expect(headerSource).toContain('v-if="!isWorkspaceShell"')
    expect(headerSource).toContain('class="h-10 w-auto max-w-[176px] object-contain logo-blue"')
    expect(headerSource).toContain('border-bottom: 0.5px solid rgba(55, 53, 47, 0.16)')
    expect(headerSource).toContain('justify-content: flex-end')
  })

  it('renders a fixed rail with a flow spacer, compact Logo, and a left-cast fade', () => {
    expect(sidebarSource).toContain('sidebar-rail-spacer')
    expect(sidebarSource).toContain('fixed bottom-0 left-0 top-0 z-50')
    expect(sidebarSource).toContain('--workspace-sidebar-width')
    expect(sidebarSource).toContain('height: 30px')
    expect(sidebarSource).toContain('rgba(55, 53, 47, 0.068) 100%')
  })

  it('offsets workspace footer content and removes only the Home divider', () => {
    expect(footerSource).toContain('route.meta.workspaceShell === true')
    expect(footerSource).toContain("route.name === 'home'")
    expect(footerSource).toContain('var(--workspace-sidebar-width, 205px)')
    expect(footerSource).toContain('border-top: 0 !important')
  })
})
