<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import MaterialUpload from '@/components/materials/MaterialUpload.vue'
import AddToCampaign from '@/components/materials/AddToCampaign.vue'
import { getMaterials, getMaterialImage, type Material } from '@/api/materials'
import { login } from '@/api'

const router = useRouter()

const activeSession = ref('sess_g001')
const chatInput = ref('')
const filterTab = ref('all')
const searchQuery = ref('')
const loading = ref(false)
const error = ref('')
const materials = ref<Material[]>([])
const materialImages = ref<Map<string, string>>(new Map())
const showUploadDialog = ref(false)
const showAddToCampaignDialog = ref(false)
const selectedMaterial = ref<Material | null>(null)

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
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场拓展', active: false },
])

// 聊天消息
const messages = ref([
  {
    role: 'ai',
    author: ' ANIFORCE助手',
    time: '刚刚',
    content: '您好！我可以帮您分析热门素材、生成创意变体或AI生成新素材。请问需要什么帮助？'
  }
])

// 快捷提示
const quickHints = [
  '分析热门素材趋势',
  '生成素材变体',
  'AI生成新素材'
]

// 初始化：加载素材数据
onMounted(async () => {
  try {
    loading.value = true
    error.value = ''
    
    // 检查是否已登录
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.log('自动登录测试账号...')
      await login('test@animagus.com', 'test123')
    }
    
    // 加载素材数据
    console.log('加载素材数据...')
    const data = await getMaterials()
    materials.value = data
    console.log('素材数据加载成功:', data.length, '条')
    
    // 加载素材图像（Base64）
    for (const material of data) {
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
})

// 获取素材图像
const getMaterialImageSrc = (materialId: string): string | undefined => {
  return materialImages.value.get(materialId)
}

// Mock素材库数据（保留作为后备）
const mockCreatives = [
  // 游戏素材
  {
    id: 'cre_g001',
    name: 'CB_Gameplay_Level15',
    thumbnail: '/images/creatives/creative_game_001.jpg',
    status: 'running',
    ctr: 1.85,
    roi: 2.3,
    impressions: '285K',
    platform: 'Google',
    tags: ['#gameplay', '#level_showcase']
  },
  {
    id: 'cre_g002',
    name: 'CB_UGC_FailMoment',
    thumbnail: '/images/creatives/creative_game_002.jpg',
    status: 'running',
    ctr: 2.21,
    roi: 2.8,
    impressions: '420K',
    platform: 'TikTok',
    tags: ['#ugc', '#fail_moment']
  },
  {
    id: 'cre_g003',
    name: 'CB_Character_CandyQueen',
    thumbnail: '/images/creatives/creative_game_003.jpg',
    status: 'running',
    ctr: 1.58,
    roi: 1.9,
    impressions: '285K',
    platform: 'Meta',
    tags: ['#character', '#story']
  },
  {
    id: 'cre_g004',
    name: 'CB_Hook_ImpossibleLevel',
    thumbnail: '/images/creatives/creative_game_004.jpg',
    status: 'running',
    ctr: 3.12,
    roi: 3.2,
    impressions: '420K',
    platform: 'TikTok',
    tags: ['#hook', '#challenge']
  },
  // AI生成糖果游戏素材
  {
    id: 'ai_candy_001',
    name: 'AI_Candy_Combo',
    thumbnail: '/images/creatives/ai_candy_combo_001.jpg',
    status: 'ready',
    ctr: 1.98,
    roi: 2.1,
    impressions: '0',
    platform: 'Google',
    tags: ['#combo', '#mega']
  },
  {
    id: 'ai_candy_002',
    name: 'AI_Candy_Hook',
    thumbnail: '/images/creatives/ai_candy_hook_001.jpg',
    status: 'ready',
    ctr: 2.15,
    roi: 2.4,
    impressions: '0',
    platform: 'TikTok',
    tags: ['#hook', '#satisfying']
  },
  {
    id: 'ai_candy_003',
    name: 'AI_Candy_Mix',
    thumbnail: '/images/creatives/ai_candy_mix_001.jpg',
    status: 'ready',
    ctr: 1.85,
    roi: 2.0,
    impressions: '0',
    platform: 'Meta',
    tags: ['#gameplay', '#mix']
  },
  {
    id: 'ai_candy_004',
    name: 'AI_Candy_Reaction',
    thumbnail: '/images/creatives/ai_candy_reaction_001.jpg',
    status: 'ready',
    ctr: 2.28,
    roi: 2.5,
    impressions: '0',
    platform: 'TikTok',
    tags: ['#ugc', '#reaction']
  },
  {
    id: 'ai_candy_005',
    name: 'AI_Candy_Trend',
    thumbnail: '/images/creatives/ai_candy_trend_001.jpg',
    status: 'ready',
    ctr: 1.92,
    roi: 2.2,
    impressions: '0',
    platform: 'Google',
    tags: ['#trend', '#viral']
  },
  {
    id: 'ai_candy_006',
    name: 'AI_Candy_UGC',
    thumbnail: '/images/creatives/ai_candy_ugc_001.jpg',
    status: 'ready',
    ctr: 2.05,
    roi: 2.3,
    impressions: '0',
    platform: 'Meta',
    tags: ['#ugc', '#authentic']
  },
  {
    id: 'ai_candy_007',
    name: 'AI_Candy_Victory',
    thumbnail: '/images/creatives/ai_candy_victory_001.jpg',
    status: 'ready',
    ctr: 1.78,
    roi: 1.9,
    impressions: '0',
    platform: 'Google',
    tags: ['#victory', '#reward']
  },
  // 短剧素材
  {
    id: 'cre_d001',
    name: 'DB_Hook_SuspenseCliffhanger',
    thumbnail: '/images/creatives/creative_drama_001.jpg',
    status: 'running',
    ctr: 3.85,
    roi: 2.8,
    impressions: '1.25M',
    platform: 'TikTok',
    tags: ['#hook', '#suspense']
  },
  {
    id: 'cre_d002',
    name: 'DB_Romance_EmotionalConflict',
    thumbnail: '/images/creatives/creative_drama_002.jpg',
    status: 'running',
    ctr: 3.21,
    roi: 2.5,
    impressions: '820K',
    platform: 'Meta',
    tags: ['#romance', '#emotional']
  },
  {
    id: 'cre_d003',
    name: 'DB_Character_BossReveal',
    thumbnail: '/images/creatives/creative_drama_003.jpg',
    status: 'running',
    ctr: 2.85,
    roi: 2.1,
    impressions: '380K',
    platform: 'Google',
    tags: ['#character', '#boss']
  },
  {
    id: 'cre_d004',
    name: 'DB_Story_RevengePlot',
    thumbnail: '/images/creatives/creative_drama_004.jpg',
    status: 'fatigue',
    ctr: 2.48,
    roi: 2.3,
    impressions: '2.1M',
    platform: 'TikTok',
    tags: ['#story', '#revenge']
  },
  // 短剧参考图片
  {
    id: 'ref_drama_001',
    name: 'Short_Drama_Apps_Reference',
    thumbnail: '/images/creatives/1_The_8_Best_Short_Drama_Apps_in_202.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#apps']
  },
  {
    id: 'ref_video_001',
    name: 'Mobile_Video_Ad_Best_Practices',
    thumbnail: '/images/creatives/2_Mobile_Video_Ad_Best_Practices_for.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#best_practices']
  },
  {
    id: 'ref_video_002',
    name: 'How_to_Create_Mobile_Video_Ads',
    thumbnail: '/images/creatives/3_How_to_Create_Mobile_Video_Ads_for.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#tutorial']
  },
  {
    id: 'ref_match3_001',
    name: 'Match_3_Workflow',
    thumbnail: '/images/creatives/4_What_is_a_Match_3_How_to_do_it_Workflow.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#workflow']
  },
  {
    id: 'ref_drama_002',
    name: 'TikTok_Microdrama_Launch',
    thumbnail: '/images/creatives/5_TikTok_quietly_launches_a_microdrama.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#tiktok']
  },
  {
    id: 'ref_match3_002',
    name: 'Match_3_Candy_Game_UI',
    thumbnail: '/images/creatives/6_Match_3_candy_game_ui_interface_background.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#ui']
  },
  {
    id: 'ref_drama_003',
    name: 'Micro_Drama_Watch_Apps',
    thumbnail: '/images/creatives/7_Micro_Drama_Watch_Short_Dramas_Apps.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#apps']
  },
  {
    id: 'ref_drama_004',
    name: 'TikTok_Micro_Dramas',
    thumbnail: '/images/creatives/8_TikTok_Is_Jumping_Into_Micro_Dramas.png',
    status: 'ready',
    ctr: 0,
    roi: 0,
    impressions: '0',
    platform: 'Reference',
    tags: ['#reference', '#industry']
  }
]

