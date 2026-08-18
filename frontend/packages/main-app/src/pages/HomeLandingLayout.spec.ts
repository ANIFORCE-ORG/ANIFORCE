import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const controllerSource = readFileSync(new URL('../composables/useAgentSessionController.ts', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../store/agent.ts', import.meta.url), 'utf8')
const workspaceHydrationSource = readFileSync(new URL('../services/workspaceArtifactStore.ts', import.meta.url), 'utf8')
const mockApiSource = readFileSync(new URL('../api/mock.ts', import.meta.url), 'utf8')

describe('Home landing layout', () => {
  it('places the welcome and quick-start group lower while keeping the composer bottom anchored', () => {
    expect(source).toContain('padding: clamp(260px, 38vh, 720px) 36px 48px;')
    expect(source).toContain('margin: auto auto 0;')
    expect(source).toContain('@media (max-width: 980px)')
    expect(source).toContain('padding-top: 48px;')
  })

  it('restores a historical conversation instead of falling back to the new-task landing page', () => {
    expect(source).toContain('Boolean(hasInteracted.value && agent.activeSession.value)')
    expect(controllerSource).toContain('store.restoreFromLocalStorage(session.id)')
    expect(controllerSource).toContain('snapshot.messages.length ? snapshot.messages : cachedMessages')
    expect(storeSource).toContain('aniforce_messages_${sessionId}')
    expect(workspaceHydrationSource).toContain('if (snapshot.artifacts.length)')
    expect(mockApiSource).toContain('agentSessionSnapshotMatch')
    expect(mockApiSource).toContain('session.messages.push(')
  })
})
