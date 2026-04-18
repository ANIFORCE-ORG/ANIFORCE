<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const auth = useAuthStore()

const activePanel = ref('settings')
const activeSession = ref('sess_g001')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false }
])

const quickHints = [
  '查看用量统计',
  '连接广告账户',
  '修改账户信息',
  '升级套餐'
]

// 用户信息
const userEmail = ref(auth.user?.email || 'test@animagus.com')

// 套餐和用量信息
const currentPlan = ref({
  name: 'Seed',
  icon: '🌱',
  color: 'text-orange-600',
  bgColor: 'bg-orange-50 dark:bg-orange-900/30'
})

const usage = ref({
  monthlyUsed: 2.40,
  monthlyLimit: 100,
  aiCalls: 156,
  aiCallsLimit: 10000,
  materialsGenerated: 23,
  materialsLimit: 500
})

// 广告账户连接状态
const adAccounts = ref([
  {
    id: 'meta',
    name: 'Meta Ads',
    icon: 'M',
    iconBg: 'bg-blue-600',
    connected: false,
    accountId: '' as string
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    icon: '♪',
    iconBg: 'bg-black dark:bg-white',
    iconColor: 'text-white dark:text-black',
    connected: false,
    accountId: '' as string
  },
  {
    id: 'google',
    name: 'Google Ads',
    icon: 'G',
    iconBg: 'bg-red-600',
    connected: false,
    accountId: '' as string
  }
])

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleEditEmail = () => {
  const newEmail = prompt('请输入新的邮箱地址:', userEmail.value)
  if (newEmail && newEmail.trim()) {
    userEmail.value = newEmail.trim()
    console.log('更新邮箱:', newEmail)
  }
}

const handleDeleteAccount = () => {
  const confirmed = confirm('确定要删除账户吗？此操作不可恢复！')
  if (confirmed) {
    console.log('删除账户')
    // TODO: 调用删除账户API
  }
}

const handleUpgradePlan = () => {
  console.log('升级套餐')
  // TODO: 跳转到升级页面或显示升级弹窗
}

const handleConnectAdAccount = (accountId: string) => {
  console.log('连接广告账户:', accountId)
  const account = adAccounts.value.find(a => a.id === accountId)
  if (account) {
    if (account.connected) {
      // 断开连接
      const confirmed = confirm(`确定要断开 ${account.name} 连接吗？`)
      if (confirmed) {
        account.connected = false
        account.accountId = ''
      }
    } else {
      // 连接账户
      // TODO: 实现OAuth授权流程
      account.connected = true
      account.accountId = `${accountId}_${Date.now()}`
    }
  }
}

onMounted(() => {
  console.log('账户设置页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间设置展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <h3 class="font-bold text-slate-900 dark:text-white">账户设置</h3>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="max-w-4xl mx-auto space-y-8">
          
          <!-- Login Account Section -->
          <section>
            <h2 class="text-lg font-bold text-slate-900 dark:text-white mb-4">登录账户信息</h2>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-6">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm text-slate-500 dark:text-slate-400 mb-1">Email</div>
                  <div class="text-base font-medium text-slate-900 dark:text-white">{{ userEmail }}</div>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    @click="handleEditEmail"
                  >
                    <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">edit</span>
                  </button>
                  <button
                    class="p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-900/20 transition-colors"
                    @click="handleDeleteAccount"
                    :disabled="true"
                  >
                    <span class="material-symbols-outlined text-red-200 text-xl">delete</span>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- Plan & Usage Section -->
          <section>
            <h2 class="text-lg font-bold text-slate-900 dark:text-white mb-4">会员等级 & 用量</h2>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-6">
              <!-- Current Plan -->
              <div class="flex items-center justify-between mb-6">
                <div class="flex items-center gap-3">
                  <span class="text-2xl">{{ currentPlan.icon }}</span>
                  <span class="text-base font-semibold" :class="currentPlan.color">{{ currentPlan.name }}</span>
                </div>
                <button
                  class="px-4 py-2 rounded-md border border-primary text-primary hover:bg-primary/10 transition-colors text-sm font-medium"
                  @click="handleUpgradePlan"
                >
                  升级套餐
                </button>
              </div>

              <!-- Monthly Usage -->
              <div class="space-y-4">
                <div>
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm text-slate-600 dark:text-slate-400">月度用量</span>
                    <span class="text-sm font-semibold text-primary">{{ usage.monthlyUsed }}% used</span>
                  </div>
                  <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-primary rounded-full transition-all"
                      :style="{ width: `${usage.monthlyUsed}%` }"
                    ></div>
                  </div>
                </div>

                <!-- AI Calls -->
                <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-lg">psychology</span>
                      <span class="text-sm text-slate-600 dark:text-slate-400">AI 调用次数</span>
                    </div>
                    <span class="text-sm font-semibold text-slate-900 dark:text-white">
                      {{ usage.aiCalls.toLocaleString() }} / {{ usage.aiCallsLimit.toLocaleString() }}
                    </span>
                  </div>
                  <div class="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-emerald-500 rounded-full transition-all"
                      :style="{ width: `${(usage.aiCalls / usage.aiCallsLimit) * 100}%` }"
                    ></div>
                  </div>
                </div>

                <!-- Materials Generated -->
                <div class="pt-4 border-t border-slate-200 dark:border-slate-700">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-lg">video_library</span>
                      <span class="text-sm text-slate-600 dark:text-slate-400">素材生成数量</span>
                    </div>
                    <span class="text-sm font-semibold text-slate-900 dark:text-white">
                      {{ usage.materialsGenerated }} / {{ usage.materialsLimit }}
                    </span>
                  </div>
                  <div class="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-purple-500 rounded-full transition-all"
                      :style="{ width: `${(usage.materialsGenerated / usage.materialsLimit) * 100}%` }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- Ad Account Connections Section -->
          <section>
            <h2 class="text-lg font-bold text-slate-900 dark:text-white mb-4">平台广告账户管理</h2>
            <div class="space-y-3">
              <div
                v-for="account in adAccounts"
                :key="account.id"
                class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-5 hover:border-primary/50 transition-all"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-4">
                    <div 
                      class="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
                      :class="account.iconBg"
                    >
                      <span :class="account.iconColor || 'text-white'">{{ account.icon }}</span>
                    </div>
                    <div>
                      <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ account.name }}</div>
                      <div v-if="account.connected" class="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
                        已连接 · {{ account.accountId }}
                      </div>
                      <div v-else class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        未连接
                      </div>
                    </div>
                  </div>
                  <button
                    class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
                    :class="account.connected 
                      ? 'border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                      : 'border border-primary text-primary hover:bg-primary/10'"
                    @click="handleConnectAdAccount(account.id)"
                  >
                    {{ account.connected ? '取消连接' : '立即连接' }}
                  </button>
                </div>
              </div>
            </div>
          </section>

        </div>
      </div>
    </main>

  </div>
</template>
