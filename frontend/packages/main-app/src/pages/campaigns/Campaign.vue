<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { getCampaigns, updateCampaignStatus, type Campaign } from '@/api'
import { navItems } from '@/config/navigation'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'

const router = useRouter()
const auth = useAuthStore()
const workspaceSessions = useWorkspaceSessions()

const statusFilter = ref('all')
const searchQuery = ref('')
const projectFilter = ref('all')
const platformFilter = ref('all')
const loading = ref(false)
const error = ref('')
const usingDemoData = ref(false)

type CampaignView = Campaign & {
  platform_account_id?: string
  platform_account_name?: string
  external_campaign_id?: string
  ad_group_count?: number
  objective?: string
  bid_strategy?: string
  cpa?: number
  ctr?: number
  roas?: number
  conversions?: number
  budget_pacing?: 'normal' | 'fast' | 'slow'
  agent_alert?: string
}

// 快捷提示
const quickHints = [
  '创建新的广告计划',
  '优化现有广告',
  '分析广告数据'
]

// 广告数据（从后端 API 获取）
const campaigns = ref<Campaign[]>([])

const demoCampaigns: CampaignView[] = [
  {
    id: 'demo-campaign-meta-001',
    project_id: 'demo-project-candy',
    project_name: 'Candy Blast 全球推广',
    name: 'Meta_US_Broad_Install_May_W4',
    platform: 'Meta',
    platform_account_id: 'act_1029384756',
    platform_account_name: 'Candy Blast Meta UA',
    external_campaign_id: '23851234567890123',
    budget: 18000,
    spent: 12480,
    status: 'running',
    material_ids: ['mat_ugc_001', 'mat_ugc_002', 'mat_static_003'],
    start_date: '2026-05-20',
    end_date: '2026-06-05',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ad_group_count: 6,
    objective: 'App installs',
    bid_strategy: 'Lowest cost',
    cpa: 5.72,
    ctr: 0.041,
    roas: 2.31,
    conversions: 2180,
    budget_pacing: 'normal',
    agent_alert: '两条 UGC 素材 CTR 连续下降，建议替换前三秒 Hook。',
  },
  {
    id: 'demo-campaign-tiktok-001',
    project_id: 'demo-project-candy',
    project_name: 'Candy Blast 全球推广',
    name: 'TikTok_US_Lookalike_ROAS_Test',
    platform: 'TikTok',
    platform_account_id: 'tt_87452019',
    platform_account_name: 'Candy Blast TikTok US',
    external_campaign_id: 'ttc_7219093345',
    budget: 12000,
    spent: 7000,
    status: 'running',
    material_ids: ['mat_short_001', 'mat_short_004'],
    start_date: '2026-05-18',
    end_date: '2026-06-02',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ad_group_count: 4,
    objective: 'Conversions',
    bid_strategy: 'Cost cap',
    cpa: 5.71,
    ctr: 0.052,
    roas: 2.86,
    conversions: 1226,
    budget_pacing: 'slow',
    agent_alert: 'ROAS 高于账户均值，建议提高日预算 10%-15%。',
  },
  {
    id: 'demo-campaign-google-001',
    project_id: 'demo-project-drama',
    project_name: 'DramaBox 北美订阅转化',
    name: 'Google_US_Search_Subscription_Core',
    platform: 'Google',
    platform_account_id: 'gads_559210',
    platform_account_name: 'DramaBox Google Ads',
    external_campaign_id: 'gads_883120991',
    budget: 22000,
    spent: 8620,
    status: 'review',
    material_ids: ['mat_drama_001'],
    start_date: '2026-05-22',
    end_date: '2026-06-12',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ad_group_count: 8,
    objective: 'Subscriptions',
    bid_strategy: 'Target CPA',
    cpa: 8.42,
    ctr: 0.028,
    roas: 2.12,
    conversions: 1024,
    budget_pacing: 'fast',
    agent_alert: '消耗偏快且 CPA 上升，建议收紧关键词和低效地区。',
  },
]

