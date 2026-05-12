<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import TodayOverview from './workspace/TodayOverview.vue'
import ActionItems from './workspace/ActionItems.vue'
import QuickActions from './workspace/QuickActions.vue'
import DataTrends from './workspace/DataTrends.vue'
import BasicInsights from './workspace/BasicInsights.vue'
import PlatformStatus from './workspace/PlatformStatus.vue'

const router = useRouter()
const route = useRoute()

const activePanel = ref('dashboard')
const activeSession = ref('sess_001')
const chatInput = ref('')

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '工作台', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/reports' }
]

const sessions = ref([
  { id: 'sess_001', name: '投放咨询', active: true }
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: '你好！我是ANIFORCE智能营销助手。有什么可以帮你的吗？'
  }
])

const quickHints = [
  '查看今日数据',
  '生成新素材',
  '创建投放计划',
  '优化建议'
]

const switchPanel = (item: any) => {
  if (item.id === 'dashboard') {
    activePanel.value = 'dashboard'
    router.push('/dashboard')
  } else if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleSendMessage = (message: string) => {
  console.log('发送消息:', message)
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
}

// Watch route query to update active panel
watch(() => route.query.panel, (newPanel) => {
  if (newPanel === 'reports') {
    router.replace('/reports')
  } else {
    activePanel.value = 'dashboard'
  }
}, { immediate: true })
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间工作台区域 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white">
            {{ activePanel === 'reports' ? '数据报表' : '工作台' }}
          </h3>
          <p class="text-xs text-slate-500 dark:text-slate-400">
            {{ new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }) }}
          </p>
        </div>
        <button
          class="h-8 w-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
          @click="$router.go(0)"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">refresh</span>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Dashboard Content -->
        <div v-if="activePanel === 'dashboard'" class="space-y-6">
          <!-- Today Overview -->
          <TodayOverview />

          <!-- Action Items -->
          <ActionItems />

          <!-- Quick Actions & Data Trends -->
          <div class="grid grid-cols-2 gap-3">
            <QuickActions />
            <DataTrends />
          </div>

          <!-- Basic Insights -->
          <BasicInsights />

          <!-- Platform Status -->
          <PlatformStatus />
        </div>

      </div>
    </main>

    <!-- 右侧对话区 -->
    <ChatPanel
      :messages="messages"
      :quick-hints="quickHints"
      :chat-input="chatInput"
      @send-message="handleSendMessage"
      @hint-click="handleHintClick"
      @update:chat-input="chatInput = $event"
    />
  </div>
</template>
