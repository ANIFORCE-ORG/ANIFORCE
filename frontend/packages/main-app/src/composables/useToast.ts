import { ref } from 'vue'

export interface ToastOptions {
  message: string
  type?: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

const toastState = ref({
  show: false,
  message: '',
  type: 'info' as 'success' | 'error' | 'warning' | 'info',
  duration: 3000
})

export function useToast() {
  const showToast = (options: ToastOptions) => {
    toastState.value = {
      show: true,
      message: options.message,
      type: options.type || 'info',
      duration: options.duration || 3000
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

  const hideToast = () => {
    toastState.value.show = false
  }

  return {
    toastState,
    showToast,
    success,
    error,
    warning,
    info,
    hideToast
  }
}
