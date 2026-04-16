<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  next: [data: any]
  prev: []
  skip: []
}>()

const platforms = ref([
  {
    id: 'meta',
    name: 'Meta Ads',
    description: '管理 Facebook 和 Instagram 广告',
    icon: 'M',
    color: 'bg-blue-600',
    connected: false
  },
  {
    id: 'google',
    name: 'Google Ads',
    description: '管理 Google 搜索和展示广告',
    icon: 'G',
    color: 'bg-red-600',
    connected: false
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    description: '管理 TikTok 短视频广告',
    icon: 'T',
    color: 'bg-slate-900 dark:bg-white',
    textColor: 'text-white dark:text-slate-900',
    connected: false
  }
])

const handleConnect = (platform: any) => {
  // 模拟连接
  platform.connected = true
  console.log('连接平台:', platform.id)
}

const handleNext = () => {
  const connectedPlatforms = platforms.value.filter(p => p.connected)
  emit('next', { platforms: connectedPlatforms })
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-2">
        连接广告平台
      </h2>
      <p class="text-sm text-slate-600 dark:text-slate-400">
        连接你的广告账户，系统会自动同步投放数据
      </p>
    </div>

    <!-- Platforms -->
    <div class="space-y-3 mb-6">
      <div
        v-for="platform in platforms"
        :key="platform.id"
        class="p-4 rounded-md border transition-all"
        :class="platform.connected
          ? 'border-primary bg-primary/5'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
      >
        <div class="flex items-center gap-3">
          <!-- Icon -->
          <div
            class="w-12 h-12 rounded-md flex items-center justify-center text-xl font-bold flex-shrink-0"
            :class="[platform.color, platform.textColor || 'text-white']"
          >
            {{ platform.icon }}
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-white mb-1 text-sm">
              {{ platform.name }}
            </h3>
            <p class="text-xs text-slate-600 dark:text-slate-400">
              {{ platform.description }}
            </p>
          </div>

          <!-- Status -->
          <div class="flex items-center gap-2">
            <div v-if="platform.connected" class="flex items-center gap-1 text-emerald-600">
              <span class="material-symbols-outlined text-lg">check_circle</span>
              <span class="text-xs font-semibold">已连接</span>
            </div>
            <button
              v-else
              class="px-3 py-1.5 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors"
              @click="handleConnect(platform)"
            >
              立即连接
            </button>
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
