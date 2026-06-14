<script setup lang="ts">
import { computed } from 'vue'

interface ActivityContent {
  activityType?: string
  toolName: string
  status: 'running' | 'completed' | 'error'
  title: string
  arguments?: Record<string, unknown>
}

const props = defineProps<{
  content: ActivityContent
}>()

const statusIcon = computed(() => {
  if (props.content.status === 'completed') return 'check_circle'
  if (props.content.status === 'error') return 'error'
  return 'pending'
})

const statusColor = computed(() => {
  if (props.content.status === 'completed') return 'text-emerald-600 dark:text-emerald-400'
  if (props.content.status === 'error') return 'text-red-600 dark:text-red-400'
  return 'text-blue-600 dark:text-blue-400'
})

const statusBg = computed(() => {
  if (props.content.status === 'completed') return 'bg-emerald-50 dark:bg-emerald-950/30'
  if (props.content.status === 'error') return 'bg-red-50 dark:bg-red-950/30'
  return 'bg-blue-50 dark:bg-blue-950/30'
})

const statusBorder = computed(() => {
  if (props.content.status === 'completed') return 'border-emerald-200 dark:border-emerald-800'
  if (props.content.status === 'error') return 'border-red-200 dark:border-red-800'
  return 'border-blue-200 dark:border-blue-800'
})

const isRunning = computed(() => props.content.status === 'running')
</script>

<template>
  <div
    class="activity-card group relative rounded-xl border transition-all duration-300"
    :class="[
      statusBg,
      statusBorder,
      isRunning ? 'animate-pulse-subtle' : 'hover:shadow-md'
    ]"
  >
    <!-- 左侧状态指示条 -->
    <div
      class="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl transition-all duration-300"
      :class="isRunning ? 'bg-blue-500 animate-pulse' : props.content.status === 'completed' ? 'bg-emerald-500' : 'bg-red-500'"
    />
    
    <div class="pl-4 pr-4 py-3 flex items-center gap-3">
      <!-- 状态图标 -->
      <div class="flex-shrink-0">
        <span
          class="material-symbols-outlined text-xl transition-all duration-300"
          :class="[statusColor, isRunning ? 'animate-spin-slow' : '']"
        >
          {{ statusIcon }}
        </span>
      </div>
      
      <!-- 内容区 -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-slate-900 dark:text-slate-100">
            {{ content.title }}
          </span>
          <span
            v-if="content.toolName"
            class="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
          >
            {{ content.toolName }}
          </span>
        </div>
        
        <!-- 参数（折叠显示） -->
        <div
          v-if="content.arguments && Object.keys(content.arguments).length > 0"
          class="mt-1.5 text-xs text-slate-500 dark:text-slate-400 font-mono"
        >
          {{ JSON.stringify(content.arguments).slice(0, 80) }}{{ Object.keys(content.arguments).length > 3 ? '...' : '' }}
        </div>
      </div>
      
      <!-- 运行中动画指示器 -->
      <div v-if="isRunning" class="flex-shrink-0">
        <div class="flex gap-1">
          <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 0s" />
          <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 0.15s" />
          <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style="animation-delay: 0.3s" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.activity-card {
  backdrop-filter: blur(8px);
}

@keyframes pulse-subtle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.92;
  }
}

.animate-pulse-subtle {
  animation: pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-spin-slow {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
