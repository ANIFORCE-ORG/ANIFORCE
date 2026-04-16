<script setup lang="ts">
import { computed } from 'vue'
import { PRODUCT_TYPES } from '@/config/productTypes'

interface Project {
  id: string
  product_type: string
  spent?: number
  roi?: number
}

interface Props {
  projects?: Project[]
}

const props = defineProps<Props>()

// 按产品类型聚合数据
const productTypeStats = computed(() => {
  if (!props.projects || props.projects.length === 0) {
    return []
  }

  const statsMap: Record<string, { count: number; spend: number; roiSum: number; roiCount: number }> = {}

  props.projects.forEach(p => {
    if (!statsMap[p.product_type]) {
      statsMap[p.product_type] = { count: 0, spend: 0, roiSum: 0, roiCount: 0 }
    }
    statsMap[p.product_type].count++
    statsMap[p.product_type].spend += p.spent || 0
    if (p.roi) {
      statsMap[p.product_type].roiSum += p.roi
      statsMap[p.product_type].roiCount++
    }
  })

  // 转换为数组并添加配置信息
  return Object.entries(statsMap)
    .map(([type, stats]) => {
      const config = PRODUCT_TYPES.find(pt => pt.value === type)
      return {
        type,
        label: config?.label || type,
        icon: config?.icon || '📦',
        color: config?.color || '#94a3b8',
        count: stats.count,
        spend: stats.spend,
        avgRoi: stats.roiCount > 0 ? stats.roiSum / stats.roiCount : 0
      }
    })
    .sort((a, b) => b.spend - a.spend)
})

// 计算总消耗（用于百分比计算）
const totalSpend = computed(() => {
  return productTypeStats.value.reduce((sum, stat) => sum + stat.spend, 0)
})

// 获取消耗占比
const getSpendPercentage = (spend: number): number => {
  if (totalSpend.value === 0) return 0
  return (spend / totalSpend.value) * 100
}
</script>

<template>
  <div class="space-y-3">
    <div
      v-for="stat in productTypeStats"
      :key="stat.type"
      class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
    >
      <!-- 产品类型头部 -->
      <div class="flex items-center gap-3 mb-3">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center text-2xl flex-shrink-0"
          :style="{ backgroundColor: stat.color + '20' }"
        >
          {{ stat.icon }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-slate-900 dark:text-white">
            {{ stat.label }}
          </div>
          <div class="text-xs text-slate-500 dark:text-slate-400">
            {{ stat.count }} 个项目
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-sm font-bold text-slate-900 dark:text-white">
            ${{ stat.spend.toLocaleString() }}
          </div>
          <div class="text-xs text-slate-400">
            {{ getSpendPercentage(stat.spend).toFixed(1) }}%
          </div>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mb-2">
        <div
          class="h-full rounded-full transition-all"
          :style="{
            width: `${getSpendPercentage(stat.spend)}%`,
            backgroundColor: stat.color
          }"
        ></div>
      </div>

      <!-- 平均ROI -->
      <div class="flex items-center justify-between text-xs">
        <span class="text-slate-500 dark:text-slate-400">平均ROI</span>
        <span
          class="font-semibold"
          :class="stat.avgRoi >= 2.0 ? 'text-green-600 dark:text-green-400' : 'text-slate-900 dark:text-white'"
        >
          {{ stat.avgRoi.toFixed(2) }}x
        </span>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="productTypeStats.length === 0" class="text-center py-8">
      <span class="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-700 mb-2">
        category
      </span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无产品类型数据</p>
    </div>
  </div>
</template>
