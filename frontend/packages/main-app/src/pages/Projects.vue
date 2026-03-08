<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'

const router = useRouter()
const auth = useAuthStore()

const activePanel = ref('projects')
const activeSession = ref('sess_g001')
const chatInput = ref('')
const searchQuery = ref('')
const filterStatus = ref('all')

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'campaign', label: '广告投放', path: '/campaigns' },
  { id: 'materials', icon: 'auto_awesome', label: '创意素材', path: '/materials' },
  { id: 'reports', icon: 'analytics', label: '数据报表', path: '/reports' },
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

const projects = ref([
  {
    id: 'proj_001',
    name: 'Candy Blast - 全球推广',
    status: 'active',
    platform: 'Meta',
    budget: '$80,000',
    spent: '$52,300',
    roi: '1.88x',
    installs: '15,420',
    cpi: '$3.39',
    progress: 65,
    startDate: '2024-01-15',
    endDate: '2024-03-15',
    manager: '李明',
    tags: ['休闲游戏', '三消', '北美']
  },
  {
    id: 'proj_002',
    name: 'DramaBox - 东南亚市场',
    status: 'active',
    platform: 'TikTok',
    budget: '$120,000',
    spent: '$98,700',
    roi: '2.15x',
    installs: '28,350',
    cpi: '$3.48',
    progress: 82,
    startDate: '2024-01-10',
    endDate: '2024-04-10',
    manager: '王芳',
    tags: ['短剧', '娱乐', '东南亚']
  },
  {
    id: 'proj_003',
    name: 'Puzzle Master - 欧洲测试',
    status: 'paused',
    platform: 'Google Ads',
    budget: '$50,000',
    spent: '$12,500',
    roi: '1.45x',
    installs: '4,200',
    cpi: '$2.98',
    progress: 25,
    startDate: '2024-02-01',
    endDate: '2024-05-01',
    manager: '张伟',
    tags: ['益智', '休闲', '欧洲']
  },
  {
    id: 'proj_004',
    name: 'Racing Fever - 全球发行',
    status: 'active',
    platform: 'Unity Ads',
    budget: '$150,000',
    spent: '$45,800',
    roi: '2.32x',
    installs: '18,900',
    cpi: '$2.42',
    progress: 31,
    startDate: '2024-02-15',
    endDate: '2024-06-15',
    manager: '李明',
    tags: ['竞速', '重度', '全球']
  },
])

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleSendMessage = () => {
  if (!chatInput.value.trim()) return
  console.log('发送消息:', chatInput.value)
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
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

const filteredProjects = ref(projects.value)

const handleSearch = () => {
  let result = projects.value
  
  if (searchQuery.value) {
    result = result.filter(p => 
      p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      p.tags.some(tag => tag.includes(searchQuery.value))
    )
  }
  
  if (filterStatus.value !== 'all') {
    result = result.filter(p => p.status === filterStatus.value)
  }
  
  filteredProjects.value = result
}

const handleCreateProject = () => {
  console.log('创建新项目')
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
                    {{ project.startDate }} - {{ project.endDate }}
                  </span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">ads_click</span>
                    {{ project.platform }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Project Stats -->
            <div class="grid grid-cols-5 gap-4 mb-4">
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">预算</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.budget }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">已消耗</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.spent }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">ROI</div>
                <div class="text-sm font-semibold text-emerald-600">{{ project.roi }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">安装数</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.installs }}</div>
              </div>
              <div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">CPI</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ project.cpi }}</div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="mb-3">
              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>预算使用进度</span>
                <span>{{ project.progress }}%</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-primary rounded-full transition-all"
                  :style="{ width: `${project.progress}%` }"
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
    <aside class="w-96 bg-slate-50 dark:bg-slate-900/50 border-l border-slate-200 dark:border-slate-800 flex flex-col">
      <!-- Chat Header -->
      <div class="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">chat</span>
          <span class="font-semibold text-slate-900 dark:text-white">AI智能助手</span>
        </div>
        <button class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors">
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">add</span>
        </button>
      </div>

      <!-- Chat Messages -->
      <div class="flex-1 overflow-y-auto p-6">
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="mb-6 flex gap-4"
        >
          <!-- Avatar -->
          <div class="h-10 w-10 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
          </div>
          <!-- Message Content -->
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ message.author }}</span>
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ message.time }}</span>
            </div>
            <div class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">{{ message.content }}</div>
          </div>
        </div>
      </div>

      <!-- Chat Input Area -->
      <div class="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-4">
        <div class="space-y-3">
          <!-- Input Wrapper -->
          <div class="flex items-end gap-3">
            <textarea
              v-model="chatInput"
              class="flex-1 resize-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="输入您的问题或需求..."
              rows="1"
              @keydown.enter.prevent="handleSendMessage"
            ></textarea>
            <button
              class="h-10 w-10 rounded-md bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors flex-shrink-0"
              @click="handleSendMessage"
            >
              <span class="material-symbols-outlined text-xl">send</span>
            </button>
          </div>
          <!-- Quick Hints -->
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs text-slate-500 dark:text-slate-400">试试：</span>
            <button
              v-for="hint in quickHints"
              :key="hint"
              class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              @click="handleHintClick(hint)"
            >
              {{ hint }}
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
