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
    expect(source).toContain('.composer.composer--expanded > .composer__reference')
    expect(source).toContain('.composer.composer--expanded > .composer__send')
  })

  it('replaces voice input with an @ reference control in both composers', () => {
    expect(source).not.toContain('aria-label="语音输入"')
    expect(source).not.toContain('>mic</span>')
    expect(source.match(/aria-label="引用系统内容或模块"/g)).toHaveLength(2)
    expect(source).toContain('class="composer__reference-trigger"')
    expect(source).toContain('@click="toggleReferencePicker"')
  })

  it('places attachment and @ together on the left and opens references for an @ typed anywhere before the caret', () => {
    expect(source).toMatch(/\.composer \{[\s\S]*?grid-template-columns: 32px 32px minmax\(0, 1fr\) 38px;[\s\S]*?column-gap: 0;/)
    expect(source).toMatch(/\.composer > \.composer__icon\[aria-label="添加附件"\] \{[\s\S]*?grid-column: 1;/)
    expect(source).toMatch(/\.composer > \.composer__reference \{[\s\S]*?grid-column: 2;/)
    expect(source).toMatch(/\.composer textarea \{[\s\S]*?grid-column: 3;/)
    expect(source).toMatch(/@media \(max-width: 520px\) \{[\s\S]*?\.composer \{[\s\S]*?grid-template-columns: 32px 32px minmax\(0, 1fr\) 38px;/)
    expect(source).toContain(String.raw`match(/@([^\s@]*)$/)`)
  })

  it('renders attachment and @ with the same icon system, color and stroke weight', () => {
    expect(source.match(/>alternate_email<\/span>/g)).toHaveLength(2)
    expect(source).not.toContain('<span aria-hidden="true">@</span>')
    expect(source).toContain('.composer__icon .material-symbols-outlined,\n.composer__reference-trigger .material-symbols-outlined')
    expect(source).toContain("font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;")
  })

  it('does not select the fixed @ trigger when typing @ opens the caret picker', () => {
    expect(source.match(/:aria-expanded="referencePickerOpen && referencePickerOrigin === 'button'"/g)).toHaveLength(2)
    expect(source).not.toContain(':aria-expanded="referencePickerOpen"')
  })

  it('keeps attachment and @ controls on the same compact hit area', () => {
    expect(source).toMatch(/\.composer__icon,\n\.composer__reference-trigger \{[\s\S]*?box-sizing: border-box;[\s\S]*?width: 32px;[\s\S]*?height: 32px;[\s\S]*?padding: 0;[\s\S]*?border-radius: 8px;[\s\S]*?background: transparent;/)
    expect(source).toMatch(/\.composer > \.composer__reference \{[\s\S]*?width: 32px;[\s\S]*?height: 32px;/)
  })

  it('narrows only the @ glyph while preserving the equal control width', () => {
    expect(source).toMatch(/\.composer__reference-trigger \.material-symbols-outlined \{[\s\S]*?transform: scaleX\(0\.88\);[\s\S]*?transform-origin: center;/)
    expect(source).toMatch(/\.composer__icon,\n\.composer__reference-trigger \{[\s\S]*?width: 32px;[\s\S]*?height: 32px;/)
  })

  it('anchors typed @ references at the caret instead of the bottom @ button', () => {
    expect(source).toContain("type ReferencePickerOrigin = 'button' | 'caret'")
    expect(source).toContain('function getTextareaCaretRect')
    expect(source).toContain('function positionReferencePickerAtCaret')
    expect(source).toContain('positionReferencePickerAtCaret(target)')
    expect(source.match(/'reference-picker--caret': referencePickerOrigin === 'caret'/g)).toHaveLength(2)
    expect(source.match(/:style="referencePickerStyle"/g)).toHaveLength(2)
    expect(source.match(/<Teleport to="body" :disabled="referencePickerOrigin === 'button'">/g)).toHaveLength(2)
    expect(source.match(/data-reference-picker-panel/g)).toHaveLength(2)
    expect(source).toMatch(/\.reference-picker--caret \{[\s\S]*?position: fixed;/)
  })

  it('lets users search and insert references to system content and module components', () => {
    expect(source).toContain("type ReferenceGroup = '系统内容' | '模块组件'")
    expect(source).toContain("label: '数据概览'")
    expect(source).toContain("label: '项目管理'")
    expect(source).toContain("label: '创意素材'")
    expect(source).toContain("label: '趋势图表'")
    expect(source).toContain("label: '核心指标'")
    expect(source).toContain('function selectReference')
    expect(source).toContain('const token = `@${item.label}`')
    expect(source).toContain('role="listbox"')
    expect(source).toContain('placeholder="搜索系统内容或模块"')
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
