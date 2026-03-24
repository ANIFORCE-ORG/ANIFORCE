<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import MaterialImageGallery from '@/components/materials/MaterialImageGallery.vue'
import MaterialImageViewer from '@/components/materials/MaterialImageViewer.vue'
import type { Material, MaterialImage } from '@/api/materials'

const router = useRouter()
const auth = useAuthStore()

const activePanel = ref('materials')
const activeSession = ref('sess_m001')
const chatInput = ref('')
const selectedMaterial = ref<Material | null>(null)
const selectedImage = ref<MaterialImage | null>(null)
const showImageViewer = ref(false)

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/materials' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
]

const sessions = ref([
  { id: 'sess_m001', name: '素材管理', active: true },
  { id: 'sess_m002', name: '素材优化', active: false },
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: `您好${auth.user?.name || '李明'}！欢迎使用创意素材管理。\n\n我可以帮您：\n• 查看和管理素材库\n• 分析素材表现\n• 推荐优质素材\n• 生成新素材\n\n请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '查看所有素材',
  '素材表现分析',
  '生成新素材',
  '素材优化建议',
  '导出素材',
  '批量管理'
]

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

const handleSelectMaterial = (material: Material) => {
  selectedMaterial.value = material
  console.log('选中素材:', material)
}

const handleSelectImage = (image: MaterialImage) => {
  selectedImage.value = image
  showImageViewer.value = true
}

const handleCloseViewer = () => {
  showImageViewer.value = false
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间素材展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <h3 class="font-bold text-slate-900 dark:text-white">创意素材</h3>
        <div class="flex items-center gap-3">
          <button
            class="flex items-center gap-2 px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <span class="material-symbols-outlined text-lg">filter_list</span>
            <span>筛选</span>
          </button>
          <button
            class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          >
            <span class="material-symbols-outlined text-lg">add</span>
            <span class="text-sm font-medium">上传素材</span>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Selected Material Info -->
        <div v-if="selectedMaterial" class="mb-6 p-4 rounded-lg border border-primary/30 bg-primary/5">
          <div class="flex items-start justify-between">
            <div>
              <h4 class="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                已选择: {{ selectedMaterial.name }}
              </h4>
              <p class="text-xs text-slate-500 dark:text-slate-400">
                类型: {{ selectedMaterial.type }} • 
                创建时间: {{ new Date(selectedMaterial.created_at).toLocaleDateString() }}
              </p>
            </div>
            <button
              class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              @click="selectedMaterial = null"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        <!-- Material Gallery -->
        <MaterialImageGallery
          @select-material="handleSelectMaterial"
          @select-image="handleSelectImage"
        />
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

    <!-- Image Viewer Modal -->
    <MaterialImageViewer
      :image="selectedImage"
      :show="showImageViewer"
      @close="handleCloseViewer"
    />
  </div>
</template>
