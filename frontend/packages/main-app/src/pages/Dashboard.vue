<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const auth = useAuthStore()

const activeSession = ref('sess_g001')
const chatInput = ref('')
const timeFilter = ref('7d')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false },
  { id: 'sess_d001', name: 'DramaBox新剧推广', active: false }
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能营销助手。

当前投放概览：
• 📊 Candy Blast：消耗$52,300，ROI 1.88x
• 🎬 DramaBox：消耗$98,700，ROI 2.15x

我可以帮您：
• 查看营销数据概览
• 创建和管理项目
• 规划和执行广告投放
• 生成和管理创意素材
• 分析数据报表

请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '数据概览',
  '项目列表',
  '广告系列',
  '生成创意',
  '热门素材',
  '素材二创'
]

const stats = ref({
  spend: { value: '$151,000', label: '总消耗', change: '+5%', trend: 'up' },
  roi: { value: '2.0x', label: '整体ROI', change: '+0.2', trend: 'up' },
  installs: { value: '45,850', label: '总安装数', change: '+8%', trend: 'up' },
  cpi: { value: '$3.3', label: '平均CPI', change: '-$0.2', trend: 'down' }
})

const alerts = ref([
  {
    id: 1,
    type: 'warning',
    icon: 'warning',
    title: '素材频次过高',
    desc: '素材"CB_Character_CandyQueen"频次4.1，建议替换',
    action: '立即处理'
  },
  {
    id: 2,
    type: 'info',
    icon: 'info',
    title: '表现优异',
    desc: 'TikTok广告"CB_US_iOS_Install_001"ROI达2.1x',
    action: '查看详情'
  },
  {
    id: 3,
    type: 'critical',
    icon: 'error',
    title: '成本异常',
    desc: 'Meta广告CPI上涨至$3.2，超出目标23%',
    action: '立即优化'
  },
  {
    id: 4,
    type: 'info',
    icon: 'lightbulb',
    title: '新热点发现',
    desc: '"霸总"题材素材互动率上升42%',
    action: '了解详情'
  }
])

const timeFilters = [
  { value: 'realtime', label: '实时' },
  { value: 'today', label: '今日' },
  { value: 'yesterday', label: '昨日' },
  { value: '7days', label: '近7日' },
  { value: '30days', label: '近30日' }
]

const switchPanel = (item: any) => {
  if (item.path) {
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

const handleRefresh = () => {
  console.log('刷新数据')
}

const handleAlertAction = (alert: any) => {
  console.log('处理提醒:', alert)
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间数据展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Panel Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <h3 class="font-bold text-slate-900 dark:text-white">数据概览</h3>
        <div class="flex items-center gap-2">
          <!-- Time Filter -->
          <select
            v-model="timeFilter"
            class="text-sm px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option v-for="filter in timeFilters" :key="filter.value" :value="filter.value">
              {{ filter.label }}
            </option>
          </select>
          <!-- Refresh Button -->
          <button
            class="h-8 w-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="handleRefresh"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-xl">refresh</span>
          </button>
        </div>
      </div>

      <!-- Panel Content -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Stats Grid -->
        <div class="grid grid-cols-2 gap-3">
          <div
            v-for="(stat, key) in stats"
            :key="key"
            class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50"
          >
            <div class="flex items-center justify-between mb-2">
              <span
                class="material-symbols-outlined text-2xl"
                :class="{
                  'text-blue-600': key === 'spend',
                  'text-emerald-600': key === 'roi',
                  'text-purple-600': key === 'installs',
                  'text-orange-600': key === 'cpi'
                }"
              >
                {{ key === 'spend' ? 'payments' : key === 'roi' ? 'trending_up' : key === 'installs' ? 'download' : 'attach_money' }}
              </span>
              <span
                class="text-xs font-semibold px-2 py-0.5 rounded-full"
                :class="(key === 'cpi' ? stat.trend === 'down' : stat.trend === 'up')
                  ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600'
                  : 'bg-red-50 dark:bg-red-900/30 text-red-600'"
              >
                {{ stat.change }}
              </span>
            </div>
            <div class="text-xl font-bold text-slate-900 dark:text-white mb-1">{{ stat.value }}</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">{{ stat.label }}</div>
          </div>
        </div>

        <!-- Alerts Section -->
        <div>
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">notifications</span>
            <h4 class="font-semibold text-slate-900 dark:text-white">异常提醒</h4>
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-900/30 text-red-600">
              {{ alerts.length }}
            </span>
          </div>
          <div class="space-y-3">
            <div
              v-for="alert in alerts"
              :key="alert.id"
              class="p-3 rounded-md border transition-all"
              :class="{
                'border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/10': alert.type === 'warning',
                'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10': alert.type === 'info',
                'border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10': alert.type === 'critical'
              }"
            >
              <div class="flex items-start gap-2 mb-2">
                <span
                  class="material-symbols-outlined text-lg flex-shrink-0"
                  :class="{
                    'text-yellow-600': alert.type === 'warning',
                    'text-blue-600': alert.type === 'info',
                    'text-red-600': alert.type === 'critical'
                  }"
                >
                  {{ alert.icon }}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-semibold text-slate-900 dark:text-white mb-1">{{ alert.title }}</div>
                  <div class="text-xs text-slate-600 dark:text-slate-400">{{ alert.desc }}</div>
                </div>
              </div>
              <button
                class="text-xs font-medium text-primary hover:underline"
                @click="handleAlertAction(alert)"
              >
                {{ alert.action }}
              </button>
            </div>
          </div>
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
