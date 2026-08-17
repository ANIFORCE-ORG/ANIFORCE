<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import type { AgentMessage } from '@/api/agent'
import ActivityMessageView from './ActivityMessageView.vue'
import { getHiddenToolActivity, getToolPresentation, type ToolPresentationState } from '@/utils/toolNameMapping'

const props = defineProps<{
  message: AgentMessage
  isStreaming?: boolean
  toolResults?: Map<string, AgentMessage>
  modelNames?: Record<string, string>
  prevTimestamp?: number
}>()

const emit = defineEmits<{
  approval: [payload: { runId: string; checkpointId: string; decision: 'approve' | 'reject' }]
}>()

const hovered = ref(false)
const copied = ref(false)
const codeCopied = ref<Record<number, boolean>>({})
const streamStartedAt = ref<number | null>(null)
const tps = ref<number | null>(null)
let tpsTimer: number | null = null

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: false,
  typographer: false
})
const defaultLinkOpen = markdown.renderer.rules.link_open || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  const targetIndex = token.attrIndex('target')
  if (targetIndex < 0) token.attrPush(['target', '_blank'])
  else token.attrs![targetIndex][1] = '_blank'
  const relIndex = token.attrIndex('rel')
  if (relIndex < 0) token.attrPush(['rel', 'noopener noreferrer'])
  else token.attrs![relIndex][1] = 'noopener noreferrer'
  return defaultLinkOpen(tokens, idx, options, env, self)
}

const isUser = computed(() => props.message.role === 'user')
const isAssistant = computed(() => props.message.role === 'assistant')
const isActivity = computed(() => props.message.role === 'activity')
const textContent = computed(() => messageText(props.message))
const blocks = computed(() => contentBlocks(props.message))
const userImageBlocks = computed(() => {
  const content = props.message.content
  if (!Array.isArray(content)) return []
  return content.filter(block => block && typeof block === 'object' && block.type === 'image') as Record<string, unknown>[]
})
const modelLabel = computed(() => {
  const provider = props.message.provider
  const model = props.message.model
  if (!model) return ''
  return props.modelNames?.[`${provider}:${model}`] || props.modelNames?.[model] || model
})
const estimatedTokens = computed(() => Math.round(textContent.value.length / 4))
const usageText = computed(() => formatUsage(props.message.usage))

interface RunActivityPresentation {
  icon: string
  label: string
  mode: 'thinking' | 'internal' | 'continuing'
}

// A run gets one foreground signal. Raw reasoning and hidden tools never enter
// the DOM, but they still keep the user informed through this safe fallback.
const hasTextOutput = computed(() => blocks.value.some(b => b.type === 'text' && String(b.text || '').trim()))
const hasRunningTools = computed(() => props.isStreaming && blocks.value.some(b => b.type === 'toolCall' && !hasToolResult(b)))
const runActivity = computed<RunActivityPresentation | null>(() => {
  if (!props.isStreaming) return null

  const visibleToolIsRunning = blocks.value.some(block => (
    block.type === 'toolCall'
    && toolState(block) === 'running'
    && toolPresentation(block).visible
  ))
  if (visibleToolIsRunning) return null

  for (let index = blocks.value.length - 1; index >= 0; index -= 1) {
    const block = blocks.value[index]
    if (block.type === 'text') {
      if (String(block.text || '').trim()) return null
      continue
    }
    if (block.type === 'approval') return null
    if (block.type === 'thinking') {
      return { icon: 'psychology', label: continuationLabel(index), mode: 'thinking' }
    }
    if (block.type === 'toolCall') {
      const state = toolState(block)
      const hiddenActivity = getHiddenToolActivity(toolName(block), state)
      if (hiddenActivity) return { ...hiddenActivity, mode: 'internal' }
      const category = toolPresentation(block).category
      return {
        icon: category === 'write' || category === 'link' ? 'fact_check' : 'psychology',
        label: category === 'write' || category === 'link' ? '正在核对执行结果' : '正在整理查询结果',
        mode: 'continuing',
      }
    }
    if (block.type === 'image') {
      return { icon: 'psychology', label: '正在整理结果', mode: 'continuing' }
    }
  }

  return { icon: 'psychology', label: '正在分析你的问题', mode: 'thinking' }
})

