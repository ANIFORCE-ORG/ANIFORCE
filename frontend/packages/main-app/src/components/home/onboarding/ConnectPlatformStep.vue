<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits<{
  next: [data: any]
  prev: []
  skip: []
}>()

interface Platform {
  id: string
  name: string
  description: string
  icon: string
  color: string
  textColor?: string
  connected: boolean
}

const platforms = ref<Platform[]>([
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

const connectingPlatform = ref<string | null>(null)

const fetchConnectedAccounts = async () => {
  try {
    const response = await axios.get('/api/v1/platform/accounts')
    const accounts = response.data

    // 更新平台连接状态
    platforms.value.forEach(platform => {
      platform.connected = accounts.some((acc: any) =>
        acc.platform === platform.id && acc.status === 'active'
      )
    })
  } catch (error) {
    console.error('Failed to fetch accounts:', error)
  }
}

const handleConnect = async (platform: Platform) => {
  connectingPlatform.value = platform.id
  try {
    const response = await axios.post(`/api/v1/platform/connect?platform=${platform.id}`)
    const { auth_url } = response.data

    // 打开 OAuth 授权窗口
    const authWindow = window.open(auth_url, '_blank', 'width=600,height=700')

    // 监听授权完成（实际应用中需要实现回调处理）
    // 这里简化处理，直接标记为已连接
    setTimeout(() => {
      platform.connected = true
      connectingPlatform.value = null
    }, 2000)
  } catch (error) {
    console.error('Failed to connect platform:', error)
    connectingPlatform.value = null
  }
}

const addTestAccount = async (platform: Platform) => {
  try {
    await axios.post(`/api/v1/platform/accounts/test?platform=${platform.id}`)
    platform.connected = true
  } catch (error) {
    console.error('Failed to add test account:', error)
  }
}

const handleNext = () => {
  const connectedPlatforms = platforms.value.filter(p => p.connected)
  emit('next', { platforms: connectedPlatforms })
}

onMounted(() => {
  fetchConnectedAccounts()
})
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
          <div class="flex flex-col items-end gap-2">
            <div v-if="platform.connected" class="flex items-center gap-1 text-emerald-600">
              <span class="material-symbols-outlined text-lg">check_circle</span>
              <span class="text-xs font-semibold">已连接</span>
            </div>
            <template v-else>
              <button
                class="px-3 py-1.5 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                :disabled="connectingPlatform === platform.id"
                @click="handleConnect(platform)"
              >
                {{ connectingPlatform === platform.id ? '连接中...' : '立即连接' }}
              </button>
              <button
                class="px-3 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                @click="addTestAccount(platform)"
              >
                添加测试账号
              </button>
            </template>
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
