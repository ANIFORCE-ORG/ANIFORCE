import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const projectsSource = readFileSync(new URL('./projects/Projects.vue', import.meta.url), 'utf8')
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

  it('fills editable starter intents without duplicating workspace forms', () => {
    const starterHandler = source.slice(
      source.indexOf('async function runStarterAction'),
      source.indexOf('function navigateTo'),
    )

    expect(source).toContain("prompt: '我想启动一个新的增长项目，请在工作台生成一份可编辑草稿。'")
    expect(source).toContain('结构化字段将在工作台中编辑。')
    expect(starterHandler).toContain('selectedStarterAction.value = action.label')
    expect(starterHandler).toContain('composerInput.value?.focus()')
    expect(starterHandler).not.toContain('handleSubmit()')
  })

  it('uses an auto-growing multiline composer for landing and conversation states', () => {
    expect(source.match(/<textarea\n/g)).toHaveLength(2)
    expect(source).toContain('@input="handleComposerInput"')
    expect(source).toContain('@compositionstart="handleComposerCompositionStart"')
    expect(source).toContain('@compositionend="handleComposerCompositionEnd"')
    expect(source).toContain('@keydown.enter="handleComposerKeydown"')
    expect(source).toContain('event.isComposing || event.keyCode === 229 || justConfirmedComposition')
    expect(source).toContain('if (composerIsComposing.value || !message')
    expect(source).toContain('const nextHeight = Math.min(target.scrollHeight, 112)')
    expect(source).toContain('max-height: 112px;')
  })

  it('keeps sent questions visible while the agent is loading', () => {
    expect(source).not.toContain('<div v-if="agent.loading.value" class="conversation-loading">')
    expect(source).toContain('v-for="(message, index) in agent.visibleMessages.value"')
    expect(source).toContain('v-if="(agent.loading.value || agent.agentRunning.value) && !agent.streamingMessage.value"')
  })

  it('scrolls restored conversations to their latest message', () => {
    const selectionHandler = source.slice(
      source.indexOf('async function selectSessionTarget'),
      source.indexOf('async function applyHomeSessionState'),
    )

    expect(source).toContain("function scrollToBottom(behavior: ScrollBehavior = 'smooth')")
    expect(selectionHandler).toContain("scrollToBottom('auto')")
  })

  it('routes agent campaign creation through the project management modal', () => {
    expect(source).toContain("void router.push({ path: '/projects', query: { createCampaignFor: projectId } })")
    expect(source).not.toContain('`/campaigns/create?projectId=${encodeURIComponent(projectId)}`')
    expect(projectsSource).toContain('openCampaignCreateFromQuery()')
    expect(projectsSource).toContain("typeof route.query.createCampaignFor === 'string'")
    expect(projectsSource).toContain('<CreateCampaignModal')
    expect(projectsSource).toContain('clearCampaignCreateQuery()')
  })

  it('keeps internal business-skill phases out of the conversation UI', () => {
    expect(source).not.toContain('class="task-state"')
    expect(source).not.toContain('task-state__steps')
    expect(source).not.toContain("label: '确认目标与对象'")
    expect(source).not.toContain("icon: 'edit_note'")
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
