<script lang="ts">
export default { name: 'Home' }
</script>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import SessionRenameDialog from '@/components/layout/SessionRenameDialog.vue'
import MessageView from '@/components/agent/MessageView.vue'
import LiveWorkspaceShell from '@/components/agent/workspace/LiveWorkspaceShell.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import type { TaskPanelAction, TaskPanelArtifact, TaskPanelStatus, TaskPanelStep } from '@/components/agent/TaskStatusPanel.vue'
import { useAgentSession, type AgentPhase, type AgentRouteContext } from '@/composables/useAgentSession'
import type { AgentMessage } from '@/api/agent'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()
const agent = useAgentSession()
const inputText = ref('')
const hasInteracted = ref(false)
const modelMenuOpen = ref(false)
const activeIntentMode = ref<'chat' | 'project'>('chat')
const workspaceCollapsed = ref(localStorage.getItem('aniforce.workspace.collapsed') === '1')
const workspaceWidth = ref(Number(localStorage.getItem('aniforce.workspace.width') || 470))
const workspaceDragging = ref(false)
const renameDialog = ref<{ id: string; name: string } | null>(null)
const renameValue = ref('')
const deleteDialog = ref<{ id: string; name: string } | null>(null)
const strategyExpanded = ref(false)
const promptInputRef = ref<HTMLTextAreaElement | null>(null)
let promptResizeObserver: ResizeObserver | null = null

const intentModes: Array<{
  key: 'chat' | 'project'
  label: string
  icon: string
  description: string
  route: AgentRouteContext & { titlePrefix: string }
}> = [
  {
    key: 'chat',
    label: '日常对话',
    icon: 'chat',
    description: '问答、数据查询、轻量分析',
    route: {
      titlePrefix: '日常对话',
      task_type: 'conversation',
      workspace_type: 'empty',
      intent: 'casual_chat'
    }
  },
  {
    key: 'project',
    label: '项目管理',
    icon: 'folder_managed',
    description: '创建项目、整理配置、推进审批',
    route: {
      titlePrefix: '项目管理',
      task_type: 'project_management',
      workspace_type: 'project_draft',
      intent: 'project_management'
    }
  }
]

const starterActions = [
  {
    icon: 'analytics',
    label: '今日投放复盘',
    description: '汇总核心指标，输出计划分层与今日调控清单。',
    prompt: '请复盘当前账号最近 7 天的投放表现。按平台、项目和广告计划汇总消耗、转化、CPA、CTR、CVR 与 ROAS；先校验数据完整性和归因成熟度，再将计划分为「可放量 / 观察 / 控量 / 暂停」，说明判断依据，并给出未来 24 小时可执行的预算、出价和素材调整清单。若缺少业务类型、渠道、目标 CPA/ROAS 或日期范围，请先向我确认。',
    mode: 'chat' as const
  },
  {
    icon: 'tune',
    label: '计划分层调控',
    description: '识别可放量、观察、控量和暂停计划。',
    prompt: '请诊断当前广告计划表现，并按「可放量 / 观察 / 控量 / 暂停」四类输出清单。综合消耗、转化量、CPA、CTR、CVR、ROAS、趋势和样本量判断；对每个计划说明关键证据，并给出明确动作，例如预算上调 10%-30%、预算下调 20%-40%、出价调整 5%-15%、补充素材或暂停。请标记数据不足和归因未成熟的计划，避免过早下结论。',
    mode: 'chat' as const
  },
  {
    icon: 'image_search',
    label: '素材表现诊断',
    description: '定位高潜、疲劳和低效素材，明确迭代方向。',
    prompt: '请分析当前素材表现。结合消耗、CTR、CVR、CPA、ROAS、转化量和连续多日趋势，识别高潜、点击强转化弱、点击弱转化强、疲劳和低效素材；输出 Top 素材、风险素材及判断依据，并给出下一批素材的选题、前 3 秒钩子、卖点、画面结构、版位尺寸和 A/B 变量建议。样本不足的素材请单独标记为待观察。',
    mode: 'chat' as const
  },
  {
    icon: 'account_balance_wallet',
    label: '预算扩量建议',
    description: '找到预算承接空间，制定阶梯扩量与止损线。',
    prompt: '请评估当前投放的预算承接能力，并制定未来 3 天的阶梯扩量方案。找出 CPA 低于目标、ROAS 高于目标且转化稳定的计划，估算可增加的预算区间；同时设置单次调幅、观察周期、回撤条件和止损线。请按平台与计划输出「维持 / 小幅扩量 / 重点扩量 / 降预算」清单，并说明每项调整的数据依据。',
    mode: 'chat' as const
  },
  {
    icon: 'compare_arrows',
    label: '渠道效果对比',
    description: '对比平台效率、量级、质量和增长潜力。',
    prompt: '请对比各投放渠道最近 7 天与前 7 天的表现。统一指标口径后，从消耗、转化量、CPA、CTR、CVR、ROAS、量级、趋势和稳定性评估渠道角色，区分扩量引擎、质量引擎、效率问题、交付问题、实验和止损渠道；输出预算迁移建议、需要保留的实验预算以及下一周期的验证指标。',
    mode: 'chat' as const
  },
  {
    icon: 'warning',
    label: '异常波动排查',
    description: '定位消耗、成本或转化突变的可能原因。',
    prompt: '请排查当前投放中的异常波动。对比最近 24 小时、近 3 天均值和上周同期，识别消耗突增或骤降、CPA 恶化、CTR/CVR 跳变、ROAS 下滑和转化断层；按「数据与归因 / 账户与审核 / 预算与出价 / 定向与流量 / 素材疲劳 / 落地页承接」逐层定位原因，列出证据、影响范围、排查顺序和可以立即执行的恢复动作。',
    mode: 'chat' as const
  },
  {
    icon: 'schedule',
    label: '素材疲劳监控',
    description: '识别衰退拐点，安排换素材和复用节奏。',
    prompt: '请监控素材疲劳并给出换新节奏。以连续 3 天 CTR 下降、CPA 上升、频次增加和转化衰减为主要信号，结合素材上线天数、消耗占比和样本量识别「健康 / 预警 / 疲劳 / 应停」素材；输出需要继续放量、降频、替换和暂停的清单，并为疲劳素材提供同主题改版、开头重剪、卖点替换和版位适配建议。',
    mode: 'chat' as const
  },
  {
    icon: 'experiment',
    label: '下一轮测试方案',
    description: '把诊断结论转成可执行的 A/B 测试矩阵。',
    prompt: '请基于当前投放问题设计下一轮 A/B 测试方案。先明确核心假设，再分别为素材、受众、版位、出价和落地页设计单变量测试；给出测试组与对照组、预算分配、最小样本量、观察周期、成功指标、停止条件和结论记录模板。请按影响力和实施成本排序，优先给出本周可落地的 3-5 个实验。',
    mode: 'chat' as const
  }
]

