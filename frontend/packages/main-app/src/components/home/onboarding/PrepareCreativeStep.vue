<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  next: [data: any]
  prev: []
  skip: []
}>()

const selectedOption = ref<'upload' | 'ai' | null>(null)

const handleNext = () => {
  if (!selectedOption.value) {
    alert('请选择一种方式')
    return
  }
  emit('next', { method: selectedOption.value })
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-2">
        准备素材
      </h2>
      <p class="text-sm text-slate-600 dark:text-slate-400">
        你可以上传现有素材，或使用AI生成全新素材
      </p>
    </div>

    <!-- Options -->
    <div class="grid grid-cols-2 gap-3 mb-6">
      <!-- Upload -->
      <div
        class="p-4 rounded-md border cursor-pointer transition-all"
        :class="selectedOption === 'upload'
          ? 'border-primary bg-primary/5'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="selectedOption = 'upload'"
      >
        <div class="w-12 h-12 rounded-md bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mx-auto mb-3">
          <span class="material-symbols-outlined text-blue-600 text-xl">upload_file</span>
        </div>
        <h3 class="text-sm font-semibold text-slate-900 dark:text-white text-center mb-1">
          上传现有素材
        </h3>
        <p class="text-xs text-slate-600 dark:text-slate-400 text-center mb-3">
          支持图片和视频格式，批量上传
        </p>
        <div class="flex items-center justify-center">
          <div
            class="w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors"
            :class="selectedOption === 'upload'
              ? 'border-primary bg-primary'
              : 'border-slate-300 dark:border-slate-600'"
          >
            <span v-if="selectedOption === 'upload'" class="material-symbols-outlined text-white text-xs">check</span>
          </div>
        </div>
      </div>

      <!-- AI Generate -->
      <div
        class="p-4 rounded-md border cursor-pointer transition-all"
        :class="selectedOption === 'ai'
          ? 'border-primary bg-primary/5'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="selectedOption = 'ai'"
      >
        <div class="w-12 h-12 rounded-md bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mx-auto mb-3">
          <span class="material-symbols-outlined text-purple-600 text-xl">auto_awesome</span>
        </div>
        <h3 class="text-sm font-semibold text-slate-900 dark:text-white text-center mb-1">
          AI生成素材
        </h3>
        <p class="text-xs text-slate-600 dark:text-slate-400 text-center mb-3">
          4种AI生成方式，快速创作高质量素材
        </p>
        <div class="flex items-center justify-center">
          <div
            class="w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors"
            :class="selectedOption === 'ai'
              ? 'border-primary bg-primary'
              : 'border-slate-300 dark:border-slate-600'"
          >
            <span v-if="selectedOption === 'ai'" class="material-symbols-outlined text-white text-xs">check</span>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Methods (if AI selected) -->
    <div v-if="selectedOption === 'ai'" class="mb-6 p-4 rounded-md bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
      <h4 class="text-xs font-semibold text-slate-900 dark:text-white mb-3">AI生成方式</h4>
      <div class="grid grid-cols-2 gap-2">
        <div class="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <div class="flex items-center gap-2 mb-1">
            <span class="material-symbols-outlined text-primary text-base">add_circle</span>
            <span class="text-xs font-semibold text-slate-900 dark:text-white">全新生成</span>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400">通过文字描述生成全新素材</p>
        </div>
        <div class="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <div class="flex items-center gap-2 mb-1">
            <span class="material-symbols-outlined text-primary text-base">shuffle</span>
            <span class="text-xs font-semibold text-slate-900 dark:text-white">爆款二创</span>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400">基于高ROI素材生成变体</p>
        </div>
        <div class="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <div class="flex items-center gap-2 mb-1">
            <span class="material-symbols-outlined text-primary text-base">trending_up</span>
            <span class="text-xs font-semibold text-slate-900 dark:text-white">热点复刻</span>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400">复刻行业热门素材并本地化</p>
        </div>
        <div class="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <div class="flex items-center gap-2 mb-1">
            <span class="material-symbols-outlined text-primary text-base">auto_awesome_motion</span>
            <span class="text-xs font-semibold text-slate-900 dark:text-white">智能混剪</span>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400">AI智能混剪多个素材片段</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
      <button
        class="px-4 py-2 rounded-md text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        @click="emit('prev')"
      >
        ← 上一步
      </button>
      <div class="flex items-center gap-2">
        <button
          class="px-4 py-2 rounded-md text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          @click="emit('skip')"
        >
          跳过
        </button>
        <button
          class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
          @click="handleNext"
        >
          下一步 →
        </button>
      </div>
    </div>
  </div>
</template>
