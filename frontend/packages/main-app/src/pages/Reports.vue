<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import ReportsContent from '@/components/home/workspace/ReportsContent.vue'

const router = useRouter()

const activeSession = ref('sess_001')
const chatInput = ref('')

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
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
    content: '你好！我是ANIFORCE智能营销助手。可以帮你解读报表、定位异常数据或整理优化建议。'
  }
])

const quickHints = [
  '解读今日报表',
  '分析ROI变化',
  '找出异常计划',
  '生成优化建议'
]

const switchPanel = (item: { path?: string }) => {
  if (item.path) router.push(item.path)
}

const switchSession = (session: { id: string }) => {
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
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="reports"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col overflow-hidden bg-white dark:bg-slate-900">
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white">数据报表</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400">汇总计划消耗、安装、ROI、平台对比、素材排行和策略洞察</p>
        </div>
        <button
          class="h-8 w-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
          @click="$router.go(0)"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">refresh</span>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <ReportsContent />
      </div>
    </main>

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
