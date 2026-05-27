<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue'
import { getProjects, createProject, type Project } from '@/api/projects'
import { navItems } from '@/config/navigation'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'

const router = useRouter()
const workspaceSessions = useWorkspaceSessions()

const showCreateModal = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const projects = ref<Project[]>([])
const searchQuery = ref('')
const filterStatus = ref('all')
const createModalRef = ref<any>(null)
const usingDemoData = ref(false)

type ProjectView = Project & {
  platform_accounts?: Array<{
    platform: string
    account_name: string
    account_id: string
    auth_status: string
  }>
  campaign_count?: number
  ad_group_count?: number
  material_count?: number
  alert_count?: number
  roas?: number
}

const demoProjects: ProjectView[] = [
  {
    id: 'demo-project-candy',
    name: 'Candy Blast 全球推广',
    description: '休闲游戏全球买量项目，优先跑通 Meta 与 TikTok 的素材测试和预算扩量。',
    game_type: 'game',
    target_market: 'US / CA / AU',
    tags: ['Meta', 'TikTok', '休闲游戏', 'Demo'],
    total_budget: 68000,
    spent: 28460,
    status: 'active',
    manager: 'Growth Team',
    start_date: '2026-05-01',
    end_date: '2026-06-30',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    platform_accounts: [
      { platform: 'Meta', account_name: 'Candy Blast Meta UA', account_id: 'act_1029384756', auth_status: 'active' },
      { platform: 'TikTok', account_name: 'Candy Blast TikTok US', account_id: 'tt_87452019', auth_status: 'active' },
    ],
    campaign_count: 5,
    ad_group_count: 18,
    material_count: 42,
    alert_count: 2,
    roas: 2.43,
  },
  {
    id: 'demo-project-drama',
    name: 'DramaBox 北美订阅转化',
    description: '短剧订阅产品转化项目，按题材和受众拆分 Campaign，素材复盘用于下一轮投放。',
    game_type: 'app',
    target_market: 'US',
    tags: ['Google', 'Meta', '订阅转化', 'Demo'],
    total_budget: 92000,
    spent: 51720,
    status: 'active',
    manager: 'Performance Team',
    start_date: '2026-04-20',
    end_date: '2026-06-15',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    platform_accounts: [
      { platform: 'Google', account_name: 'DramaBox Google Ads', account_id: 'gads_559210', auth_status: 'active' },
      { platform: 'Meta', account_name: 'DramaBox Meta Subs', account_id: 'act_9081726354', auth_status: 'active' },
    ],
    campaign_count: 7,
    ad_group_count: 26,
    material_count: 63,
    alert_count: 1,
    roas: 2.76,
  },
  {
    id: 'demo-project-ecom',
    name: 'DTC 新品黑五预热',
    description: '电商新品投放准备项目，当前处于账户绑定和素材准备阶段。',
    game_type: 'ecommerce',
    target_market: 'US / UK',
    tags: ['Meta', '素材准备', 'Demo'],
    total_budget: 45000,
    spent: 8200,
    status: 'paused',
    manager: 'Brand Team',
    start_date: '2026-05-18',
    end_date: '2026-07-01',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    platform_accounts: [
      { platform: 'Meta', account_name: 'DTC Meta Prospecting', account_id: 'act_6677889900', auth_status: 'active' },
    ],
    campaign_count: 2,
    ad_group_count: 6,
    material_count: 15,
    alert_count: 0,
    roas: 1.68,
  },
]

const quickHints = [
  '项目和计划数据分析',
  '创建新项目',
  '创建广告计划',
  '优化建议',
  '预算调整',
  '素材管理'
]

