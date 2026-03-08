<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const campaignId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const chatInput = ref('')

const campaign = ref({
  id: '',
  name: '',
  projectId: '',
  projectName: '',
  platform: '',
  budget: '',
  spend: '',
  installs: '',
  roi: '',
  targetCPA: '',
  startDate: '',
  status: 'running'
})

const creatives = ref([
  {
    id: 'creative_001',
    name: '游戏玩法展示-紫色主题',
    image: '/images/creatives/creative_game_001.jpg',
    status: 'running'
  },
  {
    id: 'creative_002',
    name: '游戏失败场景-黄色主题',
    image: '/images/creatives/creative_game_002.jpg',
    status: 'running'
  },
  {
    id: 'creative_003',
    name: '游戏爆炸特效-紫色主题',
    image: '/images/creatives/creative_game_003.jpg',
    status: 'running'
  }
])

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
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n当前正在查看"${campaign.value.name}"广告详情。\n\n我可以帮您：\n• 分析素材表现\n• 优化投放策略\n• 素材创意建议\n• 预算调整建议\n\n请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '分析素材表现',
  '优化建议',
  '创意素材推荐',
  '预算调整',
  '添加新素材',
  '数据报表'
]

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'campaign', label: '广告投放', path: '/campaigns' },
  { id: 'materials', icon: 'auto_awesome', label: '创意素材', path: '/materials' },
  { id: 'reports', icon: 'analytics', label: '数据报表', path: '/reports' },
]

onMounted(() => {
  loadCampaignData()
})

const loadCampaignData = () => {
  const mockCampaigns: Record<string, any> = {
    'camp_001': {
      id: 'camp_001',
      name: 'CB_US_Android_Install_001',
      projectId: 'proj_001',
      projectName: 'Candy Blast - 全球推广',
      platform: 'Google',
      budget: '$35,000',
      spend: '$22,800',
      installs: '8,750',
      roi: '1.85x',
      targetCPA: '$2.5',
      startDate: '2026-02-01',
      status: 'running'
    },
    'camp_002': {
      id: 'camp_002',
      name: 'CB_US_iOS_Install_001',
      projectId: 'proj_001',
      projectName: 'Candy Blast - 全球推广',
      platform: 'TikTok',
      budget: '$30,000',
      spend: '$18,900',
      installs: '7,200',
      roi: '2.1x',
      targetCPA: '$2.8',
      startDate: '2026-02-01',
      status: 'running'
    },
    'camp_003': {
      id: 'camp_003',
      name: 'CB_UK_Android_Install_001',
      projectId: 'proj_001',
      projectName: 'Candy Blast - 全球推广',
      platform: 'Meta',
      budget: '$25,000',
      spend: '$10,600',
      installs: '4,100',
      roi: '1.65x',
      targetCPA: '$3.0',
      startDate: '2026-02-05',
      status: 'running'
    }
  }
  
  const campaignData = mockCampaigns[campaignId.value]
  if (campaignData) {
    campaign.value = campaignData
  }
}

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleSendMessage = () => {
  if (!chatInput.value.trim()) return
  console.log('发送消息:', chatInput.value)
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
}

const handleBack = () => {
  router.push(`/projects/${campaign.value.projectId}`)
}

const handleAddCreative = () => {
  console.log('添加素材')
}

const getPlatformColor = (platform: string) => {
  const colors: Record<string, string> = {
    'Google': 'text-blue-600',
    'TikTok': 'text-slate-900 dark:text-white',
    'Meta': 'text-blue-500'
  }
  return colors[platform] || 'text-slate-600'
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="campaigns"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间广告详情展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center px-6">
        <div class="flex items-center gap-4">
          <button
            class="flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-primary transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-lg">arrow_back</span>
            <span class="text-sm font-medium">返回广告列表</span>
          </button>
          <div class="h-6 w-px bg-slate-200 dark:bg-slate-800"></div>
          <h3 class="font-bold text-slate-900 dark:text-white">{{ campaign.name }}</h3>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 广告配置详情 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <div class="grid grid-cols-2 gap-4">
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">所属项目</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white text-right">{{ campaign.projectName }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">投放平台</span>
              <span class="text-sm font-medium" :class="getPlatformColor(campaign.platform)">{{ campaign.platform }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">预算</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign.budget }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">已消耗</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign.spend }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">安装数</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign.installs }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">ROI</span>
              <span class="text-sm font-medium text-emerald-600">{{ campaign.roi }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">目标CPA</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign.targetCPA }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">开始日期</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign.startDate }}</span>
            </div>
          </div>
        </div>

        <!-- 投放素材列表 -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-sm font-semibold text-slate-900 dark:text-white">投放素材 ({{ creatives.length }})</h4>
            <button
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleAddCreative"
            >
              <span class="material-symbols-outlined text-lg">add_photo_alternate</span>
              添加素材
            </button>
          </div>
          
          <div class="grid grid-cols-3 gap-4">
            <div
              v-for="creative in creatives"
              :key="creative.id"
              class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden hover:border-primary/50 transition-all cursor-pointer"
            >
              <!-- Creative Image -->
              <div class="aspect-[9/16] bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
                <img
                  :src="creative.image"
                  :alt="creative.name"
                  class="w-full h-full object-cover"
                />
              </div>
              <!-- Creative Info -->
              <div class="p-3 bg-white dark:bg-slate-900">
                <div class="text-sm font-medium text-slate-900 dark:text-white mb-1 truncate">{{ creative.name }}</div>
                <div class="flex items-center justify-between">
                  <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600">
                    {{ creative.status === 'running' ? '投放中' : '待投放' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="creatives.length === 0" class="flex flex-col items-center justify-center py-16">
            <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">movie</span>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">暂无素材</p>
            <button
              class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
              @click="handleAddCreative"
            >
              <span class="material-symbols-outlined text-lg">add_photo_alternate</span>
              <span class="text-sm font-medium">添加首个素材</span>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 右侧对话区 -->
    <aside class="w-96 bg-slate-50 dark:bg-slate-900/50 border-l border-slate-200 dark:border-slate-800 flex flex-col">
      <!-- Chat Header -->
      <div class="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">chat</span>
          <span class="font-semibold text-slate-900 dark:text-white">AI智能助手</span>
        </div>
        <button class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors">
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">add</span>
        </button>
      </div>

      <!-- Chat Messages -->
      <div class="flex-1 overflow-y-auto p-6">
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="mb-6 flex gap-4"
        >
          <!-- Avatar -->
          <div class="h-10 w-10 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
          </div>
          <!-- Message Content -->
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ message.author }}</span>
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ message.time }}</span>
            </div>
            <div class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">{{ message.content }}</div>
          </div>
        </div>
      </div>

      <!-- Chat Input Area -->
      <div class="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-4">
        <div class="space-y-3">
          <!-- Input Wrapper -->
          <div class="flex items-end gap-3">
            <textarea
              v-model="chatInput"
              class="flex-1 resize-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="输入您的问题或需求..."
              rows="1"
              @keydown.enter.prevent="handleSendMessage"
            ></textarea>
            <button
              class="h-10 w-10 rounded-md bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors flex-shrink-0"
              @click="handleSendMessage"
            >
              <span class="material-symbols-outlined text-xl">send</span>
            </button>
          </div>
          <!-- Quick Hints -->
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs text-slate-500 dark:text-slate-400">试试：</span>
            <button
              v-for="hint in quickHints"
              :key="hint"
              class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              @click="handleHintClick(hint)"
            >
              {{ hint }}
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
