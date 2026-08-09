<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTimelineBlock } from '@/composables/useAgentSession'

type PlanTimelineBlock = Extract<AgentTimelineBlock, { type: 'plan' }>

const props = defineProps<{
  block: PlanTimelineBlock
}>()

type TodoStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
interface TodoItem { id: string; title: string; description?: string; status: TodoStatus }

const todos = computed<TodoItem[]>(() => props.block.todos.map((todo, index) => ({
  id: String(todo.id || `todo_${index + 1}`),
  title: String(todo.title || `步骤 ${index + 1}`),
  description: todo.description ? String(todo.description) : undefined,
  status: normalizeStatus(todo.status),
})))

const progress = computed(() => {
  if (!todos.value.length) return 0
  const done = todos.value.filter(todo => todo.status === 'completed' || todo.status === 'skipped').length
  return Math.round(done / todos.value.length * 100)
})

function normalizeStatus(value: unknown): TodoStatus {
  if (value === 'running' || value === 'completed' || value === 'failed' || value === 'skipped') return value
  return 'pending'
}

function icon(status: TodoStatus): string {
  if (status === 'completed') return '✓'
  if (status === 'running') return '…'
  if (status === 'failed') return '!'
  if (status === 'skipped') return '-'
  return '○'
}
</script>

<template>
  <section class="plan-block">
    <header>
      <div>
        <span class="eyebrow">Plan</span>
        <h3>执行计划</h3>
      </div>
      <span>{{ progress }}%</span>
    </header>
    <div class="progress"><i :style="{ width: `${progress}%` }"></i></div>
    <ol>
      <li v-for="todo in todos" :key="todo.id" :class="todo.status">
        <span>{{ icon(todo.status) }}</span>
        <div>
          <strong>{{ todo.title }}</strong>
          <p v-if="todo.description">{{ todo.description }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.plan-block { border: 1px solid color-mix(in srgb, var(--accent) 20%, var(--outline-variant)); border-radius: 16px; padding: 13px; background: color-mix(in srgb, var(--accent) 5%, var(--surface)); }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 9px; }
.eyebrow { display: block; margin-bottom: 2px; color: var(--accent); font-size: 10px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
h3 { margin: 0; color: var(--text); font-size: 15px; }
header > span { border-radius: 999px; padding: 3px 8px; background: var(--bg-selected); color: var(--accent); font-size: 11px; }
.progress { overflow: hidden; height: 4px; border-radius: 999px; background: var(--outline-variant); margin-bottom: 10px; }
.progress i { display: block; height: 100%; border-radius: inherit; background: var(--accent); transition: width .2s; }
ol { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
li { display: flex; gap: 9px; align-items: flex-start; color: var(--text-muted); }
li > span { display: grid; place-items: center; flex-shrink: 0; width: 18px; height: 18px; border-radius: 999px; background: var(--surface); color: var(--text-dim); font-size: 11px; font-weight: 700; }
li strong { color: var(--text); font-size: 12px; }
li p { margin: 2px 0 0; font-size: 11px; line-height: 1.4; }
li.running > span { color: var(--accent); animation: pulse 1.2s infinite; }
li.completed > span { color: var(--success); }
li.failed > span { color: var(--error); }
@keyframes pulse { 0%,100%{ opacity:.45 } 50%{ opacity:1 } }
</style>
