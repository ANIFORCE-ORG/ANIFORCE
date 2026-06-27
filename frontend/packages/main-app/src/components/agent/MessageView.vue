<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import type { AgentMessage } from '@/api/agent'
import ActivityMessageView from './ActivityMessageView.vue'

const props = defineProps<{
  message: AgentMessage
  isStreaming?: boolean
  toolResults?: Map<string, AgentMessage>
  modelNames?: Record<string, string>
  prevTimestamp?: number
}>()

const hovered = ref(false)
const copied = ref(false)
const expandedThinking = ref<Record<number, boolean>>({})
const expandedTools = ref<Record<string, boolean>>({})
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

// Thinking block 耗时追踪（参考 CustomPiAgent）
// 每个 block 首次出现时记录开始时间；下一个 block 出现时计算耗时
const blockStartTimes = ref<Record<number, number>>({})
const thinkingDurations = ref<Record<number, number>>({})
const liveThinkingMs = ref(0) // 流式中实时更新的毫秒数
let liveTimer: number | null = null

watch(blocks, (newBlocks) => {
  const now = Date.now()
  newBlocks.forEach((_, i) => {
    if (blockStartTimes.value[i] === undefined) {
      blockStartTimes.value[i] = now
    }
  })
  // 当非末尾 block 已有后继 block 开始时，计算其耗时
  for (let i = 0; i < newBlocks.length - 1; i++) {
    if (thinkingDurations.value[i] === undefined && blockStartTimes.value[i] !== undefined) {
      const start = blockStartTimes.value[i]
      const nextStart = blockStartTimes.value[i + 1] ?? now
      const secs = Math.round((nextStart - start) / 1000)
      if (secs > 0) thinkingDurations.value[i] = secs
    }
  }
}, { deep: true, immediate: true })

// 流式中实时更新末尾 thinking block 的耗时
watch(() => [props.isStreaming, blocks.value.length] as const, ([streaming]) => {
  if (streaming) {
    if (liveTimer) window.clearInterval(liveTimer)
    liveTimer = window.setInterval(() => {
      liveThinkingMs.value = Date.now()
    }, 200)
  } else {
    if (liveTimer) window.clearInterval(liveTimer)
    liveTimer = null
    // 流式结束时，计算未完成的 thinking block 耗时
    const now = Date.now()
    const newDurations = { ...thinkingDurations.value }
    blocks.value.forEach((block, i) => {
      if (block.type === 'thinking' && newDurations[i] === undefined && blockStartTimes.value[i] !== undefined) {
        const secs = Math.round((now - blockStartTimes.value[i]) / 1000)
        if (secs > 0) newDurations[i] = secs
      }
    })
    thinkingDurations.value = newDurations
  }
}, { immediate: true })

function thinkingDuration(index: number): number | undefined {
  // 优先用后端历史重建给的 duration
  const block = blocks.value[index]
  if (block && typeof block === 'object' && 'duration' in block && typeof block.duration === 'number') {
    return block.duration
  }
  // 已有前端实时计算值
  if (thinkingDurations.value[index] !== undefined) {
    return thinkingDurations.value[index]
  }
  // 流式中：实时计算
  if (props.isStreaming && blockStartTimes.value[index] !== undefined) {
    const secs = Math.round((liveThinkingMs.value - blockStartTimes.value[index]) / 1000)
    return secs > 0 ? secs : undefined
  }
  return undefined
}

function thinkingCharCount(index: number): number {
  const block = blocks.value[index]
  if (block && typeof block === 'object' && block.type === 'thinking') {
    return String(block.thinking || '').length
  }
  return 0
}

