<script setup lang="ts">
import { ref, computed } from 'vue'
import type { HITLConfirmationRequest } from '@/types/agui'

interface Props {
  request: HITLConfirmationRequest
  visible: boolean
}

interface Emits {
  (e: 'confirm', feedback?: string): void
  (e: 'cancel', feedback?: string): void
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const feedback = ref('')
const isProcessing = ref(false)

// 风险等级配置
const riskConfig = computed(() => {
  switch (props.request.risk_level) {
    case 'high':
      return {
        icon: 'warning',
        color: 'text-red-600 dark:text-red-400',
        bgColor: 'bg-red-100 dark:bg-red-900/30',
        borderColor: 'border-red-200 dark:border-red-800',
        label: '高风险',
      }
    case 'medium':
      return {
        icon: 'error_outline',
        color: 'text-orange-600 dark:text-orange-400',
        bgColor: 'bg-orange-100 dark:bg-orange-900/30',
        borderColor: 'border-orange-200 dark:border-orange-800',
        label: '中风险',
      }
    default:
      return {
        icon: 'info',
        color: 'text-blue-600 dark:text-blue-400',
        bgColor: 'bg-blue-100 dark:bg-blue-900/30',
        borderColor: 'border-blue-200 dark:border-blue-800',
        label: '低风险',
      }
  }
})

const handleConfirm = () => {
  isProcessing.value = true
  emit('confirm', feedback.value || undefined)
  setTimeout(() => {
    isProcessing.value = false
    feedback.value = ''
  }, 500)
}

const handleCancel = () => {
  emit('cancel', feedback.value || undefined)
  feedback.value = ''
}

const handleClose = () => {
  emit('close')
  feedback.value = ''
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        @click.self="handleClose"
      >
        <div
          class="bg-white dark:bg-slate-900 rounded-lg shadow-2xl max-w-md w-full mx-4 border border-slate-200 dark:border-slate-800"
          @click.stop
        >
          <!-- Header -->
          <div class="p-4 border-b border-slate-200 dark:border-slate-800">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="h-10 w-10 rounded-lg flex items-center justify-center"
                  :class="[riskConfig.bgColor, riskConfig.borderColor, 'border']"
                >
                  <span class="material-symbols-outlined text-[24px]" :class="riskConfig.color">
                    {{ riskConfig.icon }}
                  </span>
                </div>
                <div>
                  <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">
                    需要您的确认
                  </h3>
                  <span
                    class="text-[10px] px-2 py-0.5 rounded-full inline-block mt-1"
                    :class="[riskConfig.bgColor, riskConfig.color]"
                  >
                    {{ riskConfig.label }}操作
                  </span>
                </div>
              </div>
              <button
                class="h-7 w-7 rounded hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
                @click="handleClose"
              >
                <span class="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-400">
                  close
                </span>
              </button>
            </div>
          </div>

          <!-- Content -->
          <div class="p-4 space-y-3">
            <!-- Operation -->
            <div>
              <div class="text-[10px] text-slate-600 dark:text-slate-400 mb-1">操作</div>
              <div class="text-[12px] font-medium text-slate-900 dark:text-white">
                {{ request.operation }}
              </div>
            </div>

            <!-- Description -->
            <div>
              <div class="text-[10px] text-slate-600 dark:text-slate-400 mb-1">说明</div>
              <div class="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                {{ request.description }}
              </div>
            </div>

            <!-- Details -->
            <div v-if="request.details && Object.keys(request.details).length > 0">
              <div class="text-[10px] text-slate-600 dark:text-slate-400 mb-1">详细信息</div>
              <div class="bg-slate-50 dark:bg-slate-800 rounded p-2 text-[10px] text-slate-700 dark:text-slate-300">
                <div
                  v-for="(value, key) in request.details"
                  :key="key"
                  class="flex items-start gap-2 py-1"
                >
                  <span class="font-medium min-w-[80px]">{{ key }}:</span>
                  <span class="flex-1">{{ value }}</span>
                </div>
              </div>
            </div>

            <!-- Feedback Input -->
            <div>
              <div class="text-[10px] text-slate-600 dark:text-slate-400 mb-1">
                备注（可选）
              </div>
              <textarea
                v-model="feedback"
                class="w-full resize-none rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="您可以添加一些备注信息..."
                rows="2"
              ></textarea>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
            <button
              class="h-8 px-4 rounded text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              @click="handleCancel"
            >
              取消
            </button>
            <button
              class="h-8 px-4 rounded text-[11px] font-medium text-white bg-primary hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isProcessing"
              @click="handleConfirm"
            >
              <span v-if="isProcessing" class="h-3 w-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>确认执行</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.material-symbols-outlined {
  font-variation-settings:
    'FILL' 1,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}
</style>
