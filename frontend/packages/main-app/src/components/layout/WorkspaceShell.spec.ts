import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const readSource = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8')

describe('Codex-inspired workspace shell', () => {
  const routerSource = readSource('../../router/index.ts')
  const headerSource = readSource('./AppHeader.vue')
  const sidebarSource = readSource('./SidebarNav.vue')
  const renameDialogSource = readSource('./SessionRenameDialog.vue')
  const confirmDialogSource = readSource('../toasts/ConfirmDialog.vue')
  const footerSource = readSource('./AppFooter.vue')

  it('opts the fifteen SidebarNav routes into the workspace shell', () => {
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
    expect(routerSource).toMatch(/name: 'market-analysis',\s+component: \(\) => import\('@\/pages\/MarketAnalysis\.vue'\),\s+\},/)
  })

  it('keeps the public header Logo while removing workspace account actions', () => {
    expect(headerSource).toContain('const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)')
    expect(headerSource).toContain('v-if="!isWorkspaceShell"')
    expect(headerSource).toContain('class="h-10 w-auto max-w-[176px] object-contain logo-blue"')
    expect(headerSource).toContain('<AccountControls v-if="!isWorkspaceShell" variant="header" />')
    expect(headerSource).toContain('border-bottom: 0.5px solid rgba(55, 53, 47, 0.16)')
    expect(headerSource).toContain('justify-content: flex-end')
    expect(headerSource).toContain('min-height: 57px')
  })

  it('renders a fixed rail with a bottom account dock and right-opening surface', () => {
    expect(sidebarSource).toContain('sidebar-rail-spacer')
    expect(sidebarSource).toContain('fixed bottom-0 left-0 top-0 z-50')
    expect(sidebarSource).toContain('--workspace-sidebar-width')
    expect(sidebarSource).toContain('height: 30px')
    expect(sidebarSource).toContain('rgba(55, 53, 47, 0.068) 100%')
    expect(sidebarSource).toContain("import AccountControls from '@/components/layout/AccountControls.vue'")
    expect(sidebarSource).toContain('<AccountControls variant="sidebar" :collapsed="isCollapsed" />')
    expect(sidebarSource).not.toContain('z-50 flex flex-col overflow-hidden transition-all')
  })

  it('keeps session actions inside the sidebar and reveals them only on interaction', () => {
    expect(sidebarSource).toContain('sessionActions: true')
    expect(sidebarSource).toContain('class="sidebar-session-actions flex items-center"')
    expect(sidebarSource).toContain('<span class="material-symbols-outlined">more_horiz</span>')
    expect(sidebarSource).toContain('@contextmenu.prevent.stop="openSessionMenu(session.id)"')
    expect(sidebarSource).toMatch(/\.sidebar-session-list \{[\s\S]*?width: 100%;[\s\S]*?min-width: 0;/)
    expect(sidebarSource).toMatch(/\.sidebar-session-item \{[\s\S]*?width: 100%;[\s\S]*?min-width: 0;[\s\S]*?box-sizing: border-box;/)
    expect(sidebarSource).toMatch(/\.sidebar-session-actions \{[\s\S]*?flex: 0 0 24px;[\s\S]*?opacity: 0;[\s\S]*?pointer-events: none;/)
    expect(sidebarSource).toContain('.sidebar-session-item.sidebar-item-active .sidebar-session-actions')
    expect(sidebarSource).toContain('.sidebar-session-item:hover .sidebar-session-actions')
    expect(sidebarSource).toContain('.sidebar-session-item.is-menu-open .sidebar-session-actions')
    expect(sidebarSource).toContain('.sidebar-session-list:has(.sidebar-session-item:hover)')
    expect(sidebarSource).toContain('.sidebar-session-item.sidebar-item-active:not(:hover):not(:focus-within):not(.is-menu-open)')
  })

  it('uses compact Notion-style dialogs and a destructive delete action', () => {
    expect(renameDialogSource).toContain('width: min(420px, 100%)')
    expect(renameDialogSource).toContain('border-radius: 12px')
    expect(renameDialogSource).toContain('font-family: "Notion Sans"')
    expect(confirmDialogSource).toContain("tone?: 'primary' | 'danger'")
    expect(confirmDialogSource).toContain('.confirm-button.primary.danger')
    expect(sidebarSource).toContain('tone="danger"')
    expect(sidebarSource).toContain('variant="notion"')
  })

  it('offsets workspace footer content and removes only the Home divider', () => {
    expect(footerSource).toContain('route.meta.workspaceShell === true')
    expect(footerSource).toContain("route.name === 'home'")
    expect(footerSource).toContain('var(--workspace-sidebar-width, 205px)')
    expect(footerSource).toContain('border-top: 0 !important')
  })
})
