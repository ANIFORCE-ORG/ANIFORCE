<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import PipelineManager from '@/components/campaigns/PipelineManager.vue'
import CampaignTable from '@/components/campaigns/CampaignTable.vue'
import SelectMaterialModal from '@/components/campaigns/SelectMaterialModal.vue'
import { addMaterialToCampaign, getCampaigns, updateCampaignStatus, type Campaign, login } from '@/api'
import type { Material } from '@/api/materials'

const router = useRouter()

const activeSession = ref('sess_c001')
const chatInput = ref('')
const statusFilter = ref('all')
const searchQuery = ref('')
const projectFilter = ref('all')
const platformFilter = ref('all')
const sortBy = ref('spend')
const sortOrder = ref<'asc' | 'desc'>('desc')
const loading = ref(false)
const error = ref('')
const selectedCampaigns = ref<Set<string>>(new Set())
const showBatchActions = computed(() => selectedCampaigns.value.size > 0)
const viewMode = ref<'card' | 'table'>('card')
const showMaterialModal = ref(false)
const materialTargetCampaign = ref<Campaign | null>(null)
const addingMaterials = ref(false)

// 排序选项
const sortOptions = [
  { value: 'spend', label: '消耗' },
  { value: 'budget_usage', label: '预算进度' },
  { value: 'remaining', label: '剩余预算' },
  { value: 'roi', label: 'ROI' },
  { value: 'installs', label: '安装数' },
  { value: 'cpi', label: 'CPI' }
]

const formatMoney = (value?: number) => `$${Math.round(value || 0).toLocaleString()}`
const formatRate = (value?: number) => `${Math.round((value || 0) * 100)}%`

const budgetSummary = computed(() => {
  const byProject = new Map<string, Campaign[]>()
  campaigns.value.forEach(campaign => {
    const key = campaign.project_id || campaign.project_name
    byProject.set(key, [...(byProject.get(key) || []), campaign])
  })

  let projectTotal = 0
  let projectSpent = 0
  let allocated = 0
  let unallocated = 0
  byProject.forEach(projectCampaigns => {
    const snapshot = projectCampaigns[0]?.project_budget
    if (snapshot) {
      projectTotal += snapshot.project_total_budget || 0
      projectSpent += snapshot.project_spent || 0
      allocated += snapshot.project_allocated_budget || 0
      unallocated += snapshot.project_unallocated_budget || 0
    } else {
      allocated += projectCampaigns.reduce((sum, campaign) => sum + (campaign.budget || 0), 0)
      projectSpent += projectCampaigns.reduce((sum, campaign) => sum + (campaign.spent || 0), 0)
    }
  })

  return {
    projectCount: byProject.size,
    projectTotal,
    projectSpent,
    allocated,
    unallocated,
    running: campaigns.value.filter(c => c.status === 'running').length,
    needsAction: campaigns.value.filter(c => ['warning', 'danger', 'success'].includes(c.agent_action?.level || '')).length,
  }
})

// 导航项配置
const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
]

// 历史会话
const sessions = ref([
  { id: 'sess_c001', name: '广告投放咨询', active: true },
  { id: 'sess_c002', name: '预算优化建议', active: false },
  { id: 'sess_c003', name: '投放策略分析', active: false },
])

// 聊天消息
const messages = ref([
  {
    role: 'ai',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: '您好！我可以帮您创建广告计划、优化投放策略或分析广告数据。请问需要什么帮助？'
  }
])

// 快捷提示
const quickHints = [
  '创建新的广告计划',
  '优化现有广告',
  '分析广告数据'
]

// 广告数据（从后端 API 获取）
const campaigns = ref<Campaign[]>([])

