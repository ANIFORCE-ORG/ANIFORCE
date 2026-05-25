<script setup lang="ts">
interface Props {
  show: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmButtonClass?: string
}

interface Emits {
  (e: 'confirm'): void
  (e: 'cancel'): void
  (e: 'close'): void
}

withDefaults(defineProps<Props>(), {
  title: '确认操作',
  confirmText: '确定',
  cancelText: '取消',
  confirmButtonClass: 'bg-blue-500 hover:bg-blue-600'
})

const emit = defineEmits<Emits>()

const handleConfirm = () => {
  emit('confirm')
  emit('close')
}

const handleCancel = () => {
  emit('cancel')
  emit('close')
}

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    handleCancel()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="show"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click="handleBackdropClick"
      >
        <Transition name="scale">
          <div
            v-if="show"
            class="bg-white dark:bg-slate-800 rounded-lg shadow-2xl max-w-md w-full mx-4 overflow-hidden border border-slate-200 dark:border-slate-700"
          >
            <!-- 内容 -->
            <div class="px-8 py-6">
              <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-4">{{ title }}</h3>
              <p class="text-slate-600 dark:text-slate-300 text-base leading-relaxed">{{ message }}</p>
            </div>

            <!-- 按钮 -->
            <div class="px-8 py-5 bg-slate-50 dark:bg-slate-900/30 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-700">
              <button
                class="px-5 py-2.5 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 border border-slate-300 dark:border-slate-600 transition-all duration-200 shadow-sm hover:shadow"
                @click="handleCancel"
              >
                {{ cancelText }}
              </button>
              <button
                :class="[
                  'px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-all duration-200 shadow-sm hover:shadow-md',
                  confirmButtonClass
                ]"
                @click="handleConfirm"
              >
                {{ confirmText }}
              </button>
            </div>
          </div>
        </Transition>
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

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
