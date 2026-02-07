<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  type: 'text' | 'strategy' | 'progress' | 'materials' | 'steps'
  data?: any
}

const inputText = ref('')
const chatRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMessage[]>([])
const isGenerating = ref(false)
const generationProgress = ref(0)
const generationStage = ref('')
const selectedMaterials = ref<Set<string>>(new Set())

// ABC 三段式步骤
const abcSteps = ref([
  { key: 'A', label: 'Intro Hook', desc: '黄金3秒', status: 'pending', count: 0 },
  { key: 'B', label: 'Gameplay', desc: '核心展示', status: 'pending', count: 0 },
  { key: 'C', label: 'Outro CTA', desc: '转化下载', status: 'pending', count: 0 },
])

// Mock 素材数据
const materials = ref<Array<{
  id: string
  name: string
  duration: string
  ctr: number
  tags: string[]
}>>([])

// Mock 策略数据
const strategyData = ref({
  targeting: [
    { icon: 'videogame_asset', label: '高技巧玩家', desc: '强调操作反馈', bg: 'bg-blue-50 dark:bg-blue-900/30', color: 'text-blue-600 dark:text-blue-400' },
    { icon: 'bolt', label: '视觉冲击', desc: '3秒必杀技Hook', bg: 'bg-purple-50 dark:bg-purple-900/30', color: 'text-purple-600 dark:text-purple-400' },
  ],
  concepts: [
    { icon: 'palette', label: 'Retro 8-bit Boss Fight', desc: '怀旧像素滤镜' },
    { icon: 'music_note', label: 'Epic Orchestra BGM', desc: '史诗交响乐' },
  ],
  outputs: [
    { icon: 'movie', label: 'Boss Intros (A段)', count: 10, bg: 'bg-orange-100 dark:bg-orange-900/30', color: 'text-orange-600 dark:text-orange-400' },
    { icon: 'featured_video', label: 'Reward Animations (C段)', count: 10, bg: 'bg-emerald-100 dark:bg-emerald-900/30', color: 'text-emerald-600 dark:text-emerald-400' },
    { icon: 'touch_app', label: 'CTA Buttons', count: 10, bg: 'bg-blue-100 dark:bg-blue-900/30', color: 'text-blue-600 dark:text-blue-400' },
  ],
})

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' })
    }
  })
}

function toggleMaterial(id: string) {
  if (selectedMaterials.value.has(id)) {
    selectedMaterials.value.delete(id)
  } else {
    selectedMaterials.value.add(id)
  }
  selectedMaterials.value = new Set(selectedMaterials.value)
}

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function simulateGeneration() {
  isGenerating.value = true

  // 阶段1: A段生成
  generationStage.value = '正在生成 A段 Boss战开场视频序列...'
  abcSteps.value[0].status = 'running'
  for (let i = 0; i <= 30; i += 5) {
    generationProgress.value = i
    await sleep(100)
  }
  abcSteps.value[0].status = 'done'
  abcSteps.value[0].count = 10
  scrollToBottom()

  // 阶段2: B段等待
  generationStage.value = 'B段等待中，使用默认游戏玩法素材...'
  abcSteps.value[1].status = 'running'
  for (let i = 30; i <= 45; i += 3) {
    generationProgress.value = i
    await sleep(80)
  }
  abcSteps.value[1].status = 'done'
  abcSteps.value[1].count = 1
  scrollToBottom()

  // 阶段3: C段生成
  generationStage.value = '正在生成 C段 福利奖励动画与CTA...'
  abcSteps.value[2].status = 'running'
  for (let i = 45; i <= 75; i += 5) {
    generationProgress.value = i
    await sleep(100)
  }
  abcSteps.value[2].status = 'done'
  abcSteps.value[2].count = 10
  scrollToBottom()

  // 阶段4: 自动拼装
  generationStage.value = '正在自动拼装完整素材...'
  for (let i = 75; i <= 100; i += 5) {
    generationProgress.value = i
    await sleep(80)
  }

  // 生成素材列表
  materials.value = Array.from({ length: 10 }, (_, i) => ({
    id: `v-${String(i + 1).padStart(2, '0')}`,
    name: ['Boss Intro', 'Retro Combat', 'Dark Elite', 'Skill Hook', 'Loot Chest', 'Epic Raid', 'Dragon Fury', 'Guild War', 'Arena Clash', 'Final Boss'][i],
    duration: '15s',
    ctr: +(2.5 + Math.random() * 1.2).toFixed(1),
    tags: [['#暗色调', '#Boss挑战'], ['#复古像素', '#快节奏'], ['#暗色调', '#视觉冲击'], ['#红金色', '#技能展示'], ['#亮色调', '#福利诱惑'], ['#暗色调', '#Boss挑战'], ['#红金色', '#史诗感'], ['#社交分享', '#组队'], ['#快节奏', '#竞技'], ['#暗色调', '#终极Boss']][i],
  }))

  isGenerating.value = false
  generationStage.value = ''

  // 添加完成消息
  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'ai',
    content: '素材生成完成！已为您生成 10 条素材，请在下方预览并选择 3-5 条用于投放。',
    type: 'materials',
  })
  scrollToBottom()
}