const visibleStarterActions = computed(() => (
  strategyExpanded.value ? starterActions : starterActions.slice(0, 4)
))
const isPromptExpanded = computed(() => (
  Array.from(inputText.value).length > 72 || inputText.value.includes('\n')
))

const visibleMessages = computed(() => agent.visibleMessages.value)
const hasContent = computed(() => (
  Boolean(hasInteracted.value && agent.activeSession.value) ||
  agent.loading.value ||
  agent.agentRunning.value ||
  visibleMessages.value.length > 0 ||
  Boolean(agent.streamingMessage.value) ||
  Boolean(agent.error.value)
))
const sidebarSessions = computed(() => agent.sessions.value.map(session => ({
  id: session.id,
  name: session.title || session.id,
  active: agent.activeSession.value?.id === session.id
})))
const sidebarActivePanel = computed(() => agent.activeSession.value ? '__session__' : 'new-task')
const currentSessionTitle = computed(() => agent.activeSession.value?.title || '新 Agent 任务')
const activeMode = computed(() => intentModes.find(item => item.key === activeIntentMode.value) || intentModes[0])
const activeRoute = computed(() => {
  const { titlePrefix: _titlePrefix, ...route } = activeMode.value.route
  return route
})
const currentTask = computed(() => agent.currentTask.value)
const workspaceModuleHint = computed<'auto' | 'dashboard' | 'projects' | 'campaigns' | 'materials'>(() => {
  const taskType = currentTask.value?.task_type || ''
  if (/project|task/i.test(taskType)) return 'projects'
  if (/campaign|ad_management/i.test(taskType)) return 'campaigns'
  if (/creative|material/i.test(taskType)) return 'materials'
  if (/data|analysis|report|monitor/i.test(taskType)) return 'dashboard'

  const conversationText = [
    currentSessionTitle.value,
    ...visibleMessages.value
      .filter(message => message.role === 'user')
      .map(message => typeof message.content === 'string' ? message.content : ''),
  ].join(' ')

  if (/(数据|复盘|表现|诊断|分析|点击|转化|ROAS|CTR)/i.test(conversationText)) return 'dashboard'
  if (/(Campaign|投放计划|广告计划)/i.test(conversationText)) return 'campaigns'
  if (/(素材|创意)/i.test(conversationText)) return 'materials'
  if (/(项目|任务)/i.test(conversationText)) return 'projects'
  return 'auto'
})
const hasBusinessTask = computed(() => Boolean(currentTask.value?.task_type && currentTask.value.task_type !== 'conversation' && currentTask.value.task_type !== 'data_query'))
const hasWorkspaceToolResults = computed(() => agent.workspaceToolResults.value.length > 0)
const taskPanelVisible = computed(() => true)
const workspaceStyle = computed(() => ({
  width: workspaceCollapsed.value ? '56px' : `${workspaceWidth.value}px`
}))
const taskStatus = computed<TaskPanelStatus>(() => {
  if (currentTask.value?.status) return normalizeTaskStatus(currentTask.value.status)
  if (agent.error.value) return 'failed'
  if (agent.agentRunning.value) return agent.agentPhase.value?.kind === 'running_tools' ? 'running' : 'running'
  if (visibleMessages.value.length > 1) return 'completed'
  if (visibleMessages.value.length > 0 || hasInteracted.value) return 'created'
  return 'created'
})
const taskSummary = computed(() => {
  if (currentTask.value?.summary) return currentTask.value.summary
  if (currentTask.value?.goal) return currentTask.value.goal
  if (agent.error.value) return agent.error.value
  if (agent.agentRunning.value) return phaseLabel(agent.agentPhase.value)
  if (taskStatus.value === 'completed') return hasWorkspaceToolResults.value ? '业务结果已保留在工作台。' : '本轮回复已完成。'
  if (hasInteracted.value) return '任务已创建，描述你的投放目标后 Agent 会继续推进。'
  return '等待输入任务目标。'
})
const taskSteps = computed<TaskPanelStep[]>(() => {
  const definition = currentTask.value?.task_definition
  if (definition?.phases?.length) {
    const currentPhase = currentTask.value?.phase
    let activeSeen = false
    return definition.phases.map(phase => {
      if (currentTask.value?.status === 'completed') return { key: phase.key, label: phase.label, status: 'done' }
      if (currentTask.value?.status === 'failed') return { key: phase.key, label: phase.label, status: phase.key === currentPhase ? 'error' : 'pending' }
      if (phase.key === currentPhase) {
        activeSeen = true
        return { key: phase.key, label: phase.label, status: 'active' }
      }
      return { key: phase.key, label: phase.label, status: activeSeen ? 'pending' : 'done' }
    })
  }
  const status = taskStatus.value
  const active = agent.agentPhase.value?.kind === 'running_tools' ? 'data' : 'goal'
  const base = [
    { key: 'goal', label: '确认目标与对象' },
    { key: 'data', label: '查询业务证据' },
    { key: 'analysis', label: '形成判断' },
    { key: 'approval', label: '等待业务确认' },
    { key: 'apply', label: '执行业务变更' },
    { key: 'done', label: '验证实际结果' }
  ]
  if (status === 'failed') {
    return base.map((step, index) => ({ ...step, status: index === 0 ? 'error' : 'pending' }))
  }
  if (status === 'completed') {
    return base.map(step => ({ ...step, status: 'done' }))
  }
  if (status === 'created') {
    return base.map((step, index) => ({ ...step, status: index === 0 ? 'active' : 'pending' }))
  }
  return base.map(step => {
    if (active === 'data') {
      if (step.key === 'goal') return { ...step, status: 'done' }
      if (step.key === 'data') return { ...step, status: 'active' }
      return { ...step, status: 'pending' }
    }
    if (step.key === 'goal') return { ...step, status: 'active' }
    return { ...step, status: 'pending' }
  })
})
const taskActions = computed<TaskPanelAction[]>(() => {
  const pending = currentTask.value?.pending_actions || []
  if (pending.length) {
    return pending.flatMap(action => {
      const options = action.options?.length ? action.options : [{ value: action.action_type, label: action.title }]
      return options.map(option => ({
        key: `${action.id}:${option.value || action.action_type}`,
        label: option.label || action.title,
        icon: action.action_type === 'approval' ? 'check' : 'tune',
        tone: action.action_type === 'approval' ? 'primary' : 'neutral'
      }))
    })
  }
  if (agent.agentRunning.value) return [{ key: 'abort', label: '停止任务', icon: 'stop', tone: 'danger' }]
  if (agent.error.value) return [{ key: 'retry', label: '重新发送', icon: 'refresh', tone: 'primary' }]
  if (taskStatus.value === 'completed' && !hasWorkspaceToolResults.value) {
    return [
      { key: 'continue', label: '继续追问', icon: 'chat', tone: 'neutral' },
      { key: 'material', label: '开始创建素材', icon: 'auto_awesome', tone: 'primary' }
    ]
  }
  if (hasWorkspaceToolResults.value) return []
  return [{ key: 'focus', label: '补充任务目标', icon: 'edit_note', tone: 'primary' }]
})
const taskTags = computed(() => {
  const tags: string[] = []
  if (currentTask.value?.task_definition?.label) tags.push(currentTask.value.task_definition.label)
  if (currentTask.value?.phase) tags.push(currentTask.value.phase)
  if (agent.agentPhase.value?.kind === 'running_tools') tags.push(...agent.agentPhase.value.tools.slice(0, 2).map(tool => tool.name))
  return Array.from(new Set(tags)).slice(0, 4)
})
const currentModel = computed(() => {
  const selected = agent.selectedModel.value
  if (!selected) return agent.models.value[0] || null
  return agent.models.value.find(model => model.provider === selected.provider && model.id === selected.modelId) || null
})
const toolResults = computed(() => {
  const map = new Map<string, AgentMessage>()
  for (const msg of agent.visibleMessages.value) {
    if (msg.role === 'toolResult' && typeof msg.toolCallId === 'string') map.set(msg.toolCallId, msg)
  }
  return map
})
const taskTypeLabel = computed(() => currentTask.value?.task_definition?.label || undefined)
const taskPhaseLabel = computed(() => {
  const phase = currentTask.value?.phase
  const definition = currentTask.value?.task_definition
  if (!phase || !definition?.phases) return phase || undefined
  return definition.phases.find(item => item.key === phase)?.label || phase
})
const taskArtifacts = computed<TaskPanelArtifact[]>(() => currentTask.value?.artifacts || [])

