<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCall } from '@/types/agui'

interface Props {
  tool: ToolCall
}

const props = defineProps<Props>()

const isExpanded = ref(false)

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

// 工具名称格式化
const toolDisplayName = computed(() => {
  return props.tool.tool_name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
})

// 是否有详细信息
const hasDetails = computed(() => {
  return props.tool.tool_args || props.tool.tool_result
})

// 状态图标
const statusIcon = computed(() => {
  if (props.tool.completed_at) {
    return 'check_circle'
  } else if (props.tool.started_at) {
    return 'pending'
  } else {
    return 'build'
  }
})

// 状态颜色
const statusColor = computed(() => {
  if (props.tool.completed_at) {
    return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
  } else if (props.tool.started_at) {
    return 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30 animate-pulse'
  } else {
    return 'text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800'
  }
})
</script>

<template>
  <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-2.5">
    <!-- Tool Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 flex-1">
        <span
          class="material-symbols-outlined text-[14px] flex-shrink-0"
          :class="statusColor"
        >
          {{ statusIcon }}
        </span>
        <span class="text-[10px] font-medium text-slate-900 dark:text-slate-100">
          🔧 {{ toolDisplayName }}
        </span>
      </div>
      <button
        v-if="hasDetails"
        class="h-5 w-5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
        @click="toggleExpanded"
      >
        <span class="material-symbols-outlined text-[14px] text-slate-600 dark:text-slate-400">
          {{ isExpanded ? 'expand_less' : 'expand_more' }}
        </span>
      </button>
    </div>

    <!-- Tool Details -->
    <div v-if="isExpanded && hasDetails" class="mt-2 space-y-2">
      <!-- Arguments -->
      <div v-if="tool.tool_args" class="text-[9px]">
        <div class="text-slate-600 dark:text-slate-400 mb-1">参数:</div>
        <pre class="bg-slate-100 dark:bg-slate-900 p-2 rounded text-slate-900 dark:text-slate-100 overflow-x-auto">{{ JSON.stringify(tool.tool_args, null, 2) }}</pre>
      </div>

      <!-- Result -->
      <div v-if="tool.tool_result" class="text-[9px]">
        <div class="text-slate-600 dark:text-slate-400 mb-1">结果:</div>
        <pre class="bg-slate-100 dark:bg-slate-900 p-2 rounded text-slate-900 dark:text-slate-100 overflow-x-auto">{{ typeof tool.tool_result === 'string' ? tool.tool_result : JSON.stringify(tool.tool_result, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 1,
    'wght' 400,
    'GRAD' 0,
    'opsz' 20;
}
</style>
