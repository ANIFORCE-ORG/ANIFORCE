<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import SelectMaterialModal from '@/components/campaigns/SelectMaterialModal.vue'
import { addMaterialToCampaign } from '@/api/campaigns'
import type { Material } from '@/api/materials'
import { getPlatformAccounts, type PlatformAccount } from '@/api/platformAccounts'
import {
  bindProjectPlatformAccount,
  confirmProjectAgentAction,
  generateProjectAgentActions,
  getProjectAgentActions,
  getProjectCampaigns,
  getProjectDetail,
  getProjectPlatformAccounts,
  rejectProjectAgentAction,
  unbindProjectPlatformAccount,
  type AgentAction,
  type Project,
  type ProjectPlatformAccount,
} from '@/api/projects'

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
const projectAccounts = ref<ProjectPlatformAccount[]>([])
const allAccounts = ref<PlatformAccount[]>([])
const selectedAccountToBind = ref('')
const agentActions = ref<AgentAction[]>([])
const showMaterialModal = ref(false)
const materialTargetCampaign = ref<any | null>(null)
const addingMaterials = ref(false)

const formatMoney = (value?: number) => `$${Math.round(value || 0).toLocaleString()}`
const formatRate = (value?: number) => `${Math.round((value || 0) * 100)}%`

const projectBudgetSummary = computed(() => {
  const total = project.value?.total_budget || 0
  const spent = project.value?.spent || 0
  const allocated = campaigns.value.reduce((sum, campaign) => sum + (campaign.budget || 0), 0)
  return {
    total,
    spent,
    allocated,
    unallocated: Math.max(total - allocated, 0),
    remaining: Math.max(total - spent, 0),
    allocationRate: total ? allocated / total : 0,
    spendRate: total ? spent / total : 0,
  }
})

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
    projectAccounts.value = await getProjectPlatformAccounts(projectId.value)
    allAccounts.value = await getPlatformAccounts()
    agentActions.value = await getProjectAgentActions(projectId.value)

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
  materialTargetCampaign.value = campaigns.value.find(campaign => campaign.id === campaignId) || null
  showMaterialModal.value = Boolean(materialTargetCampaign.value)
}

const availableAccountsToBind = computed(() => {
  const linkedIds = new Set(projectAccounts.value.map(link => link.platform_account_id))
  return allAccounts.value.filter(account => !linkedIds.has(account.id))
})

const handleBindAccount = async () => {
  if (!selectedAccountToBind.value) return
  try {
    await bindProjectPlatformAccount(projectId.value, {
      platform_account_id: selectedAccountToBind.value,
      role: 'primary',
    })
    selectedAccountToBind.value = ''
    projectAccounts.value = await getProjectPlatformAccounts(projectId.value)
  } catch (err: any) {
    error.value = err.message || '绑定广告账户失败'
  }
}

const handleUnbindAccount = async (accountId: string) => {
  try {
    await unbindProjectPlatformAccount(projectId.value, accountId)
    projectAccounts.value = await getProjectPlatformAccounts(projectId.value)
  } catch (err: any) {
    error.value = err.message || '解绑广告账户失败'
  }
}

const handleGenerateActions = async () => {
  try {
    const result = await generateProjectAgentActions(projectId.value)
    agentActions.value = [...result.actions, ...agentActions.value]
  } catch (err: any) {
    error.value = err.message || '生成 Agent 行动失败'
  }
}

const handleConfirmAction = async (actionId: string) => {
  const updated = await confirmProjectAgentAction(projectId.value, actionId)
  agentActions.value = agentActions.value.map(action => action.id === actionId ? updated : action)
}

const handleRejectAction = async (actionId: string) => {
  const updated = await rejectProjectAgentAction(projectId.value, actionId)
  agentActions.value = agentActions.value.map(action => action.id === actionId ? updated : action)
}

const actionStatusLabel = (status: string) => ({
  suggested: '待处理',
  confirmed: '已确认',
  rejected: '已拒绝',
  executing: '执行中',
  executed: '已执行',
  failed: '失败',
  expired: '已过期',
}[status] || status)

const handleCloseMaterialModal = () => {
  showMaterialModal.value = false
  materialTargetCampaign.value = null
}

const handleSelectMaterials = async (materials: Material[]) => {
  if (!materialTargetCampaign.value) return
  const campaign = materialTargetCampaign.value
  const existingIds = new Set(campaign.material_ids || [])
  const newMaterials = materials.filter(material => !existingIds.has(material.id))
  if (newMaterials.length === 0) {
    handleCloseMaterialModal()
    return
  }

  try {
    addingMaterials.value = true
    await Promise.all(newMaterials.map(material => addMaterialToCampaign(campaign.id, material.id)))
    campaigns.value = await getProjectCampaigns(projectId.value)
    handleCloseMaterialModal()
  } catch (err: any) {
    error.value = err.message || '添加素材失败，请重试'
  } finally {
    addingMaterials.value = false
  }
}

const getPlatformColor = (platform: string) => {
  const colors: Record<string, string> = {
    'Google': 'text-blue-600',
    'TikTok': 'text-slate-900 dark:text-white',
    'Meta': 'text-blue-500'
  }
  return colors[platform] || 'text-slate-600'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    draft: '草稿',
    running: '投放中',
    review: '审核中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
}