function scrollToBottom() {
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

function resizePromptInput(target = promptInputRef.value) {
  if (!target) return
  target.style.height = 'auto'
  target.style.height = `${Math.max(24, target.scrollHeight)}px`
}

function observePromptInput() {
  promptResizeObserver?.disconnect()
  promptResizeObserver = null

  const target = promptInputRef.value
  if (!target) return

  resizePromptInput(target)
  if (typeof ResizeObserver === 'undefined') return

  let previousWidth = target.getBoundingClientRect().width
  promptResizeObserver = new ResizeObserver(entries => {
    const nextWidth = entries[0]?.contentRect.width ?? target.getBoundingClientRect().width
    if (Math.abs(nextWidth - previousWidth) < 0.5) return
    previousWidth = nextWidth
    resizePromptInput(target)
  })
  promptResizeObserver.observe(target)
}

function handlePromptInput(event: Event) {
  resizePromptInput(event.currentTarget as HTMLTextAreaElement)
}

function handlePromptKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void handleSubmit()
}

function phaseLabel(phase: AgentPhase): string {
  if (phase?.kind === 'queued') return '任务已入队，等待 Worker 派发...'
  if (phase?.kind === 'running_tools') {
    const names = phase.tools.map(t => t.name)
    if (!names.length) return 'Agent 正在调用工具...'
    if (names.length === 1) return `Agent 正在调用 ${names[0]}...`
    return `Agent 正在调用 ${names.slice(0, 2).join(', ')}${names.length > 2 ? ` 等 ${names.length} 个工具` : ''}...`
  }
  if (phase?.kind === 'waiting_model') return 'Agent 正在思考...'
  return 'Agent 正在处理...'
}

