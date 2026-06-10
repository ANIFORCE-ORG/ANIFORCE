<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
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
const materials = ref<any[]>([])
const materialImages = ref<Map<string, string>>(new Map())

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
    
    // 加载关联的素材
    const materialsData = await getCampaignMaterials(campaignId.value)
    materials.value = materialsData
    console.log('关联素材加载成功:', materialsData.length, '条')
    
    // 加载素材图像（Base64）
    for (const material of materialsData) {
      try {
        const imageData = await getMaterialImage(material.id, true)
        materialImages.value.set(material.id, imageData.data)
      } catch (err) {
        console.error('加载素材图像失败:', material.id, err)
      }
    }
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
}

const getMaterialImageSrc = (materialId: string): string | undefined => {
  return materialImages.value.get(materialId)
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

const handleAddCreative = () => {
  console.log('添加素材')
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
      active-panel="campaigns"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间广告详情展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center px-6">
        <div class="flex items-center gap-4">
          <button
            class="flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-primary transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-lg">arrow_back</span>
            <span class="text-sm font-medium">返回广告列表</span>
          </button>
          <div class="h-6 w-px bg-slate-200 dark:bg-slate-800"></div>
          <h2 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">{{ campaign?.name }}</h2>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 广告配置详情 -->
        <div class="mb-6 p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <div class="grid grid-cols-2 gap-4">
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">所属项目</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white text-right">{{ campaign?.project_name }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">投放平台</span>
              <span class="text-sm font-medium" :class="getPlatformColor(campaign?.platform || '')">{{ campaign?.platform }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">预算</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">${{ campaign?.budget?.toLocaleString() }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">消耗</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">${{ campaign?.spent?.toLocaleString() }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">进度</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign ? Math.round((campaign.spent / campaign.budget) * 100) : 0 }}%</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">状态</span>
              <span class="text-sm font-medium text-emerald-600">{{ campaign?.status }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">开始日期</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign?.start_date }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-200 dark:border-slate-700">
              <span class="text-sm text-slate-500 dark:text-slate-400">结束日期</span>
              <span class="text-sm font-medium text-slate-900 dark:text-white">{{ campaign?.end_date || '未设置' }}</span>
            </div>
          </div>
        </div>

        <!-- 投放素材列表 -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-sm font-semibold text-slate-900 dark:text-white">投放素材 ({{ materials.length }})</h4>
            <button
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
              @click="handleAddCreative"
            >
              <span class="material-symbols-outlined text-lg">add_photo_alternate</span>
              添加素材
            </button>
          </div>
          
          <div class="grid grid-cols-3 gap-4">
            <div
              v-for="material in materials"
              :key="material.id"
              class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden hover:border-primary/50 transition-all cursor-pointer"
            >
              <!-- Material Image -->
              <div class="aspect-[9/16] bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
                <img
                  v-if="getMaterialImageSrc(material.id)"
                  :src="getMaterialImageSrc(material.id)"
                  :alt="material.name"
                  class="w-full h-full object-cover"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <span class="material-symbols-outlined text-6xl text-slate-300">movie</span>
                </div>
              </div>
              <!-- Material Info -->
              <div class="p-3 bg-white dark:bg-slate-900">
                <div class="text-sm font-medium text-slate-900 dark:text-white mb-1 truncate">{{ material.name }}</div>
                <div class="flex items-center justify-between">
                  <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600">
                    {{ material.status }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="materials.length === 0" class="flex flex-col items-center justify-center py-16">
            <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">movie</span>
            <p class="text-sm text-slate-500 dark:text-slate-400">{{ campaign?.project_name }}</p>
            <button
              class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
              @click="handleAddCreative"
            >
              <span class="material-symbols-outlined text-lg">add_photo_alternate</span>
              <span class="text-sm font-medium">添加首个素材</span>
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
