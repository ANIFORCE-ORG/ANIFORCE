<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// --- 阶段控制 ---
type Phase = 'planning' | 'config'
const phase = ref<Phase>('planning')

// --- 对话相关 ---
interface ChatMsg {
  id: string
  role: 'user' | 'ai'
  content: string
  type: 'text' | 'planning-progress' | 'strategy-card' | 'config-card' | 'deploy-success'
}
const chatRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMsg[]>([])
const inputText = ref('')
const isPlanning = ref(false)
const planProgress = ref(0)
const planStage = ref('')

// --- 规划步骤 ---
const planSteps = ref([
  { label: '分析历史数据', detail: '10,000+ records, CTR 3.2%, CVR 5%', status: 'pending' },
  { label: '计算预算分配', detail: 'Meta $6,000, Google $4,000', status: 'pending' },
  { label: '优化广告组结构', detail: '', status: 'pending' },
  { label: '生成投放方案', detail: '', status: 'pending' },
])

// --- 策略 badges ---
const strategyBadges = [
  { label: 'Meta Nobid策略', sub: 'Bidding Mode', bg: 'bg-blue-50 dark:bg-blue-900/30', color: 'text-blue-700 dark:text-blue-300', border: 'border-blue-100 dark:border-blue-800' },
  { label: '60% Budget on Meta', sub: 'Budget Split', bg: 'bg-purple-50 dark:bg-purple-900/30', color: 'text-purple-700 dark:text-purple-300', border: 'border-purple-100 dark:border-purple-800' },
  { label: 'A/B Testing', sub: 'Methodology', bg: 'bg-blue-50 dark:bg-blue-900/30', color: 'text-blue-700 dark:text-blue-300', border: 'border-blue-100 dark:border-blue-800' },
  { label: '25-35 Male', sub: 'Targeting', bg: 'bg-indigo-50 dark:bg-indigo-900/30', color: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-100 dark:border-indigo-800' },
]

// --- 配置数据 ---
const configData = ref({
  basic: [
    { label: '游戏名称', value: '星辰霸主' },
    { label: '游戏类型', value: 'RPG' },
    { label: '投放周期', value: '7 Days' },
    { label: '投放市场', value: 'US / Europe' },
  ],
  targetROI: '200%',
  totalBudget: '$10,000',
  platforms: [
    { name: 'Meta', icon: 'smartphone', budget: '$4,000', pct: 40, strategy: 'Nobid Strategy', metric: 'CTR', metricVal: '4.1%', barColor: 'bg-[#1877F2]' },
    { name: 'Google', icon: 'search', budget: '$3,000', pct: 30, strategy: 'PMax Strategy', metric: 'CVR', metricVal: '5.2%', barColor: 'bg-[#EA4335]' },
    { name: 'TikTok', icon: 'play_circle', budget: '$2,000', pct: 20, strategy: 'Spark Ads', metric: '互动率', metricVal: '6.8%', barColor: 'bg-[#000000]' },
    { name: 'X', icon: 'tag', budget: '$1,000', pct: 10, strategy: 'Keyword Focus', metric: 'CPM', metricVal: '$4.50', barColor: 'bg-[#1D9BF0]' },
  ],
  audience: {
    age: { label: 'Age 25-35', pct: '65%', ctr: '3.5%' },
    gender: { label: 'Male', pct: '78%', ctr: '3.3%' },
    interests: [
      { label: 'RPG游戏', active: true },
      { label: '动作游戏', active: true },
      { label: '手机游戏', active: true },
      { label: '休闲游戏', active: false },
    ],
    regions: [
      { name: '美国 (US)', share: '40%', ctr: '3.4%', width: '40%', color: 'bg-primary' },
      { name: '英国 (UK)', share: '25%', ctr: '3.2%', width: '25%', color: 'bg-purple-500' },
      { name: '德国 (Germany)', share: '20%', ctr: '3.0%', width: '20%', color: 'bg-blue-400' },
    ],
    behaviors: [
      { label: '近 7 天活跃用户', bonus: '+0.8% CTR', color: 'text-emerald-500' },
      { label: '近 30 天曾下载 RPG', bonus: '+0.5% CTR', color: 'text-emerald-500' },
      { label: '有应用内付费历史', bonus: '+1.2% CVR', color: 'text-indigo-600 dark:text-indigo-400' },
    ],
  },
  nobid: {
    advantages: ['自动学习', '实时优化', '海量数据', 'RPG 强适配'],
    stats: [
      { value: '+15%', label: 'ROI 提升' },
      { value: '-80%', label: '运营时长' },
      { value: '-12%', label: '平均 CPA' },
    ],
    practices: [
      { num: '01', title: '预算门槛', desc: '建议日预算 ≥ $100，确保系统有充足样本' },
      { num: '02', title: '素材 A/B 测试', desc: '单组配置 5-10 套素材进行充分竞争' },
      { num: '03', title: '受众定向', desc: '聚焦 25-35 岁男性核心游戏玩家群体' },
      { num: '04', title: '投放时段', desc: '24/7 全天候投放，仅排除凌晨 2-6 AM 低效期' },
      { num: '05', title: '观察周期', desc: '至少保持 7 天观察期，严禁频繁修改' },
    ],
  },
  performance: [
    { label: '曝光量', value: '500k+', sub: 'Impressions', accent: false },
    { label: '点击量 (CTR)', value: '16k+', extra: '(3.2%)', sub: 'Clicks', accent: false },
    { label: '转化量 (CVR)', value: '800+', extra: '(5%)', sub: 'Conversions', accent: false },
    { label: '预估 ROI', value: '220%', sub: 'Estimated ROI', accent: true },
  ],
})

const isDeploying = ref(false)

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' })
    }
  })
}

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function simulatePlanning() {
  isPlanning.value = true

  // Step 1
  planStage.value = '正在分析同类RPG游戏投放数据...'
  planSteps.value[0].status = 'running'
  for (let i = 0; i <= 25; i += 5) { planProgress.value = i; await sleep(80) }
  planSteps.value[0].status = 'done'

  // Step 2
  planStage.value = '正在计算最佳预算分配...'
  planSteps.value[1].status = 'running'
  for (let i = 25; i <= 50; i += 5) { planProgress.value = i; await sleep(80) }
  planSteps.value[1].status = 'done'

  // Step 3
  planStage.value = '正在优化广告组结构...'
  planSteps.value[2].status = 'running'
  for (let i = 50; i <= 75; i += 5) { planProgress.value = i; await sleep(80) }
  planSteps.value[2].status = 'done'

  // Step 4
  planStage.value = '正在生成投放方案...'
  planSteps.value[3].status = 'running'
  for (let i = 75; i <= 100; i += 5) { planProgress.value = i; await sleep(60) }
  planSteps.value[3].status = 'done'

  isPlanning.value = false
  planStage.value = ''

  // AI strategy message
  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'ai',
    content: '📊 投放方案已生成！基于您的3条Boss战+福利素材，我为您制定了最优投放方案：',
    type: 'strategy-card',
  })
  scrollToBottom()

  await sleep(600)

  // Switch to config phase
  phase.value = 'config'
  messages.value.push({
    id: `msg-${Date.now() + 1}`,
    role: 'ai',
    content: '',
    type: 'config-card',
  })
  scrollToBottom()
}

