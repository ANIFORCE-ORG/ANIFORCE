<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const projectId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const chatInput = ref('')

const project = ref({
  id: '',
  name: '',
  description: '',
  status: 'active',
  platform: '',
  budget: '',
  spent: '',
  roi: '',
  installs: '',
  cpi: '',
  progress: 0,
  startDate: '',
  endDate: '',
  manager: '',
  productType: '',
  region: '',
  targetROI: '',
  tags: [] as string[]
})

const campaigns = ref([
  {
    id: 'camp_001',
    name: 'CB_US_Android_Install_001',
    platform: 'Google',
    spend: '$22,800',
    installs: '8,750',
    roi: '1.85x',
    status: 'running'
  },
  {
    id: 'camp_002',
    name: 'CB_US_iOS_Install_001',
    platform: 'TikTok',
    spend: '$18,900',
    installs: '7,200',
    roi: '2.1x',
    status: 'running'
  },
  {
    id: 'camp_003',
    name: 'CB_UK_Android_Install_001',
    platform: 'Meta',
    spend: '$10,600',
    installs: '4,100',
    roi: '1.65x',
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
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n当前正在查看"${project.value.name}"项目详情。\n\n我可以帮您：\n• 分析广告计划表现\n• 优化投放策略\n• 素材建议\n• 预算调整建议\n\n请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '分析广告表现',
  '优化建议',
  '素材推荐',
  '预算调整',
  '创建新广告',
  '数据报表'
]

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
]

onMounted(() => {
  loadProjectData()
})

const loadProjectData = () => {
  const mockProjects: Record<string, any> = {
    'proj_001': {
      id: 'proj_001',
      name: 'Candy Blast - 全球推广',
      description: 'Candy Blast休闲消除游戏北美欧洲市场推广项目',
      status: 'active',
      platform: 'Meta',
      budget: '$80,000',
      spent: '$52,300',
      roi: '1.88x',
      installs: '15,420',
      cpi: '$3.39',
      progress: 65,
      startDate: '2026-02-01',
      endDate: '2024-03-15',
      manager: '李明',
      productType: '休闲游戏',
      region: 'US, CA, UK',
      targetROI: '1.8x',
      tags: ['休闲游戏', '三消', '北美']
    },
    'proj_002': {
      id: 'proj_002',
      name: 'DramaBox - 东南亚市场',
      description: 'DramaBox短剧平台东南亚市场推广',
      status: 'active',
      platform: 'TikTok',
      budget: '$120,000',
      spent: '$98,700',
      roi: '2.15x',
      installs: '28,350',
      cpi: '$3.48',
      progress: 82,
      startDate: '2024-01-10',
      endDate: '2024-04-10',
      manager: '王芳',
      productType: '短剧娱乐',
      region: 'SG, MY, TH',
      targetROI: '2.0x',
      tags: ['短剧', '娱乐', '东南亚']
    }
  }
  
  const projectData = mockProjects[projectId.value]
  if (projectData) {
    project.value = projectData
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

const handleSendMessage = (message: string) => {
  console.log('发送消息:', message)
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
}

const handleBack = () => {
  router.push('/projects')
}

const handleCreateCampaign = () => {
  console.log('创建新广告')
}

const handleViewCampaign = (campaignId: string) => {
  router.push(`/campaigns/${campaignId}`)
}

const handleAddCreative = (campaignId: string) => {
  console.log('添加素材:', campaignId)
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
      active-panel="projects"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间项目详情展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center px-6">
        <div class="flex items-center gap-4">
          <button
            class="flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-primary transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-lg">arrow_back</span>
            <span class="text-sm font-medium">返回项目列表</span>
          </button>
          <div class="h-6 w-px bg-slate-200 dark:bg-slate-800"></div>
          <h3 class="font-bold text-slate-900 dark:text-white">{{ project.name }}</h3>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 项目详情信息 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h4 class="text-sm font-semibold text-slate-900 dark:text-white mb-4">项目描述</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">项目描述</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white text-right">{{ project.description }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">产品类型</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.productType }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">目标地区</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.region }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">预算</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.budget }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">已消耗</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.spent }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">目标ROI</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.targetROI }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">开始日期</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ project.startDate }}</span>
            </div>
          </div>
        </div>

        <!-- 广告计划列表 -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-sm font-semibold text-slate-900 dark:text-white">广告计划 ({{ campaigns.length }})</h4>
            <button
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleCreateCampaign"
            >
              <span class="material-symbols-outlined text-lg">add</span>
              新建广告
            </button>
          </div>
          
          <div class="space-y-3">
            <div
              v-for="campaign in campaigns"
              :key="campaign.id"
              class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:border-primary/50 transition-all"
            >
              <!-- Campaign Header -->
              <div class="flex items-center justify-between mb-3">
                <div class="flex-1">
                  <div class="text-base font-semibold text-slate-900 dark:text-white mb-1">{{ campaign.name }}</div>
                  <div class="text-xs font-medium" :class="getPlatformColor(campaign.platform)">{{ campaign.platform }}</div>
                </div>
              </div>

              <!-- Campaign Stats -->
              <div class="grid grid-cols-3 gap-4 mb-3">
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ campaign.spend }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">消耗</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ campaign.installs }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">安装</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-emerald-600">{{ campaign.roi }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">ROI</div>
                </div>
              </div>

              <!-- Campaign Actions -->
              <div class="flex items-center gap-2">
                <button
                  class="flex-1 px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  @click="handleViewCampaign(campaign.id)"
                >
                  查看详情
                </button>
                <button
                  class="px-3 py-1.5 text-sm font-medium text-primary hover:underline"
                  @click="handleAddCreative(campaign.id)"
                >
                  添加素材
                </button>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="campaigns.length === 0" class="flex flex-col items-center justify-center py-16">
            <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">campaign</span>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">暂无广告计划</p>
            <button
              class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
              @click="handleCreateCampaign"
            >
              <span class="material-symbols-outlined text-lg">add</span>
              <span class="text-sm font-medium">创建首个广告</span>
            </button>
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
