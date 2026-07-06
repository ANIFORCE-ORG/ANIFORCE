<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import AdUnitCardDetailed from '@/components/campaigns/AdUnitCardDetailed.vue'
import CreateAdUnitModal from '@/components/campaigns/CreateAdUnitModal.vue'
import { getCampaignDetail, getCampaignMaterials, type Campaign } from '@/api/campaigns'
import { getMaterialImage } from '@/api/materials'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const campaignId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const chatInput = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const campaign = ref<Campaign | null>(null)
const adUnits = ref<any[]>([])
const showCreateAdUnitModal = ref(false)
const createAdUnitModalRef = ref<any>(null)

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
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n我可以帮您：\n• 分析素材表现\n• 优化投放策略\n• 素材创意建议\n• 预算调整建议\n\n请告诉我您需要什么帮助？`
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

onMounted(async () => {
  await loadCampaignData()
})

const loadCampaignData = async () => {
  loading.value = true
  error.value = null

  try {
    console.log('加载广告投放详情:', campaignId.value)

    // 加载广告投放详情
    const campaignData = await getCampaignDetail(campaignId.value)
    campaign.value = campaignData
    console.log('广告投放详情加载成功:', campaignData)

    // TODO: 加载关联的 Ad Units
    // const adUnitsData = await getAdUnits(campaignId.value)
    // adUnits.value = adUnitsData

    // 临时模拟数据
    adUnits.value = []
    console.log('Ad Units 加载成功:', adUnits.value.length, '条')
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
  // 使用router.back()返回上一页，智能返回到来源页面
  router.back()
}

const handleAddAdUnit = () => {
  showCreateAdUnitModal.value = true
}

const handleCloseAdUnitModal = () => {
  showCreateAdUnitModal.value = false
}

const handleSubmitAdUnit = async (data: any) => {
  try {
    // TODO: 调用 API 创建 Ad Unit
    console.log('创建 Ad Unit:', data)

    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 成功后关闭弹窗并刷新列表
    showCreateAdUnitModal.value = false
    if (createAdUnitModalRef.value) {
      createAdUnitModalRef.value.resetForm()
    }

    // TODO: 刷新 Ad Units 列表
    console.log('Ad Unit 创建成功')
  } catch (err: any) {
    console.error('创建 Ad Unit 失败:', err)
  } finally {
    if (createAdUnitModalRef.value) {
      createAdUnitModalRef.value.setSubmitting(false)
    }
  }
}

const handleViewAdUnit = (adUnitId: string) => {
  console.log('查看 Ad Unit 详情:', adUnitId)
  // TODO: 跳转到 Ad Unit 详情页面
}

const handleEditAdUnit = (adUnit: any) => {
  console.log('编辑 Ad Unit:', adUnit)
  // TODO: 打开编辑 Ad Unit 的弹窗或页面
}

const getPlatformColor = (platform: string) => {
  const colors: Record<string, string> = {
    'Google': 'text-blue-600',
    'TikTok': 'text-slate-900 dark:text-white',
    'Meta': 'text-blue-500'
  }
  return colors[platform] || 'text-slate-600'
}

// 格式化日期
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  try {
    const date = new Date(dateString)
    return date.toISOString().slice(0, 10)
  } catch {
    return dateString
  }
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
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
      <div class="h-[50px] border-b border-slate-200 dark:border-slate-800 flex items-center px-[19px]">
        <div class="flex items-center gap-[12px]">
          <button
            class="flex items-center gap-[6px] text-slate-600 dark:text-slate-400 hover:text-primary transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-[15px]">arrow_back</span>
            <span class="text-[11px] font-medium">返回广告列表</span>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <!-- Campaign 详情信息 -->
        <aside class="mb-[15px] p-[16px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 shadow-sm">
          <div class="flex items-center gap-[12px] mb-[6px]">
            <h2 class="text-[17px] font-bold text-slate-900 dark:text-white">{{ campaign?.name }}</h2>
            <div class="h-[19px] w-px bg-slate-200 dark:bg-slate-800"></div>
            <div class="flex-1">
              <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white tracking-tight">Campaign 信息</h3>
              <p class="text-[10px] text-slate-600 dark:text-slate-400 leading-relaxed mt-[4px]">所属项目: {{ campaign?.project_name || '暂无' }}</p>
            </div>
          </div>

          <div class="grid grid-cols-4 gap-[8px]">
            <!-- 平台 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">平台</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.platform || '-' }}</strong>
            </div>

            <!-- 广告账户 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">广告账户</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.account_id || '-' }}</strong>
            </div>

            <!-- Budget Level -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">CampaignBudgetOptimization</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.campaign_budget_optimization}}</strong>
            </div>

            <!-- 预算 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">预算</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">${{ campaign?.budget?.toLocaleString() || '-' }}</strong>
            </div>

            <!-- Buying Type -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">Buying Type</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.buying_type || '-' }}</strong>
            </div>

            <!-- Bid Strategy -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">Objective</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.objective || '-' }}</strong>
            </div>

            <!-- 开始/结束日期 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">开始 / 结束</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ formatDate(campaign?.start_date) }} / {{ formatDate(campaign?.end_date) }}</strong>
            </div>

            <!-- 状态 -->
            <div class="border border-slate-200 dark:border-slate-700 rounded-md p-[8px_10px]">
              <span class="block text-[9px] text-slate-600 dark:text-slate-400 leading-snug">状态</span>
              <strong class="block text-[10px] text-slate-900 dark:text-white mt-[2px] break-words">{{ campaign?.status || '-' }}</strong>
            </div>
          </div>
        </aside>

        <!-- 广告单元列表 (Ad Sets) -->
        <div>
          <div class="flex items-center justify-between mb-[12px]">
            <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">广告单元 Ad Sets ({{ adUnits.length }})</h4>
            <button
              class="flex items-center gap-[6px] px-[9px] py-[6px] rounded-md text-[11px] font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleAddAdUnit"
            >
              <span class="material-symbols-outlined text-[15px]">add</span>
              创建新广告单元
            </button>
          </div>

          <div class="space-y-[12px]">
            <AdUnitCardDetailed
              v-for="adUnit in adUnits"
              :key="adUnit.id"
              :ad-unit="adUnit"
              @view="handleViewAdUnit"
              @edit="handleEditAdUnit"
            />
          </div>

          <!-- Empty State -->
          <div v-if="adUnits.length === 0" class="flex flex-col items-center justify-center py-[50px]">
            <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">campaign</span>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-[12px]">暂无广告单元</p>
            <button
              class="flex items-center gap-[6px] px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
              @click="handleAddAdUnit"
            >
              <span class="material-symbols-outlined text-[15px]">add</span>
              <span class="text-[11px] font-medium">创建首个广告单元</span>
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

    <!-- 创建 Ad Unit 弹窗 -->
    <CreateAdUnitModal
      ref="createAdUnitModalRef"
      :show="showCreateAdUnitModal"
      :campaign-id="campaignId"
      :campaign-buying-type="campaign?.buying_type"
      :campaign-objective="campaign?.objective"
      :campaign-budget-optimization="campaign?.campaign_budget_optimization"
      @close="handleCloseAdUnitModal"
      @submit="handleSubmitAdUnit"
    />
  </div>
</template>
