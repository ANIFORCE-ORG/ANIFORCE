<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { AgentMessage } from '@/api/agent'
import type { AgentPhase, AgentTimelineBlock } from '@/composables/useAgentSession'
import MessageView from './MessageView.vue'
import ChatInput from './ChatInput.vue'
import TimelineBlockRenderer from './timeline/TimelineBlockRenderer.vue'

const props = defineProps<{
  messages: AgentMessage[]
  streamingMessage: AgentMessage | null
  isStreaming: boolean
  agentPhase: AgentPhase
  models: Array<{ id: string; name: string; provider: string }>
  selectedModel?: { provider: string; modelId: string } | null
  modelNames?: Record<string, string>
  retryInfo?: { attempt: number; maxAttempts: number; errorMessage?: string } | null
  commandStatus?: string | null
  timelineBlocks?: AgentTimelineBlock[]
  loading?: boolean
  error?: string | null
}>()
const emit = defineEmits<{
  send: [message: string, images?: Array<{ type: 'image'; data: string; mimeType: string }>]
  abort: []
  modelChange: [provider: string, modelId: string]
  timelineAction: [action: string, payload: Record<string, unknown>]
}>()

const scroller = ref<HTMLElement | null>(null)
function messageText(message: AgentMessage): string {
  const content = message.content
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content.map(block => {
    if (!block || typeof block !== 'object') return ''
    const typed = block as { type?: unknown; text?: unknown }
    return typed.type === 'text' && typeof typed.text === 'string' ? typed.text : ''
  }).join('\n')
}

const visibleMessages = computed(() => props.messages.filter(m => m.role === 'user' || (m.role === 'assistant' && messageText(m).trim().length > 0)))
const toolResults = computed(() => {
  const map = new Map<string, AgentMessage>()
  for (const msg of props.messages) {
    if (msg.role === 'toolResult' && typeof msg.toolCallId === 'string') map.set(msg.toolCallId, msg)
  }
  return map
})
const empty = computed(() => !props.loading && visibleMessages.value.length === 0 && !props.streamingMessage && !props.isStreaming && !props.timelineBlocks?.length)
function phaseLabel(phase: AgentPhase): string {
  if (phase?.kind === 'queued') return 'Queued for worker...'
  if (phase?.kind === 'running_tools') {
    const names = phase.tools.map((t: { name: string }) => t.name)
    if (!names.length) return 'Running tool...'
    if (names.length === 1) return `Running ${names[0]}...`
    return `Running ${names.slice(0, 2).join(', ')}${names.length > 2 ? ` (+${names.length - 2})` : ''}...`
  }
  if (phase?.kind === 'waiting_model') return 'Waiting for model...'
  return 'Thinking...'
}
function scrollBottom(behavior: ScrollBehavior = 'smooth'): void {
  nextTick(() => scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior }))
}
watch(() => [props.messages.length, props.streamingMessage], () => scrollBottom(), { deep: false })
</script>

<template>
  <div class="chat-window">
    <div v-if="loading" class="center-note">Loading session...</div>
    <div v-else-if="error" class="center-note error">{{ error }}</div>
    <template v-else>
      <div v-if="empty" class="empty-wrap">
        <div class="hero-title">
          <span>Nova Agent Studio</span>
          <em>helps you think, build, and finish.<b>▍</b></em>
        </div>
        <ChatInput
          :is-streaming="isStreaming"
          :models="models"
          :selected-model="selectedModel"
          :retry-info="retryInfo"
          :command-status="commandStatus"
          @send="(message, images) => emit('send', message, images)"
          @abort="emit('abort')"
          @model-change="(p, m) => emit('modelChange', p, m)"
        />
      </div>
      <template v-else>
        <div ref="scroller" class="message-scroll">
          <div class="message-column">
            <template v-for="(message, index) in visibleMessages" :key="message.id || `${message.role}-${message.timestamp}-${index}`">
              <MessageView
                :message="message"
                :tool-results="toolResults"
                :model-names="modelNames"
                :prev-timestamp="index > 0 ? Number(visibleMessages[index - 1].timestamp || 0) : undefined"
              />
            </template>
            <MessageView
              v-if="streamingMessage"
              :message="streamingMessage"
              is-streaming
              :tool-results="toolResults"
              :model-names="modelNames"
            />
            <div v-if="timelineBlocks?.length" class="timeline-blocks">
              <TimelineBlockRenderer
                v-for="block in timelineBlocks"
                :key="block.id"
                :block="block"
                @action="(action, payload) => emit('timelineAction', action, payload)"
              />
            </div>
            <div v-if="isStreaming && !streamingMessage" class="phase-line">{{ phaseLabel(agentPhase) }}</div>
          </div>
        </div>
        <ChatInput
          :is-streaming="isStreaming"
          :models="models"
          :selected-model="selectedModel"
          :retry-info="retryInfo"
          :command-status="commandStatus"
          @send="(message, images) => emit('send', message, images)"
          @abort="emit('abort')"
          @model-change="(p, m) => emit('modelChange', p, m)"
        />
      </template>
    </template>
  </div>
</template>

<style scoped>
.chat-window { position: relative; display: flex; flex-direction: column; height: 100%; overflow: hidden; background: var(--bg); }
.center-note { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 14px; }
.center-note.error { color: var(--error); }
.empty-wrap { display: flex; flex: 1; flex-direction: column; justify-content: center; overflow-y: auto; padding: 32px 0; }
.hero-title { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; max-width: 820px; margin: 0 auto 12px; padding: 0 68px 0 16px; font-family: var(--font-mono); }
.hero-title span { color: var(--text); font-size: 22px; font-weight: 700; letter-spacing: -.01em; }
.hero-title em { min-width: 0; overflow: hidden; color: var(--text-muted); font-size: 14px; font-style: normal; white-space: nowrap; text-overflow: ellipsis; }
.hero-title b { color: var(--accent); font-weight: 400; }
.message-scroll { flex: 1; overflow-y: auto; padding-top: 16px; scrollbar-width: none; }
.message-column { max-width: 820px; margin: 0 auto; padding: 0 52px 0 16px; }
.timeline-blocks { display: flex; flex-direction: column; gap: 10px; margin: 4px 0 18px; }
.phase-line { padding: 8px 0 20px; color: var(--text-muted); font-size: 13px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{ opacity:.45 } 50%{ opacity:1 } }
</style>