// 初始化：自动登录并加载数据
onMounted(async () => {
  try {
    loading.value = true
    error.value = ''
    
    // 检查是否已登录，如果没有则自动登录测试账号
    if (!auth.isLoggedIn) {
      console.log('自动登录测试账号...')
      await auth.login({ email: 'test@animagus.com', password: 'test123' })
    }
    
    // 加载广告投放数据
    console.log('加载广告投放数据...')
    const data = await getCampaigns()
    if (data.length === 0) {
      campaigns.value = demoCampaigns
      usingDemoData.value = true
    } else {
      campaigns.value = data
      usingDemoData.value = false
    }
    console.log('广告投放数据加载成功:', data.length, '条')
  } catch (err: any) {
    error.value = ''
    campaigns.value = demoCampaigns
    usingDemoData.value = true
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
})


// 获取唯一的项目列表
const uniqueProjects = computed(() => {
  const projects = new Set(campaigns.value.map(c => c.project_name))
  return Array.from(projects)
})

// 获取唯一的平台列表
const uniquePlatforms = computed(() => {
  const platforms = new Set(campaigns.value.map(c => c.platform))
  return Array.from(platforms)
})

const campaignSummary = computed(() => {
  const list = campaigns.value as CampaignView[]
  return {
    total: list.length,
    running: list.filter(item => item.status === 'running').length,
    adGroups: list.reduce((sum, item) => sum + (item.ad_group_count || 0), 0),
    alerts: list.filter(item => item.agent_alert).length,
  }
})

// 过滤后的广告列表
const filteredCampaigns = computed(() => {
  let result = campaigns.value as CampaignView[]

  // 按状态筛选
  if (statusFilter.value !== 'all') {
    result = result.filter(c => c.status === statusFilter.value)
  }

  // 按项目筛选
  if (projectFilter.value !== 'all') {
    result = result.filter(c => c.project_name === projectFilter.value)
  }

  // 按平台筛选
  if (platformFilter.value !== 'all') {
    result = result.filter(c => c.platform === platformFilter.value)
  }

  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(c => 
      c.name.toLowerCase().includes(query) ||
      c.project_name.toLowerCase().includes(query) ||
      c.platform.toLowerCase().includes(query) ||
      (c.platform_account_name || '').toLowerCase().includes(query) ||
      (c.external_campaign_id || '').toLowerCase().includes(query)
    )
  }

  return result
})

// 切换导航
const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

// 创建广告
const handleCreateCampaign = () => {
  // 跳转到创建广告页面，不传projectId参数，让用户在页面中选择项目
  router.push('/campaigns/create')
}

// 查看广告详情
const handleViewCampaign = (campaignId: string) => {
  router.push(`/campaigns/${campaignId}`)
}

// 切换广告状态（前后端同步）
const updatingCampaigns = ref<Set<string>>(new Set())

const handleToggleStatus = async (campaign: Campaign) => {
  // 防止重复点击
  if (updatingCampaigns.value.has(campaign.id)) {
    return
  }

  const newStatus = campaign.status === 'running' ? 'paused' : 'running'
  const oldStatus = campaign.status
  
  try {
    // 添加加载状态
    updatingCampaigns.value.add(campaign.id)
    
    // 乐观更新：先更新前端显示
    campaign.status = newStatus
    
    // 调用后端API更新数据库
    await updateCampaignStatus(campaign.id, newStatus)
    
    console.log(`✅ 广告 ${campaign.name} 已${newStatus === 'running' ? '启动' : '暂停'}`)
  } catch (err: any) {
    // 如果失败，回滚前端状态
    campaign.status = oldStatus
    console.error('更新广告状态失败:', err)
    error.value = err.message || '更新状态失败，请重试'
    
    // 3秒后清除错误提示
    setTimeout(() => {
      if (error.value === (err.message || '更新状态失败，请重试')) {
        error.value = ''
      }
    }, 3000)
  } finally {
    // 移除加载状态
    updatingCampaigns.value.delete(campaign.id)
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    draft: '草稿',
    running: '进行中',
    review: '审核中',
    paused: '已暂停',
    completed: '已完成'
  }
  return statusMap[status] || status
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    draft: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30',
    running: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30',
    review: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
    paused: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30',
    completed: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30'
  }
  return colors[status] || 'text-slate-600 bg-slate-50'
}

