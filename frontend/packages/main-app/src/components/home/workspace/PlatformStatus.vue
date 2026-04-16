<script setup lang="ts">
import { ref } from 'vue'

// Mock platform status
const platforms = ref([
  {
    id: 'meta',
    name: 'Meta Ads',
    icon: 'M',
    color: 'bg-blue-600',
    connected: true,
    lastSync: '5分钟前'
  },
  {
    id: 'google',
    name: 'Google Ads',
    icon: 'G',
    color: 'bg-red-600',
    connected: true,
    lastSync: '5分钟前'
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    icon: 'T',
    color: 'bg-slate-900 dark:bg-white',
    textColor: 'text-white dark:text-slate-900',
    connected: false,
    lastSync: '需要重新授权'
  }
])

const handleReconnect = (platform: any) => {
  console.log('重新连接:', platform.id)
  // TODO: 实现重新连接逻辑
}

const handleSync = () => {
  console.log('手动同步所有平台')
  // TODO: 实现同步逻辑
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-base">link</span>
        <h4 class="text-sm font-semibold text-slate-900 dark:text-white">平台状态</h4>
      </div>
      <button
        class="text-xs text-primary hover:underline"
        @click="handleSync"
      >
        手动同步
      </button>
    </div>

    <div class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
      <div class="space-y-2">
        <div
          v-for="platform in platforms"
          :key="platform.id"
          class="flex items-center justify-between p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
        >
          <div class="flex items-center gap-2">
            <div
              class="w-8 h-8 rounded-md flex items-center justify-center text-base font-bold flex-shrink-0"
              :class="[platform.color, platform.textColor || 'text-white']"
            >
              {{ platform.icon }}
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-900 dark:text-white">
                {{ platform.name }}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400">
                {{ platform.lastSync }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="platform.connected"
              class="flex items-center gap-1 text-xs font-medium text-emerald-600"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              已连接
            </span>
            <button
              v-else
              class="px-2 py-1 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors"
              @click="handleReconnect(platform)"
            >
              重新连接
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