function continuationLabel(index: number): string {
  const earlierTools = blocks.value.slice(0, index).filter(block => block.type === 'toolCall')
  if (earlierTools.some(block => {
    const category = toolPresentation(block).category
    return category === 'write' || category === 'link'
  })) return '正在核对执行结果'
  if (earlierTools.length > 0) return '正在整理查询结果'
  return '正在分析你的问题'
}

function isLastBlock(index: number): boolean {
  return index === blocks.value.length - 1
}

watch(() => [props.isStreaming, textContent.value.length] as const, ([streaming, chars]) => {
  if (!streaming) {
    streamStartedAt.value = null
    tps.value = null
    if (tpsTimer) window.clearInterval(tpsTimer)
    tpsTimer = null
    return
  }
  if (!streamStartedAt.value) streamStartedAt.value = Date.now()
  if (!tpsTimer) {
    tpsTimer = window.setInterval(() => {
      if (!streamStartedAt.value) return
      const elapsed = (Date.now() - streamStartedAt.value) / 1000
      if (elapsed > 0.5) tps.value = textContent.value.length / 4 / elapsed
    }, 300)
  }
  if (chars > 0 && streamStartedAt.value) {
    const elapsed = (Date.now() - streamStartedAt.value) / 1000
    if (elapsed > 0.5) tps.value = chars / 4 / elapsed
  }
}, { immediate: true })

onUnmounted(() => { if (tpsTimer) window.clearInterval(tpsTimer) })

function messageText(message: AgentMessage): string {
  const content = message.content
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content.map(block => {
    if (!block || typeof block !== 'object') return ''
    if (block.type === 'text' && typeof block.text === 'string') return block.text
    return ''
  }).join('\n')
}

function contentBlocks(message: AgentMessage): Record<string, unknown>[] {
  const content = message.content
  if (Array.isArray(content)) return content as Record<string, unknown>[]
  const text = typeof content === 'string' ? content : messageText(message)
  return text ? [{ type: 'text', text }] : []
}

function approvalTitle(block: Record<string, unknown>): string {
  const interruptions = Array.isArray(block.interruptions) ? block.interruptions : []
  const first = interruptions[0] as Record<string, unknown> | undefined
  const tool = getToolPresentation(String(first?.tool_name || ''), 'running')
  return tool.visible && tool.title ? `需要确认：${tool.title.replace(/^正在/, '')}` : '需要确认一项操作'
}

function approvalArgs(block: Record<string, unknown>): string {
  const interruptions = Array.isArray(block.interruptions) ? block.interruptions : []
  const first = interruptions[0] as Record<string, unknown> | undefined
  const args = first?.arguments
  if (!args) return '{}'
  if (typeof args === 'string') return args
  return formatPayload(args)
}

function approvalStatus(block: Record<string, unknown>): string {
  const status = String(block.status || 'pending')
  if (status === 'approved') return '已确认，正在继续执行'
  if (status === 'rejected') return '已拒绝，不会执行'
  if (status === 'running') return '正在提交确认结果'
  return '操作内容已在右侧工作台准备好，确认后才会继续执行'
}

function canResolveApproval(block: Record<string, unknown>): boolean {
  return String(block.status || 'pending') === 'pending' && Boolean(block.runId && block.checkpointId)
}

function resolveApproval(block: Record<string, unknown>, decision: 'approve' | 'reject'): void {
  if (!canResolveApproval(block)) return
  emit('approval', { runId: String(block.runId), checkpointId: String(block.checkpointId), decision })
}