const getPacingText = (pacing?: string) => {
  const labels: Record<string, string> = {
    normal: '节奏正常',
    fast: '消耗偏快',
    slow: '消耗偏慢',
  }
  return labels[pacing || ''] || '待观察'
}

const getPacingColor = (pacing?: string) => {
  const colors: Record<string, string> = {
    normal: 'text-emerald-600',
    fast: 'text-amber-600',
    slow: 'text-blue-600',
  }
  return colors[pacing || ''] || 'text-slate-500'
}
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧导航栏 -->
    <SidebarNav
      :nav-items="navItems"
      active-panel="campaigns"
      :sessions="workspaceSessions.sessions.value"
      @switch-panel="switchPanel"
      @switch-session="workspaceSessions.switchSession"
    />

    <!-- 中间广告列表工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white">广告投放</h3>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Campaign / Ad Group / Material / Report Metrics</p>
        </div>
        <button
          class="flex items-center gap-2 whitespace-nowrap px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          @click="handleCreateCampaign"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          <span class="text-sm font-medium">新建广告</span>
        </button>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="mx-6 mt-4 p-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-red-600 dark:text-red-400 text-lg">error</span>
          <span class="text-sm text-red-600 dark:text-red-400">{{ error }}</span>
        </div>
      </div>

      <!-- 搜索和筛选栏 -->
      <div class="border-b border-slate-200 dark:border-slate-800 p-4">
        <div class="flex items-center gap-3">
          <div class="flex-1 relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索广告名称或项目..."
              class="w-full pl-10 pr-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select
            v-model="projectFilter"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[150px]"
          >
            <option value="all">所有项目</option>
            <option v-for="project in uniqueProjects" :key="project" :value="project">
              {{ project }}
            </option>
          </select>
          <select
            v-model="platformFilter"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[120px]"
          >
            <option value="all">所有平台</option>
            <option v-for="platform in uniquePlatforms" :key="platform" :value="platform">
              {{ platform }}
            </option>
          </select>
          <select
            v-model="statusFilter"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[120px]"
          >
            <option value="all">全部状态</option>
            <option value="running">投放中</option>
            <option value="review">审核中</option>
            <option value="paused">已暂停</option>
          </select>
        </div>
      </div>

      <!-- 广告列表 -->
      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="usingDemoData" class="mb-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-800">
          当前广告计划接口为空或不可用，已展示 Demo 投放数据，字段按广告平台对接后的 Campaign / Ad Group / Material / Metrics 结构组织。
        </div>

        <div class="mb-5 grid gap-3 md:grid-cols-4">
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">广告计划</p>
            <p class="mt-2 text-xl font-bold text-slate-950 dark:text-white">{{ campaignSummary.total }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">投放中</p>
            <p class="mt-2 text-xl font-bold text-emerald-600">{{ campaignSummary.running }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">Ad Group</p>
            <p class="mt-2 text-xl font-bold text-slate-950 dark:text-white">{{ campaignSummary.adGroups }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">Agent 提醒</p>
            <p class="mt-2 text-xl font-bold text-amber-600">{{ campaignSummary.alerts }}</p>
          </div>
        </div>

        <div class="space-y-3">
          <div
            v-for="campaign in filteredCampaigns"
            :key="campaign.id"
            class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded p-4 hover:shadow-md transition-all"
          >
            <!-- 广告头部 -->
            <div class="flex items-start justify-between gap-4 mb-3">
              <div class="min-w-0 flex-1">
                <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-1">
                  {{ campaign.name }}
                </h4>
                <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span>所属项目: {{ campaign.project_name }}</span>
                  <span>账户: {{ campaign.platform_account_name || campaign.platform_account_id || '未绑定' }}</span>
                  <span v-if="campaign.external_campaign_id">平台ID: {{ campaign.external_campaign_id }}</span>
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <span
                  class="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                >
                  {{ campaign.platform }}
                </span>
                <span
                  class="text-xs font-semibold px-2 py-0.5 rounded"
                  :class="getStatusColor(campaign.status)"
                >
                  {{ getStatusText(campaign.status) }}
                </span>
              </div>
            </div>

            <!-- 数据指标 -->
            <div class="grid grid-cols-2 gap-3 mb-3 lg:grid-cols-6">
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-slate-900 dark:text-white">
                  ${{ campaign.spent?.toLocaleString() || 0 }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">消耗</div>
              </div>
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-slate-900 dark:text-white">
                  ${{ campaign.budget?.toLocaleString() || 0 }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">预算</div>
              </div>
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-slate-900 dark:text-white">
                  {{ campaign.ad_group_count || 0 }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">Ad Group</div>
              </div>
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-slate-900 dark:text-white">
                  {{ campaign.material_ids?.length || 0 }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">素材</div>
              </div>
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-slate-900 dark:text-white">
                  {{ campaign.cpa ? `$${campaign.cpa.toFixed(2)}` : '-' }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">CPA</div>
              </div>
              <div class="rounded-md bg-slate-50 p-3 dark:bg-slate-900">
                <div class="text-base font-bold text-emerald-600">
                  {{ campaign.roas ? `${campaign.roas.toFixed(2)}x` : '-' }}
                </div>
                <div class="text-[10px] text-slate-400 mt-0.5">ROAS</div>
              </div>
            </div>

            <div class="mb-3 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
              <div class="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-900">
                <p class="font-semibold text-slate-500">投放配置</p>
                <p class="mt-1 text-slate-700 dark:text-slate-300">
                  {{ campaign.objective || 'Objective pending' }} · {{ campaign.bid_strategy || 'Bid strategy pending' }}
                </p>
              </div>
              <div class="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-900">
                <p class="font-semibold text-slate-500">预算节奏</p>
                <p class="mt-1 font-bold" :class="getPacingColor(campaign.budget_pacing)">
                  {{ getPacingText(campaign.budget_pacing) }}
                </p>
              </div>
              <div class="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-900">
                <p class="font-semibold text-slate-500">转化</p>
                <p class="mt-1 font-bold text-slate-900 dark:text-white">{{ campaign.conversions?.toLocaleString() || 0 }}</p>
              </div>
            </div>

            <div v-if="campaign.agent_alert" class="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
              {{ campaign.agent_alert }}
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center gap-2">
              <button
                class="flex-1 px-3 py-1.5 text-xs font-medium rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                @click="handleViewCampaign(campaign.id)"
              >
                查看详情
              </button>
              <button
                class="px-3 py-1.5 text-xs font-semibold rounded border transition-colors flex items-center gap-1"
                :class="[
                  campaign.status === 'running'
                    ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800 hover:bg-orange-100 dark:hover:bg-orange-900/30'
                    : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/30',
                  updatingCampaigns.has(campaign.id) ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                :disabled="updatingCampaigns.has(campaign.id)"
                @click="handleToggleStatus(campaign)"
              >
                <span v-if="updatingCampaigns.has(campaign.id)" class="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                {{ campaign.status === 'running' ? '暂停' : '启动' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="filteredCampaigns.length === 0" class="flex flex-col items-center justify-center py-16">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">
            campaign
          </span>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            暂无{{ statusFilter !== 'all' ? getStatusText(statusFilter) : '' }}广告计划
          </p>
        </div>
      </div>
    </main>

    <!-- 右侧对话区 -->
    <ChatPanel
      :session-id="workspaceSessions.activeSessionId.value"
      :quick-hints="quickHints"
    />
  </div>
</template>
