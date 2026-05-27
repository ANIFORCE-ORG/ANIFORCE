<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

const activePanel = ref('settings')

const showSystemPanel = ref(false)

const settingCards = [
  {
    id: 'organizations',
    icon: 'corporate_fare',
    title: '组织与权限',
    description: '管理组织、成员角色和广告账户的数据隔离边界',
    action: '管理组织',
    enabled: true,
    path: '/organization-settings'
  },
  {
    id: 'agent-account',
    icon: 'admin_panel_settings',
    title: '系统账号设置',
    description: '管理团队成员、登录身份和基础账号信息',
    action: '进入账号设置',
    enabled: true,
    path: '/account-config'
  },
  {
    id: 'system',
    icon: 'tune',
    title: '系统设置',
    description: '配置默认偏好、通知、权限和系统级策略',
    action: '进入系统设置',
    enabled: false,
    path: ''
  },
  {
    id: 'platform-connections',
    icon: 'hub',
    title: '平台连接',
    description: '连接 Meta、Google、TikTok 广告平台和同步广告账户',
    action: '管理平台连接',
    enabled: true,
    path: '/platform-connections'
  },
  {
    id: 'ai-usage',
    icon: 'monitoring',
    title: 'AI 使用量',
    description: '查看模型调用、Token 消耗、场景日志和预算限制',
    action: '查看使用量',
    enabled: true,
    path: '/ai-usage-config'
  }
]

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const handleCardClick = (cardId: string) => {
  const card = settingCards.find(c => c.id === cardId)
  
  if (card?.path) {
    router.push(card.path)
    return
  }
  
  switch (cardId) {
    case 'system':
      showSystemPanel.value = true
      break
  }
}

onMounted(() => {
  console.log('设置页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="[]"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <h1 class="text-xl font-bold text-slate-900 dark:text-white">设置</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">管理 Agent 系统账号、系统配置和广告平台连接</p>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <!-- 卡片式设置入口 -->
        <div v-if="!showSystemPanel" class="grid gap-4 md:grid-cols-3">
          <section
            v-for="card in settingCards"
            :key="card.id"
            class="rounded-md border border-slate-200 dark:border-slate-700 p-5 bg-white dark:bg-slate-800 hover:border-primary/50 transition-all"
          >
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-primary text-2xl">{{ card.icon }}</span>
              <h2 class="font-semibold text-slate-900 dark:text-white">{{ card.title }}</h2>
            </div>
            <p class="mt-3 text-sm text-slate-500 dark:text-slate-400 min-h-10">{{ card.description }}</p>
            <button
              class="mt-5 px-4 py-2 rounded-md text-sm font-medium transition-colors"
              :class="card.enabled 
                ? 'bg-primary text-white hover:bg-primary/90' 
                : 'border border-slate-200 dark:border-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'"
              :disabled="!card.enabled"
              @click="handleCardClick(card.id)"
            >
              {{ card.action }}
            </button>
          </section>
        </div>

        <!-- 系统设置详细面板 -->
        <div v-if="showSystemPanel" class="max-w-4xl mx-auto">
          <div class="flex items-center gap-3 mb-6">
            <button
              class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="showSystemPanel = false"
            >
              <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
            </button>
            <h2 class="text-lg font-bold text-slate-900 dark:text-white">系统设置</h2>
          </div>
          <div class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-8 text-center">
            <span class="material-symbols-outlined text-slate-400 text-5xl mb-3">construction</span>
            <p class="text-slate-500 dark:text-slate-400">系统设置功能开发中...</p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
