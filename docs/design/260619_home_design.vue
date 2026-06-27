<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

/* ------------------------------------------------------------------ *
 * 驾驶舱两态：idle 空态 / running 执行态（同一空间两相）
 * ------------------------------------------------------------------ */
type Phase = 'idle' | 'running'
const phase = ref<Phase>('idle')

/* ------------------------------------------------------------------ *
 * Block 11 真实数据（来自 aniforce-agent/logs/block11_long_task_260618.log）
 * 用于执行态的 Chat 流 + Workspace 投影。全部 Mock 已标注。
 * ------------------------------------------------------------------ */
type Panel = 'context' | 'creative' | 'analysis' | 'budget' | 'audit'

interface ToolStep {
  id: string
  label: string
  tool: string
  kind: 'hitl' | 'backend'
}

interface ChatMsg {
  role: 'user' | 'assistant' | 'system'
  content: string
  tools?: ToolStep[]
  hitlTitle?: string
  hitlDetail?: string
  phase?: string                  // 该幕 Agent 的执行阶段文案
  stats?: { in: number; out: number; cost: number; tps: number; turns: number }
}

interface Act {
  id: number
  title: string
  icon: string
  panel: Panel
  messages: ChatMsg[]
}

/* ---- 业务实体（投影数据，对齐 SaaS 类型结构） ---- */
const project = ref({
  id: '6c0ad836-e32c-4075-91c5-3c72691c0de8',
  name: 'LongTaskDemo',
  description: '长程任务全链路演示项目',
  game_type: 'RPG',
  target_market: '全球',
  total_budget: 50000,
  spent: 0,
  tags: ['夏季促销', 'Demo'],
  start_date: '2026-06-18',
  end_date: '2026-07-18',
  manager: 'PM',
})

interface Campaign {
  id: string
  name: string
  platform: 'Meta' | 'Google'
  budget: number
  spent: number
  status: string
  start_date: string
}

const campaigns = ref<Campaign[]>([])

interface Material {
  id: string
  name: string
  type: 'image' | 'copy'
  content?: string
  ai_generated: boolean
  status: string
}

const materials = ref<Material[]>([])

interface Perf {
  impressions: number
  clicks: number
  conversions: number
  spent: number
  ctr: number
  cpc: number
  cpa: number
  roi: number
}
const perfA = ref<Perf | null>(null)
const perfB = ref<Perf | null>(null)

const budgetChange = ref<{ aBefore: number; aAfter: number; bBefore: number; bAfter: number } | null>(null)

/* ------------------------------------------------------------------ *
 * 10 幕剧本（Block 11 流程）
 * ------------------------------------------------------------------ */