function normalizeTaskStatus(status: string): TaskPanelStatus {
  if (status === 'waiting_approval') return 'waiting_approval'
  if (status === 'completed') return 'completed'
  if (status === 'failed') return 'failed'
  if (status === 'canceled') return 'canceled'
  if (status === 'created') return 'created'
  return 'running'
}

function clampWorkspaceWidth(value: number): number {
  const viewportMax = Math.max(360, Math.min(640, Math.floor(window.innerWidth * 0.32)))
  return Math.min(Math.max(value, 360), viewportMax)
}

function persistWorkspaceState() {
  localStorage.setItem('aniforce.workspace.width', String(workspaceWidth.value))
  localStorage.setItem('aniforce.workspace.collapsed', workspaceCollapsed.value ? '1' : '0')
}

function toggleWorkspaceCollapsed() {
  workspaceCollapsed.value = !workspaceCollapsed.value
  persistWorkspaceState()
}

function handleWorkspacePointerMove(event: PointerEvent) {
  if (!workspaceDragging.value) return
  workspaceWidth.value = clampWorkspaceWidth(window.innerWidth - event.clientX)
  persistWorkspaceState()
}

function stopWorkspaceResize() {
  workspaceDragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

function startWorkspaceResize(event: PointerEvent) {
  if (workspaceCollapsed.value) return
  workspaceDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  event.preventDefault()
}

async function handleSubmit() {
  const message = inputText.value.trim()
  if (!message || agent.loading.value || agent.agentRunning.value) return
  hasInteracted.value = true
  inputText.value = ''
  scrollToBottom()
  await agent.send(message, undefined, activeRoute.value)
  scrollToBottom()
}

async function runStarterAction(action: typeof starterActions[number]) {
  activeIntentMode.value = action.mode
  inputText.value = action.prompt
  await nextTick()
  const input = document.querySelector<HTMLTextAreaElement>('[data-agent-input="home"]')
  resizePromptInput(input)
  input?.focus()
  input?.setSelectionRange(input.value.length, input.value.length)
}

function navigateTo(path: string) {
  router.push(path)
}

async function analyzeProject(project: { id: string; name: string }) {
  activeIntentMode.value = 'chat'
  inputText.value = `请基于当前项目「${project.name}」进行投放诊断，先汇总预算、消耗、关联投放计划和素材情况，再给出下一步优化建议。项目ID：${project.id}`
  await nextTick()
  await handleSubmit()
}

function openProject(project: { id: string }) {
  if (!project?.id) return
  navigateTo(`/projects/${encodeURIComponent(project.id)}`)
}

function handleTaskAction(action: string) {
  if (action.includes(':')) {
    window.requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>('[data-agent-input="home"]')
      input?.focus()
    })
    return
  }
  if (action === 'abort') {
    void agent.abort()
    return
  }
  if (action === 'material' || action === 'open_material') {
    navigateTo('/material')
    return
  }
  if (action === 'retry' || action === 'continue' || action === 'focus') {
    window.requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>('[data-agent-input="home"]')
      input?.focus()
    })
  }
  if (action === 'approve_campaign' || action === 'revise_campaign' || action === 'cancel_campaign' || action === 'edit_brief') {
    window.requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>('[data-agent-input="home"]')
      input?.focus()
    })
  }
}

const switchPanel = (item: any) => {
  if (item.id === 'new-task') {
    void createChatSession()
    hasInteracted.value = false
    inputText.value = ''
    return
  }
  if (item.path) {
    router.push(item.path)
  }
}

async function createSessionForActiveMode() {
  if (route.path === '/home' && route.query.session_id) {
    void router.push('/home')
  }
  agent.beginNewSession()
  hasInteracted.value = false
  inputText.value = ''
}

async function createChatSession() {
  if (route.path === '/home' && route.query.session_id) {
    void router.push('/home')
  }
  activeIntentMode.value = 'chat'
  agent.beginNewSession()
  hasInteracted.value = false
  inputText.value = ''
}

const switchSession = (session: any) => {
  const target = agent.sessions.value.find(item => item.id === session.id)
  if (target) {
    if (route.path !== '/home' || route.query.session_id !== target.id) {
      void router.push({ path: '/home', query: { session_id: target.id } })
      return
    }
    void selectSessionTarget(target)
  }
}

async function selectSessionTarget(target: typeof agent.sessions.value[number]): Promise<void> {
  hasInteracted.value = true
  await agent.selectSession(target)
}

async function selectSessionFromRoute(): Promise<boolean> {
  const querySessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  if (!querySessionId) return false
  const target = agent.sessions.value.find(session => session.id === querySessionId)
  if (!target) return false
  await selectSessionTarget(target)
  return true
}

function showNewConversationHome(): void {
  agent.beginNewSession()
  hasInteracted.value = false
  inputText.value = ''
}

function openRenameSession(session: { id: string; name: string }) {
  renameDialog.value = session
  renameValue.value = session.name
  nextTick(() => document.querySelector<HTMLInputElement>('[data-session-rename-input]')?.focus())
}

async function confirmRenameSession() {
  const session = renameDialog.value
  const title = renameValue.value.trim()
  if (!session || !title || title === session.name) {
    renameDialog.value = null
    return
  }
  await agent.renameSession(session.id, title)
  renameDialog.value = null
}

