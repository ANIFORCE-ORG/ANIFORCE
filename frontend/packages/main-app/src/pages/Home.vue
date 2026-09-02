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
import { resolveHomeSessionState, shouldApplyHomeSessionState } from '@/agent/homeSessionState'
import { normalizeTaskPanelStatus, type TaskPresentationStatus } from '@/agent/taskPresentation'
import { getHiddenToolActivity, getToolPresentation } from '@/utils/toolNameMapping'
import { useAgentSession, type AgentPhase, type AgentRouteContext } from '@/composables/useAgentSession'
import type { AgentMessage } from '@/api/agent'
import { workspaceResultProjectionRegistry } from '@/store/workspace'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()
const agent = useAgentSession()
const inputText = ref('')
const conversationScroll = ref<HTMLElement | null>(null)
const hasInteracted = ref(false)
const modelMenuOpen = ref(false)
const activeIntentMode = ref<'chat' | 'project'>('chat')
const selectedStarterAction = ref<string | null>(null)
const composerInput = ref<HTMLTextAreaElement | null>(null)
const composerIsComposing = ref(false)
const workspaceCollapsed = ref(true)
const workspaceManuallyCollapsed = ref(false)
const workspaceWidth = ref(Number(localStorage.getItem('aniforce.workspace.width') || 470))
const workspacePreviousWidth = ref(workspaceWidth.value)
const workspaceMaximized = ref(false)
const isDesktopWorkspaceViewport = ref(window.matchMedia('(min-width: 1280px)').matches)
const seenWorkspaceProjectionBySession = ref<Record<string, string>>({})
const workspaceDragging = ref(false)
const renameDialog = ref<{ id: string; name: string } | null>(null)
const renameValue = ref('')
const deleteDialog = ref<{ id: string; name: string } | null>(null)
const strategyExpanded = ref(false)
const sessionsReady = ref(false)
let skippedRouteSessionId: string | null = null
let composerCompositionEndedAt = 0

type MentionEntity = { type: 'project' | 'campaign' | 'material'; id: string; name?: string }

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
    prompt: '请复盘当前账号最近 7 天的投放表现。按真实可用维度汇总消耗、转化、CPA、CTR 与 ROAS；先校验数据完整性和归因成熟度，再将计划分为「可放量 / 观察 / 控量 / 暂停」，说明判断依据，并给出未来 24 小时可执行的调整清单。若缺少业务类型、目标值或日期范围，请先向我确认。',
    mode: 'chat' as const
  },
  {
    icon: 'tune',
    label: '计划分层调控',
    description: '识别可放量、观察、控量和暂停计划。',
    prompt: '请诊断当前广告计划表现，并按「可放量 / 观察 / 控量 / 暂停」输出清单。综合真实消耗、转化量、CPA、CTR、ROAS、趋势和样本量判断；说明关键证据并给出明确动作。数据不足或归因未成熟的计划请标记为待观察，不要补造指标。',
    mode: 'chat' as const
  },
  {
    icon: 'image_search',
    label: '素材表现诊断',
    description: '基于可关联数据定位素材机会和风险。',
    prompt: '请分析当前素材表现，识别高潜、低效和需要迭代的素材，并给出下一批素材的选题、开头钩子、卖点与 A/B 变量建议。仅使用能够真实关联到素材维度的数据；如果当前数据无法稳定关联素材，请明确说明限制，不要推导 ROAS、疲劳度或评分。',
    mode: 'chat' as const
  },
  {
    icon: 'account_balance_wallet',
    label: '预算扩量建议',
    description: '找到预算承接空间，制定阶梯扩量与止损线。',
    prompt: '请评估当前投放的预算承接能力，并制定未来 3 天的阶梯扩量方案。找出效率达标且转化稳定的计划，给出预算调整区间、观察周期、回撤条件和止损线。仅依据真实投放数据判断，缺少目标 CPA 或 ROAS 时先向我确认。',
    mode: 'chat' as const
  },
  {
    icon: 'compare_arrows',
    label: '渠道效果对比',
    description: '对比已接入渠道的效率、量级和稳定性。',
    prompt: '请对比已授权且存在真实事实数据的投放渠道最近 7 天与前 7 天表现，统一指标口径后评估消耗、转化量、CPA、CTR、ROAS、趋势和稳定性，并给出预算迁移建议。没有接入或没有真实数据的渠道请标记为不可比较，不要估算数值。',
    mode: 'chat' as const
  },
  {
    icon: 'warning',
    label: '异常波动排查',
    description: '定位消耗、成本或转化突变的可能原因。',
    prompt: '请排查当前投放中的异常波动。对比最近 24 小时、近 3 天均值和上周同期，识别消耗、成本、点击或转化的显著变化；按数据归因、账户审核、预算出价、流量和素材逐层列出证据、影响范围、排查顺序及可立即执行的恢复动作。',
    mode: 'chat' as const
  },
  {
    icon: 'schedule',
    label: '素材更新节奏',
    description: '根据真实信号安排素材观察、迭代和替换。',
    prompt: '请基于当前真实可用的素材表现数据制定素材更新节奏，输出继续观察、优先迭代和建议替换的清单。只有在具备素材级连续趋势时才判断疲劳；如果数据无法稳定关联到素材，请说明缺失字段，并先给出不依赖虚假评分的创意迭代方案。',
    mode: 'chat' as const
  },
  {
    icon: 'experiment',
    label: '下一轮测试方案',
    description: '把诊断结论转成可执行的 A/B 测试矩阵。',
    prompt: '请基于当前投放问题设计下一轮 A/B 测试方案。明确核心假设，并为素材、受众、版位、出价或落地页设计单变量测试；给出测试组、对照组、预算、观察周期、成功指标和停止条件。按影响力与实施成本排序，优先输出本周可落地的 3 至 5 个实验。',
    mode: 'chat' as const
  }
]

