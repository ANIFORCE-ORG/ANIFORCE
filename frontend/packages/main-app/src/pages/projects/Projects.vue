<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue'
import ProjectCardCompact from '@/components/projects/ProjectCardCompact.vue'
import ProjectCardDetailed from '@/components/projects/ProjectCardDetailed.vue'
import Toast from '@/components/toasts/Toast.vue'
import { getProjects, createProject, type Project } from '@/api/projects'
import { navItems } from '@/config/navigation'

const router = useRouter()
const auth = useAuthStore()

// Toast 状态
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'warning' | 'info'>('info')

const showToastMessage = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
  toastMessage.value = message
  toastType.value = type
  showToast.value = true
}

const handleToastClose = () => {
  showToast.value = false
}

const activeSession = ref('sess_g001')
const chatInput = ref('')
const showCreateModal = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const projects = ref<Project[]>([])
const searchQuery = ref('')
const filterStatus = ref('all')
const createModalRef = ref<any>(null)
const cardViewType = ref<'compact' | 'detailed'>('compact')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场拓展', active: false },
  { id: 'sess_g004', name: 'DramaBox新剧推广', active: false },
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: `您好 ${auth.user?.name} ！我是ANIFORCE智能助手。\n\n当前项目概览：\n• 📱 Candy Blast：消耗$52,300，ROI 1.88x\n• 📺 DramaBox：消耗$98,700，ROI 2.15x\n\n我可以帮您分析项目数据、优化投放策略。请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '项目数据分析',
  '创建新项目',
  '优化建议',
  '预算调整',
  '素材管理',
  '投放策略'
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
    projects.value = data
    console.log('项目数据加载成功:', data.length, '条')
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
})

// 筛选后的项目列表
const filteredProjects = computed(() => {
  let result = projects.value

  // 按状态筛选
  if (filterStatus.value !== 'all') {
    result = result.filter(p => p.status === filterStatus.value)
  }

  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => 
      p.name.toLowerCase().includes(query) ||
      p.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  return result
})

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

const handleSearch = () => {
  // 筛选逻辑在 computed 中处理
}

const handleCreateProject = () => {
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
}

const handleSubmitProject = async (data: any) => {
  try {
    console.log('=== 创建项目请求 ===')
    console.log('原始表单数据:', JSON.stringify(data, null, 2))
    
    // 转换数据格式以匹配后端要求
    const requestData = {
      ...data,
      total_budget: parseFloat(data.budget) || 0, // 添加 total_budget 字段
      start_date: data.start, // Project 的 start_date 复用表单的 start
      end_date: data.end, // Project 的 end_date 复用表单的 end
      target_market: data.countries, // target_market 使用 countries 填充
      manager: auth.user?.name || '未知', // manager 使用创建者名字
    }
    
    console.log('转换后的请求数据:', JSON.stringify(requestData, null, 2))
    
    const newProject = await createProject(requestData)
    console.log('项目创建成功:', newProject)
    
    // 添加到项目列表
    projects.value.unshift(newProject)
    
    // 显示成功提示
    showToastMessage('项目创建成功！', 'success')
    
    // 关闭弹窗并重置表单
    showCreateModal.value = false
    createModalRef.value?.resetForm()
  } catch (err: any) {
    console.error('=== 创建项目失败 ===')
    console.error('错误对象:', err)
    console.error('错误响应:', err.response)
    console.error('错误数据:', err.response?.data)
    
    // 解析错误信息
    let errorMessage = '创建项目失败，请重试'
    
    if (err.response?.data?.detail) {
      // FastAPI 返回的错误格式
      if (Array.isArray(err.response.data.detail)) {
        // Pydantic 验证错误格式
        const errors = err.response.data.detail.map((e: any) => 
          `${e.loc.join('.')}: ${e.msg}`
        ).join('; ')
        errorMessage = `数据验证失败: ${errors}`
      } else if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      } else {
        errorMessage = JSON.stringify(err.response.data.detail)
      }
    } else if (err.message) {
      errorMessage = err.message
    } else if (typeof err === 'string') {
      errorMessage = err
    }
    
    console.error('最终错误信息:', errorMessage)
    
    // 使用 Toast 显示错误
    showToastMessage(errorMessage, 'error')
  } finally {
    createModalRef.value?.setSubmitting(false)
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
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间项目展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-[50px] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[19px]">
        <h3 class="font-bold text-[13px] text-slate-900 dark:text-white">项目管理</h3>
        <div class="flex items-center gap-[9px]">
          <!-- View Toggle -->
          <div class="flex items-center gap-[4px] p-[4px] rounded-md bg-slate-100 dark:bg-slate-800">
            <button
              :class="[
                'px-[9px] py-[6px] rounded text-[10px] font-medium transition-colors',
                cardViewType === 'compact' 
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              ]"
              @click="cardViewType = 'compact'"
            >
              <span class="material-symbols-outlined text-[11px]">grid_view</span>
            </button>
            <button
              :class="[
                'px-[9px] py-[6px] rounded text-[10px] font-medium transition-colors',
                cardViewType === 'detailed' 
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              ]"
              @click="cardViewType = 'detailed'"
            >
              <span class="material-symbols-outlined text-[11px]">view_list</span>
            </button>
          </div>
          <button
            class="flex items-center gap-[6px] px-[12px] py-[6px] rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
            @click="handleCreateProject"
          >
            <span class="material-symbols-outlined text-[15px]">add</span>
            <span class="text-[11px] font-medium">创建项目</span>
          </button>
        </div>
      </div>

      <!-- Search & Filter Bar -->
      <div class="border-b border-slate-200 dark:border-slate-800 p-[12px]">
        <div class="flex items-center gap-[9px]">
          <div class="flex-1 relative">
            <span class="material-symbols-outlined absolute left-[9px] top-1/2 -translate-y-1/2 text-slate-400 text-[15px]">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索项目名称或标签..."
              class="w-full pl-[31px] pr-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
              @input="handleSearch"
            />
          </div>
          <select
            v-model="filterStatus"
            class="px-[12px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
            @change="handleSearch"
          >
            <option v-for="filter in statusFilters" :key="filter.value" :value="filter.value">
              {{ filter.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Projects List -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <!-- Compact View -->
        <div v-if="cardViewType === 'compact'" class="grid gap-[12px] md:grid-cols-2 lg:grid-cols-3">
          <ProjectCardCompact
            v-for="project in filteredProjects"
            :key="project.id"
            :project="project"
            @edit="router.push(`/projects/${$event.id}`)"
            @view-tasks="console.log('View tasks:', $event)"
            @create-task="console.log('Create task:', $event)"
            @select="console.log('Select:', $event)"
          />
        </div>

        <!-- Detailed View -->
        <div v-else class="grid gap-[12px]">
          <ProjectCardDetailed
            v-for="project in filteredProjects"
            :key="project.id"
            :project="project"
            @view-detail="router.push(`/projects/${$event.id}`)"
          />
        </div>

        <!-- Empty State -->
        <div v-if="filteredProjects.length === 0" class="flex flex-col items-center justify-center py-[50px]">
          <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">folder_off</span>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">未找到匹配的项目</p>
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

    <!-- 创建项目弹窗 -->
    <CreateProjectModal
      ref="createModalRef"
      :show="showCreateModal"
      @close="handleCloseModal"
      @submit="handleSubmitProject"
    />

    <!-- Toast 提示 -->
    <Toast
      :show="showToast"
      :message="toastMessage"
      :type="toastType"
      :duration="5000"
      @close="handleToastClose"
    />
  </div>
</template>