function openDeleteSession(session: { id: string; name: string }) {
  deleteDialog.value = session
}

async function confirmDeleteSession() {
  const session = deleteDialog.value
  if (!session) return
  await agent.deleteSession(session.id)
  deleteDialog.value = null
}

function selectModel(model: { provider: string; id: string }) {
  modelMenuOpen.value = false
  void agent.changeModel(model.provider, model.id)
}

function handleVisibilityChange() {
  if (document.hidden) agent.pauseTypewriter?.()
  else agent.resumeTypewriter?.()
}

onMounted(async () => {
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  observePromptInput()
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  if (await selectSessionFromRoute()) return
  showNewConversationHome()
})

onActivated(() => {
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  agent.resumeTypewriter?.()
  void nextTick(() => observePromptInput())
  if (route.query.session_id) void selectSessionFromRoute()
  else showNewConversationHome()
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', handleWorkspacePointerMove)
  window.removeEventListener('pointerup', stopWorkspaceResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  promptResizeObserver?.disconnect()
  promptResizeObserver = null
})

onDeactivated(() => {
  window.removeEventListener('pointermove', handleWorkspacePointerMove)
  window.removeEventListener('pointerup', stopWorkspaceResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  promptResizeObserver?.disconnect()
  promptResizeObserver = null
  agent.pauseTypewriter?.()
})

watch(
  () => route.query.session_id,
  sessionId => {
    if (sessionId) void selectSessionFromRoute()
    else showNewConversationHome()
  }
)

watch(inputText, () => {
  void nextTick(() => resizePromptInput())
})

watch(hasContent, () => {
  void nextTick(() => observePromptInput())
})
</script>

<template>
  <div class="home-shell workspace-page-canvas" :class="hasContent ? 'is-conversation' : 'is-landing'">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sidebarSessions"
      :active-panel="sidebarActivePanel"
      session-actions
      session-create
      @switch-panel="switchPanel"
      @switch-session="switchSession"
      @create-session="createSessionForActiveMode"
      @rename-session="openRenameSession"
      @delete-session="openDeleteSession"
    />

    <main class="home-main">
      <div class="home-main__scroll">
        <section v-if="!hasContent" class="landing-document">
          <div class="landing-primary">
            <header class="landing-hero">
              <h1>让每一次投放，都有清晰的下一步</h1>
              <p>ANIFORCE 串联项目、计划、素材与效果数据，帮你完成复盘诊断、预算调控和创意迭代。</p>
            </header>

            <section v-if="!hasInteracted" class="quick-start" aria-label="常用投放策略">
              <div class="quick-start__header">
                <strong>常用投放策略</strong>
                <button
                  class="quick-start__toggle"
                  type="button"
                  :aria-expanded="strategyExpanded"
                  aria-controls="strategy-grid"
                  @click="strategyExpanded = !strategyExpanded"
                >
                  <span>{{ strategyExpanded ? '收起策略' : '展开更多策略' }}</span>
                  <span class="material-symbols-outlined" :class="{ expanded: strategyExpanded }" aria-hidden="true">expand_more</span>
                </button>
              </div>
              <div id="strategy-grid" class="quick-grid">
                <button
                  v-for="action in visibleStarterActions"
                  :key="action.label"
                  class="quick-card"
                  type="button"
                  @click="runStarterAction(action)"
                >
                  <span class="quick-card__icon" aria-hidden="true">
                    <span class="material-symbols-outlined">{{ action.icon }}</span>
                  </span>
                  <strong>{{ action.label }}</strong>
                  <span>{{ action.description }}</span>
                </button>
              </div>
            </section>
          </div>

          <div class="landing-input-dock" :class="{ 'is-expanded': isPromptExpanded }">
            <div class="composer" :class="{ 'composer--expanded': isPromptExpanded }" role="search">
              <button class="composer__icon" type="button" aria-label="添加附件">
                <span class="material-symbols-outlined">attach_file</span>
              </button>
              <textarea
                ref="promptInputRef"
                v-model="inputText"
                data-agent-input="home"
                aria-label="任务内容"
                placeholder="继续输入任务或补充信息..."
                rows="1"
                @input="handlePromptInput"
                @keydown="handlePromptKeydown"
              />
              <button class="composer__icon" type="button" aria-label="语音输入">
                <span class="material-symbols-outlined">mic</span>
              </button>
              <button
                class="composer__send"
                type="button"
                :disabled="agent.loading.value || agent.agentRunning.value || !inputText.trim()"
                aria-label="发送"
                @click="handleSubmit"
              >
                <span v-if="agent.loading.value || agent.agentRunning.value" class="composer__spinner"></span>
                <span v-else class="material-symbols-outlined">arrow_forward</span>
              </button>
            </div>
          </div>
        </section>

        <section v-else class="conversation-document">
          <div class="conversation-thread">
            <div class="message-stream">
              <div v-if="agent.loading.value" class="conversation-loading">
                <span class="conversation-loading__spinner"></span>
                <span>AI 正在分析中，请稍候...</span>
              </div>

              <section v-else-if="agent.error.value" class="conversation-error">
                <span class="material-symbols-outlined">error</span>
                <p>{{ agent.error.value }}</p>
              </section>

              <template v-else>
                <template v-for="(message, index) in agent.visibleMessages.value" :key="message.id || `${message.role}-${message.timestamp}-${index}`">
                  <MessageView
                    :message="message"
                    :tool-results="toolResults"
                    :model-names="agent.modelNames.value"
                    :prev-timestamp="index > 0 ? Number(agent.visibleMessages.value[index - 1].timestamp || 0) : undefined"
                  />
                </template>

                <MessageView
                  v-if="agent.streamingMessage.value"
                  :message="agent.streamingMessage.value"
                  is-streaming
                  :tool-results="toolResults"
                  :model-names="agent.modelNames.value"
                />

                <div v-if="agent.agentRunning.value && !agent.streamingMessage.value" class="conversation-loading">
                  <span class="conversation-loading__spinner"></span>
                  <span>{{ phaseLabel(agent.agentPhase.value) }}</span>
                </div>
              </template>
            </div>
          </div>
        </section>
      </div>

      <div v-if="hasContent" class="conversation-input-dock">
        <div class="composer conversation-composer" :class="{ 'composer--expanded': isPromptExpanded }" role="search">
          <button class="composer__icon" type="button" aria-label="添加附件">
            <span class="material-symbols-outlined">attach_file</span>
          </button>
          <textarea
            ref="promptInputRef"
            v-model="inputText"
            data-agent-input="home"
            aria-label="任务内容"
            placeholder="继续输入任务或补充信息..."
            rows="1"
            @input="handlePromptInput"
            @keydown="handlePromptKeydown"
          />
          <button class="composer__icon" type="button" aria-label="语音输入">
            <span class="material-symbols-outlined">mic</span>
          </button>
          <button
            class="composer__send"
            type="button"
            :disabled="agent.loading.value || agent.agentRunning.value || !inputText.trim()"
            aria-label="发送"
            @click="handleSubmit"
          >
            <span v-if="agent.loading.value || agent.agentRunning.value" class="composer__spinner"></span>
            <span v-else class="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>
    </main>

    <div
      v-if="hasContent && taskPanelVisible"
      class="workspace-column"
      :class="{ collapsed: workspaceCollapsed }"
      :style="workspaceStyle"
    >
      <button
        v-if="!workspaceCollapsed"
        class="workspace-resize-handle"
        type="button"
        aria-label="调整工作台宽度"
        @pointerdown="startWorkspaceResize"
      ></button>
      <LiveWorkspaceShell
        class="home-workspace"
        :visible="hasContent"
        :collapsed="workspaceCollapsed"
        :session-id="agent.activeSession.value?.id"
        :module-hint="workspaceModuleHint"
        :artifacts="taskArtifacts"
        :tool-results="agent.workspaceToolResults.value"
        @toggle-collapse="toggleWorkspaceCollapsed"
        @analyze-project="analyzeProject"
        @open-project="openProject"
      />
    </div>
  </div>

  <SessionRenameDialog
    v-model="renameValue"
    :show="Boolean(renameDialog)"
    @confirm="confirmRenameSession"
    @close="renameDialog = null"
  />

  <ConfirmDialog
    :show="Boolean(deleteDialog)"
    title="删除对话"
    :message="`确定删除对话「${deleteDialog?.name || ''}」吗？删除后将从历史会话中移除，且无法撤销。`"
    confirm-text="删除"
    cancel-text="取消"
    tone="danger"
    variant="notion"
    @confirm="confirmDeleteSession"
    @close="deleteDialog = null"
  />
</template>

<style scoped>
.home-shell {
  --notion-canvas: var(--workspace-canvas);
  --notion-surface: #f7f7f5;
  --notion-surface-soft: #fbfbfa;
  --notion-line: rgba(55, 53, 47, 0.12);
  --notion-line-strong: rgba(55, 53, 47, 0.22);
  --notion-ink: #1f1f1f;
  --notion-charcoal: #37352f;
  --notion-slate: #5d5b54;
  --notion-steel: #787671;
  --notion-stone: #a4a097;
  --notion-blue: #2383e2;
  --notion-blue-soft: #f0f7ff;
  --notion-green: #0f9d73;
  display: flex;
  width: 100%;
  height: calc(100dvh + 11.111111dvh);
  min-height: 0;
  overflow: hidden;
  background: var(--notion-canvas);
  color: var(--notion-charcoal);
  font-family: "Notion Sans", "Avenir Next", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.home-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  background: var(--notion-canvas);
}

.home-main__scroll {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  scrollbar-color: var(--notion-line-strong) transparent;
}

.landing-document {
  display: grid;
  width: min(100%, 1080px);
  min-height: 100%;
  grid-template-rows: minmax(min-content, 1fr) auto;
  gap: clamp(20px, 4vh, 52px);
  margin: 0 auto;
  padding: clamp(24px, 4vh, 56px) clamp(18px, 3vw, 36px) clamp(18px, 3vh, 36px);
  box-sizing: border-box;
}

.landing-primary {
  display: flex;
  width: 100%;
  min-width: 0;
  align-self: center;
  align-items: center;
  flex-direction: column;
  padding-block: clamp(18px, 4vh, 64px);
}

.landing-hero {
  max-width: 900px;
  text-align: center;
}

.landing-hero h1 {
  margin: 0;
  color: var(--notion-ink);
  font-size: clamp(28px, 3vw, 44px);
  font-weight: 600;
  line-height: 1.14;
  letter-spacing: -1px;
}

.landing-hero p {
  margin: 14px 0 0;
  color: var(--notion-steel);
  font-size: clamp(14px, 1.2vw, 16px);
  line-height: 1.6;
}

.home-shell.is-landing,
.home-shell.is-landing .home-main,
.home-shell.is-landing .home-main__scroll {
  background: var(--notion-canvas);
}

.composer {
  display: grid;
  width: 100%;
  min-height: 60px;
  grid-template-columns: 36px minmax(0, 1fr) 36px 38px;
  grid-template-rows: auto;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--notion-line-strong);
  border-radius: 12px;
  background: var(--notion-canvas);
  box-shadow: rgba(15, 15, 15, 0.06) 0 8px 24px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.composer:focus-within {
  border-color: #a9a7a2;
  box-shadow: rgba(35, 131, 226, 0.13) 0 0 0 2px, rgba(15, 15, 15, 0.08) 0 10px 28px;
}

.composer textarea {
  grid-row: 1;
  grid-column: 2;
  min-width: 0;
  width: 100%;
  min-height: 24px;
  align-self: center;
  padding: 0 8px;
  overflow: hidden;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--notion-ink);
  field-sizing: content;
  font-size: 15px;
  line-height: 1.55;
  resize: none;
}

.composer.composer--expanded {
  grid-template-rows: auto 38px;
  align-items: center;
  row-gap: 8px;
  padding: 14px 10px 8px;
}

.composer.composer--expanded textarea {
  grid-row: 1;
  grid-column: 1 / -1;
  align-self: stretch;
  padding: 0 12px;
}

.composer textarea::placeholder {
  color: var(--notion-stone);
}

.composer__icon,
.composer__send {
  display: grid;
  place-items: center;
  border: 0;
  cursor: pointer;
}

.composer__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  color: var(--notion-steel);
}

