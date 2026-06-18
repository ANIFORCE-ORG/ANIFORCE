<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ExecutionPlan, TodoItem, TodoStatus } from '@/types/agui'

interface Props {
  plan: ExecutionPlan
}

const props = defineProps<Props>()

const isExpanded = ref(true)

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

// 计算进度
const progress = computed(() => {
  const total = props.plan.todos.length
  const completed = props.plan.todos.filter(
    (t) => t.status === 'completed' || t.status === 'skipped'
  ).length
  return total > 0 ? Math.round((completed / total) * 100) : 0
})

// 获取 Todo 状态图标
const getTodoIcon = (status: TodoStatus) => {
  switch (status) {
    case 'completed':
      return 'check_circle'
    case 'running':
      return 'pending'
    case 'failed':
      return 'error'
    case 'skipped':
      return 'cancel'
    default:
      return 'radio_button_unchecked'
  }
}

// 获取 Todo 状态颜色
const getTodoColor = (status: TodoStatus) => {
  switch (status) {
    case 'completed':
      return 'text-green-600 dark:text-green-400'
    case 'running':
      return 'text-blue-600 dark:text-blue-400 animate-pulse'
    case 'failed':
      return 'text-red-600 dark:text-red-400'
    case 'skipped':
      return 'text-slate-400 dark:text-slate-600'
    default:
      return 'text-slate-400 dark:text-slate-600'
  }
}

// 获取 Todo 状态文本
const getTodoStatusText = (status: TodoStatus) => {
  switch (status) {
    case 'completed':
      return '已完成'
    case 'running':
      return '执行中'
    case 'failed':
      return '失败'
    case 'skipped':
      return '已跳过'
    default:
      return '待执行'
  }
}
</script>

<template>
  <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
    <!-- Plan Header -->
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-[16px] text-blue-600 dark:text-blue-400">
          list_alt
        </span>
        <span class="text-[11px] font-semibold text-blue-900 dark:text-blue-100">
          执行计划
        </span>
        <span class="text-[10px] text-blue-600 dark:text-blue-400">
          {{ progress }}% 完成
        </span>
      </div>
      <button
        class="h-6 w-6 rounded hover:bg-blue-100 dark:hover:bg-blue-800/30 flex items-center justify-center transition-colors"
        @click="toggleExpanded"
      >
        <span class="material-symbols-outlined text-[16px] text-blue-600 dark:text-blue-400">
          {{ isExpanded ? 'expand_less' : 'expand_more' }}
        </span>
      </button>
    </div>

    <!-- Progress Bar -->
    <div class="h-1 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden mb-3">
      <div
        class="h-full bg-blue-600 dark:bg-blue-400 transition-all duration-300"
        :style="{ width: `${progress}%` }"
      ></div>
    </div>

    <!-- Todo List -->
    <div v-if="isExpanded" class="space-y-2">
      <div
        v-for="todo in plan.todos"
        :key="todo.id"
        class="flex items-start gap-2 text-[11px]"
      >
        <!-- Status Icon -->
        <span
          class="material-symbols-outlined text-[16px] flex-shrink-0 mt-0.5"
          :class="getTodoColor(todo.status)"
        >
          {{ getTodoIcon(todo.status) }}
        </span>

        <!-- Todo Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span
              class="font-medium text-slate-900 dark:text-slate-100"
              :class="{
                'line-through text-slate-500 dark:text-slate-500': todo.status === 'skipped',
              }"
            >
              {{ todo.title }}
            </span>
            <span
              class="text-[9px] px-1.5 py-0.5 rounded-full"
              :class="{
                'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300': todo.status === 'completed',
                'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300': todo.status === 'running',
                'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300': todo.status === 'failed',
                'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400': todo.status === 'pending' || todo.status === 'skipped',
              }"
            >
              {{ getTodoStatusText(todo.status) }}
            </span>
          </div>

          <!-- Description -->
          <p
            v-if="todo.description"
            class="text-[10px] text-slate-600 dark:text-slate-400 mt-1"
          >
            {{ todo.description }}
          </p>

          <!-- Result -->
          <p
            v-if="todo.result && todo.status === 'completed'"
            class="text-[10px] text-green-600 dark:text-green-400 mt-1"
          >
            ✓ {{ todo.result }}
          </p>

          <!-- Error -->
          <p
            v-if="todo.error && todo.status === 'failed'"
            class="text-[10px] text-red-600 dark:text-red-400 mt-1"
          >
            ✗ {{ todo.error }}
          </p>
        </div>
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
