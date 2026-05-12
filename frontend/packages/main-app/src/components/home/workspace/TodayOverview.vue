<script setup lang="ts">
// @ts-nocheck
import { ref, computed } from 'vue'

// Mock data - 实际应该从API获取
const todayStats = ref({
  spend: 12450,
  roi: 3.2,
  conversions: 1245
})

const yesterdayStats = ref({
  spend: 11500,
  roi: 2.85,
  conversions: 1185
})

const stats = computed(() => {
  const spendChange = ((todayStats.value.spend - yesterdayStats.value.spend) / yesterdayStats.value.spend * 100).toFixed(0)
  const roiChange = ((todayStats.value.roi - yesterdayStats.value.roi) / yesterdayStats.value.roi * 100).toFixed(0)
  const convChange = ((todayStats.value.conversions - yesterdayStats.value.conversions) / yesterdayStats.value.conversions * 100).toFixed(0)

  return [
    {
      label: '今日消耗',
      value: `$${todayStats.value.spend.toLocaleString()}`,
      change: `${spendChange >= 0 ? '+' : ''}${spendChange}%`,
      trend: parseFloat(spendChange) >= 0 ? 'up' : 'down',
      icon: 'payments',
      color: 'text-blue-600'
    },
    {
      label: '今日ROI',
      value: `${todayStats.value.roi.toFixed(1)}x`,
      change: `${roiChange >= 0 ? '+' : ''}${roiChange}%`,
      trend: parseFloat(roiChange) >= 0 ? 'up' : 'down',
      icon: 'trending_up',
      color: 'text-emerald-600'
    },
    {
      label: '今日转化',
      value: todayStats.value.conversions.toLocaleString(),
      change: `${convChange >= 0 ? '+' : ''}${convChange}%`,
      trend: parseFloat(convChange) >= 0 ? 'up' : 'down',
      icon: 'download',
      color: 'text-purple-600'
    }
  ]
})
</script>

<template>
  <div>
    <div class="flex items-center gap-2 mb-3">
      <span class="material-symbols-outlined text-primary text-base">today</span>
      <h4 class="text-sm font-semibold text-slate-900 dark:text-white">今日概览</h4>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <div
        v-for="(stat, index) in stats"
        :key="index"
        class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:shadow-md transition-shadow cursor-pointer"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="material-symbols-outlined text-xl" :class="stat.color">
            {{ stat.icon }}
          </span>
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="stat.trend === 'up'
              ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600'
              : 'bg-red-50 dark:bg-red-900/30 text-red-600'"
          >
            {{ stat.change }}
          </span>
        </div>
        <div class="text-xl font-bold text-slate-900 dark:text-white mb-1">
          {{ stat.value }}
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400">
          {{ stat.label }}
        </div>
      </div>
    </div>
  </div>
</template>
