<script setup lang="ts">
const emit = defineEmits<{
  next: []
  skip: []
}>()
</script>

<template>
  <div class="flex items-center justify-center min-h-full p-6">
    <div class="max-w-2xl w-full text-center space-y-6">
      <!-- Icon -->
      <div class="flex justify-center">
        <div class="w-16 h-16 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
          <span class="material-symbols-outlined text-white text-2xl">auto_awesome</span>
        </div>
      </div>

      <!-- Title -->
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
          👋 欢迎来到 ANIFORCE
        </h1>
        <p class="text-sm text-slate-600 dark:text-slate-400">
          AI驱动的广告素材管理与投放平台
        </p>
      </div>

      <!-- Features -->
      <div class="grid grid-cols-3 gap-3 py-6">
        <div class="p-4 rounded-md bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
          <div class="w-10 h-10 rounded-md bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mx-auto mb-3">
            <span class="material-symbols-outlined text-blue-600 text-xl">palette</span>
          </div>
          <h3 class="font-semibold text-slate-900 dark:text-white mb-1 text-sm">AI生成素材</h3>
          <p class="text-xs text-slate-600 dark:text-slate-400">
            4种AI生成方式，快速创作高质量广告素材
          </p>
        </div>

        <div class="p-4 rounded-md bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
          <div class="w-10 h-10 rounded-md bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-3">
            <span class="material-symbols-outlined text-emerald-600 text-xl">ads_click</span>
          </div>
          <h3 class="font-semibold text-slate-900 dark:text-white mb-1 text-sm">多平台投放</h3>
          <p class="text-xs text-slate-600 dark:text-slate-400">
            统一管理Meta、Google、TikTok广告投放
          </p>
        </div>

        <div class="p-4 rounded-md bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
          <div class="w-10 h-10 rounded-md bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mx-auto mb-3">
            <span class="material-symbols-outlined text-purple-600 text-xl">trending_up</span>
          </div>
          <h3 class="font-semibold text-slate-900 dark:text-white mb-1 text-sm">数据驱动优化</h3>
          <p class="text-xs text-slate-600 dark:text-slate-400">
            实时监控投放效果，AI智能优化建议
          </p>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-center gap-3">
        <button
          class="px-6 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
          @click="emit('next')"
        >
          开始使用
        </button>
        <button
          class="px-6 py-2 rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          @click="emit('skip')"
        >
          跳过引导
        </button>
      </div>

      <!-- Info -->
      <p class="text-xs text-slate-500 dark:text-slate-400">
        只需4个简单步骤，即可开始使用 ANIFORCE
      </p>
    </div>
  </div>
</template>