const acts: Act[] = [
  {
    id: 1, title: '创建项目', icon: 'create_new_folder', panel: 'context',
    messages: [
      { role: 'user', content: '创建项目 LongTaskDemo，总预算 50000' },
      {
        role: 'assistant', phase: 'Running create_project…',
        tools: [
          { id: 'h1', label: '审批创建项目', tool: 'confirm_action', kind: 'hitl' },
          { id: 'b1', label: 'create_project', tool: 'mcp__backend__create_project', kind: 'backend' },
        ],
        hitlTitle: '创建项目 LongTaskDemo', hitlDetail: '总预算 ¥50,000',
        stats: { in: 2840, out: 156, cost: 0.018, tps: 52.3, turns: 2 },
        content: '项目创建成功。项目 ID `6c0ad836-…`，总预算 ¥50,000。',
      },
    ],
  },
  {
    id: 2, title: '创建广告计划', icon: 'ads_click', panel: 'context',
    messages: [
      { role: 'user', content: '在 LongTaskDemo 项目下创建两个计划：A（Meta，预算 5000）和 B（Google，预算 3000）' },
      {
        role: 'assistant', phase: 'Running create_campaign…',
        tools: [
          { id: 'h2a', label: '审批计划 A', tool: 'confirm_action', kind: 'hitl' },
          { id: 'h2b', label: '审批计划 B', tool: 'confirm_action', kind: 'hitl' },
          { id: 'b2a', label: 'create_campaign A', tool: 'mcp__backend__create_campaign', kind: 'backend' },
          { id: 'b2b', label: 'create_campaign B', tool: 'mcp__backend__create_campaign', kind: 'backend' },
        ],
        hitlTitle: '创建计划 A / B', hitlDetail: 'Meta ¥5,000 · Google ¥3,000',
        stats: { in: 3120, out: 312, cost: 0.029, tps: 48.1, turns: 4 },
        content: '两个广告计划创建成功。计划 A：`f2ea0073-…`（Meta），计划 B：`302e4871-…`（Google）。',
      },
    ],
  },
  {
    id: 3, title: 'AI 生成素材', icon: 'auto_awesome', panel: 'creative',
    messages: [
      { role: 'user', content: '为计划 A 生成 3 张广告图，主题：夏季促销' },
      {
        role: 'assistant', phase: 'Running generate_material_ai…',
        tools: [{ id: 'b3', label: 'generate_material_ai', tool: 'mcp__backend__generate_material_ai', kind: 'backend' }],
        stats: { in: 1980, out: 204, cost: 0.021, tps: 55.8, turns: 1 },
        content: '3 张广告图生成成功（⚠️ Mock 占位素材，非真实生成）。已挂载到计划 A。',
      },
    ],
  },
  {
    id: 4, title: '创建文案素材', icon: 'edit_note', panel: 'creative',
    messages: [
      { role: 'user', content: '为计划 B 创建 2 个文案素材' },
      {
        role: 'assistant', phase: 'Running create_material…',
        tools: [
          { id: 'b4a', label: 'create_material 文案1', tool: 'mcp__backend__create_material', kind: 'backend' },
          { id: 'b4b', label: 'create_material 文案2', tool: 'mcp__backend__create_material', kind: 'backend' },
        ],
        stats: { in: 1560, out: 188, cost: 0.014, tps: 61.2, turns: 2 },
        content: '2 个文案素材创建成功（⚠️ Mock 数据）。已挂载到计划 B。',
      },
    ],
  },
  {
    id: 5, title: '发起投放', icon: 'rocket_launch', panel: 'context',
    messages: [
      { role: 'user', content: '把计划 A 和 B 都设置为 active 状态，开始投放' },
      {
        role: 'assistant', phase: 'Running update_campaign_status…',
        tools: [
          { id: 'h5a', label: '审批上线 A', tool: 'confirm_action', kind: 'hitl' },
          { id: 'h5b', label: '审批上线 B', tool: 'confirm_action', kind: 'hitl' },
          { id: 'b5a', label: 'update_status A', tool: 'mcp__backend__update_campaign_status', kind: 'backend' },
          { id: 'b5b', label: 'update_status B', tool: 'mcp__backend__update_campaign_status', kind: 'backend' },
        ],
        hitlTitle: '发起投放', hitlDetail: '计划 A、B 状态 DRAFT → RUNNING',
        stats: { in: 2740, out: 246, cost: 0.024, tps: 50.5, turns: 4 },
        content: '两个广告计划已上线，状态 DRAFT → RUNNING。',
      },
    ],
  },
  {
    id: 6, title: '模拟时间流逝', icon: 'schedule', panel: 'analysis',
    messages: [{ role: 'system', content: '⏰ 模拟：7 天后，PM 回来查看数据' }],
  },
  {
    id: 7, title: '获取投放数据', icon: 'query_stats', panel: 'analysis',
    messages: [
      { role: 'user', content: '查看计划 A 和 B 过去 7 天的投放数据' },
      {
        role: 'assistant', phase: 'Running get_campaign_performance…',
        tools: [
          { id: 'b7a', label: 'get_performance A', tool: 'mcp__backend__get_campaign_performance', kind: 'backend' },
          { id: 'b7b', label: 'get_performance B', tool: 'mcp__backend__get_campaign_performance', kind: 'backend' },
        ],
        stats: { in: 1820, out: 142, cost: 0.012, tps: 58.7, turns: 2 },
        content: '过去 7 天投放数据已获取（⚠️ Mock 数据，非真实投放结果）。',
      },
    ],
  },
  {
    id: 8, title: '对比分析', icon: 'insights', panel: 'analysis',
    messages: [
      { role: 'user', content: '对比 A 和 B，哪个 ROI 更好？给出详细分析' },
      {
        role: 'assistant', phase: 'Thinking…',
        stats: { in: 2240, out: 412, cost: 0.034, tps: 44.2, turns: 1 },
        content:
          '## 计划 A vs 计划 B 投放数据对比分析\n\n> ⚠️ 数据来源：Mock 数据，用于 Agent 能力演示\n\n**结论**：计划 B（Google）ROI 3.42 显著优于计划 A（Meta）ROI 1.85。\n\nB 的 CTR 高出 1.25pp、CPC 低 47%、CPA 低 67%，整体效率全面领先。建议向 B 倾斜预算。',
      },
    ],
  },
  {
    id: 9, title: '预算调整', icon: 'tune', panel: 'budget',
    messages: [
      { role: 'user', content: '根据数据分析，把 ROI 低的计划的预算调低 1000，ROI 高的加 1000' },
      {
        role: 'assistant', phase: 'Running update_campaign_budget…',
        tools: [
          { id: 'h9a', label: '审批调整 A', tool: 'confirm_action', kind: 'hitl' },
          { id: 'h9b', label: '审批调整 B', tool: 'confirm_action', kind: 'hitl' },
          { id: 'b9a', label: 'update_budget A', tool: 'mcp__backend__update_campaign_budget', kind: 'backend' },
          { id: 'b9b', label: 'update_budget B', tool: 'mcp__backend__update_campaign_budget', kind: 'backend' },
        ],
        hitlTitle: '预算调整', hitlDetail: 'A −1000 · B +1000 · 总预算不变',
        stats: { in: 2680, out: 274, cost: 0.026, tps: 49.6, turns: 4 },
        content: '两个计划预算调整完成。计划 A：¥5,000 → ¥4,000；计划 B：¥3,000 → ¥4,000。',
      },
    ],
  },
  {
    id: 10, title: '任务总结', icon: 'task_alt', panel: 'audit',
    messages: [
      { role: 'user', content: '总结一下我们完成了什么' },
      {
        role: 'assistant', phase: 'Thinking…',
        stats: { in: 3120, out: 386, cost: 0.031, tps: 42.8, turns: 1 },
        content:
          '## 任务总结报告：LongTaskDemo 项目全流程复盘\n\n> 项目 ID：6c0ad836-…\n\n1. ✅ 创建项目 LongTaskDemo（总预算 ¥50,000）\n2. ✅ 创建 2 个广告计划（Meta / Google）\n3. ✅ AI 生成 3 张广告图 + 2 条文案素材\n4. ✅ 发起投放，2 个计划进入 RUNNING\n5. ✅ 获取 7 天投放数据并完成对比分析\n6. ✅ 基于分析完成预算再分配（A −1000 / B +1000）\n\n全程 6 次 HITL 确认，所有写操作均经审批。',
      },
    ],
  },
]

/* ------------------------------------------------------------------ *
 * 播放器
 * ------------------------------------------------------------------ */
const currentActId = ref(0)
const playing = ref(false)
let playTimer: ReturnType<typeof setTimeout> | null = null

const currentAct = computed(() => acts.find(a => a.id === currentActId.value) || null)

const chatStream = computed<ChatMsg[]>(() => {
  const out: ChatMsg[] = []
  for (const a of acts) {
    if (a.id > currentActId.value) break
    out.push(...a.messages)
  }
  return out
})

// 当前运行中的 phase 文案
const livePhase = computed(() => {
  if (!playing.value) return ''
  if (currentActId.value === 0 || currentActId.value >= acts.length) return ''
  const last = currentAct.value?.messages[currentAct.value.messages.length - 1]
  return last?.phase || 'Thinking…'
})