const statusFilters = [
  { value: 'all', label: '全部项目' },
  { value: 'active', label: '进行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
]

// 加载项目数据
onMounted(async () => {
  loading.value = true
  error.value = null
  
  try {
    console.log('开始加载项目数据...')
    const data = await getProjects({ limit: 50 })
    if (data.length === 0) {
      projects.value = demoProjects
      usingDemoData.value = true
    } else {
      projects.value = data
      usingDemoData.value = false
    }
    console.log('项目数据加载成功:', data.length, '条')
  } catch (err: any) {
    error.value = ''
    projects.value = demoProjects
    usingDemoData.value = true
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
})

// 筛选后的项目列表
const filteredProjects = computed(() => {
  let result = projects.value as ProjectView[]

  // 按状态筛选
  if (filterStatus.value !== 'all') {
    result = result.filter(p => p.status === filterStatus.value)
  }

  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => 
      p.name.toLowerCase().includes(query) ||
      (p.description || '').toLowerCase().includes(query) ||
      (p.tags || []).some(tag => tag.toLowerCase().includes(query)) ||
      (p.platform_accounts || []).some(account =>
        account.platform.toLowerCase().includes(query) ||
        account.account_name.toLowerCase().includes(query) ||
        account.account_id.toLowerCase().includes(query)
      )
    )
  }

  return result
})

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const handleSearch = () => {
  // 筛选逻辑在 computed 中处理
}

const handleCreateProject = () => {
  showCreateModal.value = true
}

const handleCreateCampaign = (project: ProjectView) => {
  const account = project.platform_accounts?.[0]
  router.push({
    path: '/campaigns/create',
    query: {
      projectId: project.id,
      platform: account?.platform || 'Meta',
      platformAccountId: account?.account_id || '',
    },
  })
}

const handleCloseModal = () => {
  showCreateModal.value = false
}

const handleSubmitProject = async (data: any) => {
  try {
    console.log('创建项目:', data)
    const newProject = await createProject(data)
    console.log('项目创建成功:', newProject)
    
    // 添加到项目列表
    projects.value.unshift(newProject)
    
    // 关闭弹窗并重置表单
    showCreateModal.value = false
    createModalRef.value?.resetForm()
  } catch (err: any) {
    console.error('创建项目失败:', err)
    usingDemoData.value = true
    const fallbackProject: ProjectView = {
      id: `demo-project-${Date.now()}`,
      name: data.name,
      description: data.description || '本地 Demo 项目，后端 Project 接口就绪后将替换为真实数据。',
      game_type: data.game_type,
      target_market: data.target_market,
      tags: data.tags?.length ? data.tags : ['Demo'],
      total_budget: data.total_budget,
      spent: 0,
      status: 'active',
      manager: data.manager || 'Demo',
      start_date: data.start_date || '',
      end_date: data.end_date || '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      platform_accounts: [],
      campaign_count: 0,
      ad_group_count: 0,
      material_count: 0,
      alert_count: 0,
      roas: 0,
    }
    projects.value.unshift(fallbackProject)
    showCreateModal.value = false
    createModalRef.value?.resetForm()
    router.push({
      path: '/campaigns/create',
      query: { projectId: fallbackProject.id }
    })
  } finally {
    createModalRef.value?.setSubmitting(false)
  }
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
}

const budgetRate = (project: ProjectView) => {
  if (!project.total_budget) return 0
  return Math.min(100, Math.round((project.spent / project.total_budget) * 100))
}