const creatives = ref(mockCreatives)

// 过滤后的素材列表（使用真实数据）
const filteredCreatives = computed(() => {
  let result = materials.value

  // 按状态筛选
  if (filterTab.value !== 'all') {
    result = result.filter(m => m.status === filterTab.value)
  }

  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m => 
      m.name.toLowerCase().includes(query) ||
      (m.tags && m.tags.some((tag: string) => tag.toLowerCase().includes(query)))
    )
  }

  return result
})

// 功能卡片配置
const featureCards = [
  {
    id: 'hot-creatives',
    icon: 'trending_up',
    iconColor: 'text-red-500',
    iconBg: 'bg-red-50 dark:bg-red-900/30',
    title: '热门素材监控',
    desc: '查看行业热门素材趋势'
  },
  {
    id: 'remix',
    icon: 'shuffle',
    iconColor: 'text-blue-500',
    iconBg: 'bg-blue-50 dark:bg-blue-900/30',
    title: '跑量素材二创',
    desc: '基于优质素材生成变体'
  },
  {
    id: 'ai-generate',
    icon: 'auto_awesome',
    iconColor: 'text-purple-500',
    iconBg: 'bg-purple-50 dark:bg-purple-900/30',
    title: 'AI生成素材',
    desc: '自动生成投放素材'
  }
]

