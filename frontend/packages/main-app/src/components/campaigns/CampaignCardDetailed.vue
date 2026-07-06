<script setup lang="ts">
import { computed } from 'vue'

interface Campaign {
  id: string
  name: string
  platform: string
  account_id?: string
  status: string
  buying_type?: string
  objective?: string
  start_date?: string
  end_date?: string
}

interface Props {
  campaign: Campaign
}

interface Emits {
  (e: 'view', id: string): void
  (e: 'addCreative', id: string): void
  (e: 'edit', campaign: Campaign): void
  (e: 'delete', id: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 获取状态 chip 样式类
const getStatusChipClass = (status: string) => {
  const classes: Record<string, string> = {
    'draft': 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600',
    'running': 'text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    'paused': 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    'completed': 'text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700'
  }
  return classes[status] || 'text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'
}

// 获取状态显示文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'draft': '草稿',
    'running': '运行中',
    'paused': '已暂停',
    'completed': '已完成'
  }
  return texts[status] || status
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
  emit('view', props.campaign.id)
}

const handleEdit = () => {
  emit('edit', props.campaign)
}

const handleDelete = () => {
  emit('delete', props.campaign.id)
}
</script>

<template>
  <article class="border border-slate-200 dark:border-slate-700 rounded-md p-[14px] bg-white dark:bg-slate-800/50 hover:border-primary/50 hover:shadow-lg transition-all duration-150">
    <!-- Campaign Header -->
    <div class="flex items-start justify-between gap-[12px] mb-[10px]">
      <div class="flex-1 min-w-0">
        <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white mb-[8px] truncate">
          {{ campaign.name }}
          <span class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium border" :class="getStatusChipClass(campaign.status)">
            Status: {{ getStatusText(campaign.status) }}
          </span>
        </h3>
        <p class="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
          BuyingType - {{ campaign.buying_type }} · Objective - {{ campaign.objective }}
        </p>
      </div>
      <div class="shrink-0 flex items-center gap-[6px] w-[240px]">
        <button
          class="flex-1 px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:border-primary hover:text-primary hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors whitespace-nowrap"
          @click="handleView"
        >
          查看
        </button>
        <button
          class="flex-1 px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:border-primary hover:text-primary hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors whitespace-nowrap"
          @click="handleEdit"
        >
          编辑
        </button>
        <button
          class="flex-1 px-[9px] py-[6px] rounded-md border border-red-200 dark:border-red-800 bg-white dark:bg-slate-700 text-[11px] font-medium text-red-600 dark:text-red-400 hover:border-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors whitespace-nowrap"
          @click="handleDelete"
        >
          删除
        </button>
      </div>
    </div>

    <!-- Campaign Meta -->
    <div class="flex flex-wrap gap-[8px]">
      <span class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        平台: {{ campaign.platform }}
      </span>
      <span v-if="campaign.account_id" class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
        账户: {{ campaign.account_id }}
      </span>
      <span class="inline-flex items-center gap-[6px] px-[8px] py-[4px] rounded-lg text-[10px] font-medium text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
        生效日期: {{ formatDate(campaign.start_date) }} - {{ formatDate(campaign.end_date) }}
      </span>
    </div>
  </article>
</template>
