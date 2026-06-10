<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getDAL } from '@animagus/shared'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const inputText = ref('')
const loading = ref(false)
const hasInteracted = ref(false)

// 侧边栏相关状态
const activeSession = ref('sess_h001')
const chatInput = ref('')

const sessions = ref([
  { id: 'sess_h001', name: '新投放计划', active: true },
  { id: 'sess_h002', name: 'RPG游戏分析', active: false },
  { id: 'sess_h003', name: '素材优化建议', active: false },
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: '您好！我是ANIFORCE智能助手。\n\n我可以帮您分析市场趋势、生成创意素材、制定投放策略。请告诉我您的投放目标？'
  }
])

const quickHints = [
  '分析RPG游戏市场',
  '生成广告素材',
  '制定投放计划',
  '优化广告效果'
]

const analysisResult = ref<{
  session_id: string
  message: { role: string; content: string }
  analysis: {
    trends: Array<{ id: string; name: string; growth: number; description: string }>
    recommendations: Array<{ id: string; direction: string; ctr_estimate: number; tags: string[]; description: string }>
  }
} | null>(null)

const quickTags = [
  { emoji: '🎮', label: 'RPG游戏' },
  { emoji: '⚔️', label: '策略游戏' },
  { emoji: '🧩', label: '休闲游戏' },
]

const toolCards = [
  {
    icon: 'analytics',
    iconBg: 'bg-blue-50 dark:bg-blue-900/30',
    iconColor: 'text-primary',
    title: '市场洞察分析',
    desc: '分析竞品趋势与全球买量大盘，制定投放策略。',
    path: '/market-analysis',
  },
  {
    icon: 'auto_awesome',
    iconBg: 'bg-purple-50 dark:bg-purple-900/30',
    iconColor: 'text-purple-600 dark:text-purple-400',
    title: 'AI 素材生成',
    desc: '快速生成广告脚本、视频素材与高质量创意海报。',
    path: '/material',
  },
  {
    icon: 'campaign',
    iconBg: 'bg-emerald-50 dark:bg-emerald-900/30',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    title: '快速建站投放',
    desc: '一键同步至多渠道广告平台，自动化管理您的预算。',
    path: '/campaign',
  },
  {
    icon: 'monitoring',
    iconBg: 'bg-orange-50 dark:bg-orange-900/30',
    iconColor: 'text-orange-600 dark:text-orange-400',
    title: '投放表现追踪',
    desc: '多维度看板实时监控 ROAS 与玩家 LTV 数据表现。',
    path: '/monitor',
  },
]

const hasContent = computed(() => loading.value || analysisResult.value !== null)

