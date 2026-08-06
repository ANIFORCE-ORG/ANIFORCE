<script setup lang="ts">
import type { Campaign } from '@/api/campaigns'

withDefaults(defineProps<{
  campaigns: Campaign[]
  updatingIds?: Set<string>
  embedded?: boolean
}>(), {
  updatingIds: () => new Set<string>(),
  embedded: false
})

const emit = defineEmits<{
  view: [campaignId: string]
  toggleStatus: [campaign: Campaign]
}>()

function getStatusText(status: string) {
  const statusMap: Record<string, string> = {
    running: '进行中',
    review: '审核中',
    paused: '已暂停'
  }
  return statusMap[status] || status
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    running: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30',
    review: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
    paused: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30'
  }
  return colors[status] || 'text-slate-600 bg-slate-50'
}
</script>

<template>
  <div>
    <div v-if="campaigns.length" class="space-y-3">
      <div
        v-for="campaign in campaigns"
        :key="campaign.id"
        class="rounded border border-slate-200 bg-white p-4 transition-all hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <h4 class="mb-1 truncate text-sm font-bold text-slate-900 dark:text-white">
              {{ campaign.name }}
            </h4>
            <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span class="truncate">所属项目: {{ campaign.project_name }}</span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <span class="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-400">
              {{ campaign.platform }}
            </span>
            <span class="status-chip" :data-status="campaign.status" :class="getStatusColor(campaign.status)">
              {{ getStatusText(campaign.status) }}
            </span>
          </div>
        </div>

        <div class="mb-3 grid grid-cols-3 gap-3">
          <div class="text-center">
            <div class="text-xl font-bold text-slate-900 dark:text-white">${{ campaign.spent?.toLocaleString() || 0 }}</div>
            <div class="mt-0.5 text-[10px] text-slate-400">消耗</div>
          </div>
          <div class="text-center">
            <div class="text-xl font-bold text-slate-900 dark:text-white">{{ campaign.budget?.toLocaleString() || 0 }}</div>
            <div class="mt-0.5 text-[10px] text-slate-400">预算</div>
          </div>
          <div class="text-center">
            <div class="text-xl font-bold text-slate-900 dark:text-white">{{ campaign.material_ids?.length || 0 }}</div>
            <div class="mt-0.5 text-[10px] text-slate-400">素材</div>
          </div>
        </div>

        <div v-if="!embedded" class="flex items-center gap-2">
          <button
            class="flex-1 rounded bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
            @click="emit('view', campaign.id)"
          >
            查看详情
          </button>
          <button
            class="flex items-center gap-1 rounded border px-3 py-1.5 text-xs font-semibold transition-colors"
            :class="[
              campaign.status === 'running'
                ? 'border-orange-200 bg-orange-50 text-orange-600 hover:bg-orange-100 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-400 dark:hover:bg-orange-900/30'
                : 'border-emerald-200 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400 dark:hover:bg-emerald-900/30',
              updatingIds.has(campaign.id) ? 'cursor-not-allowed opacity-50' : ''
            ]"
            :disabled="updatingIds.has(campaign.id)"
            @click="emit('toggleStatus', campaign)"
          >
            <span v-if="updatingIds.has(campaign.id)" class="material-symbols-outlined animate-spin text-sm">progress_activity</span>
            {{ campaign.status === 'running' ? '暂停' : '启动' }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined mb-4 text-6xl text-slate-300 dark:text-slate-700">campaign</span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无广告计划</p>
    </div>
  </div>
</template>
