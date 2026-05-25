<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { getMaterials, getMaterialImage, type Material } from '@/api/materials'
import { navItems } from '@/config/navigation'
import { useToast } from '@/composables/useToast'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { error: showError, info } = useToast()
const workspaceSessions = useWorkspaceSessions()

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
const returnTo = computed(() => typeof route.query.returnTo === 'string' ? route.query.returnTo : '')
const fromCampaignCreate = computed(() => route.query.source === 'campaign-create' && Boolean(returnTo.value))

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

const handleReturnToCampaign = () => {
  if (returnTo.value) {
    router.push(returnTo.value)
  }
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

const completeUpload = async () => {
  if (uploadFiles.value.length === 0) {
    showError('请先选择要上传的文件')
    return
  }
  
  // 后端 API 未对接，显示提示信息
  info('上传功能待开发完善！')
  console.log('待上传文件:', uploadFiles.value)
  
  // TODO: 实际的后端 API 调用
  // uploading.value = true
  // uploadProgress.value.clear()
  // 
  // try {
  //   const formData = new FormData()
  //   uploadFiles.value.forEach(file => formData.append('files', file))
  //   await uploadMaterials(formData)
  //   
  //   success(`成功上传 ${uploadFiles.value.length} 个文件`)
  //   await refreshMaterials()
  //   closeUploadModal()
  // } catch (err: any) {
  //   console.error('上传失败:', err)
  //   showError(err.message || '上传失败，请稍后重试')
  // } finally {
  //   uploading.value = false
  //   uploadProgress.value.clear()
  // }
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="workspaceSessions.sessions.value"
      active-panel="materials"
      @switch-panel="switchPanel"
      @switch-session="workspaceSessions.switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h1 class="text-base font-bold text-slate-900 dark:text-white">创意素材</h1>
          <p v-if="fromCampaignCreate" class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            创建或上传素材后，可以返回新建广告计划继续选择。
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="fromCampaignCreate"
            class="inline-flex items-center gap-2 whitespace-nowrap rounded-md border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            @click="handleReturnToCampaign"
          >
            <span class="material-symbols-outlined text-lg">arrow_back</span>
            返回创建计划
          </button>
          <button
            class="flex items-center gap-2 whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
            @click="openUploadModal"
          >
            <span class="material-symbols-outlined text-lg">upload</span>
            <span>上传素材</span>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 功能卡片区域 -->
        <div class="mb-8">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              v-for="card in featureCards"
              :key="card.id"
              class="group p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-primary hover:shadow-lg transition-all cursor-pointer"
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
            <h2 class="text-lg font-bold text-slate-900 dark:text-white">素材广场</h2>
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
                <div class="grid grid-cols-2 gap-2">
                  <div class="text-left">
                    <div class="text-[10px] text-slate-400 mb-0.5">CTR预估</div>
                    <div class="text-xs font-bold text-slate-900 dark:text-white">{{ creative.ctr_estimate?.toFixed(1) || 'N/A' }}%</div>
                  </div>
                  <div class="text-left">
                    <div class="text-[10px] text-slate-400 mb-0.5">文件大小</div>
                    <div class="text-xs font-bold text-slate-900 dark:text-white">{{ creative.file_size ? (creative.file_size / 1024).toFixed(0) + 'KB' : 'N/A' }}</div>
                  </div>
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
      :session-id="workspaceSessions.activeSessionId.value"
      :quick-hints="quickHints"
    />

    <!-- 上传素材对话框 -->
    <div
      v-if="showUploadModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="closeUploadModal"
    >
      <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl mx-4">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 class="text-xl font-bold text-slate-900 dark:text-white">上传素材</h2>
          <button
            class="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            @click="closeUploadModal"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
          </button>
        </div>

        <!-- Content -->
        <div class="p-6">
          <!-- Upload Area -->
          <div
            class="border-2 border-dashed rounded-xl p-12 text-center transition-colors"
            :class="isDragging 
              ? 'border-primary bg-primary/5' 
              : 'border-slate-300 dark:border-slate-600 hover:border-primary hover:bg-slate-50 dark:hover:bg-slate-700/50'"
            @drop="handleDrop"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
          >
            <div class="flex flex-col items-center gap-4">
              <div class="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                <span class="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500">cloud_upload</span>
              </div>
              
              <div>
                <p class="text-slate-700 dark:text-slate-300 mb-2">
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
                <p class="text-sm text-slate-500 dark:text-slate-400">
                  支持 JPG, PNG, GIF, MP4, MOV 格式，最大 100MB
                </p>
              </div>
            </div>
          </div>

          <!-- File List -->
          <div v-if="uploadFiles.length > 0" class="mt-6 space-y-2">
            <div class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
              已选择 {{ uploadFiles.length }} 个文件
            </div>
            <div
              v-for="(file, index) in uploadFiles"
              :key="index"
              class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg"
            >
              <div class="flex items-center gap-3 flex-1 min-w-0">
                <span class="material-symbols-outlined text-slate-400">
                  {{ file.type.startsWith('video/') ? 'videocam' : 'image' }}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-900 dark:text-white truncate">{{ file.name }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">
                    {{ (file.size / 1024 / 1024).toFixed(2) }} MB
                  </p>
                </div>
              </div>
              <button
                class="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded transition-colors"
                @click="removeFile(index)"
              >
                <span class="material-symbols-outlined text-sm text-slate-600 dark:text-slate-400">close</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
          <button
            class="px-4 py-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            @click="closeUploadModal"
          >
            取消
          </button>
          <button
            class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            :disabled="uploadFiles.length === 0 || uploading"
            @click="completeUpload"
          >
            <span v-if="uploading" class="material-symbols-outlined animate-spin text-sm">progress_activity</span>
            <span>{{ uploading ? '上传中...' : `完成上传 (${uploadFiles.length})` }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