// 初始化：自动登录并加载数据
onMounted(async () => {
  try {
    loading.value = true
    error.value = ''
    
    // 检查是否已登录，如果没有则自动登录测试账号
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.log('自动登录测试账号...')
      await login('test@animagus.com', 'test123')
    }
    
    // 加载广告投放数据
    console.log('加载广告投放数据...')
    const data = await getCampaigns()
    campaigns.value = data
    console.log('广告投放数据加载成功:', data.length, '条')
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
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

// 过滤后的广告列表
const filteredCampaigns = computed(() => {
  let result = campaigns.value

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
      c.project_name.toLowerCase().includes(query)
    )
  }

  // 排序
  result = [...result].sort((a, b) => {
    let aVal: number = 0
    let bVal: number = 0

    switch (sortBy.value) {
      case 'spend':
        aVal = a.spent || 0
        bVal = b.spent || 0
        break
      case 'budget_usage':
        aVal = a.budget_usage_rate || ((a.spent || 0) / (a.budget || 1))
        bVal = b.budget_usage_rate || ((b.spent || 0) / (b.budget || 1))
        break
      case 'remaining':
        aVal = a.budget_remaining ?? ((a.budget || 0) - (a.spent || 0))
        bVal = b.budget_remaining ?? ((b.budget || 0) - (b.spent || 0))
        break
      case 'roi':
        aVal = a.roi || 0
        bVal = b.roi || 0
        break
      case 'installs':
        aVal = a.installs || 0
        bVal = b.installs || 0
        break
      case 'cpi':
        aVal = a.cpi || 0
        bVal = b.cpi || 0
        break
    }

    return sortOrder.value === 'desc' ? bVal - aVal : aVal - bVal
  })

  return result
})

// 切换导航
const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

// 切换会话
const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => {
    s.active = s.id === session.id
  })
}

// 发送消息
const handleSendMessage = (message: string) => {
  console.log('发送消息:', message)
}

// 快捷提示点击
const handleHintClick = (hint: string) => {
  chatInput.value = hint
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

const handleOpenMaterialModal = (campaign: Campaign) => {
  materialTargetCampaign.value = campaign
  showMaterialModal.value = true
}

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
    const data = await getCampaigns()
    campaigns.value = data
    handleCloseMaterialModal()
  } catch (err: any) {
    error.value = err.message || '添加素材失败，请重试'
  } finally {
    addingMaterials.value = false
  }
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

// 批量操作相关
const toggleSelectAll = () => {
  if (selectedCampaigns.value.size === filteredCampaigns.value.length) {
    selectedCampaigns.value.clear()
  } else {
    selectedCampaigns.value = new Set(filteredCampaigns.value.map(c => c.id))
  }
}

const toggleSelectCampaign = (campaignId: string) => {
  if (selectedCampaigns.value.has(campaignId)) {
    selectedCampaigns.value.delete(campaignId)
  } else {
    selectedCampaigns.value.add(campaignId)
  }
}

const isAllSelected = computed(() => {
  return filteredCampaigns.value.length > 0 &&
         selectedCampaigns.value.size === filteredCampaigns.value.length
})

const handleBatchStart = async () => {
  if (selectedCampaigns.value.size === 0) return

  const confirmed = confirm(`确定要启动选中的 ${selectedCampaigns.value.size} 个广告吗？`)
  if (!confirmed) return

  try {
    loading.value = true
    const promises = Array.from(selectedCampaigns.value).map(id => {
      const campaign = campaigns.value.find(c => c.id === id)
      if (campaign && campaign.status !== 'running') {
        return updateCampaignStatus(id, 'running').then(() => {
          campaign.status = 'running'
        })
      }
      return Promise.resolve()
    })

    await Promise.all(promises)
    selectedCampaigns.value.clear()
    console.log('批量启动成功')
  } catch (err: any) {
    error.value = err.message || '批量启动失败'
    console.error('批量启动失败:', err)
  } finally {
    loading.value = false
  }
}

const handleBatchPause = async () => {
  if (selectedCampaigns.value.size === 0) return

  const confirmed = confirm(`确定要暂停选中的 ${selectedCampaigns.value.size} 个广告吗？`)
  if (!confirmed) return

  try {
    loading.value = true
    const promises = Array.from(selectedCampaigns.value).map(id => {
      const campaign = campaigns.value.find(c => c.id === id)
      if (campaign && campaign.status !== 'paused') {
        return updateCampaignStatus(id, 'paused').then(() => {
          campaign.status = 'paused'
        })
      }
      return Promise.resolve()
    })

    await Promise.all(promises)
    selectedCampaigns.value.clear()
    console.log('批量暂停成功')
  } catch (err: any) {
    error.value = err.message || '批量暂停失败'
    console.error('批量暂停失败:', err)
  } finally {
    loading.value = false
  }
}