.composer > .composer__icon[aria-label="添加附件"] {
  grid-row: 1;
  grid-column: 1;
}

.composer > .composer__icon[aria-label="语音输入"] {
  grid-row: 1;
  grid-column: 3;
}

.composer.composer--expanded > .composer__icon[aria-label="添加附件"] {
  grid-row: 2;
}

.composer.composer--expanded > .composer__icon[aria-label="语音输入"] {
  grid-row: 2;
}

.composer__icon:hover {
  background: rgba(55, 53, 47, 0.06);
  color: var(--notion-ink);
}

.composer__icon .material-symbols-outlined {
  font-size: 19px;
}

.composer__send {
  width: 36px;
  height: 36px;
  grid-row: 1;
  grid-column: 4;
  border-radius: 50%;
  background: var(--notion-blue);
  color: #ffffff;
  transition: background 0.15s ease, transform 0.15s ease;
}

.composer.composer--expanded > .composer__send {
  grid-row: 2;
}

.composer__send:hover:not(:disabled) {
  background: #1b72c8;
  transform: translateY(-1px);
}

.composer__send:disabled {
  cursor: not-allowed;
  background: #a4a097;
  opacity: 1;
}

.composer__send .material-symbols-outlined {
  font-size: 19px;
}

.composer__spinner,
.conversation-loading__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 999px;
  animation: home-spin 0.8s linear infinite;
}