const getPacingLabel = (status?: string) => {
  const labels: Record<string, string> = {
    fast: '消耗偏快',
    slow: '消耗偏慢',
    normal: '节奏正常'
  }
  return labels[status || 'normal'] || '节奏正常'
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
          <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-5">
            <div class="rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">总预算</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectBudgetSummary.total) }}</div>
            </div>
            <div class="rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">计划已分配</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectBudgetSummary.allocated) }}</div>
            </div>
            <div class="rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">未分配额度</div>
              <div class="text-sm font-semibold text-emerald-600">{{ formatMoney(projectBudgetSummary.unallocated) }}</div>
            </div>
            <div class="rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">实际已消耗</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectBudgetSummary.spent) }}</div>
            </div>
            <div class="rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">现金剩余额度</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectBudgetSummary.remaining) }}</div>
            </div>
          </div>
          <div class="mb-5 grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div>
              <div class="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>计划预算分配</span>
                <span>{{ formatRate(projectBudgetSummary.allocationRate) }}</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full" :style="{ width: `${Math.min(Math.round(projectBudgetSummary.allocationRate * 100), 100)}%` }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>实际消耗进度</span>
                <span>{{ formatRate(projectBudgetSummary.spendRate) }}</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div class="h-full bg-emerald-500 rounded-full" :style="{ width: `${Math.min(Math.round(projectBudgetSummary.spendRate * 100), 100)}%` }"></div>
              </div>
            </div>
          </div>
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
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(project?.total_budget) }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(project?.spent) }}</div>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">进度</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatRate(projectBudgetSummary.spendRate) }}</div>
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

        <!-- 关联广告账户 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div class="flex items-center justify-between gap-3 mb-4">
            <div>
              <h4 class="text-sm font-semibold text-slate-900 dark:text-white">关联广告账户</h4>
              <p class="text-xs text-slate-500 mt-1">创建广告计划时优先使用这里绑定的账户，避免误选其他项目账户。</p>
            </div>
            <div class="flex items-center gap-2">
              <select v-model="selectedAccountToBind" class="px-3 py-2 rounded-md border text-sm min-w-[260px]">
                <option value="">选择广告账户</option>
                <option v-for="account in availableAccountsToBind" :key="account.id" :value="account.id">
                  {{ account.account_name }} · {{ account.account_id }}
                </option>
              </select>
              <button
                class="px-3 py-2 rounded-md bg-primary text-white text-sm disabled:opacity-50"
                :disabled="!selectedAccountToBind"
                @click="handleBindAccount"
              >
                绑定
              </button>
            </div>
          </div>
          <div v-if="projectAccounts.length === 0" class="text-sm text-slate-500 py-4">
            当前项目还没有绑定广告账户。
          </div>
          <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div
              v-for="link in projectAccounts"
              :key="link.id"
              class="rounded-md border border-slate-200 p-3"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <div class="font-semibold text-slate-900">{{ link.account?.account_name || link.platform_account_id }}</div>
                  <div class="text-xs text-slate-500 mt-1">
                    {{ link.account?.platform }} · {{ link.account?.account_id }} · {{ link.role }}
                  </div>
                </div>
                <button class="text-xs text-red-600 hover:underline" @click="handleUnbindAccount(link.platform_account_id)">
                  解绑
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Agent 行动队列 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div class="flex items-center justify-between gap-3 mb-4">
            <div>
              <h4 class="text-sm font-semibold text-slate-900 dark:text-white">Agent 行动队列</h4>
              <p class="text-xs text-slate-500 mt-1">先生成可解释的建议动作，后续再接低风险自动执行。</p>
            </div>
            <button class="px-3 py-2 rounded-md border text-sm font-medium" @click="handleGenerateActions">
              生成建议
            </button>
          </div>
          <div v-if="agentActions.length === 0" class="text-sm text-slate-500 py-4">
            暂无 Agent 行动建议。
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="action in agentActions"
              :key="action.id"
              class="rounded-md border border-slate-200 p-3"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-xs rounded bg-slate-100 px-2 py-0.5 font-semibold">{{ action.risk_level }}</span>
                    <span class="text-xs rounded bg-blue-50 text-blue-700 px-2 py-0.5">{{ actionStatusLabel(action.status) }}</span>
                  </div>
                  <div class="mt-2 font-semibold text-slate-900">{{ action.title }}</div>
                  <div class="mt-1 text-sm text-slate-500">{{ action.summary }}</div>
                </div>
                <div v-if="action.status === 'suggested'" class="flex items-center gap-2">
                  <button class="px-3 py-1.5 rounded-md bg-primary text-white text-xs" @click="handleConfirmAction(action.id)">确认</button>
                  <button class="px-3 py-1.5 rounded-md border text-xs" @click="handleRejectAction(action.id)">拒绝</button>
                </div>
              </div>
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
              <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-3">
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ formatMoney(campaign.budget) }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">计划预算</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ formatMoney(campaign.spent) }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">消耗</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ formatMoney(campaign.budget_remaining) }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">剩余</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900 dark:text-white">{{ formatRate(campaign.budget_usage_rate) }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">预算进度</div>
                </div>
                <div>
                  <div class="text-lg font-bold text-emerald-600">{{ getStatusLabel(campaign.status) }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">状态</div>
                </div>
              </div>

              <div class="mb-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-3 py-2">
                <div class="flex items-center justify-between gap-3 text-xs">
                  <span class="font-semibold text-slate-700 dark:text-slate-300">{{ getPacingLabel(campaign.pacing_status) }}</span>
                  <span class="text-slate-500 dark:text-slate-400">{{ campaign.agent_action?.label || '保持观察' }}</span>
                </div>
                <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {{ campaign.agent_action?.reason || '暂无自动化动作建议' }}
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

    <SelectMaterialModal
      :show="showMaterialModal"
      :selected-ids="materialTargetCampaign?.material_ids || []"
      @close="handleCloseMaterialModal"
      @select="handleSelectMaterials"
    />
  </div>
</template>
