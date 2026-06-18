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
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  font-size: 12px;
  animation: slide-in .28s cubic-bezier(.2, .8, .2, 1) both;
  transition: all .15s ease;
}
.tool-indicator:hover {
  background: #f1f5f9;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
  background: rgba(19, 127, 236, 0.15);
}
.status-dot.completed {
  background: rgba(16, 185, 129, 0.15);
}
.status-dot.error {
  background: rgba(239, 68, 68, 0.15);
}
.pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.4) 0%, transparent 70%);
  animation: pulse .8s ease-in-out infinite;
}
.check-icon {
  color: #10b981;
  font-size: 14px;
  font-variation-settings: 'FILL' 1, 'wght' 600, 'GRAD' 0, 'opsz' 20;
}
.error-icon {
  color: #ef4444;
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
  border-color: #a7f3d0;
  background: #d1fae5;
}
.tool-indicator.error {
  border-color: #fecaca;
  background: #fee2e2;
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

@media (prefers-reduced-motion: reduce) {
  .tool-indicator {
    animation: none;
  }
  .pulse-ring {
    animation: none;
    opacity: 0.6;
  }
}
:global(.dark) .tool-indicator {
  border-color: #334155;
  background: #1e293b;
}
:global(.dark) .tool-indicator:hover {
  background: #334155;
}
:global(.dark) .tool-indicator.completed {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.1);
}
:global(.dark) .tool-indicator.error {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.1);
}
:global(.dark) .indicator-copy strong {
  color: rgb(226, 232, 240);
}
:global(.dark) .pulse-ring {
  background: radial-gradient(circle, rgba(19, 127, 236, 0.5) 0%, transparent 70%);
}
:global(.dark) .check-icon {
  color: #34d399;
}
:global(.dark) .error-icon {
  color: #f87171;
}
</style>
