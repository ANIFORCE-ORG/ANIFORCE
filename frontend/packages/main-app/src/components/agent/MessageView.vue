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
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="assistant-model-row">
      <span v-if="modelLabel">{{ modelLabel }}</span>
      <span v-if="isStreaming && estimatedTokens > 0" class="stream-stat">↓ {{ estimatedTokens }}</span>
      <span v-if="isStreaming && tps !== null" class="tps-badge">{{ tps.toFixed(1) }} t/s</span>
    </div>

    <div class="assistant-block-list">
      <template v-for="(block, i) in blocks" :key="i">
        <div v-if="block.type === 'text'" class="markdown-body">
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

        <div v-else-if="block.type === 'thinking'" class="thinking-block">
          <button @click="expandedThinking[i] = !expandedThinking[i]">
            <span>Thinking</span>
            <span class="chev">{{ expandedThinking[i] ? '⌃' : '⌄' }}</span>
          </button>
          <div v-if="expandedThinking[i]" class="thinking-content">{{ block.thinking }}</div>
        </div>

        <div v-else-if="block.type === 'toolCall'" class="tool-call-block" :class="{ error: toolResults?.get(toolId(block))?.isError }">
          <button @click="expandedTools[toolId(block)] = !expandedTools[toolId(block)]">
            <span class="tool-name">{{ toolName(block) }}</span>
            <span class="tool-preview">{{ toolPreview(block) }}</span>
            <span class="tool-status">{{ toolResults?.has(toolId(block)) ? (toolResults.get(toolId(block))?.isError ? 'error' : 'done') : 'running' }}</span>
            <span class="chev">{{ expandedTools[toolId(block)] ? '⌃' : '⌄' }}</span>
          </button>
          <template v-if="expandedTools[toolId(block)]">
            <pre class="tool-pre">{{ formatPayload(toolInput(block)) }}</pre>
            <pre v-if="toolResults?.has(toolId(block))" class="tool-pre result">{{ toolResultText(toolResults.get(toolId(block))) || '(no output)' }}</pre>
          </template>
        </div>
      </template>
    </div>

    <div class="assistant-footer">
      <div class="footer-left">
        <span v-if="modelLabel" class="model-badge">{{ modelLabel }}</span>
      </div>

      <div class="footer-right">
        <span v-if="usageText" class="usage-text">{{ usageText }}</span>
        <button v-if="textContent && !isStreaming" class="copy-button" :class="{ visible: hovered || copied }" @click="copy(textContent)">
          <span class="material-symbols-outlined">content_copy</span>
        </button>
      </div>
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
  margin-bottom: 28px;
  padding: 0;
  animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.assistant-model-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 18px;
  margin-bottom: 8px;
  color: var(--text-dim);
  font-size: 11.5px;
  padding-left: 2px;
}

.stream-stat { color: var(--text); }

.tps-badge {
  border-radius: 6px;
  padding: 2px 8px;
  background: var(--accent);
  color: #fff;
  font-size: 10.5px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(59, 130, 246, 0.3);
}

.assistant-block-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: transparent;
  padding: 0;
}

/* Markdown Body - 增加间距和层次 */
.markdown-body {
  color: var(--text);
  font-size: 15px;
  line-height: 1.75;
  word-break: break-word;
  padding: 4px 0;
}

.markdown-body :deep(p) {
  margin: 0 0 12px;
}

.markdown-body :deep(.md-gap) { height: 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

.markdown-body :deep(h1) { font-size: 1.3em; }
.markdown-body :deep(h2) { font-size: 1.15em; }
.markdown-body :deep(h3) { font-size: 1.05em; }

.markdown-body :deep(ul) {
  margin: 8px 0 12px;
  padding-left: 24px;
}

.markdown-body :deep(blockquote) {
  margin: 8px 0;
  border-left: 3px solid var(--border);
  padding: 4px 14px;
  color: var(--text-muted);
  background: rgba(100, 116, 139, 0.04);
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  margin: 12px 0;
  border-collapse: collapse;
  font-size: 13.5px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 8px 12px;
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: var(--bg-panel);
  font-weight: 600;
  font-size: 13px;
}

.markdown-body :deep(code) {
  background: rgba(100, 116, 139, 0.08);
  border: 1px solid rgba(100, 116, 139, 0.1);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: var(--font-mono);
  font-size: 0.9em;
}

/* Code Block - 增加阴影 */
.code-block {
  overflow: hidden;
  margin: 8px 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.06);
}

.code-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-panel);
  color: var(--text-dim);
  font-size: 11.5px;
  font-weight: 500;
}

.code-head button {
  border: 0;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.code-head button:hover {
  color: var(--accent);
  background: rgba(59, 130, 246, 0.08);
}

.code-block pre {
  overflow: auto;
  margin: 0;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
}

/* Tool blocks - 增加圆润和阴影 */
.thinking-block,
.tool-call-block {
  overflow: hidden;
  border: 1px solid var(--outline-variant);
  border-radius: 12px;
  background: var(--surface-container);
  font-size: 12.5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.thinking-block:hover,
.tool-call-block:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.thinking-block > button,
.tool-call-block > button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: 0;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}

.thinking-block > button:hover,
.tool-call-block > button:hover {
  background: rgba(100, 116, 139, 0.04);
}

.thinking-content {
  border-top: 1px solid var(--outline-variant);
  padding: 10px 12px;
  color: var(--text-muted);
  background: var(--surface);
  line-height: 1.6;
  white-space: pre-wrap;
}

.tool-name {
  flex-shrink: 0;
  color: var(--success);
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 11.5px;
}

.tool-preview {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-status,
.chev {
  flex-shrink: 0;
  color: var(--text-dim);
  font-size: 11px;
}

.tool-call-block.error {
  border-color: color-mix(in srgb, var(--error) 40%, var(--outline-variant));
  background: color-mix(in srgb, var(--error) 7%, var(--surface));
}

.tool-call-block.error .tool-name { color: var(--error); }

.tool-pre {
  overflow: auto;
  max-height: 400px;
  margin: 0;
  border-top: 1px solid var(--outline-variant);
  padding: 10px 12px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-pre.result { background: var(--bg); }

.assistant-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  gap: 10px;
}

.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-badge {
  font-size: 11px;
  color: #64748b;
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
}

.usage-text {
  font-size: 11px;
  color: #94a3b8;
}

.copy-button {
  padding: 4px;
  border: 0;
  background: none;
  color: #cbd5e1;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.16s ease;
  opacity: 0;
  pointer-events: none;
}

.copy-button.visible {
  opacity: 1;
  pointer-events: auto;
}

.copy-button:hover {
  color: #137fec;
  background: #eff6ff;
}

.copy-button .material-symbols-outlined {
  font-size: 16px;
}

/* Dark mode */
:global(.dark) .assistant-footer {
  border-top-color: #334155;
}

:global(.dark) .model-badge {
  background: rgba(15, 23, 42, 0.7);
  color: #cbd5e1;
}

:global(.dark) .usage-text {
  color: #94a3b8;
}

:global(.dark) .copy-button:hover {
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.1);
}

/* Dark mode 优化 */
:global(.dark) .user-bubble {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.08) 100%);
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2), 0 1px 3px rgba(59, 130, 246, 0.1);
}

:global(.dark) .user-bubble:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 2px 4px rgba(59, 130, 246, 0.15);
}
</style>
