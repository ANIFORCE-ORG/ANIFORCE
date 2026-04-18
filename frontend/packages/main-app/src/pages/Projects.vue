<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue'
import { getProjects, createProject, type Project } from '@/api/projects'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const error = ref<string | null>(null)
const showCreateModal = ref(false)
const createModalRef = ref<InstanceType<typeof CreateProjectModal> | null>(null)

const activePanel = ref('projects')
const activeSession = ref('sess_g001')
const chatInput = ref('')
const searchQuery = ref('')
const filterStatus = ref('all')

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
  { id: 'settings', icon: 'settings', label: '账户设置', path: '/settings' }
]

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
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n当前项目概览：\n• 📱 Candy Blast：消耗$52,300，ROI 1.88x\n• 📺 DramaBox：消耗$98,700，ROI 2.15x\n\n我可以帮您分析项目数据、优化投放策略。请告诉我您需要什么帮助？`
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

const projects = ref<Project[]>([])

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
    console.log('创建项目:', data)
    const newProject = await createProject(data)
    console.log('项目创建成功:', newProject)
    
    // 添加到项目列表
    projects.value.unshift(newProject)
    
    // 关闭弹窗并重置表单
    showCreateModal.value = false
    createModalRef.value?.resetForm()
  } catch (err: any) {
    console.error('创建项目失败:', err)
    alert(err.message || '创建项目失败，请重试')
  } finally {
    createModalRef.value?.setSubmitting(false)
  }
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return labels[status] || status
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

    <!-- 中间项目展示区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <h3 class="font-bold text-slate-900 dark:text-white">项目管理</h3>
        <button
          class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
          @click="handleCreateProject"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          <span class="text-sm font-medium">创建项目</span>
        </button>
      </div>

      <!-- Search & Filter Bar -->
      <div class="border-b border-slate-200 dark:border-slate-800 p-4">
        <div class="flex items-center gap-3">
          <div class="flex-1 relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索项目名称或标签..."
              class="w-full pl-10 pr-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
              @input="handleSearch"
            />
          </div>
          <select
            v-model="filterStatus"
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
            @change="handleSearch"
          >
            <option v-for="filter in statusFilters" :key="filter.value" :value="filter.value">
              {{ filter.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Projects List -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="grid gap-4">
          <div
            v-for="project in filteredProjects"
            :key="project.id"
            class="p-5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:border-primary/50 transition-all cursor-pointer"
          >
            <!-- Project Header -->
            <div class="flex items-start justify-between mb-4">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <h4 class="text-base font-semibold text-slate-900 dark:text-white">{{ project.name }}</h4>
                  <span
                    class="text-xs font-semibold px-2 py-0.5 rounded-full"
                    :class="getStatusColor(project.status)"
                  >
                    {{ getStatusLabel(project.status) }}
                  </span>
                </div>
                <div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">person</span>
                    {{ project.manager }}
                  </span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">calendar_today</span>
                    {{ project.start_date }} - {{ project.end_date }}
                  </span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">public</span>
                    {{ project.target_market }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Project Stats -->
            <div class="grid grid-cols-5 gap-4 mb-4">
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">预算</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.total_budget.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">${{ project.spent.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">进度</div>
                <div class="text-sm font-semibold text-emerald-600">{{ Math.round((project.spent / project.total_budget) * 100) }}%</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">类型</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.game_type }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">状态</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ getStatusLabel(project.status) }}</div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="mb-3">
              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>预算使用进度</span>
                <span>{{ Math.round((project.spent / project.total_budget) * 100) }}%</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-primary rounded-full transition-all"
                  :style="{ width: `${Math.round((project.spent / project.total_budget) * 100)}%` }"
                ></div>
              </div>
            </div>

            <!-- Tags -->
            <div class="flex items-center gap-2 flex-wrap mb-3">
              <span
                v-for="tag in project.tags"
                :key="tag"
                class="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
              >
                {{ tag }}
              </span>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 pt-3 border-t border-slate-200 dark:border-slate-700">
              <button
                class="flex-1 px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                @click="router.push(`/projects/${project.id}`)"
              >
                查看详情
              </button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredProjects.length === 0" class="flex flex-col items-center justify-center py-16">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">folder_off</span>
          <p class="text-sm text-slate-500 dark:text-slate-400">未找到匹配的项目</p>
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
  </div>
</template>
