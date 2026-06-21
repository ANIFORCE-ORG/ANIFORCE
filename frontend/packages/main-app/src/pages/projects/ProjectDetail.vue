<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { getProjectDetail, getProjectCampaigns, type Project } from '@/api/projects'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()
const projectId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
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

/*
const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
]
  */

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
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
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
      <div class="h-[50px] border-b border-slate-200 dark:border-slate-800 flex items-center px-[19px]">
        <div class="flex items-center gap-[12px]">
          <button
            class="flex items-center gap-[6px] text-slate-600 dark:text-slate-400 hover:text-primary transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-[15px]">arrow_back</span>
            <span class="text-[11px] font-medium">返回项目列表</span>
          </button>
          <div class="h-[19px] w-px bg-slate-200 dark:bg-slate-800"></div>
          <h2 class="text-[17px] font-bold text-slate-900 dark:text-white mb-[6px]">{{ project?.name }}</h2>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <!-- 项目详情信息 -->
        <div class="mb-[19px] p-[16px] rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white mb-[12px]">项目描述</h4>
          <div class="grid grid-cols-2 gap-[12px]">
            <div class="col-span-2">
              <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-[12px]">{{ project?.description || '暂无描述' }}</p>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">产品类型</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project?.game_type }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">目标市场</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project?.target_market }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">总预算</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">${{ project?.total_budget.toLocaleString() }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">已消耗</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">${{ project?.spent.toLocaleString() }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">进度</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project ? Math.round((project.spent / project.total_budget) * 100) : 0 }}%</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">标签</div>
              <div class="flex gap-[4px] flex-wrap">
                <span
                  v-for="tag in project?.tags || []"
                  :key="tag"
                  class="text-[10px] px-[6px] py-[4px] rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">开始日期</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project?.start_date }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">结束日期</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project?.end_date }}</div>
            </div>
            <div class="flex justify-between py-[6px] border-b border-slate-200 dark:border-slate-700">
              <div class="text-[10px] text-slate-500 dark:text-slate-400 mb-[4px]">负责人</div>
              <div class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project?.manager }}</div>
            </div>
          </div>
        </div>

        <!-- 广告计划列表 -->
        <div>
          <div class="flex items-center justify-between mb-[12px]">
            <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">广告计划 ({{ campaigns.length }})</h4>
            <button
              class="flex items-center gap-[6px] px-[9px] py-[6px] rounded-md text-[11px] font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleCreateCampaign"
            >
              <span class="material-symbols-outlined text-[15px]">add</span>
              新建广告
            </button>
          </div>
          
          <div class="space-y-[9px]">
            <div
              v-for="campaign in campaigns"
              :key="campaign.id"
              class="p-[12px] rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:border-primary/50 transition-all"
            >
              <!-- Campaign Header -->
              <div class="flex items-center justify-between mb-[9px]">
                <div class="flex-1">
                  <div class="text-[12px] font-semibold text-slate-900 dark:text-white mb-[4px]">{{ campaign.name }}</div>
                  <div class="text-[10px] font-medium" :class="getPlatformColor(campaign.platform)">{{ campaign.platform }}</div>
                </div>
              </div>

              <!-- Campaign Stats -->
              <div class="grid grid-cols-3 gap-[12px] mb-[9px]">
                <div>
                  <div class="text-[15px] font-bold text-slate-900 dark:text-white">${{ campaign.spent?.toLocaleString() || 0 }}</div>
                  <div class="text-[10px] text-slate-500 dark:text-slate-400">消耗</div>
                </div>
                <div>
                  <div class="text-[15px] font-bold text-slate-900 dark:text-white">${{ campaign.budget?.toLocaleString() || 0 }}</div>
                  <div class="text-[10px] text-slate-500 dark:text-slate-400">预算</div>
                </div>
                <div>
                  <div class="text-[15px] font-bold text-emerald-600">{{ campaign.status }}</div>
                  <div class="text-[10px] text-slate-500 dark:text-slate-400">状态</div>
                </div>
              </div>

              <!-- Campaign Actions -->
              <div class="flex items-center gap-[6px]">
                <button
                  class="flex-1 px-[9px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  @click="handleViewCampaign(campaign.id)"
                >
                  查看详情
                </button>
                <button
                  class="px-[9px] py-[6px] text-[11px] font-medium text-primary hover:underline"
                  @click="handleAddCreative(campaign.id)"
                >
                  添加素材
                </button>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="campaigns.length === 0" class="flex flex-col items-center justify-center py-[50px]">
            <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">campaign</span>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-[12px]">{{ project?.description || '暂无描述' }}</p>
            <button
              class="flex items-center gap-[6px] px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
              @click="handleCreateCampaign"
            >
              <span class="material-symbols-outlined text-[15px]">add</span>
              <span class="text-[11px] font-medium">创建首个广告</span>
            </button>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>