function toolId(block: Record<string, unknown>): string {
  return String(block.toolCallId || block.id || '')
}
function toolName(block: Record<string, unknown>): string {
  return String(block.toolName || block.name || 'tool')
}
function toolState(block: Record<string, unknown>): ToolPresentationState {
  if (isToolError(block)) return 'error'
  return hasToolResult(block) ? 'completed' : 'running'
}
function toolResult(block: Record<string, unknown>): unknown {
  const paired = props.toolResults?.get(toolId(block))
  return paired ? messageText(paired) : block.result
}
function toolPresentation(block: Record<string, unknown>) {
  return getToolPresentation(toolName(block), toolState(block), toolResult(block))
}
function imageSrc(block: Record<string, unknown>): string {
  if (typeof block.data === 'string') return `data:${String(block.mimeType || 'image/png')};base64,${block.data}`
  const source = block.source
  if (source && typeof source === 'object') {
    const record = source as Record<string, unknown>
    if (record.type === 'base64' && typeof record.data === 'string') {
      return `data:${String(record.media_type || record.mediaType || 'image/png')};base64,${record.data}`
    }
    if (record.type === 'url' && typeof record.url === 'string') return record.url
  }
  return ''
}

function hasToolResult(block: Record<string, unknown>): boolean {
  return props.toolResults?.has(toolId(block)) || block.result !== undefined
}
function isToolError(block: Record<string, unknown>): boolean {
  const status = String(block.status || '').toLowerCase()
  return status === 'error' || status === 'failed' || !!props.toolResults?.get(toolId(block))?.isError
}
function formatPayload(value: unknown): string {
  if (value === undefined || value === null || value === '') return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}
function formatUsage(usage: AgentMessage['usage']): string {
  if (!usage) return ''
  const parts: string[] = []
  if (usage.input) parts.push(`${usage.input.toLocaleString()} in`)
  if (usage.output) parts.push(`${usage.output.toLocaleString()} out`)
  if (usage.cacheRead) parts.push(`${usage.cacheRead.toLocaleString()} cache`)
  if (usage.cost?.total) parts.push(`$${usage.cost.total.toFixed(4)}`)
  return parts.join(' · ')
}
function formatTime(value?: string | number): string | null {
  if (!value) return null
  const d = typeof value === 'number' ? new Date(value) : new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
async function copy(text: string, codeIndex?: number): Promise<void> {
  await navigator.clipboard.writeText(text).catch(() => undefined)
  copied.value = codeIndex === undefined
  if (codeIndex !== undefined) codeCopied.value[codeIndex] = true
  window.setTimeout(() => {
    if (codeIndex === undefined) copied.value = false
    else codeCopied.value[codeIndex] = false
  }, 1300)
}
function normalizeMarkdown(value: string): string {
  // Some models emit blank lines between every table row. GFM tables require
  // contiguous rows, so collapse blank lines only inside table runs.
  return value.replace(/\n\s*\n(?=\s*\|)/g, '\n')
}
function parseMarkdown(value: string): Array<{ type: 'html'; html: string } | { type: 'code'; lang: string; code: string }> {
  const out: Array<{ type: 'html'; html: string } | { type: 'code'; lang: string; code: string }> = []
  const lines = normalizeMarkdown(value).replace(/\r\n/g, '\n').split('\n')
  let mdLines: string[] = []
  let code: string[] | null = null
  let lang = 'text'
  const flushMarkdown = () => {
    if (!mdLines.length) return
    out.push({ type: 'html', html: markdown.render(mdLines.join('\n')) })
    mdLines = []
  }
  for (const line of lines) {
    const fence = /^```([^`]*)\s*$/.exec(line)
    if (fence) {
      if (code) {
        out.push({ type: 'code', lang, code: code.join('\n') })
        code = null
        lang = 'text'
      } else {
        flushMarkdown()
        code = []
        lang = fence[1]?.trim() || 'text'
      }
      continue
    }
    if (code) code.push(line)
    else mdLines.push(line)
  }
  if (code) out.push({ type: 'code', lang, code: code.join('\n') })
  flushMarkdown()
  return out
}
</script>