// 事件处理函数
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
  messages.value.push({
    role: 'user',
    author: '用户',
    time: '刚刚',
    content: message
  })
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
}

const handleFeatureClick = (featureId: string) => {
  console.log('点击功能卡片:', featureId)

  // 根据功能ID跳转到对应页面
  switch (featureId) {
    case 'hot-creatives':
      router.push('/materials/hot')
      break
    case 'remix':
      router.push('/materials/remix')
      break
    case 'ai-generate':
      router.push('/materials/ai-generate')
      break
    default:
      console.log('未知功能:', featureId)
  }
}

// 获取状态颜色样式
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    running: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    ready: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600',
    fatigue: 'bg-orange-50 dark:bg-orange-900/30 text-orange-600'
  }
  return colors[status] || 'bg-slate-50 dark:bg-slate-800 text-slate-600'
}

// 获取状态文本标签
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    running: '投放中',
    ready: '待投放',
    fatigue: '已疲劳'
  }
  return labels[status] || status
}

// 上传相关
const handleUploadClick = () => {
  showUploadDialog.value = true
}

const handleUploadComplete = (files: any[]) => {
  console.log('上传完成:', files)
  // TODO: 调用API保存素材到数据库
  // 暂时添加到本地列表
  showUploadDialog.value = false
}

const handleCloseUpload = () => {
  showUploadDialog.value = false
}

// 添加到投放计划相关
const handleAddToCampaign = (material: Material) => {
  selectedMaterial.value = material
  showAddToCampaignDialog.value = true
}

const handleAddComplete = () => {
  console.log('添加到投放计划完成')
  showAddToCampaignDialog.value = false
  selectedMaterial.value = null
}