// 流式阶段判断
const hasTextOutput = computed(() => blocks.value.some(b => b.type === 'text' && String(b.text || '').trim()))
const hasThinkingOnly = computed(() => props.isStreaming && blocks.value.some(b => b.type === 'thinking') && !hasTextOutput.value && !blocks.value.some(b => b.type === 'toolCall'))
const hasRunningTools = computed(() => props.isStreaming && blocks.value.some(b => b.type === 'toolCall' && !hasToolResult(b)))
function isLastBlock(index: number): boolean {
  return index === blocks.value.length - 1
}
function isThinkingExpanded(index: number): boolean {
  // 流式中且是当前正在输出的 thinking block：默认展开
  if (props.isStreaming && isLastBlock(index) && blocks.value[index]?.type === 'thinking') {
    return expandedThinking.value[index] ?? true
  }
  return expandedThinking.value[index] ?? false
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

onUnmounted(() => { if (tpsTimer) window.clearInterval(tpsTimer); if (liveTimer) window.clearInterval(liveTimer) })

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

function toolId(block: Record<string, unknown>): string {
  return String(block.toolCallId || block.id || '')
}
function toolName(block: Record<string, unknown>): string {
  return String(block.toolName || block.name || 'tool')
}
function toolInput(block: Record<string, unknown>): unknown {
  return block.input || block.arguments || {}
}
function toolPreview(block: Record<string, unknown>): string {
  const input = toolInput(block)
  if (!input || typeof input !== 'object' || Array.isArray(input)) return ''
  const record = input as Record<string, unknown>
  for (const key of ['command', 'path', 'file_path', 'pattern', 'query']) {
    if (record[key]) return String(record[key]).slice(0, 120)
  }
  const first = Object.keys(record)[0]
  return first ? String(record[first]).slice(0, 120) : ''
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

function toolResultText(result?: AgentMessage): string {
  if (!result) return ''
  return messageText(result)
}
function hasToolResult(block: Record<string, unknown>): boolean {
  return props.toolResults?.has(toolId(block)) || block.result !== undefined
}
function isToolError(block: Record<string, unknown>): boolean {
  return !!props.toolResults?.get(toolId(block))?.isError
}
function toolBlockResultText(block: Record<string, unknown>): string {
  const paired = props.toolResults?.get(toolId(block))
  if (paired) return toolResultText(paired)
  return formatPayload(block.result)
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
    :class="{ 'is-streaming': isStreaming, 'phase-thinking': isStreaming && hasThinkingOnly, 'phase-text': isStreaming && hasTextOutput, 'phase-tools': isStreaming && hasRunningTools }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- 流式指示器：只在有文本输出时显示 -->
    <div v-if="isStreaming && hasTextOutput" class="streaming-indicators">
      <span v-if="estimatedTokens > 0" class="stream-stat">↓ {{ estimatedTokens }}</span>
      <span v-if="tps !== null" class="tps-badge">{{ tps.toFixed(1) }} t/s</span>
    </div>

    <!-- 等待首块：脉冲点动效 -->
    <div v-if="isStreaming && blocks.length === 0" class="waiting-indicator">
      <span class="waiting-dot"></span>
      <span class="waiting-dot"></span>
      <span class="waiting-dot"></span>
    </div>

    <!-- Block 列表：thinking / text / toolCall 平级渲染 -->
    <div class="assistant-block-list">
      <template v-for="(block, i) in blocks" :key="i">
        <!-- Thinking Block: 流式时展开，完成后折叠 -->
        <div v-if="block.type === 'thinking'" class="thinking-block" :class="{ 'is-streaming-thinking': isStreaming }">
          <button class="thinking-header" @click="expandedThinking[i] = !expandedThinking[i]">
            <span class="thinking-dot" :class="{ active: isStreaming && isLastBlock(i) }"></span>
            <span class="thinking-label">Thinking</span>
            <span v-if="thinkingCharCount(i) > 0 && !isStreaming" class="thinking-char-hint">{{ thinkingCharCount(i) }} 字</span>
            <span v-if="thinkingDuration(i) !== undefined" class="thinking-duration">{{ thinkingDuration(i) }}s</span>
            <svg class="thinking-chevron" :class="{ expanded: isThinkingExpanded(i) }" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="2 3.5 5 6.5 8 3.5" />
            </svg>
          </button>
          <transition name="thinking-slide">
            <div v-if="isThinkingExpanded(i)" class="thinking-content">
              {{ block.thinking }}
              <span v-if="isStreaming && isLastBlock(i)" class="thinking-cursor">▍</span>
            </div>
          </transition>
        </div>

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

        <!-- Tool Call Block: 紧凑卡片，运行中带脉冲 -->
        <div v-else-if="block.type === 'toolCall'" class="tool-call-block" :class="{ error: isToolError(block), 'is-running': isStreaming && !hasToolResult(block) }">
          <button class="tool-header" @click="expandedTools[toolId(block)] = !expandedTools[toolId(block)]">
            <span class="tool-status-dot" :class="hasToolResult(block) ? (isToolError(block) ? 'error' : 'done') : 'running'"></span>
            <span class="tool-name">{{ toolName(block) }}</span>
            <span class="tool-preview">{{ toolPreview(block) }}</span>
            <svg class="tool-chevron" :class="{ expanded: expandedTools[toolId(block)] }" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="2 3.5 5 6.5 8 3.5" />
            </svg>
          </button>
          <template v-if="expandedTools[toolId(block)]">
            <pre class="tool-pre">{{ formatPayload(toolInput(block)) }}</pre>
            <pre v-if="hasToolResult(block)" class="tool-pre result">{{ toolBlockResultText(block) || '(no output)' }}</pre>
          </template>
        </div>
      </template>
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

/* thinking 阶段：左侧蓝色脉冲条 */
.assistant-message.phase-thinking::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--accent, #1a73e8);
  border-radius: 1px;
  animation: phase-pulse 1.5s ease-in-out infinite;
  opacity: 0.6;
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

/* 等待首块脉冲点 */
.waiting-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
}

.waiting-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent, #1a73e8);
  animation: waiting-bounce 1.4s ease-in-out infinite;
}

.waiting-dot:nth-child(2) { animation-delay: 0.2s; }
.waiting-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes waiting-bounce {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.1); }
}

/* Block 列表：thinking / text / toolCall 平级 */
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