<template>
  <!-- Activity Message (工具调用卡片) -->
  <div v-if="isActivity" class="activity-message-wrapper">
    <ActivityMessageView :content="message.content as any" />
  </div>

  <!-- User Message -->
  <div
    v-else-if="isUser"
    class="user-message"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="user-bubble">
      <div v-if="userImageBlocks.length" class="user-images">
        <img v-for="(image, index) in userImageBlocks" :key="index" :src="imageSrc(image)" alt="" />
      </div>
      <div v-if="textContent" class="user-text">{{ textContent }}</div>
    </div>
    <div class="message-actions" :class="{ visible: hovered || copied }">
      <button @click="copy(textContent)">{{ copied ? 'Copied' : 'Copy' }}</button>
      <span v-if="formatTime(message.timestamp || message.created_at)">{{ formatTime(message.timestamp || message.created_at) }}</span>
    </div>
  </div>

  <div
    v-else-if="isAssistant"
    class="assistant-message"
    :class="{ 'is-streaming': isStreaming, 'phase-text': isStreaming && hasTextOutput, 'phase-tools': isStreaming && hasRunningTools }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- 流式指示器：只在有文本输出时显示 -->
    <div v-if="isStreaming && hasTextOutput" class="streaming-indicators">
      <span v-if="estimatedTokens > 0" class="stream-stat">↓ {{ estimatedTokens }}</span>
      <span v-if="tps !== null" class="tps-badge">{{ tps.toFixed(1) }} t/s</span>
    </div>

    <!-- Block list: raw reasoning stays hidden; visible business activity remains. -->
    <div class="assistant-block-list">
      <template v-for="(block, i) in blocks" :key="i">
        <!-- Reasoning is represented by the singleton run activity below. -->
        <template v-if="block.type === 'thinking'"></template>

        <!-- Text Block: 纯 markdown，无包装，流式时带光标 -->
        <div v-else-if="block.type === 'text'" class="markdown-body" :class="{ 'streaming-text': isStreaming && isLastBlock(i) }">
          <template v-for="(part, pi) in parseMarkdown(String(block.text || ''))" :key="pi">
            <div v-if="part.type === 'html'" v-html="part.html"></div>
            <div v-else class="code-block">
              <div class="code-head">
                <span>{{ part.lang }}</span>
                <button @click="copy(part.code, pi)">{{ codeCopied[pi] ? 'copied' : 'copy' }}</button>
              </div>
              <pre><code>{{ part.code }}</code></pre>
            </div>
          </template>
        </div>

        <!-- Approval Block: SDK HITL / MCP approval -->
        <div v-else-if="block.type === 'approval'" class="approval-block compact" :class="String(block.status || 'pending')">
          <div class="approval-head">
            <span class="material-symbols-outlined approval-icon">verified_user</span>
            <div class="approval-title-wrap">
              <div class="approval-title">{{ approvalTitle(block) }}</div>
              <div class="approval-subtitle">{{ approvalStatus(block) }}</div>
            </div>
          </div>
        </div>

        <!-- Tool activity: user-facing business status only; raw payloads stay out of the UI. -->
        <div
          v-else-if="block.type === 'toolCall' && toolPresentation(block).visible"
          class="tool-call-block"
          :class="[`is-${toolState(block)}`, `is-${toolPresentation(block).category}`]"
          role="status"
          aria-live="polite"
        >
          <div class="tool-header">
            <span class="material-symbols-outlined tool-icon" aria-hidden="true">{{ toolPresentation(block).icon }}</span>
            <span class="tool-copy">
              <strong class="tool-name">{{ toolPresentation(block).title }}</strong>
              <small v-if="toolPresentation(block).summary" class="tool-summary">{{ toolPresentation(block).summary }}</small>
            </span>
            <span class="tool-state-icon" :class="toolState(block)" aria-hidden="true">
              <span v-if="toolState(block) === 'running'" class="tool-spinner"></span>
              <span v-else class="material-symbols-outlined">{{ toolState(block) === 'error' ? 'priority_high' : 'check' }}</span>
            </span>
          </div>
        </div>
      </template>

      <div
        v-if="runActivity"
        class="run-activity"
        :data-mode="runActivity.mode"
        role="status"
        aria-live="polite"
      >
        <span class="material-symbols-outlined run-activity__icon" aria-hidden="true">{{ runActivity.icon }}</span>
        <span class="run-activity__label">{{ runActivity.label }}</span>
        <span class="run-activity__dots" aria-hidden="true"><i></i><i></i><i></i></span>
      </div>
    </div>

    <!-- 底部行：usage + copy + timestamp（完成时显示） -->
    <div v-if="!isStreaming" class="assistant-footer">
      <span v-if="usageText" class="usage-text">{{ usageText }}</span>
      <button v-if="textContent" class="copy-button" :class="{ visible: hovered || copied }" @click="copy(textContent)">
        <span class="material-symbols-outlined">content_copy</span>
      </button>
      <span v-if="formatTime(message.timestamp || message.created_at)" class="time-text">{{ formatTime(message.timestamp || message.created_at) }}</span>
    </div>
  </div>
