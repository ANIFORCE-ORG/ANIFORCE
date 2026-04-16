<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  complete: []
  prev: []
}>()

const campaignName = ref('')
const platform = ref('meta')
const budget = ref(1000)

const platforms = [
  { value: 'meta', label: 'Meta Ads', icon: 'M', color: 'bg-blue-600' },
  { value: 'google', label: 'Google Ads', icon: 'G', color: 'bg-red-600' },
  { value: 'tiktok', label: 'TikTok Ads', icon: 'T', color: 'bg-slate-900 dark:bg-white' }
]

const handleComplete = () => {
  if (!campaignName.value.trim()) {
    alert('请输入投放计划名称')
    return
  }
  emit('complete')
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-2">
        创建投放计划
      </h2>
      <p class="text-sm text-slate-600 dark:text-slate-400">
        最后一步，创建你的第一个投放计划
      </p>
    </div>

    <!-- Form -->
    <div class="space-y-4 mb-6">
      <!-- Campaign Name -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          投放计划名称 *
        </label>
        <input
          v-model="campaignName"
          type="text"
          placeholder="例如：Candy Blast 美国iOS安装"
          class="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <!-- Platform -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          投放平台
        </label>
        <div class="grid grid-cols-3 gap-2">
          <div
            v-for="p in platforms"
            :key="p.value"
            class="p-3 rounded-md border cursor-pointer transition-all"
            :class="platform === p.value
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
            @click="platform = p.value"
          >
            <div class="flex items-center gap-2">
              <div
                class="w-8 h-8 rounded-md flex items-center justify-center text-base font-bold text-white"
                :class="p.color"
              >
                {{ p.icon }}
              </div>
              <span class="text-xs font-semibold text-slate-900 dark:text-white">
                {{ p.label }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Budget -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          日预算 (USD)
        </label>
        <div class="flex items-center gap-3">
          <input
            v-model.number="budget"
            type="range"
            min="100"
            max="10000"
            step="100"
            class="flex-1"
          />
          <div class="w-28 px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white text-center font-semibold">
            ${{ budget.toLocaleString() }}
          </div>
        </div>
      </div>
    </div>

    <!-- Success Message -->
    <div class="mb-6 p-4 rounded-md bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
      <div class="flex items-start gap-2">
        <span class="material-symbols-outlined text-emerald-600 text-xl">check_circle</span>
        <div>
          <h4 class="text-sm font-semibold text-emerald-900 dark:text-emerald-400 mb-1">
            准备就绪！
          </h4>
          <p class="text-xs text-emerald-700 dark:text-emerald-500">
            完成这一步后，你就可以开始使用 ANIFORCE 管理你的广告投放了。系统会帮你监控投放效果，并提供优化建议。
          </p>
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
      <button
        class="px-6 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
        @click="handleComplete"
      >
        完成引导，进入工作台 →
      </button>
    </div>
  </div>
</template>
