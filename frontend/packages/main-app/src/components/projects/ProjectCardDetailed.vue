<script setup lang="ts">
import type { Project } from '@/api/projects'

interface Props {
  project: Project
}

const props = defineProps<Props>()
const emit = defineEmits<{
  viewDetail: [project: Project]
}>()

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
}
</script>

<template>
  <div class="project-card-detailed">
    <!-- Project Header -->
    <div class="flex items-start justify-between mb-[12px]">
      <div class="flex-1">
        <div class="flex items-center gap-[9px] mb-[6px]">
          <h4 class="text-[12px] font-semibold text-slate-900 dark:text-white">{{ project.name }}</h4>
          <span
            class="text-[10px] font-semibold px-[6px] py-[2px] rounded-full"
            :class="getStatusColor(project.status)"
          >
            {{ getStatusLabel(project.status) }}
          </span>
        </div>
        <div class="flex items-center gap-[12px] text-[10px] text-slate-500 dark:text-slate-400">
          <span class="flex items-center gap-[4px]">
            <span class="material-symbols-outlined text-[11px]">person</span>
            {{ project.manager }}
          </span>
          <span class="flex items-center gap-[4px]">
            <span class="material-symbols-outlined text-[11px]">calendar_today</span>
            {{ project.start_date }} - {{ project.end_date }}
          </span>
          <span class="flex items-center gap-[4px]">
            <span class="material-symbols-outlined text-[11px]">public</span>
            {{ project.target_market }}
          </span>
        </div>
      </div>
    </div>

    <!-- Project Stats -->
    <div class="grid grid-cols-5 gap-[12px] mb-[12px]">
      <div>
        <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">预算</div>
        <div class="text-[11px] font-semibold text-slate-900 dark:text-white">${{ project.total_budget.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">已消耗</div>
        <div class="text-[11px] font-semibold text-slate-900 dark:text-white">${{ project.spent.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">进度</div>
        <div class="text-[11px] font-semibold text-emerald-600">{{ Math.round((project.spent / project.total_budget) * 100) }}%</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">类型</div>
        <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project.game_type }}</div>
      </div>
      <div>
        <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">状态</div>
        <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ getStatusLabel(project.status) }}</div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="mb-[9px]">
      <div class="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">
        <span>预算使用进度</span>
        <span>{{ Math.round((project.spent / project.total_budget) * 100) }}%</span>
      </div>
      <div class="h-[6px] bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          class="h-full bg-primary rounded-full transition-all"
          :style="{ width: `${Math.round((project.spent / project.total_budget) * 100)}%` }"
        ></div>
      </div>
    </div>

    <!-- Tags -->
    <div class="flex items-center gap-[6px] flex-wrap mb-[9px]">
      <span
        v-for="tag in project.tags"
        :key="tag"
        class="text-[10px] px-[6px] py-[4px] rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
      >
        {{ tag }}
      </span>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-[6px] pt-[9px] border-t border-slate-200 dark:border-slate-700">
      <button
        class="flex-1 px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        @click="emit('viewDetail', project)"
      >
        查看详情
      </button>
    </div>
  </div>
</template>

<style scoped>
.project-card-detailed {
  padding: 16px;
  border-radius: 6px;
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