</template>

<style scoped>
/* Activity Message */
.activity-message-wrapper {
  margin-bottom: 20px;
}

/* User Message - 增加阴影和圆润 */
.user-message {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-bottom: 24px;
}

.user-bubble {
  max-width: 85%;
  background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 18px;
  padding: 12px 16px;
  color: var(--text);
  font-size: 14.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.user-bubble:hover {
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12), 0 2px 4px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.user-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.user-images img {
  display: block;
  max-width: 240px;
  max-height: 240px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  object-fit: contain;
  background: var(--surface);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.user-text:empty { display: none; }

.message-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 6px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  color: var(--text-dim);
  font-size: 11px;
}

.message-actions.visible {
  opacity: 1;
  pointer-events: auto;
}

.message-actions button,
.copy-assistant {
  border: 0;
  background: none;
  color: var(--text-dim);
  cursor: pointer;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 11px;
  transition: all 0.15s ease;
}

.message-actions button:hover,
.copy-assistant:hover {
  color: var(--accent);
  background: rgba(59, 130, 246, 0.08);
}

/* Assistant Message - 增加呼吸感 */
.assistant-message {
  margin-bottom: 24px;
  padding: 0;
  transition: opacity 0.2s ease;
}

/* 流式阶段动效 */
.assistant-message.is-streaming {
  position: relative;
}

/* text 阶段：无额外动效，靠光标 */

/* tools 阶段：左侧琥珀色脉冲条 */
.assistant-message.phase-tools::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #f9ab00;
  border-radius: 1px;
  animation: phase-pulse 1.5s ease-in-out infinite;
  opacity: 0.6;
}

@keyframes phase-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}