// 累计统计
const accStats = computed(() => {
  let i = 0, o = 0, c = 0, tps = 0, turns = 0, n = 0
  for (const a of acts) {
    if (a.id > currentActId.value) break
    for (const m of a.messages) {
      if (m.stats) {
        i += m.stats.in; o += m.stats.out; c += m.stats.cost
        tps += m.stats.tps; turns += m.stats.turns; n++
      }
    }
  }
  if (!n) return null
  return { in: i, out: o, cost: c, tps: Math.round(tps / n), turns }
})

const manualPanel = ref<Panel | null>(null)
const activePanel = computed<Panel>(() => manualPanel.value ?? currentAct.value?.panel ?? 'context')

const tabs: { id: Panel; label: string; icon: string }[] = [
  { id: 'context', label: '上下文', icon: 'folder_open' },
  { id: 'creative', label: '素材', icon: 'video_library' },
  { id: 'analysis', label: '分析', icon: 'insights' },
  { id: 'budget', label: '预算', icon: 'tune' },
  { id: 'audit', label: '审计', icon: 'task_alt' },
]

/* 折叠状态：默认所有 thinking trace 折叠，运行中当前幕展开 */
const expandedTraces = ref<Set<number>>(new Set())
function toggleTrace(idx: number) {
  if (expandedTraces.value.has(idx)) expandedTraces.value.delete(idx)
  else expandedTraces.value.add(idx)
}

function applyActSideEffect(actId: number) {
  if (actId >= 1) project.value.spent = 0
  if (actId >= 2) {
    campaigns.value = [
      { id: 'f2ea0073-b563-416d-bff7-55afa4c3cfb7', name: '计划 A · 夏季促销', platform: 'Meta', budget: 5000, spent: 0, status: 'DRAFT', start_date: '2026-06-18' },
      { id: '302e4871-ebdc-4870-9289-c74972787c46', name: '计划 B · 品牌词', platform: 'Google', budget: 3000, spent: 0, status: 'DRAFT', start_date: '2026-06-18' },
    ]
  }
  if (actId >= 3) {
    materials.value.push(
      { id: 'm-a1', name: '夏季促销主图 01', type: 'image', ai_generated: true, status: 'ready' },
      { id: 'm-a2', name: '夏季促销主图 02', type: 'image', ai_generated: true, status: 'ready' },
      { id: 'm-a3', name: '夏季促销主图 03', type: 'image', ai_generated: true, status: 'ready' },
    )
  }
  if (actId >= 4) {
    materials.value.push(
      { id: 'm-b1', name: '品牌词文案 01', type: 'copy', content: '夏日狂欢，限时特惠！即刻开玩，领专属礼包。', ai_generated: false, status: 'ready' },
      { id: 'm-b2', name: '品牌词文案 02', type: 'copy', content: 'RPG 大作首发，全球玩家都在玩。点击下载。', ai_generated: false, status: 'ready' },
    )
  }
  if (actId >= 5) campaigns.value = campaigns.value.map(c => ({ ...c, status: 'RUNNING' }))
  if (actId >= 7) {
    perfA.value = { impressions: 125300, clicks: 3780, conversions: 92, spent: 4860, ctr: 3.02, cpc: 1.29, cpa: 52.8, roi: 1.85 }
    perfB.value = { impressions: 98500, clicks: 4210, conversions: 168, spent: 2910, ctr: 4.27, cpc: 0.69, cpa: 17.3, roi: 3.42 }
    campaigns.value = campaigns.value.map(c => ({ ...c, spent: c.platform === 'Meta' ? 4860 : 2910 }))
  }
  if (actId >= 9) {
    budgetChange.value = { aBefore: 5000, aAfter: 4000, bBefore: 3000, bAfter: 4000 }
    campaigns.value = campaigns.value.map(c => ({ ...c, budget: 4000 }))
  }
}

function resetData() {
  campaigns.value = []
  materials.value = []
  perfA.value = null
  perfB.value = null
  budgetChange.value = null
  manualPanel.value = null
  expandedTraces.value.clear()
}

function goToAct(actId: number) {
  stopPlay()
  resetData()
  currentActId.value = actId
  for (let i = 1; i <= actId; i++) applyActSideEffect(i)
  scrollChatToBottom()
}

function playNext() {
  if (currentActId.value >= acts.length) { playing.value = false; return }
  currentActId.value += 1
  manualPanel.value = null
  applyActSideEffect(currentActId.value)
  scrollChatToBottom()
  if (playing.value) playTimer = setTimeout(playNext, 1900)
}

function togglePlay() {
  if (currentActId.value === 0 || currentActId.value >= acts.length) {
    phase.value = 'running'
    resetData()
    currentActId.value = 1
    applyActSideEffect(1)
    scrollChatToBottom()
  }
  playing.value = !playing.value
  if (playing.value) {
    playTimer = setTimeout(playNext, 1900)
  } else if (playTimer) {
    clearTimeout(playTimer); playTimer = null
  }
}

function stopPlay() {
  playing.value = false
  if (playTimer) { clearTimeout(playTimer); playTimer = null }
}

function restart() {
  stopPlay()
  resetData()
  currentActId.value = 0
  phase.value = 'idle'
}

function selectTab(t: Panel) { manualPanel.value = t }
function switchPanel(item: any) { if (item.path) router.push(item.path) }
function switchSession(s: any) { void s }

