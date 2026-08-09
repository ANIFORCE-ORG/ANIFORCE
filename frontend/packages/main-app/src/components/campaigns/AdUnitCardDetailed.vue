<script setup lang="ts">
import type { AdSetPerformance } from '@/api/campaigns'

interface Props {
  adUnit: AdSetPerformance
}

interface Emits {
  (e: 'view', id: string): void
  (e: 'edit', adUnit: AdSetPerformance): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const getStatusChipClass = (status: string) => {
  const classes: Record<string, string> = {
    draft: 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600',
    learning: 'text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    running: 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    active: 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    paused: 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    completed: 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600',
    review: 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
  }
  return classes[status.toLowerCase()] || classes.draft
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    draft: '草稿',
    learning: '学习中',
    running: '运行中',
    active: '运行中',
    paused: '已暂停',
    completed: '已结束',
    review: '审核中',
  }
  return texts[status.toLowerCase()] || status
}

const formatMoney = (value?: number | null) =>
  typeof value === 'number'
    ? value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
    : '-'

const formatPercent = (value?: number | null) =>
  typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '-'

const roiClass = (value?: number | null) => {
  if (typeof value !== 'number') return 'text-slate-500 dark:text-slate-400'
  return value >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'
}
</script>

<template>
  <article class="border border-slate-200 dark:border-slate-700 rounded-md p-[14px] bg-white dark:bg-slate-800/50 hover:border-primary/50 hover:shadow-lg transition-all duration-150">
    <!-- Ad Unit Header -->
    <div class="flex items-start justify-between gap-[12px] mb-[10px]">
      <div class="flex-1 min-w-0">
        <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white mb-[8px] truncate">
          {{ adUnit.name }}
          <span class="status-chip" :data-status="adUnit.status" :class="getStatusChipClass(adUnit.status)">
            Status: {{ getStatusText(adUnit.status) }}
          </span>
        </h3>
        <p class="mt-[5px] text-[10px] text-slate-500 dark:text-slate-400">
          {{ adUnit.audience || '未配置受众' }}
        </p>
      </div>
      <button
        class="shrink-0 p-[6px] rounded-md text-slate-500 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        title="编辑广告单元"
        @click="emit('edit', adUnit)"
      >
        <span class="material-symbols-outlined text-[16px]">edit</span>
      </button>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-px bg-slate-100 dark:bg-slate-700">
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">每日预算</span>
        <strong class="block mt-[3px] text-[11px] text-slate-900 dark:text-white">${{ formatMoney(adUnit.daily_budget) }}</strong>
      </div>
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">累计消耗</span>
        <strong class="block mt-[3px] text-[11px] text-slate-900 dark:text-white">${{ formatMoney(adUnit.spent) }}</strong>
      </div>
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">最新 ROI</span>
        <strong class="block mt-[3px] text-[11px]" :class="roiClass(adUnit.latest?.roi)">{{ formatPercent(adUnit.latest?.roi) }}</strong>
      </div>
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">最新 CPI</span>
        <strong class="block mt-[3px] text-[11px] text-slate-900 dark:text-white">${{ formatMoney(adUnit.latest?.cpi) }}</strong>
      </div>
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">安装</span>
        <strong class="block mt-[3px] text-[11px] text-slate-900 dark:text-white">{{ adUnit.latest?.installs ?? '-' }}</strong>
      </div>
      <div class="bg-white dark:bg-slate-800 px-[12px] py-[10px]">
        <span class="block text-[9px] text-slate-500 dark:text-slate-400">样本天数</span>
        <strong class="block mt-[3px] text-[11px] text-slate-900 dark:text-white">{{ adUnit.data_available ? adUnit.sample_count : '暂无数据' }}</strong>
      </div>
    </div>

    <div class="flex flex-wrap gap-x-[18px] gap-y-[5px] px-[14px] py-[9px] text-[10px] text-slate-600 dark:text-slate-400">
      <span>版位：{{ adUnit.placements || '-' }}</span>
      <span>优化目标：{{ adUnit.optimization_goal || '-' }}</span>
      <span>出价：{{ adUnit.bid_strategy || '-' }}</span>
    </div>
  </article>
</template>
