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

const userEmail = ref(auth.user?.email || 'test@animagus.com')

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
  }
}

const handleUpgradePlan = () => {
  console.log('升级套餐')
}

onMounted(() => {
  console.log('账号配置页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">系统账号设置</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">管理团队成员、登录身份和基础账号信息</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="space-y-6">
          <!-- 登录账户信息 -->
          <section>
            <h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3">登录账户信息</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-6">
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

          <!-- 会员等级 & 用量 -->
          <section>
            <h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3">会员等级 & 用量</h3>
            <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-6">
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

              <div class="space-y-4">
                <!-- 月度用量 -->
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

                <!-- AI 调用次数 -->
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

                <!-- 素材生成数量 -->
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
        </div>
      </div>
    </main>
  </div>
</template>