const handleCloseAddToCampaign = () => {
  showAddToCampaignDialog.value = false
  selectedMaterial.value = null
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="materials"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <h1 class="text-xl font-bold text-slate-900 dark:text-white">创意素材</h1>
        <button
          class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          @click="handleUploadClick"
        >
          <span class="material-symbols-outlined text-lg">upload</span>
          <span class="text-sm font-medium">上传素材</span>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 功能卡片区域 -->
        <div class="mb-8">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              v-for="card in featureCards"
              :key="card.id"
              class="group p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-primary hover:shadow-lg transition-all cursor-pointer"
              @click="handleFeatureClick(card.id)"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <div 
                    class="w-12 h-12 rounded-lg flex items-center justify-center"
                    :class="card.iconBg"
                  >
                    <span 
                      class="material-symbols-outlined text-2xl"
                      :class="card.iconColor"
                    >
                      {{ card.icon }}
                    </span>
                  </div>
                  <div>
                    <div class="text-sm font-bold text-slate-900 dark:text-white">{{ card.title }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ card.desc }}</div>
                  </div>
                </div>
                <span class="material-symbols-outlined text-slate-400 group-hover:text-primary transition-colors">
                  chevron_right
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 素材库区域 -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold text-slate-900 dark:text-white">素材库</h2>
          </div>

          <!-- 搜索和筛选栏 -->
          <div class="mb-4">
            <div class="flex items-center gap-3">
              <div class="flex-1 relative">
                <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="搜索素材名称或标签..."
                  class="w-full pl-10 pr-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <select
                v-model="filterTab"
                class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[120px]"
              >
                <option value="all">全部</option>
                <option value="running">投放中</option>
                <option value="ready">待投放</option>
                <option value="fatigue">已疲劳</option>
              </select>
            </div>
          </div>

          <!-- 素材网格 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div
              v-for="creative in filteredCreatives"
              :key="creative.id"
              class="group bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden hover:shadow-lg transition-all cursor-pointer"
            >
              <!-- 缩略图 - 竖向比例 9:16 -->
              <div class="aspect-[9/16] bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
                <img 
                  v-if="getMaterialImageSrc(creative.id)"
                  :src="getMaterialImageSrc(creative.id)" 
                  :alt="creative.name"
                  class="w-full h-full object-cover"
                />
                <div v-else class="w-full h-full bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-6xl text-slate-400 dark:text-slate-500">
                    video_library
                  </span>
                </div>
                <!-- 状态标签 -->
                <div class="absolute top-2 right-2">
                  <span 
                    class="text-xs font-semibold px-2 py-1 rounded-md backdrop-blur-sm"
                    :class="getStatusColor(creative.status)"
                  >
                    {{ getStatusLabel(creative.status) }}
                  </span>
                </div>
                <!-- AI生成标签 -->
                <div class="absolute bottom-2 right-2">
                  <span class="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg">
                    <span class="material-symbols-outlined text-xs">auto_awesome</span>
                    <span>AI生成</span>
                  </span>
                </div>
                <!-- 播放按钮 -->
                <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                  <div class="w-12 h-12 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-primary">
                    <span class="material-symbols-outlined text-2xl">play_arrow</span>
                  </div>
                </div>
              </div>

              <!-- 信息区域 -->
              <div class="p-3">
                <h3 class="text-xs font-bold text-slate-900 dark:text-white mb-2 line-clamp-1">{{ creative.name }}</h3>
                
                <!-- 时长和标签 -->
                <div class="flex items-center gap-2 mb-2 text-xs text-slate-500 dark:text-slate-400">
                  <span v-if="creative.duration">{{ creative.duration }}s</span>
                  <span v-if="creative.duration && creative.tags && creative.tags.length > 0">·</span>
                  <span v-if="creative.tags && creative.tags.length > 0">{{ creative.tags[0] }}</span>
                </div>

                <!-- 数据指标 -->
                <div class="grid grid-cols-3 gap-2 mb-2">
                  <div class="text-left">
                    <div class="text-[10px] text-slate-400 mb-0.5">ROI</div>
                    <div class="text-xs font-bold" :class="creative.roi && creative.roi >= 2.0 ? 'text-emerald-600' : 'text-slate-900 dark:text-white'">
                      {{ creative.roi ? `${creative.roi.toFixed(2)}x` : 'N/A' }}
                    </div>
                  </div>
                  <div class="text-left">
                    <div class="text-[10px] text-slate-400 mb-0.5">消耗</div>
                    <div class="text-xs font-bold text-slate-900 dark:text-white">
                      {{ creative.spend ? `$${creative.spend.toLocaleString()}` : 'N/A' }}
                    </div>
                  </div>
                  <div class="text-left">
                    <div class="text-[10px] text-slate-400 mb-0.5">CTR</div>
                    <div class="text-xs font-bold text-slate-900 dark:text-white">{{ creative.ctr_estimate?.toFixed(1) || 'N/A' }}%</div>
                  </div>
                </div>

                <!-- 关联投放计划 -->
                <div v-if="creative.campaign_ids && creative.campaign_ids.length > 0" class="mb-2">
                  <div class="text-[10px] text-slate-400 mb-1">关联计划</div>
                  <div class="text-xs text-slate-600 dark:text-slate-400">
                    {{ creative.campaign_ids.length }} 个投放计划
                  </div>
                </div>

                <!-- 疲劳度标签 -->
                <div v-if="creative.fatigue && creative.fatigue > 3.0" class="mb-2">
                  <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-full bg-orange-50 dark:bg-orange-900/30 text-orange-600">
                    <span class="material-symbols-outlined text-xs">warning</span>
                    疲劳度 {{ creative.fatigue.toFixed(1) }}
                  </span>
                </div>

                <!-- Hero素材标签 -->
                <div v-if="creative.is_hero">
                  <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-full bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600">
                    <span class="material-symbols-outlined text-xs">star</span>
                    跑量素材
                  </span>
                </div>

                <!-- 操作按钮 -->
                <div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                  <button
                    class="w-full px-3 py-2 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors flex items-center justify-center gap-1"
                    @click="handleAddToCampaign(creative)"
                  >
                    <span class="material-symbols-outlined text-sm">add_circle</span>
                    添加到投放计划
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="filteredCreatives.length === 0" class="flex flex-col items-center justify-center py-16">
            <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">
              video_library
            </span>
            <p class="text-sm text-slate-500 dark:text-slate-400">
              {{ searchQuery || filterTab !== 'all' ? '未找到匹配的素材' : '暂无素材' }}
            </p>
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

    <!-- 上传素材对话框 -->
    <MaterialUpload
      v-if="showUploadDialog"
      @upload-complete="handleUploadComplete"
      @close="handleCloseUpload"
    />

    <!-- 添加到投放计划对话框 -->
    <AddToCampaign
      v-if="showAddToCampaignDialog"
      :material="selectedMaterial"
      @add-complete="handleAddComplete"
      @close="handleCloseAddToCampaign"
    />
  </div>
</template>