function scrollToBottom() {
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

async function handleSubmit() {
  if (!inputText.value.trim() || loading.value) return
  hasInteracted.value = true
  loading.value = true
  analysisResult.value = null
  scrollToBottom()
  try {
    const dal = getDAL()
    const gameType = quickTags.find(t => inputText.value.includes(t.label))?.label || 'RPG'
    const res = await dal.chat.analyzeGame(inputText.value, gameType)
    if (res.success && res.data) {
      analysisResult.value = res.data
      scrollToBottom()
    }
  } catch (e) {
    console.error('分析失败:', e)
  } finally {
    loading.value = false
  }
}

function handleTagClick(tag: string) {
  inputText.value = tag
}

function navigateTo(path: string) {
  router.push(path)
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
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="flex-1 overflow-y-auto">
        <div class="flex flex-col items-center px-4 pb-8">
    <!-- Top spacer: pushes content to center when no output -->
    <div v-if="!hasContent" class="flex-1 min-h-[120px]"></div>

    <!-- Greeting -->
    <div
      class="max-w-[800px] w-full text-center space-y-6 transition-all duration-500"
      :class="hasContent ? 'pt-8 mb-6 opacity-50 scale-[0.92]' : 'mb-12'"
    >
      <h1 class="text-slate-900 dark:text-white text-4xl md:text-5xl font-poppins font-semibold tracking-tight">
        又见面啦！有新的投放计划吗？
      </h1>
      <p class="text-slate-500 dark:text-slate-400 text-lg">
        利用 AI 驱动的见解和素材生成，快速启动您的下一个全球营销活动。
      </p>
    </div>

    <!-- Output Content Area (above the input bar, only when has content) -->
    <div v-if="hasContent" class="max-w-[1080px] w-full px-4 space-y-6 mb-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center gap-3 py-8">
        <div class="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span class="text-slate-500 text-sm">AI 正在分析中，请稍候...</span>
      </div>

      <!-- Analysis Result -->
      <template v-if="analysisResult">
        <!-- AI Message -->
        <div class="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <div class="flex items-start gap-3">
            <div class="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              <span class="material-symbols-outlined text-primary text-sm">smart_toy</span>
            </div>
            <p class="text-slate-700 dark:text-slate-300 leading-relaxed">{{ analysisResult.message.content }}</p>
          </div>
        </div>

        <!-- Trends -->
        <div>
          <h3 class="text-lg font-bold mb-4 dark:text-white">
            <span class="material-symbols-outlined text-primary align-middle mr-1">trending_up</span>
            市场热点趋势
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div
              v-for="trend in analysisResult.analysis.trends"
              :key="trend.id"
              class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-primary/50 transition-all"
            >
              <div class="flex items-center justify-between mb-2">
                <h4 class="font-semibold text-slate-900 dark:text-white">{{ trend.name }}</h4>
                <span class="text-xs font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded-full">
                  +{{ trend.growth }}%
                </span>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400">{{ trend.description }}</p>
            </div>
          </div>
        </div>

        <!-- Recommendations -->
        <div>
          <h3 class="text-lg font-bold mb-4 dark:text-white">
            <span class="material-symbols-outlined text-primary align-middle mr-1">lightbulb</span>
            推荐素材方向
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div
              v-for="rec in analysisResult.analysis.recommendations"
              :key="rec.id"
              class="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group"
            >
              <div class="flex items-center justify-between mb-2">
                <h4 class="font-semibold text-slate-900 dark:text-white group-hover:text-primary transition-colors">{{ rec.direction }}</h4>
                <span class="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded-full">
                  CTR {{ rec.ctr_estimate }}%
                </span>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">{{ rec.description }}</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tag in rec.tags"
                  :key="tag"
                  class="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Floating Command Bar (always below output content) -->
    <div class="max-w-[860px] w-full px-4 mb-6">
      <div class="relative group">
        <!-- Glow effect -->
        <div class="absolute -inset-1 bg-gradient-to-r from-primary/20 to-blue-400/20 rounded-full blur opacity-25 group-focus-within:opacity-100 transition duration-1000 group-hover:duration-200"></div>
        <!-- Input bar -->
        <div class="relative flex items-center bg-white dark:bg-slate-900 rounded-full border border-slate-200 dark:border-slate-700 shadow-xl shadow-slate-200/50 dark:shadow-none p-2 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
          <button class="flex items-center justify-center p-3 text-slate-400 hover:text-primary transition-colors">
            <span class="material-symbols-outlined">attach_file</span>
          </button>
          <input
            v-model="inputText"
            class="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-lg text-slate-800 dark:text-slate-200 placeholder:text-slate-400 py-3 px-2"
            placeholder="描述您的投放目标或上传素材..."
            type="text"
            @keydown.enter="handleSubmit"
          />
          <div class="flex items-center gap-2 pr-2">
            <button class="flex items-center justify-center p-3 text-slate-400 hover:text-primary transition-colors">
              <span class="material-symbols-outlined">mic</span>
            </button>
            <button
              class="bg-primary text-white h-12 w-12 rounded-full flex items-center justify-center hover:bg-primary/90 transition-all shadow-lg shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="loading || !inputText.trim()"
              @click="handleSubmit"
            >
              <span v-if="loading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span v-else class="material-symbols-outlined">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Create Material Button (only show after interaction) -->
      <button
        v-if="hasInteracted"
        class="w-full mt-3 py-3 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-sm font-medium hover:bg-slate-300 dark:hover:bg-slate-600 hover:text-primary transition-all cursor-pointer"
        @click="navigateTo('/material')"
      >
        开始创建素材
      </button>

      <!-- Quick Tags (hide after interaction) -->
      <div v-if="!hasContent" class="flex flex-wrap justify-center gap-3 mt-6">
        <button
          v-for="tag in quickTags"
          :key="tag.label"
          class="flex items-center gap-2 px-5 py-2 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-primary hover:text-primary transition-all shadow-sm"
          @click="handleTagClick(tag.label)"
        >
          <span class="text-lg">{{ tag.emoji }}</span>
          <span class="text-sm font-medium">{{ tag.label }}</span>
        </button>
      </div>
    </div>

    <!-- Tool Cards (only show when no content) -->
    <div v-if="!hasContent && !hasInteracted" class="w-full max-w-[1080px] mt-8">
      <div class="flex items-center justify-between px-6 mb-6">
        <h3 class="text-lg font-bold dark:text-white">推荐工具</h3>
        <!--  <a class="text-sm font-semibold text-primary hover:underline" href="#">查看全部</a> -->
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 px-4">
        <div
          v-for="card in toolCards"
          :key="card.title"
          class="group bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all cursor-pointer"
          @click="navigateTo(card.path)"
        >
          <div
            class="h-12 w-12 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
            :class="[card.iconBg, card.iconColor]"
          >
            <span class="material-symbols-outlined">{{ card.icon }}</span>
          </div>
          <h4 class="font-bold text-slate-900 dark:text-white mb-2">{{ card.title }}</h4>
          <p class="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{{ card.desc }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom spacer: pushes content to center when no output -->
    <div v-if="!hasContent" class="flex-1"></div>
        </div>
      </div>
    </main>
  </div>
</template>
