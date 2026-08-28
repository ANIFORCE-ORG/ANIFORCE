import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const workspaceShellSource = readFileSync(new URL('../components/agent/workspace/LiveWorkspaceShell.vue', import.meta.url), 'utf8')
const controllerSource = readFileSync(new URL('../composables/useAgentSessionController.ts', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../store/agent.ts', import.meta.url), 'utf8')
const workspaceHydrationSource = readFileSync(new URL('../services/workspaceArtifactStore.ts', import.meta.url), 'utf8')
const mockApiSource = readFileSync(new URL('../api/mock.ts', import.meta.url), 'utf8')

describe('Home landing layout', () => {
  it('keeps the first composer visible in short viewports', () => {
    expect(source).toContain('padding: clamp(32px, 8vh, 96px) 36px 24px;')
    expect(source).toContain('margin-top: clamp(20px, 4vh, 32px);')
    expect(source).toContain('margin: clamp(24px, 5vh, 60px) auto 0;')
    expect(source).toContain('@media (max-width: 980px)')
    expect(source).toContain('padding-top: 48px;')
  })

  it('uses a floating workspace trigger without reserving a collapsed rail', () => {
    expect(source).toContain("width: workspaceEffectiveCollapsed.value ? '0px' : `${workspaceWidth.value}px`")
    expect(source).toContain(':can-expand="true"')
    expect(source).toContain('.workspace-column.collapsed {\n  min-width: 0;')
    expect(workspaceShellSource).toContain("class=\"workspace-rail__tooltip\" role=\"tooltip\"")
    expect(workspaceShellSource).toContain("{{ attentionLabel || '打开工作台' }}")
    expect(workspaceShellSource).toContain('.workspace-shell.is-collapsed {')
    expect(workspaceShellSource).not.toContain('workspace-rail__label')
  })

  it('opens the workspace whenever a new projection arrives', () => {
    expect(source).toContain('workspaceManuallyCollapsed.value = false')
    expect(source).toContain('workspaceCollapsed.value = false')
    expect(source).not.toContain('if (!workspaceManuallyCollapsed.value) workspaceCollapsed.value = false')
  })

  it('restores server history without treating stale browser caches as authoritative', () => {
    expect(source).toContain('agent.hasAnyRunningRun.value')
    expect(controllerSource).toContain('store.setMessages(session.id, snapshot.messages)')
    expect(controllerSource).not.toContain('snapshot.messages.length ? snapshot.messages : cachedMessages')
    expect(storeSource).not.toContain('aniforce_messages_${sessionId}')
    expect(workspaceHydrationSource).toContain('workspace.clearSession(sessionId)')
    expect(workspaceHydrationSource).not.toContain('if (snapshot.artifacts.length)')
    expect(mockApiSource).toContain('agentSessionSnapshotMatch')
    expect(mockApiSource).toContain('session.messages.push(')
  })
})
