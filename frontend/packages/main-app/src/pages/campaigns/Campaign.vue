<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { getCampaigns, updateCampaignStatus, type Campaign } from '@/api'
import { navItems } from '@/config/navigation'

const router = useRouter()
const auth = useAuthStore()

const activeSession = ref('sess_c001')
const statusFilter = ref('all')
const searchQuery = ref('')
const projectFilter = ref('all')
const platformFilter = ref('all')
const loading = ref(false)
const error = ref('')

// 历史会话
const sessions = ref([
  { id: 'sess_c001', name: '广告投放咨询', active: true },
  { id: 'sess_c002', name: '预算优化建议', active: false },
  { id: 'sess_c003', name: '投放策略分析', active: false },
])

// 广告数据（从后端 API 获取）
const campaigns = ref<Campaign[]>([])

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
    running: '进行中',
    review: '审核中',
    paused: '已暂停'
  }
  return statusMap[status] || status
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    running: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30',
    review: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
    paused: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30'
  }
  return colors[status] || 'text-slate-600 bg-slate-50'
}
</script>

<template>
  <div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">
    <!-- 左侧导航栏 -->
    <SidebarNav
      :nav-items="navItems"
      active-id="campaigns"
      @switch-panel="switchPanel"
    />

    <!-- 中间广告列表工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <header data-workspace-page-header class="workspace-page-header border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[19px]">
        <div class="workspace-page-heading">
          <span class="workspace-page-heading-icon" aria-hidden="true"><span class="material-symbols-outlined">campaign</span></span>
          <h3 class="text-slate-900 dark:text-white">广告投放</h3>
        </div>
        <button
          class="flex items-center gap-[6px] px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          @click="handleCreateCampaign"
        >
          <span class="material-symbols-outlined text-[15px]">add</span>
          <span class="text-[11px] font-medium">新建广告</span>
        </button>
      </header>

      <!-- 错误提示 -->
      <div v-if="error" class="workspace-page-margin-x mx-[19px] mt-[12px] p-[9px] rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <div class="flex items-center gap-[6px]">
          <span class="material-symbols-outlined text-red-600 dark:text-red-400 text-[15px]">error</span>
          <span class="text-[11px] text-red-600 dark:text-red-400">{{ error }}</span>
        </div>
      </div>

      <!-- 搜索和筛选栏 -->
      <div class="workspace-page-content border-b border-slate-200 dark:border-slate-800 p-[12px]">
        <div class="flex items-center gap-[9px]">
          <div class="flex-1 relative">
            <span class="material-symbols-outlined absolute left-[9px] top-1/2 -translate-y-1/2 text-slate-400 text-[15px]">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索广告名称或项目..."
              class="w-full pl-[31px] pr-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select
            v-model="projectFilter"
            class="px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[117px]"
          >
            <option value="all">所有项目</option>
            <option v-for="project in uniqueProjects" :key="project" :value="project">
              {{ project }}
            </option>
          </select>
          <select
            v-model="platformFilter"
            class="px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[94px]"
          >
            <option value="all">所有平台</option>
            <option v-for="platform in uniquePlatforms" :key="platform" :value="platform">
              {{ platform }}
            </option>
          </select>
          <select
            v-model="statusFilter"
            class="px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[94px]"
          >
            <option value="all">全部状态</option>
            <option value="running">投放中</option>
            <option value="review">审核中</option>
            <option value="paused">已暂停</option>
          </select>
        </div>
      </div>

      <!-- 广告列表 -->
      <div class="workspace-page-content flex-1 overflow-y-auto p-[19px]">
        <div class="space-y-[9px]">
          <div
            v-for="campaign in filteredCampaigns"
            :key="campaign.id"
            class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded p-[12px] hover:shadow-md transition-all"
          >
            <!-- 广告头部 -->
            <div class="flex items-start justify-between mb-[6px]">
              <div class="flex-1">
                <h4 class="text-[11px] font-bold text-slate-900 dark:text-white mb-[4px]">
                  {{ campaign.name }}
                </h4>
                <div class="flex items-center gap-[6px] text-[10px] text-slate-500 dark:text-slate-400">
                  <span>所属项目: {{ campaign.project_name }}</span>
                </div>
              </div>
              <div class="flex items-center gap-[6px]">
                <span
                  class="text-[10px] font-medium px-[6px] py-[2px] rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                >
                  {{ campaign.platform }}
                </span>
                <span
                  class="status-chip"
                  :data-status="campaign.status"
                  :class="getStatusColor(campaign.status)"
                >
                  {{ getStatusText(campaign.status) }}
                </span>
              </div>
            </div>

            <!-- 数据指标 -->
            <div class="grid grid-cols-3 gap-[9px] mb-[9px]">
              <div class="text-center">
                <div class="text-[15px] font-bold text-slate-900 dark:text-white">
                  ${{ campaign.spent?.toLocaleString() || 0 }}
                </div>
                <div class="text-[8px] text-slate-400 mt-[2px]">消耗</div>
              </div>
              <div class="text-center">
                <div class="text-[15px] font-bold text-slate-900 dark:text-white">
                  {{ campaign.budget?.toLocaleString() || 0 }}
                </div>
                <div class="text-[8px] text-slate-400 mt-[2px]">预算</div>
              </div>
              <div class="text-center">
                <div class="text-[15px] font-bold text-slate-900 dark:text-white">
                  {{ campaign.material_ids?.length || 0 }}
                </div>
                <div class="text-[8px] text-slate-400 mt-[2px]">素材</div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center gap-[6px]">
              <button
                class="flex-1 px-[9px] py-[6px] text-[10px] font-medium rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                @click="handleViewCampaign(campaign.id)"
              >
                查看详情
              </button>
              <button
                class="px-[9px] py-[6px] text-[10px] font-semibold rounded border transition-colors flex items-center gap-[4px]"
                :class="[
                  campaign.status === 'running'
                    ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800 hover:bg-orange-100 dark:hover:bg-orange-900/30'
                    : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/30',
                  updatingCampaigns.has(campaign.id) ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                :disabled="updatingCampaigns.has(campaign.id)"
                @click="handleToggleStatus(campaign)"
              >
                <span v-if="updatingCampaigns.has(campaign.id)" class="material-symbols-outlined text-[11px] animate-spin">progress_activity</span>
                {{ campaign.status === 'running' ? '暂停' : '启动' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="filteredCampaigns.length === 0" class="flex flex-col items-center justify-center py-[50px]">
          <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">
            campaign
          </span>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">
            暂无{{ statusFilter !== 'all' ? getStatusText(statusFilter) : '' }}广告计划
          </p>
        </div>
      </div>
    </main>

  </div>
</template>