const projectTotals = computed(() => {
  const list = projects.value as ProjectView[]
  return {
    projects: list.length,
    accounts: list.reduce((sum, project) => sum + (project.platform_accounts?.length || 0), 0),
    campaigns: list.reduce((sum, project) => sum + (project.campaign_count || 0), 0),
    alerts: list.reduce((sum, project) => sum + (project.alert_count || 0), 0),
  }
})
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="workspaceSessions.sessions.value"
      @switch-panel="switchPanel"
      @switch-session="workspaceSessions.switchSession"
    />

    <!-- 中间项目展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white">项目与广告计划</h3>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">先创建项目，再在项目下管理广告账户、Campaign 和计划</p>
        </div>
        <button
          class="flex items-center gap-2 whitespace-nowrap px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          @click="handleCreateProject"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          <span class="text-sm font-medium">创建项目</span>
        </button>
      </div>

      <!-- Search & Filter Bar -->
      <div class="border-b border-slate-200 dark:border-slate-800 p-4">
        <div class="flex items-center gap-3">
          <div class="flex-1 relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索项目名称或标签..."
              class="w-full pl-10 pr-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
              @input="handleSearch"
            />
          </div>
          <select
            v-model="filterStatus"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
            @change="handleSearch"
          >
            <option v-for="filter in statusFilters" :key="filter.value" :value="filter.value">
              {{ filter.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Projects List -->
      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="usingDemoData" class="mb-4 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-800">
          当前项目接口为空或不可用，已展示 Demo 项目数据；创建项目失败时会生成本地 Demo 项目并继续进入新建广告计划，方便完整测试主流程。
        </div>

        <div class="mb-5 grid gap-3 md:grid-cols-4">
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">项目数</p>
            <p class="mt-2 text-xl font-bold text-slate-950 dark:text-white">{{ projectTotals.projects }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">绑定广告账户</p>
            <p class="mt-2 text-xl font-bold text-slate-950 dark:text-white">{{ projectTotals.accounts }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">广告计划</p>
            <p class="mt-2 text-xl font-bold text-slate-950 dark:text-white">{{ projectTotals.campaigns }}</p>
          </div>
          <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs text-slate-500">待处理提醒</p>
            <p class="mt-2 text-xl font-bold text-amber-600">{{ projectTotals.alerts }}</p>
          </div>
        </div>

        <div class="grid gap-4">
          <div
            v-for="project in filteredProjects"
            :key="project.id"
            class="p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:border-primary/50 transition-all cursor-pointer"
          >
            <!-- Project Header -->
            <div class="flex items-start justify-between gap-4 mb-4">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <h4 class="text-base font-semibold text-slate-900 dark:text-white">{{ project.name }}</h4>
                  <span
                    class="text-xs font-semibold px-2 py-0.5 rounded-full"
                    :class="getStatusColor(project.status)"
                  >
                    {{ getStatusLabel(project.status) }}
                  </span>
                </div>
                <div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">person</span>
                    {{ project.manager }}
                  </span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">calendar_today</span>
                    {{ project.start_date }} - {{ project.end_date }}
                  </span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">public</span>
                    {{ project.target_market }}
                  </span>
                </div>
                <p class="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-400">
                  {{ project.description || '暂无项目描述' }}
                </p>
              </div>
              <button
                class="whitespace-nowrap rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90"
                @click.stop="handleCreateCampaign(project)"
              >
                新建广告
              </button>
            </div>

            <!-- Project Stats -->
            <div class="grid grid-cols-2 gap-3 mb-4 lg:grid-cols-6">
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">预算</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.total_budget.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.spent.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">进度</div>
                <div class="text-sm font-semibold text-emerald-600">{{ budgetRate(project) }}%</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Campaign</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.campaign_count || 0 }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Ad Group</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.ad_group_count || 0 }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">素材</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.material_count || 0 }}</div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="mb-3">
              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>预算使用进度</span>
                <span>{{ budgetRate(project) }}%</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-primary rounded-full transition-all"
                  :style="{ width: `${budgetRate(project)}%` }"
                ></div>
              </div>
            </div>

            <div class="mb-3 rounded-md border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
              <div class="mb-2 flex items-center justify-between">
                <p class="text-xs font-semibold text-slate-500">绑定广告账户</p>
                <p class="text-xs font-bold text-slate-700 dark:text-slate-300">ROAS {{ (project.roas || 0).toFixed(2) }}x</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="account in project.platform_accounts || []"
                  :key="account.account_id"
                  class="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
                  {{ account.platform }} · {{ account.account_name }}
                </span>
                <span v-if="!project.platform_accounts?.length" class="text-xs text-slate-500">未绑定广告账户</span>
              </div>
            </div>

            <!-- Tags -->
            <div class="flex items-center gap-2 flex-wrap mb-3">
              <span
                v-for="tag in project.tags || []"
                :key="tag"
                class="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
              >
                {{ tag }}
              </span>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 pt-3 border-t border-slate-200 dark:border-slate-700">
              <button
                class="flex-1 px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                @click="router.push(`/projects/${project.id}`)"
              >
                查看详情
              </button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredProjects.length === 0" class="flex flex-col items-center justify-center py-16">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">folder_off</span>
          <p class="text-sm text-slate-500 dark:text-slate-400">未找到匹配的项目</p>
        </div>
      </div>
    </main>

    <!-- 右侧对话区 -->
    <ChatPanel
      :session-id="workspaceSessions.activeSessionId.value"
      :quick-hints="quickHints"
    />

    <!-- 创建项目弹窗 -->
    <CreateProjectModal
      ref="createModalRef"
      :show="showCreateModal"
      @close="handleCloseModal"
      @submit="handleSubmitProject"
    />
  </div>
</template>
