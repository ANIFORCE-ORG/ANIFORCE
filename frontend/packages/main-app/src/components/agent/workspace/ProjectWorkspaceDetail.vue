<script setup lang="ts">
import { computed } from 'vue'
import type { Project } from '@/api/projects'

const props = defineProps<{
  project: Project
}>()

const emit = defineEmits<{
  back: []
  analyze: [project: Project]
  openFullPage: [project: Project]
}>()

const totalBudget = computed(() => Number(props.project.total_budget || 0))
const spent = computed(() => Number(props.project.spent || 0))
const budgetUsage = computed(() => {
  if (!totalBudget.value) return 0
  return Math.min(100, Math.round((spent.value / totalBudget.value) * 100))
})
const remainingBudget = computed(() => Math.max(0, totalBudget.value - spent.value))

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    active: '进行中',
    running: '进行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
}
</script>

<template>
  <section class="space-y-5">
    <div class="flex items-center justify-between gap-3">
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-md px-1 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
        @click="emit('back')"
      >
        <span class="material-symbols-outlined text-base">arrow_back</span>
        项目列表
      </button>
      <span class="status-chip" :data-status="project.status">
        {{ getStatusLabel(project.status) }}
      </span>
    </div>

    <article class="rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <header class="border-b border-slate-100 px-5 py-5 dark:border-slate-800">
        <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="mb-2 flex items-center gap-2 text-xs text-slate-400">
            <span class="material-symbols-outlined text-base">folder_managed</span>
            Project
          </div>
          <h3 class="text-xl font-semibold text-slate-950 dark:text-white">{{ project.name }}</h3>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">
            {{ project.description || `${project.game_type} · ${project.target_market}` }}
          </p>
        </div>
        <div class="shrink-0 text-right">
          <div class="text-xs text-slate-400">预算使用</div>
          <div class="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">{{ budgetUsage }}%</div>
        </div>
        </div>
      </header>

      <section class="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
        <div class="mb-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>${{ spent.toLocaleString() }} used of ${{ totalBudget.toLocaleString() }}</span>
          <span>${{ remainingBudget.toLocaleString() }} remaining</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div class="h-full rounded-full bg-slate-900 dark:bg-white" :style="{ width: `${budgetUsage}%` }"></div>
        </div>
      </section>

      <section class="grid gap-0 divide-y divide-slate-100 px-5 py-2 dark:divide-slate-800">
        <div class="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4 py-2.5 text-sm">
          <span class="text-slate-500 dark:text-slate-400">目标市场</span>
          <span class="truncate font-medium text-slate-900 dark:text-white">{{ project.target_market || '-' }}</span>
        </div>
        <div class="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4 py-2.5 text-sm">
          <span class="text-slate-500 dark:text-slate-400">负责人</span>
          <span class="truncate font-medium text-slate-900 dark:text-white">{{ project.manager || '-' }}</span>
        </div>
        <div class="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4 py-2.5 text-sm">
          <span class="text-slate-500 dark:text-slate-400">品类</span>
          <span class="truncate font-medium text-slate-900 dark:text-white">{{ project.game_type || '-' }}</span>
        </div>
        <div v-if="project.tags?.length" class="grid grid-cols-[96px_minmax(0,1fr)] items-start gap-4 py-2.5 text-sm">
          <span class="text-slate-500 dark:text-slate-400">标签</span>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="tag in project.tags"
              :key="tag"
              class="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </section>
    </article>

    <section class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/60">
      <div class="mb-3 flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        <span class="material-symbols-outlined text-base">auto_awesome</span>
        Agent 下一步
      </div>
      <div class="grid gap-2 sm:grid-cols-2">
        <button
          class="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-white hover:bg-primary/90 dark:bg-primary dark:text-white dark:hover:bg-primary/90"
          @click="emit('analyze', project)"
        >
          <span class="material-symbols-outlined text-base">query_stats</span>
          分析项目
        </button>
        <button
          class="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          @click="emit('openFullPage', project)"
        >
          <span class="material-symbols-outlined text-base">open_in_new</span>
          完整页面
        </button>
      </div>
    </section>
  </section>
</template>
