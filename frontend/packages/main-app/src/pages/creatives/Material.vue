<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { getMaterials, getMaterialImage, uploadMaterials, type Material } from '@/api/materials'
import { navItems } from '@/config/navigation'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const { success, error: showError } = useToast()

const activeSession = ref('sess_g001')
const chatInput = ref('')
const filterTab = ref('all')
const searchQuery = ref('')
const loading = ref(false)
const error = ref('')
const materials = ref<Material[]>([])
const materialImages = ref<Map<string, string>>(new Map())

// 上传素材相关状态
const showUploadModal = ref(false)
const uploadFiles = ref<File[]>([])
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref<Map<string, number>>(new Map())

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
    if (!auth.isLoggedIn) {
      console.log('自动登录测试账号...')
      await auth.login({ email: 'test@animagus.com', password: 'test123' })
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
        materialImages.value.set(material.id, imageData.url || imageData.data || '')
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
const getMaterialImageSrc = (material: Material): string | undefined => {
  return materialImages.value.get(material.id) || material.thumbnail_url || material.url
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

// 上传素材相关函数
const openUploadModal = () => {
  showUploadModal.value = true
  uploadFiles.value = []
}

const closeUploadModal = () => {
  showUploadModal.value = false
  uploadFiles.value = []
  isDragging.value = false
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    const files = Array.from(target.files)
    addFiles(files)
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragging.value = false
  
  if (event.dataTransfer?.files) {
    const files = Array.from(event.dataTransfer.files)
    addFiles(files)
  }
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const addFiles = (files: File[]) => {
  const validFiles = files.filter(file => {
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime']
    const maxSize = 100 * 1024 * 1024 // 100MB
    
    if (!validTypes.includes(file.type)) {
      showError(`文件 ${file.name} 格式不支持`)
      return false
    }
    
    if (file.size > maxSize) {
      showError(`文件 ${file.name} 超过100MB限制`)
      return false
    }
    
    return true
  })
  
  uploadFiles.value = [...uploadFiles.value, ...validFiles]
}

const removeFile = (index: number) => {
  uploadFiles.value.splice(index, 1)
}

const refreshMaterials = async () => {
  try {
    loading.value = true
    const data = await getMaterials()
    materials.value = data
    
    // 加载新素材的图像
    for (const material of data) {
      if (!materialImages.value.has(material.id)) {
        try {
          const imageData = await getMaterialImage(material.id, true)
          materialImages.value.set(material.id, imageData.url || imageData.data || '')
        } catch (err) {
          console.error('加载素材图像失败:', material.id, err)
        }
      }
    }
  } catch (err: any) {
    console.error('刷新素材列表失败:', err)
    showError('刷新素材列表失败')
  } finally {
    loading.value = false
  }
}

const completeUpload = async () => {
  if (uploadFiles.value.length === 0) {
    showError('请先选择要上传的文件')
    return
  }

  uploading.value = true
  uploadProgress.value.clear()
  try {
    for (const file of uploadFiles.value) uploadProgress.value.set(file.name, 0)
    await uploadMaterials(uploadFiles.value)
    for (const file of uploadFiles.value) uploadProgress.value.set(file.name, 100)
    success(`成功上传 ${uploadFiles.value.length} 个文件`)
    await refreshMaterials()
    closeUploadModal()
  } catch (err: any) {
    console.error('上传失败:', err)
    showError(err.message || '上传失败，请稍后重试')
  } finally {
    uploading.value = false
    uploadProgress.value.clear()
  }
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
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
      <div class="h-[50px] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[19px]">
        <h1 class="text-[17px] font-bold text-slate-900 dark:text-white">创意素材</h1>
        <button
          class="flex items-center gap-[6px] px-[12px] py-[6px] bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          @click="openUploadModal"
        >
          <span class="material-symbols-outlined text-[15px]">upload</span>
          <span class="font-medium text-[11px]">上传素材</span>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <!-- 功能卡片区域 -->
        <div class="mb-[25px]">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-[12px]">
            <div
              v-for="card in featureCards"
              :key="card.id"
              class="group p-[9px] bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-primary hover:shadow-lg transition-all cursor-pointer"
              @click="handleFeatureClick(card.id)"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-[12px]">
                  <div 
                    class="w-[37px] h-[37px] rounded-lg flex items-center justify-center"
                    :class="card.iconBg"
                  >
                    <span 
                      class="material-symbols-outlined text-[17px]"
                      :class="card.iconColor"
                    >
                      {{ card.icon }}
                    </span>
                  </div>
                  <div>
                    <div class="text-[11px] font-bold text-slate-900 dark:text-white">{{ card.title }}</div>
                    <div class="text-[10px] text-slate-500 dark:text-slate-400 mt-[4px]">{{ card.desc }}</div>
                  </div>
                </div>
                <span class="material-symbols-outlined text-[17px] text-slate-400 group-hover:text-primary transition-colors">
                  chevron_right
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 素材库区域 -->
        <div>
          <div class="flex items-center justify-between mb-[12px]">
            <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">素材广场</h2>
          </div>

          <!-- 搜索和筛选栏 -->
          <div class="mb-[12px]">
            <div class="flex items-center gap-[9px]">
              <div class="flex-1 relative">
                <span class="material-symbols-outlined absolute left-[9px] top-1/2 -translate-y-1/2 text-slate-400 text-[15px]">search</span>
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="搜索素材名称或标签..."
                  class="w-full pl-[31px] pr-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <select
                v-model="filterTab"
                class="px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[94px]"
              >
                <option value="all">全部</option>
                <option value="running">投放中</option>
                <option value="ready">待投放</option>
                <option value="fatigue">已疲劳</option>
              </select>
            </div>
          </div>

          <!-- 素材网格 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-[12px]">
            <div
              v-for="creative in filteredCreatives"
              :key="creative.id"
              class="group bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden hover:shadow-lg transition-all cursor-pointer"
            >
              <!-- 缩略图 - 竖向比例 9:16 -->
              <div class="aspect-[9/16] bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
                <img 
                  v-if="getMaterialImageSrc(creative)"
                  :src="getMaterialImageSrc(creative)" 
                  :alt="creative.name"
                  class="w-full h-full object-cover"
                />
                <div v-else class="w-full h-full bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-[47px] text-slate-400 dark:text-slate-500">
                    video_library
                  </span>
                </div>
                <!-- 状态标签 -->
                <div class="absolute top-[6px] right-[6px]">
                  <span 
                    class="text-[10px] font-semibold px-[6px] py-[4px] rounded-md backdrop-blur-sm"
                    :class="getStatusColor(creative.status)"
                  >
                    {{ getStatusLabel(creative.status) }}
                  </span>
                </div>
                <!-- AI生成标签 -->
                <div class="absolute bottom-[6px] right-[6px]">
                  <span class="inline-flex items-center gap-[4px] text-[8px] font-bold px-[6px] py-[4px] rounded-full bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg">
                    <span class="material-symbols-outlined text-[10px]">auto_awesome</span>
                    <span>AI生成</span>
                  </span>
                </div>
                <!-- 播放按钮 -->
                <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                  <div class="w-[37px] h-[37px] rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-primary">
                    <span class="material-symbols-outlined text-[17px]">play_arrow</span>
                  </div>
                </div>
              </div>

              <!-- 信息区域 -->
              <div class="p-[9px]">
                <h3 class="text-[10px] font-bold text-slate-900 dark:text-white mb-[6px] line-clamp-1">{{ creative.name }}</h3>
                
                <!-- 时长和标签 -->
                <div class="flex items-center gap-[6px] mb-[6px] text-[10px] text-slate-500 dark:text-slate-400">
                  <span v-if="creative.duration">{{ creative.duration }}s</span>
                  <span v-if="creative.duration && creative.tags && creative.tags.length > 0">·</span>
                  <span v-if="creative.tags && creative.tags.length > 0">{{ creative.tags[0] }}</span>
                </div>

                <!-- 数据指标 -->
                <div class="grid grid-cols-2 gap-[6px]">
                  <div class="text-left">
                    <div class="text-[8px] text-slate-400 mb-[2px]">CTR预估</div>
                    <div class="text-[10px] font-bold text-slate-900 dark:text-white">{{ creative.ctr_estimate?.toFixed(1) || 'N/A' }}%</div>
                  </div>
                  <div class="text-left">
                    <div class="text-[8px] text-slate-400 mb-[2px]">文件大小</div>
                    <div class="text-[10px] font-bold text-slate-900 dark:text-white">{{ creative.file_size ? (creative.file_size / 1024).toFixed(0) + 'KB' : 'N/A' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="filteredCreatives.length === 0" class="flex flex-col items-center justify-center py-[50px]">
            <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">
              video_library
            </span>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">
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
    <div
      v-if="showUploadModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="closeUploadModal"
    >
      <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-[624px] mx-4">
        <!-- Header -->
        <div class="flex items-center justify-between px-[19px] py-[12px] border-b border-slate-200 dark:border-slate-700">
          <h2 class="text-[17px] font-bold text-slate-900 dark:text-white">上传素材</h2>
          <button
            class="p-[6px] hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            @click="closeUploadModal"
          >
            <span class="material-symbols-outlined text-[17px] text-slate-600 dark:text-slate-400">close</span>
          </button>
        </div>

        <!-- Content -->
        <div class="p-[19px]">
          <!-- Upload Area -->
          <div
            class="border-2 border-dashed rounded-xl p-[37px] text-center transition-colors"
            :class="isDragging 
              ? 'border-primary bg-primary/5' 
              : 'border-slate-300 dark:border-slate-600 hover:border-primary hover:bg-slate-50 dark:hover:bg-slate-700/50'"
            @drop="handleDrop"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
          >
            <div class="flex flex-col items-center gap-[12px]">
              <div class="w-[50px] h-[50px] rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                <span class="material-symbols-outlined text-[31px] text-slate-400 dark:text-slate-500">cloud_upload</span>
              </div>
              
              <div>
                <p class="text-[11px] text-slate-700 dark:text-slate-300 mb-[6px]">
                  拖拽文件到此处,或
                  <label class="text-primary hover:text-primary/80 cursor-pointer font-medium">
                    点击浏览
                    <input
                      type="file"
                      multiple
                      accept="image/jpeg,image/png,image/gif,video/mp4,video/quicktime"
                      class="hidden"
                      @change="handleFileSelect"
                    />
                  </label>
                </p>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  支持 JPG, PNG, GIF, MP4, MOV 格式，最大 100MB
                </p>
              </div>
            </div>
          </div>

          <!-- File List -->
          <div v-if="uploadFiles.length > 0" class="mt-[19px] space-y-[6px]">
            <div class="text-[10px] font-medium text-slate-700 dark:text-slate-300 mb-[9px]">
              已选择 {{ uploadFiles.length }} 个文件
            </div>
            <div
              v-for="(file, index) in uploadFiles"
              :key="index"
              class="flex items-center justify-between p-[9px] bg-slate-50 dark:bg-slate-700 rounded-lg"
            >
              <div class="flex items-center gap-[9px] flex-1 min-w-0">
                <span class="material-symbols-outlined text-[15px] text-slate-400">
                  {{ file.type.startsWith('video/') ? 'videocam' : 'image' }}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-[10px] font-medium text-slate-900 dark:text-white truncate">{{ file.name }}</p>
                  <p class="text-[9px] text-slate-500 dark:text-slate-400">
                    {{ (file.size / 1024 / 1024).toFixed(2) }} MB
                  </p>
                </div>
              </div>
              <button
                class="p-[4px] hover:bg-slate-200 dark:hover:bg-slate-600 rounded transition-colors"
                @click="removeFile(index)"
              >
                <span class="material-symbols-outlined text-[11px] text-slate-600 dark:text-slate-400">close</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-[9px] px-[19px] py-[12px] border-t border-slate-200 dark:border-slate-700">
          <button
            class="px-[12px] py-[6px] text-[11px] text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            @click="closeUploadModal"
          >
            取消
          </button>
          <button
            class="px-[12px] py-[6px] bg-primary text-white text-[11px] rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-[6px]"
            :disabled="uploadFiles.length === 0 || uploading"
            @click="completeUpload"
          >
            <span v-if="uploading" class="material-symbols-outlined animate-spin text-[11px]">progress_activity</span>
            <span>{{ uploading ? '上传中...' : `完成上传 (${uploadFiles.length})` }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
