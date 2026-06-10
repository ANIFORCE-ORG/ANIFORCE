<script setup lang="ts">
import type { MaterialImage } from '@/api/materials'

interface Props {
  image: MaterialImage | null
  show: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

const handleClose = () => {
  emit('close')
}

const handleBackdropClick = (event: MouseEvent) => {
  if (event.target === event.currentTarget) {
    handleClose()
  }
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show && image"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      @click="handleBackdropClick"
    >
      <div class="relative max-w-[1170px] max-h-[90vh] w-full mx-4">
        <!-- Close Button -->
        <button
          class="absolute -top-[37px] right-0 p-[6px] rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
          @click="handleClose"
        >
          <span class="material-symbols-outlined text-[17px]">close</span>
        </button>

        <!-- Image Container -->
        <div class="bg-white dark:bg-slate-900 rounded-lg overflow-hidden shadow-2xl">
          <img
            :src="image.data"
            :alt="image.filename"
            class="w-full h-auto max-h-[80vh] object-contain"
          />
          
          <!-- Image Info -->
          <div class="p-[12px] border-t border-slate-200 dark:border-slate-800">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-[11px] font-semibold text-slate-900 dark:text-white">
                  {{ image.filename }}
                </h3>
                <p class="text-[10px] text-slate-500 dark:text-slate-400 mt-[4px]">
                  {{ image.mime_type }} • {{ (image.size / 1024).toFixed(1) }} KB
                </p>
              </div>
              <button
                class="px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors text-[11px] font-medium"
                @click="handleClose"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
