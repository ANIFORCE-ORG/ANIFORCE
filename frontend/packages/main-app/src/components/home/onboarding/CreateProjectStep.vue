<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  next: [data: any]
  prev: []
  skip: []
}>()

const projectName = ref('')
const productType = ref('casual_game')
const targetRegion = ref('US')

const productTypes = [
  { value: 'casual_game', label: '休闲游戏', icon: '🎮' },
  { value: 'mid_core_game', label: '中重度游戏', icon: '⚔️' },
  { value: 'drama_app', label: '短剧应用', icon: '🎬' },
  { value: 'novel_app', label: '小说应用', icon: '📚' },
  { value: 'ecommerce', label: '电商', icon: '🛍️' },
  { value: 'other', label: '其他', icon: '📦' }
]

const regions = [
  { value: 'US', label: '美国', flag: '🇺🇸' },
  { value: 'UK', label: '英国', flag: '🇬🇧' },
  { value: 'JP', label: '日本', flag: '🇯🇵' },
  { value: 'KR', label: '韩国', flag: '🇰🇷' },
  { value: 'CN', label: '中国', flag: '🇨🇳' }
]

const handleNext = () => {
  if (!projectName.value.trim()) {
    alert('请输入项目名称')
    return
  }
  emit('next', {
    name: projectName.value,
    productType: productType.value,
    targetRegion: targetRegion.value
  })
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-2">
        创建第一个项目
      </h2>
      <p class="text-sm text-slate-600 dark:text-slate-400">
        项目是管理广告的基本单位，一个项目可以包含多个投放计划和素材
      </p>
    </div>

    <!-- Form -->
    <div class="space-y-4 mb-6">
      <!-- Project Name -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          项目名称 *
        </label>
        <input
          v-model="projectName"
          type="text"
          placeholder="例如：Candy Blast 全球推广"
          class="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <!-- Product Type -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          产品类型
        </label>
        <div class="grid grid-cols-3 gap-2">
          <div
            v-for="type in productTypes"
            :key="type.value"
            class="p-3 rounded-md border cursor-pointer transition-all"
            :class="productType === type.value
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
            @click="productType = type.value"
          >
            <div class="text-xl mb-1">{{ type.icon }}</div>
            <div class="text-xs font-semibold text-slate-900 dark:text-white">
              {{ type.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- Target Region -->
      <div>
        <label class="block text-xs font-semibold text-slate-900 dark:text-white mb-2">
          目标市场
        </label>
        <div class="grid grid-cols-5 gap-2">
          <div
            v-for="region in regions"
            :key="region.value"
            class="p-3 rounded-md border cursor-pointer transition-all text-center"
            :class="targetRegion === region.value
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
            @click="targetRegion = region.value"
          >
            <div class="text-xl mb-1">{{ region.flag }}</div>
            <div class="text-xs font-semibold text-slate-900 dark:text-white">
              {{ region.label }}
            </div>
          </div>
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
