<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()

const getIcon = (type: string) => {
  switch (type) {
    case 'success':
      return 'check_circle'
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    case 'info':
    default:
      return 'info'
  }
}

const getColorClass = (type: string) => {
  switch (type) {
    case 'success':
      return 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
    case 'error':
      return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
    case 'warning':
      return 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200'
    case 'info':
    default:
      return 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200'
  }
}

const getIconColorClass = (type: string) => {
  switch (type) {
    case 'success':
      return 'text-emerald-600 dark:text-emerald-400'
    case 'error':
      return 'text-red-600 dark:text-red-400'
    case 'warning':
      return 'text-yellow-600 dark:text-yellow-400'
    case 'info':
    default:
      return 'text-blue-600 dark:text-blue-400'
  }
}
</script>

<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
    <TransitionGroup name="toast-list">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto min-w-[300px] max-w-md"
      >
        <div
          :class="[
            'flex items-center gap-3 px-4 py-3 rounded-md border shadow-lg',
            getColorClass(toast.type)
          ]"
        >
          <span :class="['material-symbols-outlined text-2xl', getIconColorClass(toast.type)]">
            {{ getIcon(toast.type) }}
          </span>
          <p class="flex-1 text-sm font-medium">{{ toast.message }}</p>
          <button
            class="p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            @click="removeToast(toast.id)"
          >
            <span class="material-symbols-outlined text-lg">close</span>
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-list-enter-active {
  transition: all 0.3s ease;
}

.toast-list-leave-active {
  transition: all 0.3s ease;
}

.toast-list-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-list-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-list-move {
  transition: transform 0.3s ease;
}
</style>