/* 流式指示器：只在有文本输出时显示 */
.streaming-indicators {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  margin-bottom: 6px;
  color: var(--text-dim, #9aa0a6);
  animation: fade-in 0.3s ease;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Block list: transient reasoning status, text, approvals, and tools. */
.assistant-block-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
}

/* Markdown Body - 对齐 CustomPiAgent: 14px/1.7，紧凑间距 */
.markdown-body {
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  padding: 0;
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}
.markdown-body :deep(p:last-child) { margin-bottom: 0; }

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 10px 0 4px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

.markdown-body :deep(h1) { font-size: 1.15em; }
.markdown-body :deep(h2) { font-size: 1.05em; }
.markdown-body :deep(h3) { font-size: 0.95em; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.markdown-body :deep(li) { margin: 2px 0; }

.markdown-body :deep(blockquote) {
  margin: 4px 0;
  border-left: 3px solid var(--border);
  padding: 2px 10px;
  color: var(--text-muted);
}

.markdown-body :deep(table) {
  width: 100%;
  margin: 8px 0;
  border-collapse: collapse;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 5px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--bg-panel, #f8fafd);
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: var(--accent, #1a73e8);
  text-decoration: underline;
}

.markdown-body :deep(code) {
  background: rgba(100, 116, 139, 0.1);
  border: 1px solid rgba(100, 116, 139, 0.12);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: var(--font-mono, monospace);
  font-size: 0.9em;
}

/* Code Block - 轻量卡片 */
.code-block {
  overflow: hidden;
  margin: 8px 0;
  border: 1px solid var(--border, #e8eaed);
  border-radius: 8px;
  background: var(--bg, #fff);
}

.code-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 12px;
  border-bottom: 1px solid var(--border, #e8eaed);
  background: var(--bg-panel, #f8fafd);
  color: var(--text-dim, #9aa0a6);
  font-size: 11px;
  font-weight: 500;
}

.code-head button {
  border: 0;
  background: none;
  color: var(--text-muted, #5f6368);
  cursor: pointer;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  transition: all 0.12s ease;
}

.code-head button:hover {
  color: var(--accent, #1a73e8);
  background: rgba(26, 115, 232, 0.08);
}

.code-block pre {
  overflow: auto;
  margin: 0;
  padding: 10px 12px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text);
  font-family: var(--font-mono, monospace);
}

/* One quiet fallback covers reasoning and otherwise invisible run activity. */
.run-activity {
  display: flex;
  min-width: 0;
  min-height: 30px;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  color: var(--text-muted, #5f6368);
  animation: run-activity-enter 160ms cubic-bezier(0.16, 1, 0.3, 1) both;
}

.run-activity__icon {
  width: 18px;
  flex: 0 0 18px;
  color: var(--text-muted, #5f6368);
  font-size: 16px;
  line-height: 1;
  text-align: center;
}

.run-activity[data-mode="internal"] .run-activity__icon {
  color: var(--accent, #1a73e8);
}

.run-activity__label {
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-activity__dots {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 2px;
  margin-left: -1px;
}

.run-activity__dots i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--accent, #1a73e8);
  opacity: 0.25;
  animation: run-activity-dot-step 1.2s ease-in-out infinite;
}

.run-activity__dots i:nth-child(2) { animation-delay: 160ms; }
.run-activity__dots i:nth-child(3) { animation-delay: 320ms; }

@keyframes run-activity-enter {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes run-activity-dot-step {
  0%, 65%, 100% { opacity: 0.25; }
  30% { opacity: 1; }
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* text 流式光标：最后一个字符后闪烁 */
.markdown-body.streaming-text::after {
  content: '▍';
  display: inline-block;
  color: var(--accent, #1a73e8);
  animation: cursor-blink 1s steps(2) infinite;
  margin-left: 1px;
  font-size: 0.9em;
}

/* Approval Block - SDK HITL */
.approval-block {
  overflow: hidden;
  border: 1px solid rgba(217, 119, 6, 0.22);
  border-radius: 8px;
  background: #fffaf0;
  color: var(--text, #202124);
}

.approval-block.compact {
  padding: 8px;
}

.approval-block.approved {
  border-color: rgba(24, 128, 56, 0.22);
  background: #f3faf5;
}

.approval-block.rejected {
  border-color: rgba(217, 48, 37, 0.22);
  background: #fff5f5;
}

.approval-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.approval-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: rgba(217, 119, 6, 0.12);
  color: #b45309;
  font-size: 15px;
  flex-shrink: 0;
}

.approval-title-wrap {
  min-width: 0;
  flex: 1;
}

.approval-title {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
}

.approval-subtitle {
  margin-top: 2px;
  color: var(--text-muted, #5f6368);
  font-size: 11.5px;
  line-height: 1.35;
}

.approval-args {
  margin: 0;
  max-height: 180px;
  overflow: auto;
  border-top: 1px solid rgba(217, 119, 6, 0.18);
  padding: 9px 12px;
  background: rgba(255, 255, 255, 0.55);
  color: var(--text-muted, #5f6368);
  font-family: var(--font-mono, monospace);
  font-size: 11.5px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

.approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid rgba(217, 119, 6, 0.18);
  padding: 10px 12px;
}

.approval-button {
  height: 30px;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease;
}

.approval-button.secondary {
  border: 1px solid var(--outline-variant, #e8eaed);
  background: #fff;
  color: var(--text-muted, #5f6368);
}

.approval-button.secondary:hover {
  background: #f8fafc;
}

.approval-button.primary {
  border: 1px solid #b45309;
  background: #b45309;
  color: #fff;
}

.approval-button.primary:hover {
  background: #92400e;
}

/* Tool activity - business language, no raw runtime payloads. */
.tool-call-block {
  overflow: hidden;
  border: 1px solid var(--outline-variant, #e8eaed);
  border-radius: 8px;
  background: var(--surface-container, #f8fafd);
  color: var(--text, #202124);
  font-size: 12px;
  animation: tool-activity-enter 180ms cubic-bezier(0.16, 1, 0.3, 1) both;
  transition: border-color 160ms cubic-bezier(0.16, 1, 0.3, 1), background-color 160ms cubic-bezier(0.16, 1, 0.3, 1);
}

.tool-call-block.is-running {
  border-color: color-mix(in srgb, var(--accent, #1a73e8) 24%, var(--outline-variant, #e8eaed));
}

.tool-call-block.is-error {
  border-color: color-mix(in srgb, var(--error, #d93025) 34%, var(--outline-variant, #e8eaed));
  background: color-mix(in srgb, var(--error, #d93025) 5%, var(--surface, #fff));
}

.tool-header {
  display: flex;
  min-width: 0;
  min-height: 38px;
  align-items: center;
  gap: 9px;
  padding: 7px 11px;
}

.tool-icon {
  width: 20px;
  flex: 0 0 20px;
  color: var(--text-muted, #5f6368);
  font-size: 16px;
  line-height: 1;
  text-align: center;
}

.tool-call-block.is-read .tool-icon {
  color: var(--accent, #1a73e8);
}

.tool-call-block.is-write .tool-icon,
.tool-call-block.is-link .tool-icon {
  color: var(--text, #202124);
}

.tool-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: baseline;
  gap: 8px;
}

.tool-name {
  overflow: hidden;
  color: inherit;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-summary {
  overflow: hidden;
  color: var(--text-dim, #9aa0a6);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-call-block.is-error .tool-name {
  color: var(--error, #d93025);
}

.tool-state-icon {
  display: grid;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  place-items: center;
  border-radius: 50%;
}

.tool-state-icon .material-symbols-outlined {
  font-size: 15px;
}

.tool-state-icon.completed {
  background: color-mix(in srgb, var(--success, #16803c) 10%, transparent);
  color: var(--success, #16803c);
}

.tool-state-icon.error {
  background: color-mix(in srgb, var(--error, #d93025) 9%, transparent);
  color: var(--error, #d93025);
}

.tool-spinner {
  width: 14px;
  height: 14px;
  border: 1.5px solid color-mix(in srgb, var(--accent, #1a73e8) 22%, transparent);
  border-top-color: var(--accent, #1a73e8);
  border-radius: 50%;
  animation: tool-spinner-rotate 900ms linear infinite;
}

@keyframes tool-activity-enter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes tool-spinner-rotate {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .run-activity,
  .tool-call-block {
    animation: none;
  }

  .run-activity__dots i {
    animation: none;
    opacity: 0.55;
  }

  .tool-spinner {
    animation-duration: 1600ms;
  }
}

/* 流式指示器内部元素 */
.stream-stat { color: var(--text-muted, #5f6368); }

.tps-badge {
  border-radius: 4px;
  padding: 1px 6px;
  background: var(--accent, #1a73e8);
  color: #fff;
  font-size: 10.5px;
  font-weight: 500;
}

/* Footer - usage + copy + timestamp（完成时显示） */
.assistant-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-dim, #9aa0a6);
}

.usage-text {
  font-size: 11px;
  color: var(--text-dim, #9aa0a6);
}

.time-text {
  font-size: 10px;
  color: var(--text-dim, #9aa0a6);
  margin-left: auto;
}

.copy-button {
  display: flex;
  align-items: center;
  border: 0;
  background: none;
  color: var(--text-dim, #9aa0a6);
  border-radius: 4px;
  cursor: pointer;
  padding: 2px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease, color 0.12s ease, background 0.12s ease;
}

.copy-button.visible {
  opacity: 1;
  pointer-events: auto;
}

.copy-button:hover {
  color: var(--accent, #1a73e8);
  background: rgba(26, 115, 232, 0.08);
}

.copy-button .material-symbols-outlined {
  font-size: 14px;
}

/* Dark mode */
:global(.dark) .user-bubble {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.08) 100%);
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2), 0 1px 3px rgba(59, 130, 246, 0.1);
}

:global(.dark) .user-bubble:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 2px 4px rgba(59, 130, 246, 0.15);
}
</style>
