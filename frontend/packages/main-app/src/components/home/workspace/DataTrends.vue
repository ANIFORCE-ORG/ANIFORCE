<script setup lang="ts">
import { ref } from 'vue'

const timeRange = ref('7d')

const timeRanges = [
  { value: '7d', label: '7日' },
  { value: '30d', label: '30日' }
]

// Mock chart data
const chartData = ref({
  labels: ['4/10', '4/11', '4/12', '4/13', '4/14', '4/15', '4/16'],
  spend: [1800, 2100, 1950, 2300, 2150, 2400, 2200],
  roi: [2.8, 3.1, 2.9, 3.3, 3.0, 3.4, 3.2],
  conversions: [150, 180, 165, 195, 175, 200, 185]
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-base">show_chart</span>
        <h4 class="text-sm font-semibold text-slate-900 dark:text-white">数据趋势</h4>
      </div>
      <div class="flex gap-1">
        <button
          v-for="range in timeRanges"
          :key="range.value"
          class="px-2 py-1 rounded-md text-xs font-medium transition-colors"
          :class="timeRange === range.value
            ? 'bg-primary text-white'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
          @click="timeRange = range.value"
        >
          {{ range.label }}
        </button>
      </div>
    </div>

    <div class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
      <!-- Simple chart visualization -->
      <div class="space-y-3">
        <!-- Spend Trend -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-600 dark:text-slate-400">消耗趋势</span>
            <span class="text-xs font-semibold text-blue-600">$2,200</span>
          </div>
          <div class="h-12 flex items-end gap-1">
            <div
              v-for="(value, index) in chartData.spend"
              :key="index"
              class="flex-1 bg-blue-500 rounded-t transition-all hover:bg-blue-600"
              :style="{ height: `${(value / Math.max(...chartData.spend)) * 100}%` }"
              :title="`${chartData.labels[index]}: $${value}`"
            ></div>
          </div>
        </div>

        <!-- ROI Trend -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-600 dark:text-slate-400">ROI趋势</span>
            <span class="text-xs font-semibold text-emerald-600">3.2x</span>
          </div>
          <div class="h-12 flex items-end gap-1">
            <div
              v-for="(value, index) in chartData.roi"
              :key="index"
              class="flex-1 bg-emerald-500 rounded-t transition-all hover:bg-emerald-600"
              :style="{ height: `${(value / Math.max(...chartData.roi)) * 100}%` }"
              :title="`${chartData.labels[index]}: ${value}x`"
            ></div>
          </div>
        </div>

        <!-- Conversions Trend -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-600 dark:text-slate-400">转化趋势</span>
            <span class="text-xs font-semibold text-purple-600">185</span>
          </div>
          <div class="h-12 flex items-end gap-1">
            <div
              v-for="(value, index) in chartData.conversions"
              :key="index"
              class="flex-1 bg-purple-500 rounded-t transition-all hover:bg-purple-600"
              :style="{ height: `${(value / Math.max(...chartData.conversions)) * 100}%` }"
              :title="`${chartData.labels[index]}: ${value}`"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
