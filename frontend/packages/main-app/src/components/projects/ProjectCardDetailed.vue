<script setup lang="ts">
import type { Project } from '@/api/projects'

interface Props {
  project: Project
  mode?: 'page' | 'workspace' | 'readonly'
}

withDefaults(defineProps<Props>(), {
  mode: 'page'
})
const emit = defineEmits<{
  viewDetail: [project: Project]
}>()

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    running: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
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
  <div class="project-card-detailed">
    <!-- Project Header -->
    <div class="flex items-start justify-between mb-4">
      <div class="flex-1">
        <div class="flex items-center gap-3 mb-2">
          <h4 class="text-base font-semibold text-slate-900 dark:text-white">{{ project.name }}</h4>
          <span
            class="status-chip"
            :data-status="project.status"
            :class="getStatusColor(project.status)"
          >
            {{ getStatusLabel(project.status) }}
          </span>
        </div>
        <div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
          <span class="flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">person</span>
            {{ project.manager }}
          </span>
          <span class="flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">calendar_today</span>
            {{ project.start_date }} - {{ project.end_date }}
          </span>
          <span class="flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">public</span>
            {{ project.target_market }}
          </span>
        </div>
      </div>
    </div>

    <!-- Project Stats -->
    <div class="grid grid-cols-5 gap-4 mb-4">
      <div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">预算</div>
        <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.total_budget.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
        <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.spent.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">进度</div>
        <div class="text-sm font-semibold text-emerald-600">{{ Math.round((project.spent / project.total_budget) * 100) }}%</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">类型</div>
        <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.game_type }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">状态</div>
        <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ getStatusLabel(project.status) }}</div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="mb-3">
      <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
        <span>预算使用进度</span>
        <span>{{ Math.round((project.spent / project.total_budget) * 100) }}%</span>
      </div>
      <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          class="h-full bg-primary rounded-full transition-all"
          :style="{ width: `${Math.round((project.spent / project.total_budget) * 100)}%` }"
        ></div>
      </div>
    </div>

    <!-- Tags -->
    <div class="flex items-center gap-2 flex-wrap mb-3">
      <span
        v-for="tag in project.tags"
        :key="tag"
        class="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
      >
        {{ tag }}
      </span>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-2 pt-3 border-t border-slate-200 dark:border-slate-700">
      <button
        v-if="mode !== 'readonly'"
        class="flex-1 px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        @click="emit('viewDetail', project)"
      >
        {{ mode === 'workspace' ? '在画布查看' : '查看详情' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.project-card-detailed {
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  transition: all 0.16s ease;
}

.project-card-detailed:hover {
  border-color: rgba(19, 127, 236, 0.5);
}

.dark .project-card-detailed {
  background: rgba(30, 41, 59, 0.5);
  border-color: #334155;
}

.dark .project-card-detailed:hover {
  border-color: rgba(59, 130, 246, 0.5);
}
</style>