/* Thinking Block - 对齐 CustomPiAgent: 折叠卡片 + 耗时 */
.thinking-block {
  overflow: hidden;
  border: 1px solid var(--outline-variant, #e8eaed);
  border-radius: 12px;
  background: var(--surface-container, #f8fafd);
  font-size: 12px;
  transition: border-color 0.2s ease;
}

/* 流式 thinking：边框高亮 + 轻微脉冲 */
.thinking-block.is-streaming-thinking {
  border-color: color-mix(in srgb, var(--accent, #1a73e8) 40%, var(--outline-variant, #e8eaed));
  animation: thinking-glow 2s ease-in-out infinite;
}

@keyframes thinking-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(26, 115, 232, 0); }
  50% { box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.08); }
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: 0;
  background: none;
  color: var(--text-muted, #5f6368);
  cursor: pointer;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  transition: background 0.12s ease;
}

.thinking-header:hover {
  background: rgba(100, 116, 139, 0.05);
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-dim, #9aa0a6);
  flex-shrink: 0;
  transition: background 0.2s ease;
}

.thinking-dot.active {
  background: var(--accent, #1a73e8);
  animation: thinking-pulse 1.5s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.1); }
}

.thinking-label {
  flex: 1;
}

.thinking-duration {
  font-size: 11px;
  color: var(--text-dim, #9aa0a6);
  font-variant-numeric: tabular-nums;
}

.thinking-char-hint {
  font-size: 10px;
  color: var(--text-dim, #9aa0a6);
  opacity: 0.7;
}

.thinking-chevron {
  flex-shrink: 0;
  color: var(--text-dim, #9aa0a6);
  transform: rotate(0deg);
  transition: transform 0.15s ease;
}

.thinking-chevron.expanded {
  transform: rotate(180deg);
}

.thinking-content {
  border-top: 1px solid var(--outline-variant, #e8eaed);
  padding: 10px 12px;
  color: var(--text-muted, #5f6368);
  background: var(--surface, #fff);
  line-height: 1.6;
  white-space: pre-wrap;
  font-size: 12px;
}

/* thinking 流式光标 */
.thinking-cursor {
  display: inline-block;
  color: var(--accent, #1a73e8);
  animation: cursor-blink 1s steps(2) infinite;
  margin-left: 1px;
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* thinking 展开/折叠过渡 */
.thinking-slide-enter-active,
.thinking-slide-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  max-height: 500px;
  overflow: hidden;
}
.thinking-slide-enter-from,
.thinking-slide-leave-to {
  max-height: 0;
  opacity: 0;
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

/* Tool Call Block - 紧凑卡片 */
.tool-call-block {
  overflow: hidden;
  border: 1px solid var(--outline-variant, #e8eaed);
  border-radius: 8px;
  background: var(--surface-container, #f8fafd);
  font-size: 12px;
  transition: border-color 0.2s ease;
}

/* 运行中：边框高亮 + 轻微脉冲 */
.tool-call-block.is-running {
  border-color: color-mix(in srgb, #f9ab00 40%, var(--outline-variant, #e8eaed));
  animation: tool-glow 1.8s ease-in-out infinite;
}

@keyframes tool-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(249, 171, 0, 0); }
  50% { box-shadow: 0 0 0 3px rgba(249, 171, 0, 0.1); }
}

.tool-call-block.error {
  border-color: color-mix(in srgb, var(--error, #d93025) 40%, var(--outline-variant, #e8eaed));
  background: color-mix(in srgb, var(--error, #d93025) 7%, var(--surface, #fff));
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: 0;
  background: none;
  color: var(--text-muted, #5f6368);
  cursor: pointer;
  text-align: left;
  font-size: 12px;
  transition: background 0.12s ease;
  min-width: 0;
}

.tool-header:hover {
  background: rgba(100, 116, 139, 0.05);
}

.tool-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tool-status-dot.running {
  background: var(--accent, #1a73e8);
  animation: thinking-pulse 1.5s ease-in-out infinite;
}

.tool-status-dot.done {
  background: var(--success, #188038);
}

.tool-status-dot.error {
  background: var(--error, #d93025);
}

.tool-name {
  flex-shrink: 0;
  color: var(--text, #202124);
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  font-size: 11.5px;
}

.tool-call-block.error .tool-name {
  color: var(--error, #d93025);
}

.tool-preview {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--text-dim, #9aa0a6);
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-chevron {
  flex-shrink: 0;
  color: var(--text-dim, #9aa0a6);
  transform: rotate(0deg);
  transition: transform 0.15s ease;
}

.tool-chevron.expanded {
  transform: rotate(180deg);
}

.tool-pre {
  overflow: auto;
  max-height: 400px;
  margin: 0;
  border-top: 1px solid var(--outline-variant, #e8eaed);
  padding: 10px 12px;
  background: var(--surface, #fff);
  color: var(--text-muted, #5f6368);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono, monospace);
}

.tool-pre.result { background: var(--bg, #fff); }

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
