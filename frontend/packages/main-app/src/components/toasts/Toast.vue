<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

export interface ToastProps {
  show: boolean
  message: string
  type?: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

interface Emits {
  (e: 'close'): void
}

const props = withDefaults(defineProps<ToastProps>(), {
  type: 'info',
  duration: 3000
})

const emit = defineEmits<Emits>()

const visible = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

watch(() => props.show, (newVal) => {
  if (newVal) {
    visible.value = true
    startTimer()
  } else {
    visible.value = false
  }
})

const startTimer = () => {
  if (timer) {
    clearTimeout(timer)
  }
  if (props.duration > 0) {
    timer = setTimeout(() => {
      handleClose()
    }, props.duration)
  }
}

const handleClose = () => {
  visible.value = false
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
  emit('close')
}

onMounted(() => {
  if (props.show) {
    visible.value = true
    startTimer()
  }
})

const getIcon = () => {
  switch (props.type) {
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

const getColorClass = () => {
  switch (props.type) {
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

const getIconColorClass = () => {
  switch (props.type) {
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
  <Transition name="toast">
    <div
      v-if="visible"
      class="fixed top-4 right-4 z-50 z-50"
      style="min-width: 240px; max-width: 358px;"
    >
      <div
        :class="[
          'flex items-center gap-2 rounded-md border shadow-lg',
          getColorClass()
        ]"
        style="padding: 9.6px 12.8px;"
      >
        <span :class="['material-symbols-outlined', getIconColorClass()]" style="font-size: 19.2px;">
          {{ getIcon() }}
        </span>
        <p class="flex-1 font-medium" style="font-size: 11.2px;">{{ message }}</p>
        <button
          class="rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          style="padding: 3.2px;"
          @click="handleClose"
        >
          <span class="material-symbols-outlined" style="font-size: 14.4px;">close</span>
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