.landing-input-dock {
  width: min(100%, 860px);
  margin: 0 auto;
  align-self: end;
  transition: width 0.2s ease;
}

.landing-input-dock.is-expanded {
  width: min(100%, 1080px);
}

.quick-start {
  width: min(100%, 860px);
  margin: clamp(32px, 5vh, 56px) auto 0;
}

.quick-start__header {
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.quick-start__header strong {
  color: var(--notion-ink);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.quick-start__toggle {
  min-height: 34px;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 10px;
  border: 1px solid var(--notion-line);
  border-radius: 8px;
  background: var(--notion-canvas);
  color: var(--notion-slate);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.quick-start__toggle:hover {
  border-color: var(--notion-line-strong);
  background: var(--notion-surface-soft);
  color: var(--notion-ink);
}

.quick-start__toggle .material-symbols-outlined {
  font-size: 18px;
  transition: transform 0.18s ease;
}

.quick-start__toggle .material-symbols-outlined.expanded {
  transform: rotate(180deg);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-card {
  display: flex;
  min-height: 158px;
  flex-direction: column;
  align-items: flex-start;
  padding: 19px;
  border: 1px solid #e5e3df;
  border-radius: 12px;
  background: #ffffff;
  color: var(--notion-charcoal);
  cursor: pointer;
  text-align: left;
  box-shadow: none;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.quick-card:hover {
  border-color: #c8c4be;
  background: #fafaf9;
  transform: translateY(-1px);
  box-shadow: rgba(15, 15, 15, 0.06) 0 4px 10px;
}

.quick-card__icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  margin-bottom: 18px;
  background: transparent;
  color: var(--notion-charcoal);
  box-shadow: none;
}

.quick-card__icon .material-symbols-outlined {
  color: var(--notion-charcoal);
  font-size: 34px;
  font-variation-settings: 'FILL' 0, 'wght' 420, 'GRAD' 0, 'opsz' 32;
}

.quick-card strong {
  margin-bottom: 7px;
  color: var(--notion-ink);
  font-size: 15px;
  font-weight: 600;
}

.quick-card > span:last-child {
  display: -webkit-box;
  overflow: hidden;
  color: rgba(55, 53, 47, 0.72);
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.conversation-document {
  min-height: 100%;
  padding: 34px clamp(24px, 5vw, 72px) 72px;
  background: var(--notion-canvas);
}

.conversation-thread {
  width: min(100%, 880px);
  margin: 0 auto;
}

.message-stream {
  margin-top: 0;
}

.conversation-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 28px 0;
  color: var(--notion-steel);
  font-size: 11px;
}

.conversation-loading__spinner {
  color: var(--notion-blue);
}

.conversation-error {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 14px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff7f7;
  color: #b42318;
  font-size: 13px;
}

.conversation-error .material-symbols-outlined {
  font-size: 17px;
}

.conversation-error p {
  margin: 0;
}

.conversation-input-dock {
  flex: 0 0 auto;
  padding: 10px clamp(24px, 3vw, 48px) 16px;
  border-top: 0;
  background: var(--notion-canvas);
}

.conversation-composer {
  width: min(100%, 720px);
  margin: 0 auto;
  background: #ffffff;
  transition: width 0.2s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.conversation-composer.composer--expanded {
  width: min(100%, 960px);
}

.conversation-thread :deep(.user-message) {
  margin: 34px 0 24px;
}

.conversation-thread :deep(.user-bubble) {
  max-width: min(92%, 610px);
  padding: 12px 15px;
  border: 1px solid #d1e4fa;
  border-radius: 8px;
  background: var(--notion-blue-soft);
  color: var(--notion-charcoal);
  font-size: 14px;
  line-height: 1.55;
  box-shadow: rgba(15, 15, 15, 0.04) 0 1px 2px;
}

.conversation-thread :deep(.user-bubble:hover) {
  transform: none;
  box-shadow: rgba(15, 15, 15, 0.04) 0 1px 2px;
}

.conversation-thread :deep(.assistant-message) {
  margin-bottom: 42px;
  color: var(--notion-charcoal);
}

.conversation-thread :deep(.assistant-block-list) {
  gap: 7px;
}

.conversation-thread :deep(.markdown-body) {
  color: var(--notion-charcoal);
  font-size: 14px;
  line-height: 1.65;
}

.conversation-thread :deep(.activity-message-wrapper) {
  margin: 7px 0;
}

.conversation-thread :deep(.activity-card),
.conversation-thread :deep(.tool-call-block),
.conversation-thread :deep(.thinking-block) {
  border: 1px solid rgba(55, 53, 47, 0.1);
  border-radius: 6px;
  background: var(--notion-surface-soft);
  box-shadow: none;
}

.conversation-thread :deep(.activity-card) {
  padding: 9px 11px;
}

.conversation-thread :deep(.tool-header),
.conversation-thread :deep(.thinking-header) {
  min-height: 35px;
  padding: 0 11px;
}

.conversation-thread :deep(.tool-name),
.conversation-thread :deep(.activity-tool) {
  font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
  font-size: 11px;
  font-weight: 600;
}

.conversation-thread :deep(.tool-status-dot.done),
.conversation-thread :deep(.status-dot-completed) {
  background: var(--notion-green);
}

.conversation-thread :deep(.assistant-footer),
.conversation-thread :deep(.message-actions) {
  color: var(--notion-stone);
  font-size: 10px;
}

.workspace-column {
  position: relative;
  min-width: 360px;
  flex: 0 0 auto;
  border-left: 1px solid var(--notion-line);
  background: var(--notion-surface-soft);
}

.workspace-column.collapsed {
  min-width: 56px;
}

.workspace-resize-handle {
  position: absolute;
  z-index: 5;
  top: 0;
  bottom: 0;
  left: -3px;
  width: 6px;
  border: 0;
  background: transparent;
  cursor: col-resize;
}

.workspace-resize-handle:hover {
  background: rgba(35, 131, 226, 0.16);
}

.home-workspace {
  width: 100%;
  height: 100%;
  border-left: 0 !important;
  background: var(--notion-surface-soft) !important;
}

.home-workspace :deep(header) {
  background: rgba(255, 255, 255, 0.72) !important;
  border-color: var(--notion-line) !important;
}

.home-workspace :deep(main) {
  background: var(--notion-surface-soft);
}

.home-workspace :deep(footer) {
  border-color: var(--notion-line) !important;
  background: #ffffff !important;
}

@keyframes home-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1279px) {
  .workspace-column {
    display: none;
  }
}

@media (min-width: 1280px) and (max-width: 1399px) {
  .conversation-document,
  .conversation-input-dock {
    padding-right: 32px;
    padding-left: 32px;
  }
}

@media (max-width: 980px) {
  .landing-document {
    gap: 28px;
    padding: 32px 24px 24px;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .home-shell {
    height: calc(100dvh + 11.111111dvh);
  }

  .landing-document {
    margin: 0 auto;
    gap: 24px;
    padding: 24px 20px 18px;
  }

  .landing-hero h1 {
    font-size: clamp(27px, 7vw, 34px);
  }

  .conversation-document {
    padding: 30px 18px 40px;
  }

  .conversation-input-dock {
    padding: 12px 18px 14px;
  }
}

@media (max-width: 520px) {
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .quick-card {
    min-height: 140px;
  }

  .quick-start__header {
    align-items: flex-start;
  }

  .composer {
    min-height: 60px;
    grid-template-columns: 34px minmax(0, 1fr) 34px 38px;
    padding: 8px;
    border-radius: 12px;
  }

  .conversation-input-dock {
    padding-right: 14px;
    padding-left: 14px;
  }
}

@media (max-height: 820px) and (min-width: 981px) {
  .landing-document {
    gap: 18px;
    padding-top: 18px;
    padding-bottom: 18px;
  }

  .landing-primary {
    padding-block: 0;
  }

  .landing-hero h1 {
    font-size: 32px;
  }

  .landing-hero p {
    margin-top: 8px;
    font-size: 14px;
  }

  .quick-start {
    margin-top: 22px;
  }

  .quick-card {
    min-height: 124px;
    padding: 14px;
  }

  .quick-card__icon {
    width: 32px;
    height: 32px;
    margin-bottom: 10px;
  }

  .quick-card__icon .material-symbols-outlined {
    font-size: 30px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-shell *,
  .home-shell *::before,
  .home-shell *::after {
    transition-duration: 0.01ms !important;
  }
}
</style>