async function handleSubmit() {
  if (!inputText.value.trim() || isGenerating.value) return

  const userMsg = inputText.value.trim()
  inputText.value = ''

  // 添加用户消息
  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'user',
    content: userMsg,
    type: 'text',
  })
  scrollToBottom()

  await sleep(500)

  // AI 分析回复
  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'ai',
    content: `收到！开始为您生成素材。基于市场分析，我将重点围绕 **"Boss挑战"** 和 **"高技巧受众"** 构建创意脚本，强调硬核动作感。`,
    type: 'strategy',
  })
  scrollToBottom()

  await sleep(800)

  // 开始生成
  messages.value.push({
    id: `msg-${Date.now()}`,
    role: 'ai',
    content: '',
    type: 'progress',
  })
  scrollToBottom()

  await simulateGeneration()
}

onMounted(() => {
  // 初始欢迎消息
  messages.value.push({
    id: 'welcome',
    role: 'ai',
    content: '欢迎来到素材生成工作台！请描述您的目标受众和创意方向，我将为您生成 ABC 三段式广告素材。',
    type: 'text',
  })
})
</script>

<template>
  <div class="flex flex-1 flex-col relative overflow-hidden">
    <!-- Chat Area -->
    <main ref="chatRef" class="flex-1 overflow-y-auto p-4 md:p-8">
      <div class="max-w-5xl mx-auto space-y-6">
        <!-- Messages -->
        <template v-for="msg in messages" :key="msg.id">
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[70%] bg-primary text-white px-6 py-3 rounded-3xl rounded-tr-none shadow-md text-sm font-medium">
              {{ msg.content }}
            </div>
          </div>

          <!-- AI Text Message -->
          <div v-else-if="msg.type === 'text'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-xs font-bold text-slate-400">ANIMAGUS Agent</span>
            </div>
            <div class="ml-11 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-5 rounded-3xl shadow-sm max-w-2xl">
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{{ msg.content }}</p>
            </div>
          </div>

          <!-- AI Strategy Card -->
          <div v-else-if="msg.type === 'strategy'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-sm font-bold text-slate-800 dark:text-slate-200">AI Creative Engine</span>
            </div>
            <div class="ml-11">
              <p class="text-slate-800 dark:text-slate-200 text-base font-medium leading-relaxed mb-4" v-html="msg.content.replace(/\*\*(.*?)\*\*/g, '<span class=\'text-primary font-bold\'>$1</span>')"></p>
            </div>

            <!-- Strategy Card -->
            <div class="ml-11 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-3xl shadow-xl overflow-hidden">
              <!-- Header -->
              <div class="px-8 py-5 border-b border-slate-50 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-primary text-xl">movie_filter</span>
                  </div>
                  <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">素材定位与生成策略</h3>
                </div>
                <span class="text-[10px] font-bold text-slate-400 bg-white dark:bg-slate-800 px-3 py-1 rounded-full border border-slate-100 dark:border-slate-700 uppercase tracking-widest">Job #AM-RPG-0042</span>
              </div>

              <div class="p-8">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 mb-10">
                  <!-- Left: Targeting & Concepts -->
                  <div class="space-y-8">
                    <div>
                      <div class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        Targeting Logic <span class="h-px flex-1 bg-slate-100 dark:bg-slate-700"></span>
                      </div>
                      <div class="grid grid-cols-2 gap-4">
                        <div
                          v-for="t in strategyData.targeting"
                          :key="t.label"
                          class="rounded-2xl p-4 border flex items-center gap-3"
                          :class="[t.bg, 'border-slate-100 dark:border-slate-700']"
                        >
                          <div class="w-10 h-10 rounded-full bg-white dark:bg-slate-800 shadow-sm flex items-center justify-center" :class="t.color">
                            <span class="material-symbols-outlined text-xl">{{ t.icon }}</span>
                          </div>
                          <div>
                            <div class="text-xs font-bold text-slate-700 dark:text-slate-300">{{ t.label }}</div>
                            <div class="text-[10px] text-slate-500">{{ t.desc }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div>
                      <div class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        Creative Concepts <span class="h-px flex-1 bg-slate-100 dark:bg-slate-700"></span>
                      </div>
                      <div class="space-y-3">
                        <div
                          v-for="c in strategyData.concepts"
                          :key="c.label"
                          class="flex items-center justify-between p-3.5 rounded-2xl border border-slate-100 dark:border-slate-700 hover:border-primary/20 hover:bg-blue-50/10 transition-all group"
                        >
                          <div class="flex items-center gap-3">
                            <span class="material-symbols-outlined text-slate-400 group-hover:text-primary transition-colors">{{ c.icon }}</span>
                            <span class="text-sm font-bold text-slate-700 dark:text-slate-300">{{ c.label }}</span>
                          </div>
                          <span class="text-[10px] text-slate-400 font-medium">{{ c.desc }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Right: Planned Outputs -->
                  <div>
                    <div class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                      Planned Outputs <span class="h-px flex-1 bg-slate-100 dark:bg-slate-700"></span>
                    </div>
                    <div class="bg-slate-50/50 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-100 dark:border-slate-700 space-y-6">
                      <div v-for="o in strategyData.outputs" :key="o.label" class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                          <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="[o.bg, o.color]">
                            <span class="material-symbols-outlined text-lg">{{ o.icon }}</span>
                          </div>
                          <span class="text-sm font-bold text-slate-700 dark:text-slate-300">{{ o.label }}</span>
                        </div>
                        <span class="text-sm font-poppins font-bold text-slate-400">× {{ o.count }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- ABC Flow -->
                <div class="mb-6 pt-6 border-t border-slate-100 dark:border-slate-800">
                  <div class="text-[10px] font-bold text-slate-400 uppercase text-center mb-6 tracking-widest">ABC Material Structure Flow</div>
                  <div class="flex items-center justify-between max-w-2xl mx-auto relative px-4">
                    <div class="absolute top-5 left-0 right-0 h-[2px] bg-slate-100 dark:bg-slate-700 -z-0"></div>
                    <div v-for="step in abcSteps" :key="step.key" class="relative z-10 flex flex-col items-center gap-3">
                      <div
                        class="w-12 h-12 rounded-2xl flex items-center justify-center font-bold shadow-lg transition-all duration-300"
                        :class="step.status === 'done'
                          ? 'bg-emerald-500 text-white shadow-emerald-500/20'
                          : step.status === 'running'
                            ? 'bg-primary text-white shadow-primary/20 animate-pulse'
                            : 'bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-600 text-slate-400'"
                      >
                        <span v-if="step.status === 'done'" class="material-symbols-outlined">check</span>
                        <span v-else>{{ step.key }}</span>
                      </div>
                      <div class="text-center">
                        <div class="text-xs font-bold text-slate-800 dark:text-slate-200">{{ step.label }}</div>
                        <div class="text-[10px] text-slate-400">{{ step.desc }}</div>
                      </div>
                    </div>
                    <!-- Arrows -->
                    <span class="material-symbols-outlined text-slate-300 absolute left-[30%] top-3 z-10">chevron_right</span>
                    <span class="material-symbols-outlined text-slate-300 absolute left-[62%] top-3 z-10">chevron_right</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- AI Progress Message -->
          <div v-else-if="msg.type === 'progress' && isGenerating" class="ml-11">
            <div class="bg-purple-50/50 dark:bg-purple-900/20 rounded-2xl p-6 border border-purple-100 dark:border-purple-800/30">
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-3">
                  <div class="w-6 h-6 border-2 border-purple-300 dark:border-purple-600 border-t-purple-600 dark:border-t-purple-400 rounded-full animate-spin"></div>
                  <span class="text-sm font-bold text-purple-600 dark:text-purple-400">正在为您生成...</span>
                </div>
                <span class="text-xs font-bold text-purple-600 dark:text-purple-400">{{ generationProgress }}%</span>
              </div>
              <div class="w-full h-2 bg-purple-100 dark:bg-purple-900/30 rounded-full overflow-hidden">
                <div
                  class="h-full bg-purple-500 rounded-full shadow-[0_0_10px_rgba(139,92,246,0.5)] transition-all duration-300"
                  :style="{ width: generationProgress + '%' }"
                ></div>
              </div>
              <p class="mt-3 text-[11px] text-slate-500 dark:text-slate-400">{{ generationStage }}</p>
            </div>
          </div>

          <!-- AI Materials Result -->
          <div v-else-if="msg.type === 'materials'" class="flex flex-col gap-3">
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined text-lg">smart_toy</span>
              </div>
              <span class="text-xs font-bold text-slate-400">ANIMAGUS Agent</span>
            </div>
            <div class="ml-11 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-5 rounded-3xl shadow-sm max-w-2xl mb-2">
              <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">{{ msg.content }}</p>
            </div>

            <!-- Tags -->
            <div class="ml-11 flex flex-wrap items-center gap-3 mb-2">
              <div class="flex items-center gap-2 px-3 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-full text-[11px] font-bold text-slate-600 dark:text-slate-400">
                <span>🎨 Style:</span>
                <span class="text-primary">#Dark</span>
                <span class="text-purple-500">#Red-Gold</span>
              </div>
              <div class="flex items-center gap-2 px-3 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-full text-[11px] font-bold text-slate-600 dark:text-slate-400">
                <span>⚡ Content:</span>
                <span class="text-primary">#Boss</span>
                <span class="text-purple-500">#Rewards</span>
              </div>
              <div class="flex items-center gap-2 px-3 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-full text-[11px] font-bold text-slate-600 dark:text-slate-400">
                <span>🎯 Pacing:</span>
                <span class="text-primary">#Fast</span>
                <span class="text-purple-500">#Medium</span>
              </div>
            </div>

            <!-- Material Thumbnails -->
            <div class="ml-11 overflow-x-auto pb-4">
              <div class="flex gap-4 min-w-max">
                <div
                  v-for="m in materials"
                  :key="m.id"
                  class="w-32 aspect-[9/16] rounded-2xl border overflow-hidden relative group cursor-pointer shadow-sm hover:shadow-lg transition-all hover:-translate-y-1"
                  :class="selectedMaterials.has(m.id)
                    ? 'border-primary ring-2 ring-primary/30'
                    : 'border-slate-200 dark:border-slate-700'"
                  @click="toggleMaterial(m.id)"
                >
                  <div class="w-full h-full bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center">
                    <span class="material-symbols-outlined text-4xl text-slate-400 dark:text-slate-500">movie</span>
                  </div>
                  <!-- Play button -->
                  <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div class="w-8 h-8 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center text-primary">
                      <span class="material-symbols-outlined">play_arrow</span>
                    </div>
                  </div>
                  <!-- Selection indicator -->
                  <div v-if="selectedMaterials.has(m.id)" class="absolute top-2 right-2 w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center">
                    <span class="material-symbols-outlined text-sm">check</span>
                  </div>
                  <!-- Info -->
                  <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                    <div class="text-[9px] font-bold text-white">{{ m.id.toUpperCase() }}: {{ m.name }}</div>
                    <div class="flex items-center justify-between mt-0.5">
                      <span class="text-[8px] text-white/70">{{ m.duration }}</span>
                      <span class="text-[8px] font-bold text-emerald-300">CTR {{ m.ctr }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Selection Status -->
            <div class="ml-11 flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
              <div class="flex items-center gap-3">
                <span class="text-sm font-bold text-slate-700 dark:text-slate-300">
                  已选择 {{ selectedMaterials.size }} 条素材
                </span>
                <span v-if="selectedMaterials.size < 3" class="text-xs text-orange-500 font-medium">⚠️ 最少需选择 3 条</span>
                <span v-else class="text-xs text-emerald-500 font-medium">✅ 可以进入下一步</span>
              </div>
              <div class="flex items-center gap-3">
                <button class="px-4 py-2 text-xs font-bold text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl hover:border-primary hover:text-primary transition-all">
                  预览选中素材
                </button>
                <button
                  class="px-4 py-2 text-xs font-bold text-white rounded-xl transition-all"
                  :class="selectedMaterials.size >= 3
                    ? 'bg-primary hover:bg-primary/90 shadow-lg shadow-primary/30'
                    : 'bg-slate-300 dark:bg-slate-600 cursor-not-allowed'"
                  :disabled="selectedMaterials.size < 3"
                  @click="router.push('/campaign')"
                >
                  下一步 →
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </main>

    <!-- Bottom Input Bar (flex shrink-0, isolated from chat scroll) -->
    <div class="shrink-0 px-6 pb-4 pt-3 border-t border-slate-100 dark:border-slate-800 bg-background-light dark:bg-background-dark">
      <div class="max-w-4xl mx-auto">
        <!-- Input Bar -->
        <div class="relative flex items-center bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-700 rounded-3xl px-5 py-3 shadow-2xl shadow-blue-500/10">
          <div class="flex items-center gap-2 mr-3 text-primary opacity-60">
            <span class="material-symbols-outlined text-2xl">magic_button</span>
          </div>
          <input
            v-model="inputText"
            class="w-full bg-transparent border-none focus:ring-0 focus:outline-none text-sm placeholder:text-slate-400 font-medium py-1 text-slate-800 dark:text-slate-200"
            placeholder="描述您的目标受众和创意方向，例如：'为欧美市场RPG游戏生成高技巧玩家素材'..."
            type="text"
            :disabled="isGenerating"
            @keydown.enter="handleSubmit"
          />
          <div class="flex items-center gap-2 ml-3">
            <!-- Quick Actions (inline with tooltip) -->
            <div class="relative group/tip">
              <button class="p-1.5 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800">
                <span class="material-symbols-outlined text-lg">pause</span>
              </button>
              <span class="tooltip-label">暂停生成任务</span>
            </div>
            <div class="relative group/tip">
              <button class="p-1.5 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800">
                <span class="material-symbols-outlined text-lg">tune</span>
              </button>
              <span class="tooltip-label">调整受众参数</span>
            </div>
            <div class="relative group/tip">
              <button class="p-1.5 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800">
                <span class="material-symbols-outlined text-lg">auto_fix</span>
              </button>
              <span class="tooltip-label">更换视觉风格</span>
            </div>
            <div class="w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1"></div>
            <button class="p-1.5 text-slate-400 hover:text-primary transition-colors">
              <span class="material-symbols-outlined text-lg">attach_file</span>
            </button>
            <button
              class="bg-primary text-white p-2 rounded-xl hover:bg-primary/90 transition-all shadow-lg flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isGenerating || !inputText.trim()"
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

<style scoped>
.chat-container::-webkit-scrollbar {
  width: 4px;
}
.chat-container::-webkit-scrollbar-thumb {
  @apply bg-slate-200 rounded-full;
}

.tooltip-label {
  @apply absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 text-[11px] font-medium text-white bg-slate-800 rounded-lg whitespace-nowrap opacity-0 pointer-events-none transition-all duration-200 shadow-lg;
}
.tooltip-label::after {
  content: '';
  @apply absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent;
  border-top-color: theme('colors.slate.800');
}
.group\/tip:hover .tooltip-label {
  @apply opacity-100 -translate-x-1/2 -translate-y-0.5;
}
</style>
