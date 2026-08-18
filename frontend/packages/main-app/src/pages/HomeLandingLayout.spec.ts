import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const controllerSource = readFileSync(new URL('../composables/useAgentSessionController.ts', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../store/agent.ts', import.meta.url), 'utf8')
const workspaceHydrationSource = readFileSync(new URL('../services/workspaceArtifactStore.ts', import.meta.url), 'utf8')
const mockApiSource = readFileSync(new URL('../api/mock.ts', import.meta.url), 'utf8')

describe('Home landing layout', () => {
  it('keeps the welcome content and composer responsive across width and height changes', () => {
    expect(source).toContain('class="landing-primary"')
    expect(source).toContain('grid-template-rows: minmax(min-content, 1fr) auto;')
    expect(source).not.toContain('aniforceWorkflowHero')
    expect(source).not.toContain('class="landing-visual"')
    expect(source).toContain('@media (max-width: 980px)')
    expect(source).toContain('@media (max-height: 820px) and (min-width: 981px)')
  })

  it('offers four default strategies and expands to eight optimized ad-operation prompts', () => {
    expect(source).toContain('const strategyExpanded = ref(false)')
    expect(source).toContain('strategyExpanded.value ? starterActions : starterActions.slice(0, 4)')
    expect(source).toContain(':aria-expanded="strategyExpanded"')
    expect(source).toContain("strategyExpanded ? '收起策略' : '展开更多策略'")
    expect(source).toContain('今日投放复盘')
    expect(source).toContain('计划分层调控')
    expect(source).toContain('素材表现诊断')
    expect(source).toContain('预算扩量建议')
    expect(source).toContain('渠道效果对比')
    expect(source).toContain('异常波动排查')
    expect(source).toContain('素材疲劳监控')
    expect(source).toContain('下一轮测试方案')
    expect(source).toContain('可放量 / 观察 / 控量 / 暂停')
    expect(source).toContain('归因成熟度')
  })

  it('stages a starter prompt in the composer without sending it automatically', () => {
    const starterHandler = source.match(/async function runStarterAction[\s\S]*?\n}/)?.[0] ?? ''

    expect(starterHandler).toContain('inputText.value = action.prompt')
    expect(starterHandler).toContain('input?.focus()')
    expect(starterHandler).toContain('input?.setSelectionRange')
    expect(starterHandler).not.toContain('handleSubmit()')
  })

  it('expands long prompts horizontally and vertically without hiding their content', () => {
    expect(source.match(/<textarea/g)).toHaveLength(2)
    expect(source).toContain('const isPromptExpanded = computed')
    expect(source).toContain('Array.from(inputText.value).length > 72')
    expect(source).toContain("'composer--expanded': isPromptExpanded")
    expect(source).toContain('@input="handlePromptInput"')
    expect(source).toContain('@keydown="handlePromptKeydown"')
    expect(source).toContain("event.key !== 'Enter' || event.shiftKey || event.isComposing")
    expect(source).toContain('target.style.height = `${Math.max(24, target.scrollHeight)}px`')
    expect(source).toContain('promptResizeObserver = new ResizeObserver')
    expect(source).toContain('.landing-input-dock.is-expanded')
    expect(source).toContain('.conversation-composer.composer--expanded')
    expect(source).toContain('field-sizing: content;')
    expect(source).toMatch(/\.composer \{[\s\S]*?align-items: center;/)
    expect(source).toMatch(/\.composer\.composer--expanded \{[\s\S]*?grid-template-rows: auto 38px;[\s\S]*?row-gap: 8px;/)
    expect(source).toMatch(/\.composer\.composer--expanded textarea \{[\s\S]*?grid-column: 1 \/ -1;[\s\S]*?align-self: stretch;/)
    expect(source).toContain('.composer.composer--expanded > .composer__icon[aria-label="添加附件"]')
    expect(source).toContain('.composer.composer--expanded > .composer__icon[aria-label="语音输入"]')
    expect(source).toContain('.composer.composer--expanded > .composer__send')
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