async function handleSubmit() {
  if (!inputText.value.trim() || isPlanning.value || isDeploying.value) return
  const userMsg = inputText.value.trim()
  inputText.value = ''

  messages.value.push({ id: `msg-${Date.now()}`, role: 'user', content: userMsg, type: 'text' })
  scrollToBottom()

  await sleep(500)

  messages.value.push({ id: `msg-${Date.now()}`, role: 'ai', content: '', type: 'planning-progress' })
  scrollToBottom()

  await simulatePlanning()
}

async function handleConfirmDeploy() {
  isDeploying.value = true

  messages.value.push({ id: `msg-${Date.now()}`, role: 'user', content: '确认配置，开始投放', type: 'text' })
  scrollToBottom()

  await sleep(500)

  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'ai',
    content: '',
    type: 'deploy-success',
  })
  scrollToBottom()

  await sleep(3000)
  router.push('/monitor')
}

onMounted(() => {
  messages.value.push({
    id: 'welcome',
    role: 'ai',
    content: '欢迎进入投放计划配置！请描述您的投放需求，我将为您智能规划多平台投放方案。',
    type: 'text',
  })
})
</script>

<template>
  <div class="flex flex-1 flex-col relative overflow-hidden">
    <!-- Chat Area -->
    <main ref="chatRef" class="flex-1 overflow-y-auto p-4 md:p-8">
      <div class="max-w-5xl mx-auto space-y-6">
        <template v-for="msg in messages" :key="msg.id">
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[70%] bg-primary text-white px-6 py-3 rounded-3xl rounded-tr-none shadow-md text-sm font-medium whitespace-pre-line">
              {{ msg.content }}
            </div>
          </div>

          <!-- AI Text -->
          <div v-else-if="msg.type === 'text'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-xs font-bold text-slate-400">AI Marketing Agent</span>
            </div>
            <div class="ml-11 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-5 rounded-3xl shadow-sm max-w-2xl">
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed whitespace-pre-line">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Planning Progress -->
          <div v-else-if="msg.type === 'planning-progress'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-sm font-semibold text-slate-800 dark:text-slate-300">AI Marketing Agent</span>
            </div>
            <div class="ml-11 max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
              <div class="flex items-center justify-between mb-5">
                <div class="flex items-center gap-2">
                  <span class="text-xl">🎯</span>
                  <h3 class="text-sm font-bold text-slate-800 dark:text-white">AI 投放规划中...</h3>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-primary">{{ planProgress }}%</span>
                  <div class="w-32 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full bg-primary transition-all duration-300" :style="{ width: planProgress + '%' }"></div>
                  </div>
                </div>
              </div>
              <ul class="space-y-3">
                <li
                  v-for="step in planSteps"
                  :key="step.label"
                  class="flex items-center gap-3 text-xs font-medium"
                  :class="step.status === 'done'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : step.status === 'running'
                      ? 'text-primary'
                      : 'text-slate-400 dark:text-slate-500'"
                >
                  <span v-if="step.status === 'done'" class="material-symbols-outlined text-sm">check_circle</span>
                  <span v-else-if="step.status === 'running'" class="material-symbols-outlined text-sm animate-spin">sync</span>
                  <span v-else class="material-symbols-outlined text-sm">radio_button_unchecked</span>
                  <span>{{ step.label }}<template v-if="step.status === 'done' && step.detail"> ({{ step.detail }})</template></span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Strategy Card -->
          <div v-else-if="msg.type === 'strategy-card'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-sm font-semibold text-slate-800 dark:text-slate-300">AI Marketing Agent</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">刚刚</span>
            </div>
            <div class="ml-11 space-y-4">
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{{ msg.content }}</p>
              <!-- Strategy badges card -->
              <div class="border border-slate-200 dark:border-slate-800 p-8 rounded-3xl bg-white dark:bg-slate-900 shadow-md relative overflow-hidden">
                <div class="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -mr-10 -mt-10"></div>
                <div class="flex items-center gap-3 mb-8">
                  <div class="h-10 w-10 rounded-xl bg-primary text-white flex items-center justify-center">
                    <span class="material-symbols-outlined">auto_graph</span>
                  </div>
                  <div>
                    <h3 class="text-base font-bold text-slate-900 dark:text-white">核心策略建议 (Core Strategy)</h3>
                    <p class="text-xs text-slate-400 uppercase tracking-widest font-bold">Recommended Deployment</p>
                  </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div
                    v-for="b in strategyBadges"
                    :key="b.label"
                    class="flex flex-col items-center gap-1 px-3 py-3 rounded-lg text-xs font-bold border text-center"
                    :class="[b.bg, b.color, b.border]"
                  >
                    <span class="text-[10px] opacity-60 uppercase">{{ b.sub }}</span>
                    <span class="text-sm">{{ b.label }}</span>
                  </div>
                </div>
                <!-- Nobid explanation -->
                <div class="bg-slate-50 dark:bg-slate-800/50 p-6 rounded-xl border border-slate-100 dark:border-slate-700">
                  <div class="flex items-center gap-2 mb-3">
                    <span class="material-symbols-outlined text-primary text-lg">info</span>
                    <h4 class="text-sm font-bold text-slate-800 dark:text-white">为什么选择 Nobid 策略?</h4>
                  </div>
                  <ul class="space-y-2">
                    <li class="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <span class="text-primary mt-0.5">•</span>
                      <span><strong>高效率曝光：</strong>在初期快速覆盖潜在核心玩家，适合 Boss 战这种高冲击力素材。</span>
                    </li>
                    <li class="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <span class="text-primary mt-0.5">•</span>
                      <span><strong>ROI 优化：</strong>利用 Meta 的算法优势自动寻找最低转化成本，预计降低 15% 的初始获客成本。</span>
                    </li>
                    <li class="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <span class="text-primary mt-0.5">•</span>
                      <span><strong>动态调整：</strong>结合福利诱惑素材，系统会自动向展现出高活跃倾向的用户倾斜预算。</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- Config Card (投放方案详情) -->
          <div v-else-if="msg.type === 'config-card'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-sm font-semibold text-slate-800 dark:text-slate-300">AI Marketing Agent</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">刚刚</span>
            </div>
            <div class="ml-11 space-y-8">
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
                📊 投放方案已更新！基于您的素材库，我已完成多平台（Meta, Google, TikTok, X）的精细化配置，并为您同步生成了核心受众画像报告。
              </p>

              <!-- Main Config Card -->
              <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-xl overflow-hidden">
                <!-- Card Header -->
                <div class="px-8 py-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                  <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
                      <span class="material-symbols-outlined text-2xl">settings_applications</span>
                    </div>
                    <div>
                      <h3 class="text-lg font-bold text-slate-900 dark:text-white">多平台广告投放详细配置</h3>
                      <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider">Multi-Platform Campaign Configuration</p>
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <span class="px-3 py-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-[10px] font-bold rounded-full">AI 高可信度</span>
                    <span class="px-3 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 text-[10px] font-bold rounded-full">版本 v2.0</span>
                  </div>
                </div>

                <div class="p-8">
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-x-12 gap-y-10 mb-10">
                    <!-- Basic Info -->
                    <div>
                      <div class="flex items-center gap-2 mb-4 border-l-4 border-primary pl-3">
                        <h4 class="text-sm font-bold text-slate-800 dark:text-slate-200">基本信息</h4>
                      </div>
                      <div class="grid grid-cols-2 gap-4">
                        <div
                          v-for="item in configData.basic"
                          :key="item.label"
                          class="bg-slate-50 dark:bg-slate-800/30 p-3 rounded-xl border border-slate-100 dark:border-slate-800"
                        >
                          <p class="text-[10px] text-slate-400 mb-1">{{ item.label }}</p>
                          <p class="text-sm font-semibold text-slate-900 dark:text-white">{{ item.value }}</p>
                        </div>
                        <div class="col-span-2 bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-xl border border-blue-100 dark:border-blue-900/30">
                          <p class="text-[10px] text-blue-500 mb-1">目标 ROI</p>
                          <p class="text-base font-bold text-primary">{{ configData.targetROI }}</p>
                        </div>
                      </div>
                    </div>

                    <!-- Budget -->
                    <div>
                      <div class="flex items-center gap-2 mb-4 border-l-4 border-primary pl-3">
                        <h4 class="text-sm font-bold text-slate-800 dark:text-slate-200">预算分配</h4>
                      </div>
                      <div class="flex items-end justify-between mb-2">
                        <span class="text-xs text-slate-500">总预算</span>
                        <span class="text-xl font-poppins font-bold text-slate-900 dark:text-white">{{ configData.totalBudget }}</span>
                      </div>
                      <div class="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full flex overflow-hidden mb-4">
                        <div v-for="p in configData.platforms" :key="p.name" class="h-full" :class="p.barColor" :style="{ width: p.pct + '%' }"></div>
                      </div>
                      <div class="grid grid-cols-2 gap-2">
                        <div
                          v-for="p in configData.platforms"
                          :key="p.name"
                          class="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900"
                        >
                          <div class="flex items-center gap-1.5">
                            <span class="material-symbols-outlined text-sm text-slate-500">{{ p.icon }}</span>
                            <span class="text-xs font-medium text-slate-900 dark:text-white">{{ p.name }}</span>
                          </div>
                          <span class="text-xs font-bold text-slate-900 dark:text-white">{{ p.budget }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Ad Group Structure -->
                    <div class="lg:col-span-2">
                      <div class="flex items-center gap-2 mb-4 border-l-4 border-primary pl-3">
                        <h4 class="text-sm font-bold text-slate-800 dark:text-slate-200">广告组结构 (Ad Group Structure)</h4>
                      </div>
                      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div
                          v-for="p in configData.platforms"
                          :key="p.name"
                          class="border border-slate-100 dark:border-slate-800 rounded-2xl p-4 bg-white dark:bg-slate-900 shadow-sm"
                        >
                          <div class="flex items-center gap-2 mb-4">
                            <span class="material-symbols-outlined text-slate-500">{{ p.icon }}</span>
                            <div class="min-w-0">
                              <p class="text-sm font-bold truncate text-slate-900 dark:text-white">{{ p.name }} Ads</p>
                              <p class="text-[10px] text-slate-500">{{ p.strategy }}</p>
                            </div>
                          </div>
                          <div class="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                            <div class="flex justify-between items-center mb-1">
                              <span class="text-[10px] text-slate-500">分配预算</span>
                              <span class="text-xs font-bold text-slate-900 dark:text-white">{{ p.budget }}</span>
                            </div>
                            <div class="flex justify-between items-center">
                              <span class="text-[10px] text-slate-500">{{ p.metric }}</span>
                              <span class="text-xs font-bold text-emerald-500">{{ p.metricVal }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Audience Profile -->
                  <div class="mb-10">
                    <div class="flex items-center gap-2 mb-4 border-l-4 border-primary pl-3">
                      <h4 class="text-sm font-bold text-slate-800 dark:text-slate-200">RPG 游戏玩家画像 - 欧美市场</h4>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div class="space-y-6">
                        <!-- Core Audience -->
                        <div class="bg-slate-50 dark:bg-slate-800/30 rounded-2xl p-5 border border-slate-100 dark:border-slate-800">
                          <h5 class="text-xs font-bold text-slate-500 mb-4 flex items-center gap-2">
                            <span class="material-symbols-outlined text-primary text-sm">groups</span> 核心受众基础
                          </h5>
                          <div class="grid grid-cols-2 gap-4">
                            <div>
                              <p class="text-[10px] text-slate-400 mb-1">年龄段 ({{ configData.audience.age.label }})</p>
                              <div class="flex items-baseline gap-2">
                                <span class="text-lg font-bold text-slate-900 dark:text-white">{{ configData.audience.age.pct }}</span>
                                <span class="text-[10px] text-emerald-500 font-medium">{{ configData.audience.age.ctr }} CTR</span>
                              </div>
                            </div>
                            <div>
                              <p class="text-[10px] text-slate-400 mb-1">性别 ({{ configData.audience.gender.label }})</p>
                              <div class="flex items-baseline gap-2">
                                <span class="text-lg font-bold text-slate-900 dark:text-white">{{ configData.audience.gender.pct }}</span>
                                <span class="text-[10px] text-emerald-500 font-medium">{{ configData.audience.gender.ctr }} CTR</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <!-- Interest Tags -->
                        <div class="bg-slate-50 dark:bg-slate-800/30 rounded-2xl p-5 border border-slate-100 dark:border-slate-800">
                          <h5 class="text-xs font-bold text-slate-500 mb-3">兴趣标签 (Interest Tags)</h5>
                          <div class="flex flex-wrap gap-2">
                            <span
                              v-for="tag in configData.audience.interests"
                              :key="tag.label"
                              class="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-full"
                              :class="tag.active
                                ? 'bg-primary/10 text-primary'
                                : 'bg-slate-200/50 text-slate-400 font-medium'"
                            >
                              <span class="material-symbols-outlined text-sm">{{ tag.active ? 'check_circle' : 'cancel' }}</span>
                              {{ tag.label }}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div class="space-y-6">
                        <!-- Region Breakdown -->
                        <div class="bg-slate-50 dark:bg-slate-800/30 rounded-2xl p-5 border border-slate-100 dark:border-slate-800">
                          <h5 class="text-xs font-bold text-slate-500 mb-4 flex items-center gap-2">
                            <span class="material-symbols-outlined text-purple-500 text-sm">public</span> 地区细分 (Region Breakdown)
                          </h5>
                          <div class="space-y-4">
                            <div v-for="r in configData.audience.regions" :key="r.name">
                              <div class="flex justify-between text-[11px] mb-1.5">
                                <span class="font-bold text-slate-900 dark:text-white">{{ r.name }}</span>
                                <span class="text-slate-500">{{ r.share }} Share / {{ r.ctr }} CTR</span>
                              </div>
                              <div class="h-1.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div class="h-full" :class="r.color" :style="{ width: r.width }"></div>
                              </div>
                            </div>
                          </div>
                        </div>
                        <!-- Behavior Bonus -->
                        <div class="bg-indigo-50/50 dark:bg-indigo-900/10 rounded-2xl p-5 border border-indigo-100 dark:border-indigo-900/30">
                          <h5 class="text-xs font-bold text-indigo-600 dark:text-indigo-400 mb-3 flex items-center gap-2">
                            <span class="material-symbols-outlined text-sm">bolt</span> 行为特征加成
                          </h5>
                          <ul class="space-y-2">
                            <li v-for="b in configData.audience.behaviors" :key="b.label" class="flex items-center justify-between text-[11px]">
                              <span class="text-slate-600 dark:text-slate-400">{{ b.label }}</span>
                              <span class="font-bold" :class="b.color">{{ b.bonus }}</span>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Nobid Knowledge -->
                  <div class="lg:col-span-2 mb-10">
                    <div class="bg-gradient-to-br from-primary/5 to-purple-500/5 rounded-3xl border border-primary/10 p-6 md:p-8">
                      <div class="flex items-center gap-3 mb-6">
                        <div class="p-2 bg-primary rounded-lg text-white">
                          <span class="material-symbols-outlined text-xl">school</span>
                        </div>
                        <h4 class="text-lg font-bold text-slate-900 dark:text-white">游戏广告最佳策略: <span class="text-primary">Nobid 模式科普</span></h4>
                      </div>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div class="space-y-6">
                          <div>
                            <h5 class="text-sm font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-2">
                              <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>1. 什么是 Nobid？
                            </h5>
                            <p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed pl-3.5">
                              Nobid = No Bidding（无竞价上限）。在 Meta 投放中，系统会跳过手动设置出价门槛，由 AI 实时根据大盘波动自动寻找最优转化机会。
                            </p>
                          </div>
                          <div>
                            <h5 class="text-sm font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-2">
                              <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>2. 核心优势
                            </h5>
                            <div class="grid grid-cols-2 gap-2 pl-3.5">
                              <div
                                v-for="adv in configData.nobid.advantages"
                                :key="adv"
                                class="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800/50 py-1.5 px-2.5 rounded-lg border border-slate-100 dark:border-slate-800"
                              >
                                <span class="material-symbols-outlined text-emerald-500 text-sm">check_circle</span> {{ adv }}
                              </div>
                            </div>
                          </div>
                          <div class="bg-white/60 dark:bg-slate-800/60 p-4 rounded-2xl border border-white dark:border-slate-700">
                            <h5 class="text-xs font-bold text-slate-800 dark:text-slate-200 mb-3 flex items-center justify-between">
                              <span>3. 数据支撑 (100+ RPG 案例)</span>
                              <span class="text-[10px] font-normal text-slate-400">Nobid vs. 手动竞价</span>
                            </h5>
                            <div class="flex items-center justify-evenly">
                              <template v-for="(s, idx) in configData.nobid.stats" :key="s.label">
                                <div v-if="idx > 0" class="w-px h-8 bg-slate-200 dark:bg-slate-700"></div>
                                <div class="text-center flex-1">
                                  <p class="text-emerald-500 text-lg font-bold font-poppins">{{ s.value }}</p>
                                  <p class="text-[10px] text-slate-500">{{ s.label }}</p>
                                </div>
                              </template>
                            </div>
                          </div>
                        </div>
                        <div class="bg-primary/5 dark:bg-primary/10 rounded-2xl p-5 border border-primary/10">
                          <h5 class="text-sm font-bold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
                            <span class="material-symbols-outlined text-primary text-lg">verified</span>
                            4. 最佳实践 (Best Practices)
                          </h5>
                          <ul class="space-y-3">
                            <li v-for="p in configData.nobid.practices" :key="p.num" class="flex items-start gap-3">
                              <span class="text-primary font-bold text-xs mt-0.5">{{ p.num }}</span>
                              <div class="text-[11px] leading-relaxed">
                                <p class="font-bold text-slate-800 dark:text-slate-300">{{ p.title }}</p>
                                <p class="text-slate-500">{{ p.desc }}</p>
                              </div>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Expected Performance -->
                  <div>
                    <div class="flex items-center gap-2 mb-4 border-l-4 border-primary pl-3">
                      <h4 class="text-sm font-bold text-slate-800 dark:text-slate-200">预期效果 (Expected Performance)</h4>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div
                        v-for="perf in configData.performance"
                        :key="perf.label"
                        class="p-5 rounded-2xl text-center border"
                        :class="perf.accent
                          ? 'bg-emerald-500/10 border-emerald-500/20'
                          : 'bg-primary/5 dark:bg-primary/10 border-primary/20'"
                      >
                        <p class="text-xs mb-2" :class="perf.accent ? 'text-emerald-600' : 'text-slate-500'">{{ perf.label }}</p>
                        <p class="text-xl font-poppins font-bold" :class="perf.accent ? 'text-emerald-600' : 'text-slate-900 dark:text-white'">
                          {{ perf.value }}
                          <span v-if="perf.extra" class="text-xs font-normal opacity-60">{{ perf.extra }}</span>
                        </p>
                        <p class="text-[10px] mt-1" :class="perf.accent ? 'text-emerald-500' : 'text-emerald-500'">{{ perf.sub }}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Card Footer: Actions -->
                <div class="px-8 py-6 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex items-center justify-center gap-4">
                  <button
                    class="px-8 py-3.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-all flex items-center gap-2"
                    @click="router.push('/material')"
                  >
                    <span class="material-symbols-outlined text-xl">undo</span>
                    返回修改
                  </button>
                  <button
                    class="px-12 py-3.5 rounded-xl bg-primary text-white font-bold text-sm hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    :disabled="isDeploying"
                    @click="handleConfirmDeploy"
                  >
                    <span v-if="isDeploying" class="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <template v-else>确认投放 →</template>
                  </button>
                </div>
              </div>

              <!-- Multi-platform insight -->
              <div class="bg-slate-50 dark:bg-slate-800/50 p-6 rounded-3xl border border-slate-100 dark:border-slate-700 max-w-2xl">
                <div class="flex items-center gap-2 mb-3">
                  <span class="material-symbols-outlined text-primary text-lg">info</span>
                  <h4 class="text-sm font-bold text-slate-800 dark:text-white">多平台策略洞察</h4>
                </div>
                <ul class="space-y-2">
                  <li class="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                    <span class="text-primary mt-0.5">•</span>
                    <span><strong>矩阵优势：</strong>通过 TikTok 的病毒式传播配合 Google 的精准转化，形成完整的营销漏斗。</span>
                  </li>
                  <li class="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                    <span class="text-primary mt-0.5">•</span>
                    <span><strong>动态分配：</strong>AI 将根据首日表现，在四个平台间自动微调预算分配。</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Deploy Success -->
          <div v-else-if="msg.type === 'deploy-success'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-500">
                <span class="material-symbols-outlined text-lg">check_circle</span>
              </div>
              <span class="text-sm font-semibold text-slate-800 dark:text-slate-300">AI Marketing Agent</span>
            </div>
            <div class="ml-11 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30 p-6 rounded-3xl max-w-2xl">
              <h3 class="text-base font-bold text-emerald-700 dark:text-emerald-400 mb-4">🎉 投放计划创建成功！</h3>
              <div class="space-y-2 text-sm text-emerald-600 dark:text-emerald-400">
                <p>✅ Meta Ads: 已启动 (Nobid)</p>
                <p>✅ Google Ads: 已启动 (PMax)</p>
                <p>✅ TikTok Ads: 已启动 (Spark)</p>
                <p>✅ X Ads: 已启动 (Keyword)</p>
              </div>
              <p class="mt-4 text-xs text-emerald-500 font-medium animate-pulse">3秒后自动跳转到监控看板...</p>
            </div>
          </div>
        </template>
      </div>
    </main>

    <!-- Bottom Input Bar -->
    <div class="shrink-0 px-6 pb-4 pt-3 border-t border-slate-100 dark:border-slate-800 bg-background-light dark:bg-background-dark">
      <div class="max-w-4xl mx-auto">
        <div class="relative flex items-center bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-700 rounded-3xl px-5 py-3 shadow-2xl shadow-blue-500/10">
          <div class="flex items-center gap-2 mr-3 text-primary opacity-60">
            <span class="material-symbols-outlined text-2xl">auto_fix_high</span>
          </div>
          <input
            v-model="inputText"
            class="w-full bg-transparent border-none focus:ring-0 focus:outline-none text-sm placeholder:text-slate-400 font-medium py-1 text-slate-800 dark:text-slate-200"
            placeholder="在此输入后续指令，例如：'减少 Meta 预算'..."
            type="text"
            :disabled="isPlanning || isDeploying"
            @keydown.enter="handleSubmit"
          />
          <div class="flex items-center gap-2 ml-3">
            <button class="p-1.5 text-slate-400 hover:text-primary transition-colors">
              <span class="material-symbols-outlined text-lg">attach_file</span>
            </button>
            <button
              class="bg-primary text-white p-2 rounded-xl hover:bg-primary/90 transition-all shadow-lg flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isPlanning || isDeploying || !inputText.trim()"
              @click="handleSubmit"
            >
              <span class="material-symbols-outlined text-lg">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
