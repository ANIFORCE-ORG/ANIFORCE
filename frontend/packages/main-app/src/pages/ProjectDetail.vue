<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { getProjectDetail, getProjectCampaigns, type Project } from '@/api/projects'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const projectId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const chatInput = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const project = ref<Project | null>(null)
const campaigns = ref<any[]>([])

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
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n我可以帮您：\n• 分析广告计划表现\n• 优化投放策略\n• 素材建议\n• 预算调整建议\n\n请告诉我您需要什么帮助？`
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

onMounted(async () => {
  await loadProjectData()
})

const loadProjectData = async () => {
  loading.value = true
  error.value = null
  
  try {
    console.log('加载项目详情:', projectId.value)
    
    // 加载项目详情
    const projectData = await getProjectDetail(projectId.value)
    project.value = projectData
    console.log('项目详情加载成功:', projectData)
    
    // 加载关联的广告投放
    const campaignsData = await getProjectCampaigns(projectId.value)
    campaigns.value = campaignsData
    console.log('关联广告投放加载成功:', campaignsData.length, '条')
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
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
  router.push({
    path: '/campaigns/create',
    query: { projectId: projectId.value }
  })
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
          <h2 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">{{ project?.name }}</h2>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 项目详情信息 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h4 class="text-sm font-semibold text-slate-900 dark:text-white mb-4">项目描述</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">{{ project?.description || '暂无描述' }}</p>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">产品类型</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.game_type }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">目标市场</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.target_market }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">总预算</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project?.total_budget.toLocaleString() }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project?.spent.toLocaleString() }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">进度</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project ? Math.round((project.spent / project.total_budget) * 100) : 0 }}%</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">目标ROI</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.target_roi ? `${project.target_roi}x` : '-' }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">当前ROI</div>
              <div class="text-sm font-semibold" :class="project?.current_roi && project?.target_roi && project.current_roi >= project.target_roi ? 'text-emerald-600' : 'text-red-600'">
                {{ project?.current_roi ? `${project.current_roi}x` : '-' }}
              </div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">安装数</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.installs?.toLocaleString() || '-' }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">广告计划数</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.campaign_count || 0 }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">标签</div>
              <div class="flex gap-1 flex-wrap">
                <span
                  v-for="tag in project?.tags || []"
                  :key="tag"
                  class="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">开始日期</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.start_date }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">结束日期</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.end_date }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">负责人</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project?.manager }}</div>
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
                  <div class="text-lg font-bold text-slate-900 dark:text-white">${{ campaign.spent?.toLocaleString() || 0 }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">消耗</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">${{ campaign.budget?.toLocaleString() || 0 }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">预算</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-emerald-600">{{ campaign.status }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">状态</div>
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
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">{{ project?.description || '暂无描述' }}</p>
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
