import { ref } from 'vue'

export interface ToastItem {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration: number
}

export interface ToastOptions {
  message: string
  type?: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

const MAX_TOASTS = 3
const toasts = ref<ToastItem[]>([])
let toastIdCounter = 0

export function useToast() {
  const showToast = (options: ToastOptions) => {
    const id = `toast-${Date.now()}-${toastIdCounter++}`
    const newToast: ToastItem = {
      id,
      message: options.message,
      type: options.type || 'info',
      duration: options.duration || 3000
    }

    // 如果已经有 3 个 toast，移除最早的一个
    if (toasts.value.length >= MAX_TOASTS) {
      toasts.value.shift()
    }

    toasts.value.push(newToast)

    // 自动移除 toast
    if (newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, newToast.duration)
    }
  }

  const removeToast = (id: string) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message: string, duration?: number) => {
    showToast({ message, type: 'success', duration })
  }

  const error = (message: string, duration?: number) => {
    showToast({ message, type: 'error', duration })
  }

  const warning = (message: string, duration?: number) => {
    showToast({ message, type: 'warning', duration })
  }

  const info = (message: string, duration?: number) => {
    showToast({ message, type: 'info', duration })
  }

  const clearAll = () => {
    toasts.value = []
  }

  return {
    toasts,
    showToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clearAll
  }
}
