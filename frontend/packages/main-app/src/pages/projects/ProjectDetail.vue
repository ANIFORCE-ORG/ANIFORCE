<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import CampaignCardDetailed from '@/components/campaigns/CampaignCardDetailed.vue'
import CreateCampaignModal from '@/components/campaigns/CreateCampaignModal.vue'
import Toast from '@/components/toasts/Toast.vue'
import { getProjectDetail, getProjectCampaigns, type Project } from '@/api/projects'
import { createCampaign, updateCampaign } from '@/api/campaigns'
import { navItems } from '@/config/navigation'

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
const showCampaignModal = ref(false)
const campaignModalRef = ref<any>(null)
const editingCampaign = ref<any>(null)

// Toast 状态管理
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'warning' | 'info'>('info')

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
  showCampaignModal.value = true
}

const handleSubmitCampaign = async (data: any) => {
  try {
    const isEdit = !!data.id
    console.log(`=== ${isEdit ? '更新' : '创建'} Campaign 请求 ===`)
    console.log('Campaign 数据:', JSON.stringify(data, null, 2))

    let result
    if (isEdit) {
      // 编辑模式：更新 Campaign
      console.log('Campaign ID:', data.id)
      result = await updateCampaign(data.id, data)
      console.log('Campaign 更新成功:', result)

      // 显示成功提示
      toastMessage.value = 'Campaign 更新成功！'
      toastType.value = 'success'
      showToast.value = true
    } else {
      // 创建模式：创建新 Campaign
      console.log('关联项目 ID:', projectId.value)

      if (!projectId.value) {
        console.error('项目 ID 缺失，无法创建 Campaign')
        toastMessage.value = '项目 ID 缺失，无法创建 Campaign'
        toastType.value = 'error'
        showToast.value = true
        return
      }

      // 添加 project_id（字段映射已在 CreateCampaignModal 中完成）
      const requestData = {
        project_id: projectId.value,
        ...data
      }

      console.log('请求数据:', JSON.stringify(requestData, null, 2))
      result = await createCampaign(requestData)
      console.log('Campaign 创建成功:', result)

      // 显示成功提示
      toastMessage.value = 'Campaign 创建成功！'
      toastType.value = 'success'
      showToast.value = true
    }

    // 关闭 Campaign 模态框
    showCampaignModal.value = false
    editingCampaign.value = null

    // 刷新 Campaign 列表
    await loadCampaigns()
  } catch (err: any) {
    console.error(`=== ${data.id ? '更新' : '创建'} Campaign 失败 ===`, err)

    // 显示错误提示
    toastMessage.value = `${data.id ? '更新' : '创建'} Campaign 失败：${err.message || '未知错误'}`
    toastType.value = 'error'
    showToast.value = true

    // 重置提交状态
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  } finally {
    // 确保重置提交状态
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  }
}

const loadCampaigns = async () => {
  try {
    const data = await getProjectCampaigns(projectId.value)
    campaigns.value = data
    console.log('Campaign 列表加载成功:', data.length, '条')
  } catch (err: any) {
    console.error('加载 Campaign 列表失败:', err)
  }
}

const handleViewCampaign = (campaignId: string) => {
  router.push(`/campaigns/${campaignId}`)
}

const handleAddCreative = (campaignId: string) => {
  console.log('添加素材:', campaignId)
}

const handleEditCampaign = (campaign: any) => {
  console.log('编辑 Campaign:', campaign)
  editingCampaign.value = campaign
  showCampaignModal.value = true
}

const handleCloseToast = () => {
  showToast.value = false
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
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <!-- 项目详情信息 -->
        <aside class="mb-[15px] p-[16px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 shadow-sm">
          <div class="flex items-center gap-[12px] mb-[6px]">
            <h2 class="text-[17px] font-bold text-slate-900 dark:text-white">{{ project?.name }}</h2>
            <div class="h-[19px] w-px bg-slate-200 dark:bg-slate-800"></div>
            <div class="flex-1">
              <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white tracking-tight">项目信息</h3>
              <p class="text-[10px] text-slate-600 dark:text-slate-400 leading-relaxed mt-[4px]">{{ project?.description || '暂无描述' }}</p>
            </div>
          </div>

          <div class="grid grid-cols-4 gap-[8px]">
            <!-- 产品类型 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">产品类型</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ project?.game_type || '-' }}</strong>
            </div>

            <!-- 目标市场 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">目标市场</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ project?.target_market || '-' }}</strong>
            </div>

            <!-- 总预算 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">总预算</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">${{ project?.total_budget.toLocaleString() || '-' }}</strong>
            </div>

            <!-- 已消耗 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">已消耗</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">${{ project?.spent.toLocaleString() || '-' }}</strong>
            </div>

            <!-- 标签 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug mb-[5px]">标签</span>
              <div class="flex gap-[5px] flex-wrap">
                <span
                  v-for="tag in project?.tags || []"
                  :key="tag"
                  class="inline-flex items-center px-[6px] py-[2px] rounded-md text-[8px] font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600"
                >
                  {{ tag }}
                </span>
                <span v-if="!project?.tags || project.tags.length === 0" class="text-[9px] text-slate-400 dark:text-slate-500">-</span>
              </div>
            </div>

            <!-- 开始/结束日期 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">开始 / 结束</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ project?.start_date || '-' }} / {{ project?.end_date || '-' }}</strong>
            </div>

            <!-- 负责人 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">负责人</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ project?.manager || '-' }}</strong>
            </div>

            <!-- 状态 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">状态</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ project?.status || '-' }}</strong>
            </div>

          </div>
        </aside>

        <!-- 广告计划列表 -->
        <div>
          <div class="flex items-center justify-between mb-[12px]">
            <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">广告 Campaigns ({{ campaigns.length }})</h4>
            <button
              class="flex items-center gap-[6px] px-[9px] py-[6px] rounded-md text-[11px] font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleCreateCampaign"
            >
              <span class="material-symbols-outlined text-[15px]">add</span>
              创建广告任务
            </button>
          </div>

          <div class="space-y-[9px]">
            <CampaignCardDetailed
              v-for="campaign in campaigns"
              :key="campaign.id"
              :campaign="campaign"
              @view="handleViewCampaign"
              @add-creative="handleAddCreative"
              @edit="handleEditCampaign"
            />
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
              <span class="text-[11px] font-medium">创建首个广告任务</span>
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

    <!-- Campaign 创建/编辑模态框 -->
    <CreateCampaignModal
      ref="campaignModalRef"
      :show="showCampaignModal"
      :initial-data="editingCampaign"
      @close="showCampaignModal = false; editingCampaign = null"
      @submit="handleSubmitCampaign"
    />

    <!-- Toast 提示组件 -->
    <Toast
      :show="showToast"
      :message="toastMessage"
      :type="toastType"
      @close="handleCloseToast"
    />
  </div>
</template>