const handleBatchDelete = async () => {
  if (selectedCampaigns.value.size === 0) return

  const confirmed = confirm(`确定要删除选中的 ${selectedCampaigns.value.size} 个广告吗？此操作不可恢复！`)
  if (!confirmed) return

  try {
    loading.value = true
    // TODO: 实现批量删除API
    // 暂时只从前端移除
    campaigns.value = campaigns.value.filter(c => !selectedCampaigns.value.has(c.id))
    selectedCampaigns.value.clear()
    console.log('批量删除成功')
  } catch (err: any) {
    error.value = err.message || '批量删除失败'
    console.error('批量删除失败:', err)
  } finally {
    loading.value = false
  }
}

// Pipeline 管理相关
const showPipelineManager = ref(false)
const managingCampaign = ref<Campaign | null>(null)

const handleManagePipeline = (campaign: Campaign) => {
  managingCampaign.value = campaign
  showPipelineManager.value = true
}

const handleClosePipelineManager = () => {
  showPipelineManager.value = false
  managingCampaign.value = null
}

const handleUpdatePipeline = async (data: { pipeline_step: string }) => {
  if (!managingCampaign.value) return

  try {
    // TODO: 调用API更新pipeline_step
    // await updateCampaignPipeline(managingCampaign.value.id, data.pipeline_step)

    // 乐观更新
    managingCampaign.value.pipeline_step = data.pipeline_step

    console.log('Pipeline阶段更新成功:', data.pipeline_step)
    handleClosePipelineManager()
  } catch (err: any) {
    error.value = err.message || '更新Pipeline阶段失败'
    console.error('更新Pipeline阶段失败:', err)
  }
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

const getPacingText = (status?: string) => {
  const labels: Record<string, string> = {
    fast: '消耗偏快',
    slow: '消耗偏慢',
    normal: '节奏正常'
  }
  return labels[status || 'normal'] || '节奏正常'
}

const getPacingColor = (status?: string) => {
  const colors: Record<string, string> = {
    fast: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
    slow: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
    normal: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20'
  }
  return colors[status || 'normal'] || colors.normal
}

const getAgentActionColor = (level?: string) => {
  const colors: Record<string, string> = {
    success: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300',
    warning: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-900/50 dark:bg-orange-900/20 dark:text-orange-300',
    danger: 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300',
    info: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/50 dark:bg-blue-900/20 dark:text-blue-300',
    neutral: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
  }
  return colors[level || 'neutral'] || colors.neutral
}
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧导航栏 -->
    <SidebarNav
      :nav-items="navItems"
      active-id="campaigns"
      @switch-panel="switchPanel"
    />

    <!-- 中间广告列表工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div class="flex items-center gap-3">
          <h3 class="font-bold text-slate-900 dark:text-white">广告投放</h3>
          <span class="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
            {{ budgetSummary.projectCount }} 个项目 · {{ budgetSummary.running }} 个投放中
          </span>
          <!-- 视图切换 -->
          <div class="flex items-center gap-1 p-1 rounded-md bg-slate-100 dark:bg-slate-800">
            <button
              class="px-3 py-1 rounded text-xs font-medium transition-colors"
              :class="viewMode === 'card'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
              @click="viewMode = 'card'"
            >
              <span class="material-symbols-outlined text-sm">grid_view</span>
            </button>
            <button
              class="px-3 py-1 rounded text-xs font-medium transition-colors"
              :class="viewMode === 'table'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
              @click="viewMode = 'table'"
            >
              <span class="material-symbols-outlined text-sm">table_rows</span>
            </button>
          </div>
        </div>
        <button
          class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
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
        <div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
          <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">项目总预算</div>
            <div class="text-lg font-semibold text-slate-900 dark:text-white">{{ formatMoney(budgetSummary.projectTotal) }}</div>
          </div>
          <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">计划已分配</div>
            <div class="text-lg font-semibold text-slate-900 dark:text-white">{{ formatMoney(budgetSummary.allocated) }}</div>
          </div>
          <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">实际已消耗</div>
            <div class="text-lg font-semibold text-slate-900 dark:text-white">{{ formatMoney(budgetSummary.projectSpent) }}</div>
          </div>
          <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 px-4 py-3">
            <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">需要处理</div>
            <div class="text-lg font-semibold text-orange-600 dark:text-orange-400">{{ budgetSummary.needsAction }} 项</div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-[minmax(240px,1fr)_180px_140px_140px] gap-3 mb-3">
          <div class="relative">
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
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">所有项目</option>
            <option v-for="project in uniqueProjects" :key="project" :value="project">
              {{ project }}
            </option>
          </select>
          <select
            v-model="platformFilter"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">所有平台</option>
            <option v-for="platform in uniquePlatforms" :key="platform" :value="platform">
              {{ platform }}
            </option>
          </select>
          <select
            v-model="statusFilter"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">全部状态</option>
            <option value="draft">草稿</option>
            <option value="running">投放中</option>
            <option value="review">审核中</option>
            <option value="paused">已暂停</option>
          </select>
        </div>

        <!-- 排序选项和批量操作 -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-500 dark:text-slate-400">排序:</span>
            <select
              v-model="sortBy"
              class="px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option v-for="option in sortOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <button
              class="px-2 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              @click="sortOrder = sortOrder === 'desc' ? 'asc' : 'desc'"
            >
              <span class="material-symbols-outlined text-sm text-slate-600 dark:text-slate-400">
                {{ sortOrder === 'desc' ? 'arrow_downward' : 'arrow_upward' }}
              </span>
            </button>
            <span class="text-xs text-slate-500 dark:text-slate-400 ml-2">
              共 {{ filteredCampaigns.length }} 条
            </span>
          </div>

          <!-- 批量操作按钮 -->
          <div v-if="showBatchActions" class="flex items-center gap-2">
            <span class="text-xs text-slate-500 dark:text-slate-400">
              已选 {{ selectedCampaigns.size }} 个
            </span>
            <button
              class="px-3 py-1.5 rounded-md bg-green-600 text-white text-xs font-medium hover:bg-green-700 transition-colors"
              @click="handleBatchStart"
            >
              批量启动
            </button>
            <button
              class="px-3 py-1.5 rounded-md bg-yellow-600 text-white text-xs font-medium hover:bg-yellow-700 transition-colors"
              @click="handleBatchPause"
            >
              批量暂停
            </button>
            <button
              class="px-3 py-1.5 rounded-md bg-red-600 text-white text-xs font-medium hover:bg-red-700 transition-colors"
              @click="handleBatchDelete"
            >
              批量删除
            </button>
          </div>
        </div>
      </div>

      <!-- 广告列表 -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 卡片视图 -->
        <div v-if="viewMode === 'card'">
          <!-- 全选控制 -->
          <div v-if="filteredCampaigns.length > 0" class="flex items-center gap-2 mb-3 pb-3 border-b border-slate-200 dark:border-slate-800">
            <input
              type="checkbox"
              :checked="isAllSelected"
              @change="toggleSelectAll"
              class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
            />
            <span class="text-sm text-slate-600 dark:text-slate-400">全选</span>
          </div>

          <div class="grid grid-cols-1 2xl:grid-cols-2 gap-4">
          <div
            v-for="campaign in filteredCampaigns"
            :key="campaign.id"
            class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-4 hover:border-primary/50 hover:shadow-sm transition-all"
          >
            <!-- 广告头部 -->
            <div class="flex items-start justify-between gap-3 mb-3">
              <div class="flex items-center gap-3 flex-1">
                <!-- 复选框 -->
                <input
                  type="checkbox"
                  :checked="selectedCampaigns.has(campaign.id)"
                  @change="toggleSelectCampaign(campaign.id)"
                  class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
                />
                <div class="flex-1">
                  <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-1">
                    {{ campaign.name }}
                  </h4>
                  <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
                    <span>所属项目: {{ campaign.project_name }}</span>
                    <span v-if="campaign.external_campaign_id" class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">
                      Meta ID {{ campaign.external_campaign_id }}
                    </span>
                    <span v-if="campaign.budget_type" class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700">
                      {{ campaign.budget_type === 'daily' ? '日预算' : '总预算' }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-wrap justify-end">
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

            <!-- 预算与节奏 -->
            <div class="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3 mb-3">
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                <div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">计划预算</div>
                  <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(campaign.budget) }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
                  <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(campaign.spent) }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">剩余</div>
                  <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(campaign.budget_remaining) }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mb-1">节奏</div>
                  <span class="text-xs font-semibold px-2 py-1 rounded" :class="getPacingColor(campaign.pacing_status)">
                    {{ getPacingText(campaign.pacing_status) }}
                  </span>
                </div>
              </div>
              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                  <span>预算进度 {{ formatRate(campaign.budget_usage_rate) }}</span>
                  <span>时间进度 {{ formatRate(campaign.elapsed_rate) }}</span>
                </div>
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="campaign.pacing_status === 'fast' ? 'bg-orange-500' : campaign.pacing_status === 'slow' ? 'bg-blue-500' : 'bg-emerald-500'"
                    :style="{ width: `${Math.min(Math.round((campaign.budget_usage_rate || 0) * 100), 100)}%` }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- 数据指标 -->
            <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-3">
              <div>
                <div class="text-base font-bold text-slate-900 dark:text-white">{{ campaign.installs?.toLocaleString() || 0 }}</div>
                <div class="text-[11px] text-slate-400">安装数</div>
              </div>
              <div>
                <div class="text-base font-bold text-slate-900 dark:text-white">${{ campaign.cpi?.toFixed(2) || '0.00' }}</div>
                <div class="text-[11px] text-slate-400">CPI</div>
              </div>
              <div>
                <div class="text-base font-bold" :class="campaign.roi && campaign.roi >= 2 ? 'text-emerald-600' : 'text-red-600'">
                  {{ campaign.roi ? `${campaign.roi.toFixed(2)}x` : '-' }}
                </div>
                <div class="text-[11px] text-slate-400">ROI</div>
              </div>
              <div>
                <div class="text-base font-bold text-slate-900 dark:text-white">{{ campaign.ctr ? `${campaign.ctr.toFixed(1)}%` : '-' }}</div>
                <div class="text-[11px] text-slate-400">CTR</div>
              </div>
              <div>
                <div class="text-base font-bold text-slate-900 dark:text-white">{{ campaign.material_ids?.length || 0 }}</div>
                <div class="text-[11px] text-slate-400">素材</div>
              </div>
            </div>

            <!-- 投放日期和目标CPA -->
            <div class="flex items-center gap-4 mb-3 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
              <span v-if="campaign.platform_account_id" class="flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">account_balance_wallet</span>
                账户 {{ campaign.platform_account_id }}
              </span>
              <span class="flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">calendar_today</span>
                {{ campaign.start_date }} - {{ campaign.end_date || '持续投放' }}
              </span>
              <span v-if="campaign.target_cpa" class="flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">flag</span>
                目标CPA: ${{ campaign.target_cpa.toFixed(2) }}
              </span>
            </div>

            <div
              class="mb-3 rounded-md border px-3 py-2"
              :class="getAgentActionColor(campaign.agent_action?.level)"
            >
              <div class="flex items-start gap-2">
                <span class="material-symbols-outlined text-base mt-0.5">smart_toy</span>
                <div class="min-w-0">
                  <div class="text-xs font-semibold">{{ campaign.agent_action?.label || '保持观察' }}</div>
                  <div class="text-xs opacity-90 leading-relaxed">{{ campaign.agent_action?.reason || '暂无自动化动作建议' }}</div>
                </div>
              </div>
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
                class="px-3 py-1.5 text-xs font-medium rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
                @click="handleManagePipeline(campaign)"
              >
                阶段管理
              </button>
              <button
                class="px-3 py-1.5 text-xs font-medium rounded bg-primary/10 text-primary border border-primary/20 hover:bg-primary/15 transition-colors"
                @click="handleOpenMaterialModal(campaign)"
              >
                添加素材
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

        <!-- 表格视图 -->
        <div v-else-if="viewMode === 'table'">
          <CampaignTable
            :campaigns="filteredCampaigns"
            @view="handleViewCampaign"
            @toggle-status="handleToggleStatus"
            @select="toggleSelectCampaign"
            @add-material="handleOpenMaterialModal"
          />
        </div>
      </div>
    </main>

    <!-- 右侧对话区 -->
    <ChatPanel
      :messages="messages"
      :quick-hints="quickHints"
      :chat-input="chatInput"
      :sessions="sessions"
      @send-message="handleSendMessage"
      @hint-click="handleHintClick"
      @switch-session="switchSession"
    />

    <!-- Pipeline 管理对话框 -->
    <div
      v-if="showPipelineManager"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="handleClosePipelineManager"
    >
      <div class="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-2xl p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">
            Pipeline 阶段管理 - {{ managingCampaign?.name }}
          </h3>
          <button
            class="w-8 h-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
            @click="handleClosePipelineManager"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
          </button>
        </div>

        <PipelineManager
          v-if="managingCampaign"
          :campaign="managingCampaign"
          @update="handleUpdatePipeline"
        />
      </div>
    </div>

    <SelectMaterialModal
      :show="showMaterialModal"
      :selected-ids="materialTargetCampaign?.material_ids || []"
      @close="handleCloseMaterialModal"
      @select="handleSelectMaterials"
    />
  </div>
</template>
