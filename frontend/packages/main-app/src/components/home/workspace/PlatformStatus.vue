<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Platform {
  id: string
  name: string
  icon: string
  color: string
  textColor?: string
  connected: boolean
  lastSync: string
  accountName?: string
}

// Mock platform status
const platforms = ref<Platform[]>([
  {
    id: 'meta',
    name: 'Meta Ads',
    icon: 'M',
    color: 'bg-blue-600',
    connected: false,
    lastSync: '未连接'
  },
  {
    id: 'google',
    name: 'Google Ads',
    icon: 'G',
    color: 'bg-red-600',
    connected: false,
    lastSync: '未连接'
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    icon: 'T',
    color: 'bg-slate-900 dark:bg-white',
    textColor: 'text-white dark:text-slate-900',
    connected: false,
    lastSync: '未连接'
  }
])

const connectingPlatform = ref<string | null>(null)
const showManageModal = ref(false)

const fetchConnectedAccounts = async () => {
  try {
    const response = await axios.get('/api/v1/platform/accounts')
    const accounts = response.data

    // 更新平台连接状态
    platforms.value.forEach(platform => {
      const account = accounts.find((acc: any) =>
        acc.platform === platform.id && acc.status === 'active'
      )
      if (account) {
        platform.connected = true
        platform.accountName = account.account_name
        platform.lastSync = '5分钟前' // 实际应该从 API 获取
      } else {
        platform.connected = false
        platform.lastSync = '未连接'
      }
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
    window.open(auth_url, '_blank', 'width=600,height=700')

    // 监听授权完成
    setTimeout(() => {
      fetchConnectedAccounts()
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
    await fetchConnectedAccounts()
  } catch (error) {
    console.error('Failed to add test account:', error)
  }
}

const handleSync = async () => {
  console.log('手动同步所有平台')
  await fetchConnectedAccounts()
}

const handleManage = () => {
  showManageModal.value = true
}

onMounted(() => {
  fetchConnectedAccounts()
})
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
            <div v-if="platform.connected" class="flex items-center gap-2">
              <span class="flex items-center gap-1 text-xs font-medium text-emerald-600">
                <span class="material-symbols-outlined text-sm">check_circle</span>
                已连接
              </span>
              <button
                class="px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                @click="handleConnect(platform)"
              >
                重新连接
              </button>
            </div>
            <div v-else class="flex flex-col gap-1">
              <button
                class="px-2 py-1 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                :disabled="connectingPlatform === platform.id"
                @click="handleConnect(platform)"
              >
                {{ connectingPlatform === platform.id ? '连接中...' : '立即连接' }}
              </button>
              <button
                class="px-2 py-1 rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                @click="addTestAccount(platform)"
              >
                测试账号
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
