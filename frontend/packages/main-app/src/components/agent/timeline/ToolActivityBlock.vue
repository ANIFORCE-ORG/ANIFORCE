<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTimelineBlock } from '@/composables/useHomeAgentSession'

type ToolActivityTimelineBlock = Extract<AgentTimelineBlock, { type: 'tool_activity' }>

const props = defineProps<{
  block: ToolActivityTimelineBlock
}>()

const status = computed(() => props.block.status)
const title = computed(() => props.block.title)
const summary = computed(() => props.block.summary || '')
const toolName = computed(() => String(props.block.toolName || 'tool'))

const statusMeta = computed(() => {
  if (status.value === 'completed') return { icon: 'check', tone: 'completed' }
  if (status.value === 'error') return { icon: 'priority_high', tone: 'error' }
  return { icon: 'pending', tone: 'running' }
})
</script>

<template>
  <div class="tool-indicator" :class="statusMeta.tone">
    <span class="status-dot" :class="statusMeta.tone">
      <span v-if="status === 'completed'" class="material-symbols-outlined check-icon">{{ statusMeta.icon }}</span>
      <span v-else-if="status === 'error'" class="material-symbols-outlined error-icon">{{ statusMeta.icon }}</span>
      <span v-else class="pulse-ring"></span>
    </span>
    <div class="indicator-copy">
      <strong>{{ title }}</strong>
      <span v-if="summary" class="summary">{{ summary }}</span>
      <small>{{ toolName }}</small>
    </div>
  </div>
</template>

<style scoped>
.tool-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  padding: 8px 12px;
  background: rgba(248, 250, 252, 0.6);
  backdrop-filter: blur(8px);
  font-size: 12px;
  animation: slide-in .28s cubic-bezier(.2, .8, .2, 1) both;
  transition: all .18s ease;
}
.tool-indicator:hover {
  background: rgba(248, 250, 252, 0.85);
  box-shadow: 0 4px 12px rgba(15, 23, 42, .04);
}
.status-dot {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.1);
}
.status-dot.running {
  background: rgba(37, 99, 235, 0.12);
}
.status-dot.completed {
  background: rgba(5, 150, 105, 0.12);
}
.status-dot.error {
  background: rgba(220, 38, 38, 0.12);
}
.pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.4) 0%, transparent 70%);
  animation: pulse .8s ease-in-out infinite;
}
.check-icon {
  color: #059669;
  font-size: 14px;
  font-variation-settings: 'FILL' 1, 'wght' 600, 'GRAD' 0, 'opsz' 20;
  animation: check-pop .32s cubic-bezier(.34, 1.56, .64, 1) both;
}
.error-icon {
  color: #dc2626;
  font-size: 14px;
  font-variation-settings: 'FILL' 1, 'wght' 600, 'GRAD' 0, 'opsz' 20;
}
.indicator-copy {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.indicator-copy strong {
  overflow: hidden;
  color: rgb(30, 41, 59);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.indicator-copy .summary {
  flex-shrink: 0;
  color: rgb(100, 116, 139);
  font-size: 11px;
}
.indicator-copy small {
  margin-left: auto;
  flex-shrink: 0;
  color: rgb(148, 163, 184);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
}
.tool-indicator.completed {
  border-color: rgba(5, 150, 105, 0.16);
  background: rgba(220, 252, 231, 0.4);
}
.tool-indicator.error {
  border-color: rgba(220, 38, 38, 0.16);
  background: rgba(254, 226, 226, 0.4);
}
@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.4);
  }
}
@keyframes check-pop {
  0% {
    opacity: 0;
    transform: scale(0.6);
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}
:global(.dark) .tool-indicator {
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.6);
}
:global(.dark) .tool-indicator:hover {
  background: rgba(30, 41, 59, 0.75);
}
:global(.dark) .tool-indicator.completed {
  border-color: rgba(5, 150, 105, 0.22);
  background: rgba(5, 150, 105, 0.08);
}
:global(.dark) .tool-indicator.error {
  border-color: rgba(220, 38, 38, 0.22);
  background: rgba(220, 38, 38, 0.08);
}
:global(.dark) .indicator-copy strong {
  color: rgb(226, 232, 240);
}
:global(.dark) .pulse-ring {
  background: radial-gradient(circle, rgba(96, 165, 250, 0.5) 0%, transparent 70%);
}
:global(.dark) .check-icon {
  color: #6ee7b7;
}
:global(.dark) .error-icon {
  color: #fca5a5;
}
</style>