const visibleStarterActions = computed(() => strategyExpanded.value ? starterActions : starterActions.slice(0, 4))
const isPromptExpanded = computed(() => Array.from(inputText.value).length > 72 || inputText.value.includes('\n'))
const visibleMessages = computed(() => agent.visibleMessages.value)
const hasContent = computed(() => (
  Boolean(hasInteracted.value && agent.activeSession.value) ||
  agent.loading.value ||
  agent.hasAnyRunningRun.value ||
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
const activeMode = computed(() => intentModes.find(item => item.key === activeIntentMode.value) || intentModes[0])
const starterActionHint = computed(() => {
  if (!selectedStarterAction.value) return ''
  if (activeIntentMode.value === 'project') {
    return '可继续补充产品、市场或预算；结构化字段将在工作台中编辑。'
  }
  return '任务描述已填入，可以修改后发送。'
})
const activeRoute = computed(() => {
  const { titlePrefix: _titlePrefix, ...route } = activeMode.value.route
  return route
})
const activeSessionId = computed(() => agent.activeSession.value?.id || '')
const currentTask = computed(() => agent.currentTask.value)
const workspaceProjection = computed(() => agent.workspaceProjection.value)
const workspaceApprovalDraft = computed(() => agent.workspaceApprovalDraft.value)
const workspaceUpdating = computed(() => {
  const draftStatus = workspaceApprovalDraft.value?.status
  if (draftStatus === 'executing' || draftStatus === 'approved') return true
  if (!agent.agentRunning.value || agent.agentPhase.value?.kind !== 'running_tools') return false
  return agent.agentPhase.value.tools.some(tool => (
    tool.name === 'request_workspace_projection'
    || Boolean(workspaceResultProjectionRegistry[tool.name])
  ))
})
const workspaceHasNewResult = computed(() => {
  const projection = workspaceProjection.value
  if (!projection) return false
  return seenWorkspaceProjectionBySession.value[activeSessionId.value] !== projection.id
})
const workspaceAttention = computed<'idle' | 'updating' | 'new' | 'approval' | 'executing' | 'error'>(() => {
  const draftStatus = workspaceApprovalDraft.value?.status
  if (draftStatus === 'pending') return 'approval'
  if (draftStatus === 'executing' || draftStatus === 'approved') return 'executing'
  if (workspaceProjection.value?.mode === 'failed') return 'error'
  if (workspaceUpdating.value) return 'updating'
  if (workspaceHasNewResult.value) return 'new'
  return 'idle'
})
const workspaceStatusLabel = computed(() => ({
  idle: '',
  updating: workspaceProjection.value ? '更新中' : '准备中',
  new: '',
  approval: '需要确认',
  executing: '执行中',
  error: '未完成',
})[workspaceAttention.value])
const workspaceEffectiveCollapsed = computed(() => workspaceCollapsed.value)
const runningSession = computed(() => agent.sessions.value.find(session => session.id === agent.activeRunSessionId.value) || null)
const workspaceStyle = computed(() => ({
  width: workspaceEffectiveCollapsed.value ? '0px' : `${workspaceWidth.value}px`
}))
const taskStatus = computed<TaskPresentationStatus>(() => {
  if (currentTask.value?.status) return normalizeTaskPanelStatus(currentTask.value.status)
  if (agent.error.value) return 'failed'
  if (agent.agentRunning.value) return agent.agentPhase.value?.kind === 'running_tools' ? 'running' : 'running'
  if (visibleMessages.value.length > 1) return 'completed'
  if (visibleMessages.value.length > 0 || hasInteracted.value) return 'created'
  return 'created'
})
const hasPendingApprovalMessage = computed(() => {
  const streaming = agent.streamingMessage.value
  const messages = streaming ? [...visibleMessages.value, streaming] : visibleMessages.value
  return messages.some(message => (
    Array.isArray(message.content)
    && message.content.some(block => {
      const item = block as Record<string, unknown>
      return item?.type === 'approval' && String(item.status || 'pending') === 'pending'
    })
  ))
})
const approvalNoticeVisible = computed(() => {
  if (hasPendingApprovalMessage.value) return false
  const draft = agent.workspaceApprovalDraft.value
  return draft ? draft.status === 'pending' : taskStatus.value === 'waiting_approval'
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
const selectedContextEntities = computed(() => agent.workspaceSelectedEntities.value)
const projectionContextEntities = computed<MentionEntity[]>(() => {
  const payload = agent.workspaceProjection.value?.payload || {}
  const collections: Array<{ type: MentionEntity['type']; items: unknown }> = [
    { type: 'project', items: payload.projects },
    { type: 'campaign', items: payload.campaigns },
    { type: 'material', items: payload.materials },
  ]
  return collections.flatMap(({ type, items }) => Array.isArray(items)
    ? items.flatMap((item: any) => item?.id
      ? [{ type, id: String(item.id), name: String(item.name || item.id) }]
      : [])
    : [])
})
const mentionCandidates = computed<MentionEntity[]>(() => projectionContextEntities.value)
const mentionQuery = computed(() => {
  const match = /(?:^|\s)@([^\s@]*)$/.exec(inputText.value)
  return match ? match[1].toLowerCase() : null
})
const filteredMentionCandidates = computed(() => {
  if (mentionQuery.value === null) return []
  const query = mentionQuery.value
  return mentionCandidates.value
    .filter(item => !query || (item.name || item.id).toLowerCase().includes(query) || item.id.toLowerCase().includes(query))
    .slice(0, 6)
})
const showMentionPanel = computed(() => mentionQuery.value !== null && filteredMentionCandidates.value.length > 0)

function scrollToBottom(behavior: ScrollBehavior = 'smooth') {
  nextTick(() => {
    window.requestAnimationFrame(() => {
      const container = conversationScroll.value
      if (!container) return
      container.scrollTo({ top: container.scrollHeight, behavior })
    })
  })
}

function phaseLabel(phase: AgentPhase): string {
  if (phase?.kind === 'queued') return '任务已入队，正在等待执行...'
  if (phase?.kind === 'running_tools') {
    if (!phase.tools.length) return '正在处理任务...'
    if (phase.tools.length > 1) return `正在并行处理 ${phase.tools.length} 项任务...`
    const toolName = phase.tools[0].name
    const hidden = getHiddenToolActivity(toolName, 'running')
    if (hidden) return `${hidden.label}...`
    return `${getToolPresentation(toolName, 'running').title}...`
  }
  if (phase?.kind === 'waiting_model') return '正在分析和整理结果...'
  return '正在处理任务...'
}

function clampWorkspaceWidth(value: number): number {
  const viewportMax = Math.max(360, Math.min(1200, window.innerWidth - 620))
  return Math.min(Math.max(value, 360), viewportMax)
}

function handleWorkspaceViewportResize(): void {
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  isDesktopWorkspaceViewport.value = window.matchMedia('(min-width: 1280px)').matches
  if (isDesktopWorkspaceViewport.value && !workspaceCollapsed.value) markWorkspaceProjectionSeen()
}

function persistWorkspaceState() {
  localStorage.setItem('aniforce.workspace.width', String(workspaceWidth.value))
  localStorage.setItem('aniforce.workspace.collapsed', workspaceCollapsed.value ? '1' : '0')
}

function markWorkspaceProjectionSeen(): void {
  const projection = workspaceProjection.value
  const sessionId = activeSessionId.value
  if (!projection || !sessionId) return
  seenWorkspaceProjectionBySession.value = {
    ...seenWorkspaceProjectionBySession.value,
    [sessionId]: projection.id,
  }
}

function toggleWorkspaceCollapsed() {
  workspaceCollapsed.value = !workspaceCollapsed.value
  workspaceManuallyCollapsed.value = workspaceCollapsed.value
  if (!workspaceCollapsed.value) markWorkspaceProjectionSeen()
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
  workspaceMaximized.value = false
  workspaceDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  event.currentTarget instanceof HTMLElement && event.currentTarget.setPointerCapture?.(event.pointerId)
  event.preventDefault()
}

function handleWorkspaceResizeKeydown(event: KeyboardEvent) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
  event.preventDefault()
  const direction = event.key === 'ArrowLeft' ? 1 : -1
  const step = event.shiftKey ? 96 : 32
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value + direction * step)
  persistWorkspaceState()
}

function resetWorkspaceWidth() {
  workspaceMaximized.value = false
  workspaceWidth.value = clampWorkspaceWidth(720)
  persistWorkspaceState()
}

function toggleWorkspaceMaximized() {
  if (workspaceMaximized.value) {
    workspaceWidth.value = clampWorkspaceWidth(workspacePreviousWidth.value)
    workspaceMaximized.value = false
  } else {
    workspacePreviousWidth.value = workspaceWidth.value
    workspaceWidth.value = clampWorkspaceWidth(1200)
    workspaceMaximized.value = true
  }
  persistWorkspaceState()
}

function resizeComposer(target: HTMLTextAreaElement | null = composerInput.value): void {
  if (!target) return
  target.style.height = 'auto'
  const nextHeight = Math.min(target.scrollHeight, 112)
  target.style.height = `${Math.max(nextHeight, 42)}px`
  target.style.overflowY = target.scrollHeight > 112 ? 'auto' : 'hidden'
}

function handleComposerInput(event: Event): void {
  resizeComposer(event.currentTarget as HTMLTextAreaElement)
}

function handleComposerCompositionStart(): void {
  composerIsComposing.value = true
}

function handleComposerCompositionEnd(): void {
  composerIsComposing.value = false
  composerCompositionEndedAt = Date.now()
}

function handleComposerKeydown(event: KeyboardEvent): void {
  const justConfirmedComposition = Date.now() - composerCompositionEndedAt < 120
  if (composerIsComposing.value || event.isComposing || event.keyCode === 229 || justConfirmedComposition || event.shiftKey) return
  event.preventDefault()
  void handleSubmit()
}

async function handleSubmit() {
  const message = inputText.value.trim()
  if (composerIsComposing.value || !message || agent.loading.value || agent.hasAnyRunningRun.value) return
  if (!agent.activeSession.value) {
    await agent.createSession(activeRoute.value)
    const sessionId = activeSessionId.value
    if (!sessionId) return
    skippedRouteSessionId = sessionId
    await router.replace({ path: '/home', query: { session_id: sessionId } })
  }
  hasInteracted.value = true
  selectedStarterAction.value = null
  inputText.value = ''
  await nextTick()
  resizeComposer()
  scrollToBottom()
  await agent.send(message, undefined, activeRoute.value)
  scrollToBottom()
}

async function runStarterAction(action: typeof starterActions[number]) {
  activeIntentMode.value = action.mode
  selectedStarterAction.value = action.label
  inputText.value = action.prompt
  await nextTick()
  resizeComposer()
  composerInput.value?.focus()
  composerInput.value?.setSelectionRange(inputText.value.length, inputText.value.length)
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

function openMaterial(materialId: string): void {
  if (!materialId) return
  navigateTo(`/material?material_id=${encodeURIComponent(materialId)}`)
}

function editProject(projectId: string): void {
  if (!projectId) return
  navigateTo(`/projects?editProjectId=${encodeURIComponent(projectId)}`)
}

function createProjectTask(projectId: string): void {
  if (!projectId) return
  void router.push({ path: '/projects', query: { createCampaignFor: projectId } })
}

function viewProjectTasks(projectId: string): void {
  if (!projectId) return
  navigateTo(`/projects/${encodeURIComponent(projectId)}`)
}

function openCampaign(campaignId: string): void {
  if (!campaignId) return
  navigateTo(`/campaigns/${encodeURIComponent(campaignId)}`)
}

function entityTypeLabel(type: MentionEntity['type']): string {
  if (type === 'project') return '项目'
  if (type === 'campaign') return '广告计划'
  return '素材'
}

function entityTypeIcon(type: MentionEntity['type']): string {
  if (type === 'project') return 'folder_managed'
  if (type === 'campaign') return 'campaign'
  return 'video_library'
}

function appendMentionToInput(entity: MentionEntity): void {
  agent.selectWorkspaceEntity(entity)
  const label = entity.name || entity.id
  const mention = `@${label}`
  if (inputText.value.match(/(?:^|\s)@[^\s@]*$/)) {
    inputText.value = inputText.value.replace(
      /(?:^|\s)@[^\s@]*$/,
      match => `${match.startsWith(' ') ? ' ' : ''}${mention} `,
    )
  } else if (!inputText.value.trim()) {
    inputText.value = `${mention} `
  } else if (!inputText.value.includes(mention)) {
    inputText.value = `${inputText.value.trimEnd()} ${mention} `
  }
  nextTick(() => {
    const input = document.querySelector<HTMLTextAreaElement>('[data-agent-input="home"]')
    resizeComposer(input)
    input?.focus()
  })
}

function removeContextEntity(entity: MentionEntity): void {
  agent.unselectWorkspaceEntity(entity)
  const label = entity.name || entity.id
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  inputText.value = inputText.value
    .replace(new RegExp(`(^|\\s)@${escaped}(?=\\s|$)`, 'g'), ' ')
    .replace(/\s{2,}/g, ' ')
    .trimStart()
}

function handleTaskAction(action: 'abort' | 'open_approval') {
  if (action === 'abort') {
    void agent.abort()
    return
  }
  workspaceCollapsed.value = false
  workspaceManuallyCollapsed.value = false
  markWorkspaceProjectionSeen()
  persistWorkspaceState()
}

const switchPanel = (item: any) => {
  if (item.id === 'new-task') {
    void createChatSession()
    return
  }
  if (item.path) {
    router.push(item.path)
  }
}

async function createSessionForActiveMode() {
  if (!agent.beginNewSession()) {
    await openRunningSession()
    return
  }
  hasInteracted.value = false
  selectedStarterAction.value = null
  inputText.value = ''
  workspaceCollapsed.value = true
  workspaceManuallyCollapsed.value = false
  persistWorkspaceState()
  if (route.path !== '/home' || route.query.session_id) await router.push('/home')
}

async function createChatSession() {
  activeIntentMode.value = 'chat'
  await createSessionForActiveMode()
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
  scrollToBottom('auto')
}

async function applyHomeSessionState(): Promise<void> {
  if (!sessionsReady.value || !shouldApplyHomeSessionState(route.path)) return
  const querySessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  const savedSessionId = localStorage.getItem('aniforce.activeSessionId')
  const decision = resolveHomeSessionState(
    querySessionId,
    agent.sessions.value.map(session => session.id),
    savedSessionId,
  )
  if (decision.kind === 'draft') {
    const openedDraft = showNewConversationHome()
    if (openedDraft && decision.clearRoute) await router.replace('/home')
    return
  }
  const target = agent.sessions.value.find(session => session.id === decision.sessionId)
  if (!target) return
  if (decision.syncRoute) {
    skippedRouteSessionId = decision.sessionId
    await router.replace({ path: '/home', query: { session_id: decision.sessionId } })
  }
  await selectSessionTarget(target)
}

function showNewConversationHome(): boolean {
  if (!agent.beginNewSession()) {
    void openRunningSession()
    return false
  }
  hasInteracted.value = false
  selectedStarterAction.value = null
  inputText.value = ''
  workspaceCollapsed.value = true
  workspaceManuallyCollapsed.value = false
  persistWorkspaceState()
  return true
}

async function openRunningSession(): Promise<void> {
  const sessionId = agent.activeRunSessionId.value
  if (!sessionId) return
  if (route.path === '/home' && route.query.session_id === sessionId) return
  await router.push({ path: '/home', query: { session_id: sessionId } })
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
  if (session.id === agent.activeRunSessionId.value) {
    deleteDialog.value = null
    await openRunningSession()
    return
  }
  await agent.deleteSession(session.id)
  deleteDialog.value = null
  const activeSessionId = agent.activeSession.value?.id
  if (activeSessionId) {
    skippedRouteSessionId = activeSessionId
    await router.replace({ path: '/home', query: { session_id: activeSessionId } })
  } else {
    await router.replace('/home')
  }
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
  handleWorkspaceViewportResize()
  window.addEventListener('resize', handleWorkspaceViewportResize)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  sessionsReady.value = true
  await applyHomeSessionState()
})

onActivated(() => {
  handleWorkspaceViewportResize()
  window.addEventListener('resize', handleWorkspaceViewportResize)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  agent.resumeTypewriter?.()
  if (sessionsReady.value) void applyHomeSessionState()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWorkspaceViewportResize)
  window.removeEventListener('pointermove', handleWorkspacePointerMove)
  window.removeEventListener('pointerup', stopWorkspaceResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

onDeactivated(() => {
  window.removeEventListener('resize', handleWorkspaceViewportResize)
  window.removeEventListener('pointermove', handleWorkspacePointerMove)
  window.removeEventListener('pointerup', stopWorkspaceResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  agent.pauseTypewriter?.()
})

watch(
  () => route.query.session_id,
  sessionId => {
    if (!sessionsReady.value || !shouldApplyHomeSessionState(route.path)) return
    if (typeof sessionId === 'string' && sessionId === skippedRouteSessionId) {
      skippedRouteSessionId = null
      return
    }
    void applyHomeSessionState()
  }
)

watch(
  () => [activeSessionId.value, workspaceProjection.value?.id || ''] as const,
  ([sessionId, projectionId], previous) => {
    if (!projectionId) return
    if (previous && sessionId === previous[0] && projectionId === previous[1]) return
    workspaceManuallyCollapsed.value = false
    workspaceCollapsed.value = false
    if (isDesktopWorkspaceViewport.value) {
      markWorkspaceProjectionSeen()
    }
    persistWorkspaceState()
  },
  { immediate: true },
)

watch(
  () => taskStatus.value === 'waiting_approval' || workspaceApprovalDraft.value?.status === 'pending',
  needsApproval => {
    if (!needsApproval || !workspaceCollapsed.value || workspaceManuallyCollapsed.value) return
    workspaceCollapsed.value = false
    markWorkspaceProjectionSeen()
    persistWorkspaceState()
  },
  { immediate: true },
)
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
      <div ref="conversationScroll" class="home-main__scroll">
        <section v-if="!hasContent" class="landing-document">
          <div class="landing-primary">
            <header class="landing-hero">
              <h1>让每一次投放，都有清晰的下一步</h1>
              <p>ANIFORCE 串联项目、计划、素材与效果数据，帮你完成复盘诊断、预算调控和创意迭代。</p>
            </header>

            <section v-if="!hasInteracted" class="quick-start" aria-label="常用投放策略">
              <div class="quick-start__header">
                <strong>常用投放策略</strong>
                <button class="quick-start__toggle" type="button" :aria-expanded="strategyExpanded" aria-controls="strategy-grid" @click="strategyExpanded = !strategyExpanded">
                  <span>{{ strategyExpanded ? '收起策略' : '展开更多策略' }}</span>
                  <span class="material-symbols-outlined" :class="{ expanded: strategyExpanded }" aria-hidden="true">expand_more</span>
                </button>
              </div>
              <div id="strategy-grid" class="quick-grid">
                <button
                  v-for="action in visibleStarterActions"
                  :key="action.label"
                  class="quick-card"
                  :class="{ 'is-selected': selectedStarterAction === action.label }"
                  type="button"
                  @click="runStarterAction(action)"
                >
                  <span class="quick-card__icon" aria-hidden="true"><span class="material-symbols-outlined">{{ action.icon }}</span></span>
                  <strong>{{ action.label }}</strong>
                  <span>{{ action.description }}</span>
                </button>
              </div>
            </section>
          </div>

          <div class="landing-input-dock" :class="{ 'is-expanded': isPromptExpanded }">
            <div v-if="starterActionHint" class="composer-intent-hint" role="status">
              <span class="material-symbols-outlined" aria-hidden="true">{{ activeMode.icon }}</span>
              <strong>{{ activeMode.label }}</strong>
              <span>{{ starterActionHint }}</span>
            </div>
            <div class="composer" :class="{ 'composer--expanded': isPromptExpanded }" role="search">
              <button class="composer__icon" type="button" aria-label="添加附件">
                <span class="material-symbols-outlined">attach_file</span>
              </button>
              <textarea
                ref="composerInput"
                v-model="inputText"
                data-agent-input="home"
                rows="1"
                aria-label="任务描述"
                placeholder="继续输入任务或补充信息..."
                @input="handleComposerInput"
                @compositionstart="handleComposerCompositionStart"
                @compositionend="handleComposerCompositionEnd"
                @keydown.enter="handleComposerKeydown"
              ></textarea>
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
            <section v-if="agent.runningInAnotherSession.value" class="cross-session-run" aria-live="polite">
              <span class="material-symbols-outlined">sync</span>
              <div>
                <strong>另一个对话正在运行</strong>
                <p>{{ runningSession?.title || 'Agent 任务' }}仍在后台执行，完成或停止后才能发起新任务。</p>
              </div>
              <button type="button" @click="openRunningSession">查看任务</button>
            </section>

            <div class="message-stream">
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

              <section v-if="agent.error.value" class="conversation-error">
                <span class="material-symbols-outlined">error</span>
                <p>{{ agent.error.value }}</p>
              </section>

              <div v-if="(agent.loading.value || agent.agentRunning.value) && !agent.streamingMessage.value" class="conversation-loading">
                <span class="conversation-loading__spinner"></span>
                <span>{{ agent.commandStatus.value || phaseLabel(agent.agentPhase.value) }}</span>
              </div>

              <section v-if="approvalNoticeVisible" class="conversation-approval-notice" role="status">
                <span class="material-symbols-outlined" aria-hidden="true">verified_user</span>
                <div>
                  <strong>等待你确认</strong>
                  <p>操作内容已在右侧工作台准备好，确认后才会继续执行。</p>
                </div>
                <button type="button" @click="handleTaskAction('open_approval')">查看</button>
              </section>
            </div>
          </div>
        </section>
      </div>

      <div v-if="hasContent" class="conversation-input-dock">
        <div class="composer-context">
          <div v-if="selectedContextEntities.length" class="context-entities">
            <span class="context-entities__label">上下文</span>
            <span
              v-for="entity in selectedContextEntities"
              :key="`${entity.type}:${entity.id}`"
              class="context-entity"
            >
              <span class="material-symbols-outlined">{{ entityTypeIcon(entity.type) }}</span>
              <span class="context-entity__name">{{ entity.name || entity.id }}</span>
              <button type="button" title="移除上下文" @click.stop.prevent="removeContextEntity(entity)">
                <span class="material-symbols-outlined">close</span>
              </button>
            </span>
          </div>

          <div v-if="showMentionPanel" class="mention-panel">
            <div class="mention-panel__title">从当前工作台选择上下文</div>
            <button
              v-for="entity in filteredMentionCandidates"
              :key="`${entity.type}:${entity.id}`"
              type="button"
              class="mention-panel__item"
              @click="appendMentionToInput(entity)"
            >
              <span class="material-symbols-outlined">{{ entityTypeIcon(entity.type) }}</span>
              <span class="mention-panel__name">{{ entity.name || entity.id }}</span>
              <span class="mention-panel__type">{{ entityTypeLabel(entity.type) }}</span>
            </button>
          </div>

          <div class="composer conversation-composer" role="search">
            <button class="composer__icon" type="button" aria-label="添加附件">
              <span class="material-symbols-outlined">attach_file</span>
            </button>
            <textarea
              ref="composerInput"
              v-model="inputText"
              data-agent-input="home"
              rows="1"
              aria-label="任务描述"
              placeholder="继续输入任务，或输入 @ 选择工作台上下文..."
              @input="handleComposerInput"
              @compositionstart="handleComposerCompositionStart"
              @compositionend="handleComposerCompositionEnd"
              @keydown.enter="handleComposerKeydown"
            ></textarea>
            <button class="composer__icon" type="button" aria-label="语音输入">
              <span class="material-symbols-outlined">mic</span>
            </button>
            <button
              v-if="agent.agentRunning.value"
              data-agent-action="cancel"
              class="composer__stop"
              type="button"
              title="停止任务"
              aria-label="停止任务"
              @click="handleTaskAction('abort')"
            >
              <span class="material-symbols-outlined">stop</span>
            </button>
            <button
              v-else
              data-agent-action="send"
              class="composer__send"
              type="button"
              :disabled="agent.loading.value || agent.hasAnyRunningRun.value || !inputText.trim()"
              aria-label="发送"
              @click="handleSubmit"
            >
              <span v-if="agent.loading.value" class="composer__spinner"></span>
              <span v-else class="material-symbols-outlined">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>
    </main>

    <div
      v-if="isDesktopWorkspaceViewport"
      class="workspace-column"
      :class="{ collapsed: workspaceEffectiveCollapsed }"
      :style="workspaceStyle"
    >
      <button
        v-if="!workspaceEffectiveCollapsed"
        class="workspace-resize-handle"
        type="button"
        role="separator"
        aria-label="调整工作台宽度"
        aria-orientation="vertical"
        aria-valuemin="360"
        aria-valuemax="1200"
        :aria-valuenow="workspaceWidth"
        title="拖动调整工作台宽度，双击恢复推荐宽度"
        @pointerdown="startWorkspaceResize"
        @keydown="handleWorkspaceResizeKeydown"
        @dblclick="resetWorkspaceWidth"
      ></button>
      <LiveWorkspaceShell
        class="home-workspace"
        visible
        :collapsed="workspaceEffectiveCollapsed"
        :can-expand="true"
        :maximized="workspaceMaximized"
        :session-id="agent.activeSession.value?.id"
        :projection="workspaceProjection"
        :approval-draft="workspaceApprovalDraft"
        :attention="workspaceAttention"
        :status-label="workspaceStatusLabel"
        @toggle-collapse="toggleWorkspaceCollapsed"
        @toggle-maximize="toggleWorkspaceMaximized"
        @approve="payload => agent.resolveWorkspaceApproval({ ...payload, runId: agent.workspaceApprovalDraft.value?.runId || '' })"
        @reject="checkpointId => agent.rejectWorkspaceApproval(checkpointId, agent.workspaceApprovalDraft.value?.runId || '')"
        @update-approval-form="payload => agent.updateApprovalDraftForm(payload.checkpointId, payload.formModel)"
        @select-entity="agent.selectWorkspaceEntity"
        @mention-entity="appendMentionToInput"
        @view-project="projectId => openProject({ id: projectId })"
        @edit-project="editProject"
        @create-project-task="createProjectTask"
        @view-project-tasks="viewProjectTasks"
        @view-campaign="openCampaign"
        @view-material="openMaterial"
      />
    </div>

    <LiveWorkspaceShell
      v-if="!isDesktopWorkspaceViewport"
      mobile
      visible
      :can-expand="true"
      :session-id="agent.activeSession.value?.id"
      :projection="workspaceProjection"
      :approval-draft="workspaceApprovalDraft"
      :attention="workspaceAttention"
      :status-label="workspaceStatusLabel"
      @opened="markWorkspaceProjectionSeen"
      @approve="payload => agent.resolveWorkspaceApproval({ ...payload, runId: workspaceApprovalDraft?.runId || '' })"
      @reject="checkpointId => agent.rejectWorkspaceApproval(checkpointId, workspaceApprovalDraft?.runId || '')"
      @update-approval-form="payload => agent.updateApprovalDraftForm(payload.checkpointId, payload.formModel)"
      @select-entity="agent.selectWorkspaceEntity"
      @mention-entity="appendMentionToInput"
      @view-project="projectId => openProject({ id: projectId })"
      @edit-project="editProject"
      @create-project-task="createProjectTask"
      @view-project-tasks="viewProjectTasks"
      @view-campaign="openCampaign"
      @view-material="openMaterial"
    />
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
  height: 100vh;
  min-height: 620px;
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
  gap: clamp(18px, 3vh, 36px);
  margin: 0 auto;
  padding: clamp(24px, 4vh, 56px) 36px clamp(18px, 3vh, 32px);
  box-sizing: border-box;
}

.landing-primary {
  display: flex;
  min-width: 0;
  align-self: center;
  align-items: center;
  flex-direction: column;
  padding-block: clamp(10px, 3vh, 44px);
}

.landing-hero {
  max-width: 900px;
  text-align: center;
}

.landing-hero h1 {
  margin: 0;
  color: var(--notion-ink);
  font-size: clamp(34px, 3.2vw, 46px);
  font-weight: 600;
  line-height: 1.14;
  letter-spacing: -1px;
}

.landing-hero p {
  margin: 14px 0 0;
  color: var(--notion-steel);
  font-size: 16px;
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
  grid-template-rows: minmax(42px, auto);
  align-items: end;
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
  width: 100%;
  min-width: 0;
  min-height: 42px;
  max-height: 112px;
  box-sizing: border-box;
  align-self: center;
  padding: 9px 8px;
  overflow-y: hidden;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--notion-ink);
  font: inherit;
  font-size: 15px;
  line-height: 1.55;
  resize: none;
}

.composer textarea::placeholder {
  color: var(--notion-stone);
}

.composer__icon,
.composer__send,
.composer__stop {
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

.composer__icon:hover {
  background: rgba(55, 53, 47, 0.06);
  color: var(--notion-ink);
}

.composer__icon .material-symbols-outlined {
  font-size: 19px;
}

.composer__send,
.composer__stop {
  width: 36px;
  height: 36px;
  grid-row: 1;
  grid-column: 4;
  border-radius: 50%;
  color: #ffffff;
  transition: background 0.15s ease, transform 0.15s ease;
}

.composer__send {
  background: var(--notion-blue);
}

.composer__stop {
  background: #dc2626;
}

.composer__stop:hover {
  background: #b91c1c;
  transform: translateY(-1px);
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

.composer__send .material-symbols-outlined,
.composer__stop .material-symbols-outlined {
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
  justify-self: center;
  padding-top: 0;
  transition: width .18s ease;
}

.landing-input-dock.is-expanded {
  width: min(100%, 960px);
}

.composer.composer--expanded textarea {
  max-height: 180px;
}

.composer-intent-hint {
  display: flex;
  min-height: 24px;
  align-items: center;
  gap: 6px;
  margin: 0 4px 8px;
  color: var(--notion-steel);
  font-size: 11px;
  line-height: 1.45;
}

.composer-intent-hint .material-symbols-outlined {
  color: var(--notion-blue);
  font-size: 16px;
}

.composer-intent-hint strong {
  color: var(--notion-charcoal);
  font-weight: 600;
}

.quick-start {
  width: min(100%, 860px);
  margin: clamp(22px, 4vh, 48px) auto 0;
}

.quick-start__header {
  display: flex;
  min-height: 34px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.quick-start__header > strong {
  color: var(--notion-ink);
  font-size: 13px;
  font-weight: 600;
}

.quick-start__toggle {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 9px;
  border: 1px solid var(--notion-line);
  border-radius: 7px;
  background: var(--notion-canvas);
  color: var(--notion-slate);
  cursor: pointer;
  font: inherit;
  font-size: 11px;
}

.quick-start__toggle:hover { background: var(--notion-surface); color: var(--notion-ink); }
.quick-start__toggle .material-symbols-outlined { font-size: 17px; transition: transform .18s ease; }
.quick-start__toggle .material-symbols-outlined.expanded { transform: rotate(180deg); }

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-card {
  display: flex;
  min-height: 142px;
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

.quick-card:focus-visible {
  outline: 2px solid rgba(35, 131, 226, 0.32);
  outline-offset: 2px;
}

.quick-card.is-selected {
  border-color: rgba(35, 131, 226, 0.38);
  background: var(--notion-blue-soft);
  box-shadow: rgba(35, 131, 226, 0.1) 0 0 0 1px;
}

.quick-card__icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  margin-bottom: 14px;
  border-radius: 8px;
  background: var(--notion-blue-soft);
  color: var(--notion-blue);
}

.quick-card__icon .material-symbols-outlined { font-size: 19px; }

.quick-card strong {
  margin-bottom: 7px;
  color: var(--notion-ink);
  font-size: 15px;
  font-weight: 600;
}

.quick-card > span:last-child {
  color: rgba(55, 53, 47, 0.72);
  font-size: 13px;
  line-height: 1.55;
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

.cross-session-run {
  margin-bottom: 22px;
  border: 1px solid var(--notion-line);
  border-radius: 8px;
  background: var(--notion-surface-soft);
}

.cross-session-run {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  color: var(--notion-charcoal);
}

.cross-session-run > .material-symbols-outlined {
  color: var(--notion-blue);
  font-size: 19px;
  animation: home-spin 1.2s linear infinite;
}

.cross-session-run strong,
.cross-session-run p {
  display: block;
  margin: 0;
}

.cross-session-run strong {
  font-size: 12px;
  font-weight: 600;
}

.cross-session-run p {
  margin-top: 2px;
  color: var(--notion-steel);
  font-size: 11px;
  line-height: 1.45;
}

.cross-session-run button {
  border: 1px solid var(--notion-line-strong);
  border-radius: 6px;
  background: #ffffff;
  color: var(--notion-charcoal);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.cross-session-run button {
  padding: 6px 10px;
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

.conversation-approval-notice {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  padding: 11px 12px;
  border: 1px solid rgba(180, 83, 9, 0.2);
  border-radius: 6px;
  background: #fffaf0;
  color: var(--notion-charcoal);
}

.conversation-approval-notice > .material-symbols-outlined {
  color: #b45309;
  font-size: 18px;
}

.conversation-approval-notice strong,
.conversation-approval-notice p {
  display: block;
  margin: 0;
}

.conversation-approval-notice strong {
  font-size: 12px;
  font-weight: 650;
}

.conversation-approval-notice p {
  margin-top: 2px;
  color: var(--notion-steel);
  font-size: 11px;
  line-height: 1.4;
}

.conversation-approval-notice button {
  height: 28px;
  border: 1px solid rgba(180, 83, 9, 0.3);
  border-radius: 5px;
  padding: 0 10px;
  background: #ffffff;
  color: #92400e;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.conversation-approval-notice button:hover {
  background: #fff7e6;
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

.composer-context {
  position: relative;
  width: min(100%, 720px);
  margin: 0 auto;
}

.conversation-composer {
  width: 100%;
  background: #ffffff;
}

.context-entities {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 0 8px;
}

.context-entities__label {
  color: var(--notion-stone);
  font-size: 10px;
  font-weight: 600;
}

.context-entity {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 4px;
  padding: 4px 4px 4px 8px;
  border: 1px solid rgba(35, 131, 226, 0.22);
  border-radius: 999px;
  background: var(--notion-blue-soft);
  color: var(--notion-blue);
  font-size: 10px;
  font-weight: 600;
}

.context-entity > .material-symbols-outlined,
.context-entity button .material-symbols-outlined {
  font-size: 13px;
}

.context-entity__name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-entity button {
  display: grid;
  width: 18px;
  height: 18px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.context-entity button:hover {
  background: rgba(35, 131, 226, 0.12);
}

.mention-panel {
  position: absolute;
  right: 42px;
  bottom: calc(100% + 8px);
  left: 42px;
  z-index: 20;
  overflow: hidden;
  border: 1px solid var(--notion-line-strong);
  border-radius: 8px;
  background: var(--notion-canvas);
  box-shadow: rgba(15, 15, 15, 0.14) 0 12px 30px;
}

.mention-panel__title {
  padding: 8px 12px;
  border-bottom: 1px solid var(--notion-line);
  color: var(--notion-stone);
  font-size: 10px;
  font-weight: 600;
}

.mention-panel__item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 0;
  background: transparent;
  color: var(--notion-charcoal);
  text-align: left;
  cursor: pointer;
}

.mention-panel__item:hover {
  background: var(--notion-surface);
}

.mention-panel__item > .material-symbols-outlined {
  color: var(--notion-steel);
  font-size: 16px;
}

.mention-panel__name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
}

.mention-panel__type {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--notion-surface);
  color: var(--notion-steel);
  font-size: 10px;
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
.conversation-thread :deep(.tool-call-block) {
  border: 1px solid rgba(55, 53, 47, 0.1);
  border-radius: 6px;
  background: var(--notion-surface-soft);
  box-shadow: none;
}

.conversation-thread :deep(.activity-card) {
  padding: 9px 11px;
}

.conversation-thread :deep(.tool-header) {
  min-height: 38px;
  padding: 7px 11px;
}

.conversation-thread :deep(.tool-name) {
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
}

.conversation-thread :deep(.activity-tool) {
  font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
  font-size: 11px;
  font-weight: 600;
}

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
  min-width: 0;
  border-left: 0;
  background: transparent;
}

.workspace-resize-handle {
  position: absolute;
  z-index: 12;
  top: 0;
  bottom: 0;
  left: -6px;
  width: 12px;
  padding: 0;
  border: 0;
  outline: none;
  background: transparent;
  cursor: col-resize;
  touch-action: none;
}

.workspace-resize-handle::after {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 5px;
  width: 2px;
  background: transparent;
  content: '';
  transition: background-color .15s ease;
}

.workspace-resize-handle:hover::after,
.workspace-resize-handle:focus-visible::after {
  background: rgba(35, 131, 226, 0.55);
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
    padding-top: 32px;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-height: 820px) and (min-width: 981px) {
  .landing-document { gap: 14px; padding-top: 16px; padding-bottom: 16px; }
  .landing-primary { padding-block: 0; }
  .landing-hero h1 { font-size: 32px; }
  .landing-hero p { margin-top: 8px; font-size: 14px; }
  .quick-start { margin-top: 18px; }
  .quick-card { min-height: 116px; padding: 13px; }
  .quick-card__icon { margin-bottom: 9px; }
  .quick-card > span:last-child { font-size: 11px; }
}

@media (max-width: 720px) {
  .home-shell {
    height: auto;
    min-height: 100vh;
  }

  .landing-document {
    margin: 0 auto;
    padding: 40px 20px 18px;
  }

  .landing-hero h1 {
    font-size: 32px;
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

  .landing-input-dock {
    margin-top: 20px;
  }

  .composer {
    min-height: 60px;
    grid-template-columns: 34px minmax(0, 1fr) 34px 38px;
    padding: 8px;
    border-radius: 18px;
  }

  .composer-intent-hint {
    align-items: flex-start;
    margin-right: 2px;
    margin-left: 2px;
  }

  .conversation-input-dock {
    padding-right: 14px;
    padding-left: 14px;
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