function fmt(n: number): string { return n.toLocaleString('en-US') }
function fmtTokens(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

const chatScrollRef = ref<HTMLElement | null>(null)
function scrollChatToBottom() {
  nextTick(() => { if (chatScrollRef.value) chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight })
}

const sessions = ref([
  { id: 'sess_block11', name: 'LongTaskDemo 全流程', active: true },
  { id: 'sess_prev1', name: 'RPG 游戏分析', active: false },
  { id: 'sess_prev2', name: '素材优化建议', active: false },
])

const quickStarts = [
  { emoji: '🎮', label: 'RPG游戏', prompt: '为我的 RPG 游戏创建一个夏季促销投放项目' },
  { emoji: '⚔️', label: '策略游戏', prompt: '分析策略游戏市场并制定投放计划' },
  { emoji: '🧩', label: '休闲游戏', prompt: '为休闲游戏生成广告素材' },
]

function startWithPrompt(p: string) {
  phase.value = 'running'
  resetData()
  currentActId.value = 1
  applyActSideEffect(1)
  scrollChatToBottom()
}
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="new-task"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- ============== 空态 ============== -->
    <main v-if="phase === 'idle'" class="flex flex-1 flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="flex flex-1 flex-col items-center justify-center px-4">
        <div class="w-full max-w-[624px] text-center">
          <div class="mb-[12px] flex justify-center">
            <div class="flex h-[48px] w-[48px] items-center justify-center rounded-2xl bg-primary/10">
              <span class="material-symbols-outlined text-primary text-[26px]">smart_toy</span>
            </div>
          </div>
          <h1 class="font-poppins text-[28px] font-semibold tracking-tight text-slate-900 dark:text-white md:text-[34px]">
            又见面啦！有新的投放计划吗？
          </h1>
          <p class="mt-[12px] text-[15px] text-slate-500 dark:text-slate-400">
            一句话描述目标，ANIFORCE 帮你建项目、配计划、生素材、跑数据、调预算。
          </p>

          <div class="mt-[28px] rounded-2xl border border-slate-200 bg-slate-50 p-[16px] text-left dark:border-slate-800 dark:bg-slate-800/50">
            <div class="flex items-center gap-[8px]">
              <span class="material-symbols-outlined text-[15px] text-primary">play_circle</span>
              <span class="text-[12px] font-semibold text-slate-900 dark:text-white">全流程演示</span>
              <span class="ml-auto font-mono text-[10px] text-slate-400">Block 11 · 10 steps</span>
            </div>
            <p class="mt-[6px] text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              从创建项目到预算再分配的完整长程任务流，含 6 次 HITL 确认。点击回放 Agent 真实执行轨迹。
            </p>
            <button
              class="mt-[12px] flex w-full items-center justify-center gap-[6px] rounded-xl bg-primary py-[10px] text-[12px] font-semibold text-white transition-colors hover:bg-primary/90"
              @click="togglePlay"
            >
              <span class="material-symbols-outlined text-[16px]">play_arrow</span>
              播放全流程
            </button>
          </div>

          <div class="mt-[19px] flex flex-wrap justify-center gap-[9px]">
            <button
              v-for="q in quickStarts"
              :key="q.label"
              class="flex items-center gap-[6px] rounded-full border border-slate-200 bg-white px-[16px] py-[6px] text-[11px] font-medium text-slate-600 shadow-sm transition-all hover:border-primary hover:text-primary dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
              @click="startWithPrompt(q.prompt)"
            >
              <span class="text-[15px]">{{ q.emoji }}</span>
              {{ q.label }}
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- ============== 执行态 ============== -->
    <template v-else>
      <!-- 中间 Chat 区 -->
      <section class="flex w-[480px] flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <!-- Chat Header：标题 + stat chips + 播放 -->
        <header class="flex h-[50px] items-center gap-[10px] border-b border-slate-200 px-[16px] dark:border-slate-800">
          <button
            class="flex items-center gap-[4px] text-[11px] font-medium text-slate-500 transition-colors hover:text-primary dark:text-slate-400"
            @click="restart"
          >
            <span class="material-symbols-outlined text-[15px]">arrow_back</span>
            返回
          </button>
          <div class="h-[16px] w-px bg-slate-200 dark:bg-slate-800"></div>
          <span class="truncate text-[13px] font-semibold text-slate-900 dark:text-white">LongTaskDemo 全流程</span>

          <!-- stat chips -->
          <div v-if="accStats" class="ml-auto flex items-center gap-[4px]">
            <span class="inline-flex h-[22px] items-center gap-[3px] rounded-md border border-slate-200 bg-slate-50 px-[6px] font-mono text-[10px] tabular-nums text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400">
              ↑{{ fmtTokens(accStats.in) }}
            </span>
            <span class="inline-flex h-[22px] items-center gap-[3px] rounded-md border border-slate-200 bg-slate-50 px-[6px] font-mono text-[10px] tabular-nums text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400">
              ↓{{ fmtTokens(accStats.out) }}
            </span>
            <span
              class="inline-flex h-[22px] items-center gap-[3px] rounded-md border px-[6px] font-mono text-[10px] tabular-nums"
              :class="accStats.cost >= 0.01
                ? 'border-primary/30 bg-primary/5 text-primary'
                : 'border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-800/60'"
            >${{ accStats.cost.toFixed(3) }}</span>
            <button
              class="ml-[4px] flex h-[26px] w-[26px] items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-primary dark:text-slate-400 dark:hover:bg-slate-800"
              :title="playing ? '暂停' : '播放'"
              @click="togglePlay"
            >
              <span class="material-symbols-outlined text-[16px]">{{ playing ? 'pause' : 'play_arrow' }}</span>
            </button>
          </div>
        </header>

        <!-- step pip 进度（10 点） -->
        <div class="flex h-[28px] items-center gap-[6px] border-b border-slate-100 px-[16px] dark:border-slate-800/60">
          <span class="font-mono text-[10px] text-slate-400">{{ String(currentActId).padStart(2, '0') }}/10</span>
          <div class="flex flex-1 items-center gap-[4px]">
            <span
              v-for="a in acts"
              :key="a.id"
              class="h-[4px] flex-1 rounded-full transition-all duration-300"
              :class="a.id < currentActId ? 'bg-primary' : a.id === currentActId ? 'bg-primary/40' : 'bg-slate-200 dark:bg-slate-700'"
            ></span>
          </div>
          <span v-if="accStats" class="font-mono text-[10px] text-slate-400">{{ accStats.turns }} turns</span>
        </div>

        <!-- Chat 消息流 -->
        <div ref="chatScrollRef" class="flex-1 space-y-[18px] overflow-y-auto px-[16px] py-[16px]">
          <template v-for="(msg, i) in chatStream" :key="i">
            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'" class="flex justify-end">
              <div class="max-w-[85%] rounded-2xl bg-primary px-[12px] py-[8px] text-[12px] leading-relaxed text-white">
                {{ msg.content }}
              </div>
            </div>

            <!-- 系统提示 -->
            <div v-else-if="msg.role === 'system'" class="flex justify-center">
              <span class="rounded-full bg-slate-100 px-[12px] py-[3px] text-[10px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {{ msg.content }}
              </span>
            </div>

            <!-- Agent 消息：头像 + (折叠的 trace) + 主体文本 + HITL 徽标 -->
            <div v-else class="flex gap-[10px]">
              <div class="flex h-[24px] w-[24px] flex-none items-center justify-center rounded-lg bg-primary/10">
                <span class="material-symbols-outlined text-primary text-[14px]">smart_toy</span>
              </div>
              <div class="min-w-0 flex-1 space-y-[6px]">
                <!-- phase 行（只在该幕最后一条消息，且当前正在运行此幕时显示） -->
                <div v-if="livePhase && i === chatStream.length - 1" class="flex items-center gap-[6px] text-[11px] text-slate-400">
                  <span class="material-symbols-outlined animate-pulse text-[13px] text-primary">progress_activity</span>
                  <span class="font-mono">{{ livePhase }}</span>
                  <span v-if="msg.stats" class="font-mono text-[10px] text-slate-400">· {{ msg.stats.tps }} tok/s</span>
                </div>

                <!-- 折叠的 thinking trace（工具调用） -->
                <div v-if="msg.tools?.length">
                  <button
                    class="group flex items-center gap-[6px] rounded-md py-[2px] text-[11px] text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-300"
                    @click="toggleTrace(i)"
                  >
                    <span
                      class="material-symbols-outlined text-[14px] transition-transform"
                      :class="expandedTraces.has(i) ? 'rotate-90' : ''"
                    >chevron_right</span>
                    <span>{{ msg.tools.length }} 步 ·</span>
                    <span class="font-mono">{{ msg.tools.filter(t => t.kind === 'hitl').length }} 审批</span>
                    <span>·</span>
                    <span class="font-mono">{{ msg.tools.filter(t => t.kind === 'backend').length }} 工具</span>
                    <span class="ml-[2px] text-emerald-500">✓</span>
                  </button>
                  <!-- 展开的 trace 细线时间线 -->
                  <div v-if="expandedTraces.has(i)" class="mt-[4px] ml-[6px] border-l border-slate-200 pl-[12px] dark:border-slate-700">
                    <div
                      v-for="t in msg.tools"
                      :key="t.id"
                      class="flex items-center gap-[6px] py-[2px] text-[11px]"
                    >
                      <span
                        class="h-[5px] w-[5px] flex-none rounded-full"
                        :class="t.kind === 'hitl' ? 'bg-amber-400' : 'bg-slate-300 dark:bg-slate-600'"
                      ></span>
                      <span
                        class="material-symbols-outlined text-[12px]"
                        :class="t.kind === 'hitl' ? 'text-amber-500' : 'text-slate-400'"
                      >{{ t.kind === 'hitl' ? 'verified_user' : 'bolt' }}</span>
                      <span class="font-mono text-[10px] text-slate-500 dark:text-slate-400">{{ t.label }}</span>
                    </div>
                  </div>
                </div>

                <!-- HITL 徽标：inline 单行，不是大块卡 -->
                <div
                  v-if="msg.hitlTitle"
                  class="inline-flex items-center gap-[6px] rounded-md border border-amber-200/60 bg-amber-50/50 px-[8px] py-[3px] text-[11px] dark:border-amber-900/40 dark:bg-amber-950/20"
                >
                  <span class="material-symbols-outlined text-[12px] text-amber-600">check_circle</span>
                  <span class="text-slate-600 dark:text-slate-300">{{ msg.hitlTitle }}</span>
                  <span class="text-slate-400">·</span>
                  <span class="text-slate-500 dark:text-slate-400">{{ msg.hitlDetail }}</span>
                </div>

                <!-- Agent 文本回复（主体） -->
                <div
                  v-if="msg.content"
                  class="markdown-body whitespace-pre-line text-[13px] leading-[1.7] text-slate-700 dark:text-slate-300"
                  v-html="renderMarkdown(msg.content)"
                ></div>
              </div>
            </div>
          </template>

          <!-- 运行中等待 -->
          <div v-if="playing && currentActId < acts.length && !livePhase" class="flex gap-[10px]">
            <div class="flex h-[24px] w-[24px] flex-none items-center justify-center rounded-lg bg-primary/10">
              <span class="material-symbols-outlined animate-pulse text-primary text-[14px]">smart_toy</span>
            </div>
            <div class="flex items-center gap-[4px] py-[4px]">
              <span class="h-[4px] w-[4px] animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]"></span>
              <span class="h-[4px] w-[4px] animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]"></span>
              <span class="h-[4px] w-[4px] animate-bounce rounded-full bg-slate-400"></span>
            </div>
          </div>
        </div>

        <!-- 输入条 -->
        <div class="border-t border-slate-200 p-[12px] dark:border-slate-800">
          <div class="flex items-center gap-[8px] rounded-xl border border-slate-200 bg-slate-50 px-[12px] py-[9px] dark:border-slate-700 dark:bg-slate-800/50">
            <span class="material-symbols-outlined text-[16px] text-slate-400">attach_file</span>
            <input class="flex-1 bg-transparent text-[12px] text-slate-400 outline-none" placeholder="描述下一个投放目标…" disabled />
            <span class="material-symbols-outlined text-[16px] text-slate-300">send</span>
          </div>
        </div>
      </section>

      <!-- 右侧 Workspace -->
      <section class="flex flex-1 flex-col bg-slate-50 dark:bg-slate-950">
        <header class="flex h-[50px] items-center gap-[4px] border-b border-slate-200 bg-white px-[16px] dark:border-slate-800 dark:bg-slate-900">
          <div class="mr-[12px] flex items-center gap-[6px]">
            <span class="material-symbols-outlined text-[15px] text-primary">{{ currentAct?.icon || 'dashboard' }}</span>
            <span class="text-[12px] font-semibold text-slate-900 dark:text-white">{{ currentAct?.title || '工作区' }}</span>
          </div>
          <nav class="flex items-center gap-[2px]">
            <button
              v-for="t in tabs"
              :key="t.id"
              class="flex items-center gap-[4px] rounded-md px-[10px] py-[5px] text-[11px] font-medium transition-colors"
              :class="activePanel === t.id
                ? 'bg-primary/10 text-primary'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800'"
              @click="selectTab(t.id)"
            >
              <span class="material-symbols-outlined text-[13px]">{{ t.icon }}</span>
              {{ t.label }}
            </button>
          </nav>
        </header>

        <div class="flex flex-1 overflow-hidden">
          <div class="flex-1 overflow-y-auto p-[19px]">
            <!-- 上下文面板 -->
            <div v-if="activePanel === 'context'" class="space-y-[16px]">
              <div class="rounded-md border border-slate-200 bg-white p-[16px] dark:border-slate-800 dark:bg-slate-900">
                <h4 class="mb-[12px] text-[11px] font-semibold text-slate-900 dark:text-white">项目信息</h4>
                <div class="grid grid-cols-2 gap-[12px]">
                  <div class="col-span-2">
                    <p class="mb-[12px] text-[11px] text-slate-500 dark:text-slate-400">{{ project.description }}</p>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">项目 ID</span>
                    <span class="font-mono text-[10px] text-slate-400">{{ project.id.slice(0, 8) }}…</span>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">产品类型</span>
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project.game_type }}</span>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">目标市场</span>
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ project.target_market }}</span>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">总预算</span>
                    <span class="font-mono text-[11px] font-semibold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(project.total_budget) }}</span>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">已消耗</span>
                    <span class="font-mono text-[11px] font-semibold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(project.spent) }}</span>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">标签</span>
                    <div class="flex flex-wrap gap-[4px]">
                      <span v-for="tag in project.tags" :key="tag" class="rounded bg-slate-100 px-[5px] py-[1px] text-[10px] text-slate-600 dark:bg-slate-700 dark:text-slate-400">{{ tag }}</span>
                    </div>
                  </div>
                  <div class="flex justify-between border-b border-slate-200 py-[6px] dark:border-slate-700">
                    <span class="text-[10px] text-slate-500 dark:text-slate-400">起止</span>
                    <span class="font-mono text-[10px] text-slate-900 dark:text-white">{{ project.start_date }} → {{ project.end_date }}</span>
                  </div>
                </div>
              </div>

              <div>
                <div class="mb-[12px] flex items-center justify-between">
                  <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">广告计划 <span class="font-mono text-slate-400">({{ campaigns.length }})</span></h4>
                </div>
                <div v-if="campaigns.length === 0" class="flex flex-col items-center justify-center py-[40px]">
                  <span class="material-symbols-outlined mb-[12px] text-[40px] text-slate-300 dark:text-slate-700">ads_click</span>
                  <p class="text-[11px] text-slate-400">尚未创建广告计划</p>
                </div>
                <div v-else class="space-y-[9px]">
                  <div
                    v-for="c in campaigns"
                    :key="c.id"
                    class="rounded-md border border-slate-200 bg-white p-[12px] transition-colors hover:border-primary/40 dark:border-slate-800 dark:bg-slate-900"
                  >
                    <div class="mb-[9px] flex items-center justify-between">
                      <div class="flex-1">
                        <div class="mb-[4px] text-[12px] font-semibold text-slate-900 dark:text-white">{{ c.name }}</div>
                        <div class="text-[10px] font-medium" :class="c.platform === 'Meta' ? 'text-blue-600' : 'text-red-500'">{{ c.platform }}</div>
                      </div>
                      <span
                        class="rounded border px-[6px] py-[1px] text-[10px] font-medium"
                        :class="c.status === 'RUNNING'
                          ? 'border-emerald-200 text-emerald-600 dark:border-emerald-900/50 dark:text-emerald-300'
                          : 'border-slate-200 text-slate-500 dark:border-slate-700'"
                      >{{ c.status }}</span>
                    </div>
                    <div class="grid grid-cols-3 gap-[12px]">
                      <div>
                        <div class="font-mono text-[15px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(c.spent) }}</div>
                        <div class="text-[10px] text-slate-500 dark:text-slate-400">消耗</div>
                      </div>
                      <div>
                        <div class="font-mono text-[15px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(c.budget) }}</div>
                        <div class="text-[10px] text-slate-500 dark:text-slate-400">预算</div>
                      </div>
                      <div>
                        <div class="font-mono text-[15px] font-bold tabular-nums text-slate-900 dark:text-white">{{ c.budget > 0 ? Math.round((c.spent / c.budget) * 100) : 0 }}%</div>
                        <div class="text-[10px] text-slate-500 dark:text-slate-400">进度</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 素材面板 -->
            <div v-else-if="activePanel === 'creative'">
              <div class="mb-[12px] flex items-center justify-between">
                <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">创意素材 <span class="font-mono text-slate-400">({{ materials.length }})</span></h4>
                <span class="text-[10px] text-amber-500">⚠️ Mock</span>
              </div>
              <div v-if="materials.length === 0" class="flex flex-col items-center justify-center py-[40px]">
                <span class="material-symbols-outlined mb-[12px] text-[40px] text-slate-300 dark:text-slate-700">video_library</span>
                <p class="text-[11px] text-slate-400">尚未生成素材</p>
              </div>
              <div v-else class="grid grid-cols-3 gap-[12px]">
                <div
                  v-for="m in materials"
                  :key="m.id"
                  class="overflow-hidden rounded-md border border-slate-200 transition-colors hover:border-primary/40 dark:border-slate-800"
                >
                  <div class="flex aspect-[9/16] items-center justify-center bg-slate-100 dark:bg-slate-800">
                    <template v-if="m.type === 'image'">
                      <div class="flex flex-col items-center gap-[6px]">
                        <span class="material-symbols-outlined text-[36px] text-slate-300 dark:text-slate-600">image</span>
                        <span class="rounded bg-gradient-to-r from-purple-500 to-pink-500 px-[6px] py-[1px] text-[8px] font-bold text-white">AI</span>
                      </div>
                    </template>
                    <template v-else>
                      <span class="material-symbols-outlined text-[36px] text-slate-300 dark:text-slate-600">description</span>
                    </template>
                  </div>
                  <div class="bg-white p-[9px] dark:bg-slate-900">
                    <div class="mb-[4px] truncate text-[11px] font-medium text-slate-900 dark:text-white">{{ m.name }}</div>
                    <div class="flex items-center justify-between">
                      <span class="text-[10px] text-slate-400">{{ m.type === 'image' ? '图片' : '文案' }}</span>
                      <span class="rounded border border-emerald-200 px-[5px] py-[0px] text-[10px] text-emerald-600 dark:border-emerald-900/50 dark:text-emerald-300">{{ m.status }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="materials.some(m => m.type === 'copy')" class="mt-[16px] space-y-[8px]">
                <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">文案内容</h4>
                <div v-for="m in materials.filter(x => x.type === 'copy')" :key="m.id" class="rounded-md border border-slate-200 bg-white p-[12px] dark:border-slate-800 dark:bg-slate-900">
                  <div class="mb-[4px] text-[11px] font-medium text-slate-900 dark:text-white">{{ m.name }}</div>
                  <p class="text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">{{ m.content }}</p>
                </div>
              </div>
            </div>

            <!-- 分析面板 -->
            <div v-else-if="activePanel === 'analysis'" class="space-y-[16px]">
              <div v-if="!perfA && !perfB" class="flex flex-col items-center justify-center py-[60px]">
                <span class="material-symbols-outlined mb-[12px] text-[40px] text-slate-300 dark:text-slate-700">schedule</span>
                <p class="text-[12px] text-slate-500 dark:text-slate-400">数据积累中…</p>
                <p class="mt-[4px] text-[10px] text-slate-400">投放 7 天后返回查看</p>
              </div>
              <template v-else>
                <div class="flex items-center justify-between">
                  <h4 class="text-[12px] font-semibold text-slate-900 dark:text-white">过去 7 天投放数据</h4>
                  <span class="text-[10px] text-amber-500">⚠️ Mock</span>
                </div>
                <div class="grid grid-cols-2 gap-[12px]">
                  <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
                    <div class="mb-[10px] flex items-center justify-between">
                      <span class="text-[11px] font-semibold text-slate-900 dark:text-white">计划 A · Meta</span>
                      <span class="rounded border border-amber-200 px-[6px] py-[0px] text-[10px] text-amber-600 dark:border-amber-900/50 dark:text-amber-300">ROI 低</span>
                    </div>
                    <div class="space-y-[8px]">
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">展示</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfA!.impressions) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">点击</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfA!.clicks) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">转化</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfA!.conversions) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">花费</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(perfA!.spent) }}</span></div>
                      <div class="h-px bg-slate-100 dark:bg-slate-800"></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CTR</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">{{ perfA!.ctr }}%</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CPC</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">¥{{ perfA!.cpc }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CPA</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">¥{{ perfA!.cpa }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">ROI</span><span class="font-mono text-[16px] font-bold tabular-nums text-amber-600">{{ perfA!.roi }}</span></div>
                    </div>
                  </div>
                  <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
                    <div class="mb-[10px] flex items-center justify-between">
                      <span class="text-[11px] font-semibold text-slate-900 dark:text-white">计划 B · Google</span>
                      <span class="rounded border border-emerald-200 px-[6px] py-[0px] text-[10px] text-emerald-600 dark:border-emerald-900/50 dark:text-emerald-300">ROI 高</span>
                    </div>
                    <div class="space-y-[8px]">
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">展示</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfB!.impressions) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">点击</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfB!.clicks) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">转化</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt(perfB!.conversions) }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">花费</span><span class="font-mono text-[13px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(perfB!.spent) }}</span></div>
                      <div class="h-px bg-slate-100 dark:bg-slate-800"></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CTR</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">{{ perfB!.ctr }}%</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CPC</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">¥{{ perfB!.cpc }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">CPA</span><span class="font-mono text-[13px] font-medium tabular-nums text-slate-700 dark:text-slate-300">¥{{ perfB!.cpa }}</span></div>
                      <div class="flex items-baseline justify-between"><span class="text-[10px] text-slate-500">ROI</span><span class="font-mono text-[16px] font-bold tabular-nums text-emerald-600">{{ perfB!.roi }}</span></div>
                    </div>
                  </div>
                </div>
                <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
                  <div class="mb-[8px] flex items-center gap-[6px]">
                    <span class="material-symbols-outlined text-[15px] text-primary">insights</span>
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">对比结论</span>
                  </div>
                  <p class="text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                    计划 B（Google）ROI <span class="font-mono font-bold text-emerald-600">3.42</span> 显著优于计划 A（Meta）ROI <span class="font-mono font-bold text-amber-600">1.85</span>。
                    B 的 CTR 高出 1.25pp、CPC 低 47%、CPA 低 67%，整体效率全面领先。建议向 B 倾斜预算。
                  </p>
                </div>
              </template>
            </div>

            <!-- 预算面板 -->
            <div v-else-if="activePanel === 'budget'">
              <div v-if="!budgetChange" class="flex flex-col items-center justify-center py-[60px]">
                <span class="material-symbols-outlined mb-[12px] text-[40px] text-slate-300 dark:text-slate-700">tune</span>
                <p class="text-[11px] text-slate-400">尚未进行预算调整</p>
              </div>
              <template v-else>
                <h4 class="mb-[12px] text-[12px] font-semibold text-slate-900 dark:text-white">预算再分配</h4>
                <div class="space-y-[9px]">
                  <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
                    <div class="mb-[10px] flex items-center justify-between">
                      <span class="text-[11px] font-semibold text-slate-900 dark:text-white">计划 A · Meta</span>
                      <span class="rounded border border-amber-200 px-[6px] py-[0px] text-[10px] text-amber-600 dark:border-amber-900/50 dark:text-amber-300">−1000</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="font-mono text-[14px] font-bold tabular-nums text-slate-400 line-through">¥{{ fmt(budgetChange.aBefore) }}</span>
                      <span class="material-symbols-outlined text-[16px] text-slate-400">arrow_forward</span>
                      <span class="font-mono text-[18px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(budgetChange.aAfter) }}</span>
                    </div>
                  </div>
                  <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
                    <div class="mb-[10px] flex items-center justify-between">
                      <span class="text-[11px] font-semibold text-slate-900 dark:text-white">计划 B · Google</span>
                      <span class="rounded border border-emerald-200 px-[6px] py-[0px] text-[10px] text-emerald-600 dark:border-emerald-900/50 dark:text-emerald-300">+1000</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="font-mono text-[14px] font-bold tabular-nums text-slate-400 line-through">¥{{ fmt(budgetChange.bBefore) }}</span>
                      <span class="material-symbols-outlined text-[16px] text-slate-400">arrow_forward</span>
                      <span class="font-mono text-[18px] font-bold tabular-nums text-slate-900 dark:text-white">¥{{ fmt(budgetChange.bAfter) }}</span>
                    </div>
                  </div>
                </div>
                <div class="mt-[12px] flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-[12px] py-[10px] dark:border-slate-800 dark:bg-slate-800/50">
                  <span class="text-[11px] text-slate-500 dark:text-slate-400">总预算</span>
                  <span class="font-mono text-[11px] font-semibold tabular-nums text-slate-900 dark:text-white">¥8,000（不变）</span>
                </div>
              </template>
            </div>

            <!-- 审计面板 -->
            <div v-else-if="activePanel === 'audit'">
              <div v-if="currentActId < 10" class="flex flex-col items-center justify-center py-[60px]">
                <span class="material-symbols-outlined mb-[12px] text-[40px] text-slate-300 dark:text-slate-700">task_alt</span>
                <p class="text-[11px] text-slate-400">任务完成后展示全流程复盘</p>
              </div>
              <template v-else>
                <h4 class="mb-[12px] text-[12px] font-semibold text-slate-900 dark:text-white">全流程复盘</h4>
                <div class="space-y-[6px]">
                  <div
                    v-for="(a, i) in acts"
                    :key="a.id"
                    class="flex items-center gap-[10px] rounded-md border border-slate-200 bg-white px-[12px] py-[8px] dark:border-slate-800 dark:bg-slate-900"
                  >
                    <span class="flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full bg-emerald-50 font-mono text-[9px] font-bold text-emerald-600 dark:bg-emerald-950/40">{{ i + 1 }}</span>
                    <span class="material-symbols-outlined text-[15px] text-slate-400">{{ a.icon }}</span>
                    <span class="flex-1 text-[11px] font-medium text-slate-900 dark:text-white">{{ a.title }}</span>
                    <span class="material-symbols-outlined text-[14px] text-emerald-500">check</span>
                  </div>
                </div>
                <div class="mt-[12px] flex items-center gap-[8px] rounded-md border border-slate-200 bg-slate-50 px-[12px] py-[10px] dark:border-slate-800 dark:bg-slate-800/50">
                  <span class="material-symbols-outlined text-[14px] text-amber-500">verified_user</span>
                  <span class="text-[11px] text-slate-600 dark:text-slate-400">全程 6 次 HITL 确认，所有写操作均经审批</span>
                </div>
              </template>
            </div>
          </div>

          <!-- 右侧竖向 Timeline -->
          <aside class="w-[196px] flex-none border-l border-slate-200 bg-white p-[14px] dark:border-slate-800 dark:bg-slate-900">
            <h4 class="mb-[14px] font-mono text-[10px] uppercase tracking-wider text-slate-400">Trace</h4>
            <ol class="space-y-[1px]">
              <li
                v-for="a in acts"
                :key="a.id"
                class="flex cursor-pointer items-center gap-[8px] rounded-md px-[6px] py-[5px] transition-colors"
                :class="a.id === currentActId
                  ? 'bg-primary/10'
                  : a.id < currentActId
                    ? 'hover:bg-slate-100 dark:hover:bg-slate-800'
                    : 'opacity-50 hover:bg-slate-100 dark:hover:bg-slate-800'"
                @click="goToAct(a.id)"
              >
                <span
                  class="flex h-[18px] w-[18px] flex-none items-center justify-center rounded font-mono text-[9px] font-bold"
                  :class="a.id < currentActId
                    ? 'bg-primary text-white'
                    : a.id === currentActId
                      ? 'border border-primary text-primary'
                      : 'border border-slate-200 text-slate-400 dark:border-slate-700'"
                >{{ a.id < currentActId ? '✓' : a.id }}</span>
                <span
                  class="flex-1 truncate text-[11px]"
                  :class="a.id === currentActId ? 'font-semibold text-primary' : 'text-slate-600 dark:text-slate-400'"
                >{{ a.title }}</span>
              </li>
            </ol>
          </aside>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts">
/* 极简 markdown 渲染：标题 / 引用 / 加粗 / 删除线感的代码块标记。 */
function renderMarkdown(src: string): string {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = esc(src).split('\n')
  let html = ''
  for (const line of lines) {
    if (line.startsWith('## ')) { html += `<h3 class="text-[13px] font-bold text-slate-900 dark:text-white mt-[4px] mb-[2px]">${line.slice(3)}</h3>`; continue }
    let l = line
      .replace(/`([^`]+)`/g, '<code class="rounded bg-slate-100 px-[4px] py-[0px] font-mono text-[11px] text-slate-700 dark:bg-slate-800 dark:text-slate-300">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-slate-900 dark:text-white">$1</strong>')
      .replace(/✅/g, '<span class="text-emerald-500">✓</span>')
      .replace(/⚠️/g, '<span class="text-amber-500">⚠</span>')
      .replace(/📊|📋/g, '')
    if (l.startsWith('> ')) { html += `<p class="text-[10px] italic text-slate-400">${l.slice(2)}</p>`; continue }
    if (l.trim() === '') { html += '<div class="h-[4px]"></div>'; continue }
    html += `<p>${l}</p>`
  }
  return html
}
export default {}
</script>

<style scoped>
@media (prefers-reduced-motion: reduce) {
  .animate-pulse, .animate-bounce { animation: none !important; }
}
</style>