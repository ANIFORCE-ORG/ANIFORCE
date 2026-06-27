<script setup lang="ts">
import { computed } from 'vue'

interface AdUnit {
  id: string
  name: string
  status: string
  budget?: number
  spent?: number
  conversion_location?: string
  performance_goal?: string
  placements?: string
  start_date?: string
  end_date?: string
}

interface Props {
  adUnit: AdUnit
}

interface Emits {
  (e: 'view', id: string): void
  (e: 'edit', adUnit: AdUnit): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 获取状态 chip 样式类
const getStatusChipClass = (status: string) => {
  const classes: Record<string, string> = {
    'draft': 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600',
    'learning': 'text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    'active': 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    'paused': 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    'review': 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800'
  }
  return classes[status.toLowerCase()] || 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'
}

// 获取状态显示文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'draft': '草稿',
    'learning': '学习中',
    'active': '运行中',
    'paused': '已暂停',
    'review': '审核中'
  }
  return texts[status.toLowerCase()] || status
}

// 格式化日期
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return dateStr
  }
}

const handleView = () => {
  emit('view', props.adUnit.id)
}

const handleEdit = () => {
  emit('edit', props.adUnit)
}
</script>

<template>
  <article class="border border-slate-200 dark:border-slate-700 rounded-md p-[14px] bg-white dark:bg-slate-800/50 hover:border-primary/50 hover:shadow-lg transition-all duration-150">
    <!-- Ad Unit Header -->
    <div class="flex items-start justify-between gap-[12px] mb-[10px]">
      <div class="flex-1 min-w-0">
        <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white mb-[8px] truncate">
          {{ adUnit.name }}
          <span class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium border" :class="getStatusChipClass(adUnit.status)">
            Status: {{ getStatusText(adUnit.status) }}
          </span>
        </h3>
        <p class="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
          预算 ${{ adUnit.budget?.toLocaleString() || 0 }} · 已消耗 ${{ adUnit.spent?.toLocaleString() || 0 }}
        </p>
      </div>
      <div class="shrink-0 flex flex-col gap-[6px]">
        <button
          class="px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:border-primary hover:text-primary hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
          @click="handleView"
        >
          查看详情
        </button>
        <button
          class="px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:border-primary hover:text-primary hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
          @click="handleEdit"
        >
          编辑
        </button>
      </div>
    </div>

    <!-- Ad Unit Meta -->
    <div class="flex flex-wrap gap-[8px]">
      <span v-if="adUnit.conversion_location" class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        转化位置: {{ adUnit.conversion_location }}
      </span>
      <span v-if="adUnit.performance_goal" class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
        目标: {{ adUnit.performance_goal }}
      </span>
      <span v-if="adUnit.placements" class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
        版位: {{ adUnit.placements }}
      </span>
      <span class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
        生效日期: {{ formatDate(adUnit.start_date) }} - {{ formatDate(adUnit.end_date) }}
      </span>
    </div>
  </article>
</template>
