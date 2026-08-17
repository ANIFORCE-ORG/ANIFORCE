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
import type { TaskPanelAction, TaskPanelStatus, TaskPanelStep } from '@/components/agent/TaskStatusPanel.vue'
import { resolveHomeSessionState, shouldApplyHomeSessionState } from '@/agent/homeSessionState'
import { normalizeTaskPanelStatus, taskStatusPresentation } from '@/agent/taskPresentation'
import { useAgentSession, type AgentPhase, type AgentRouteContext } from '@/composables/useAgentSession'
import type { AgentMessage } from '@/api/agent'
import { navItems } from '@/config/navigation'
import aniforceWorkflowHero from '@/assets/aniforce-workflow-hero.png'

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
const sessionsReady = ref(false)
let skippedRouteSessionId: string | null = null

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
    icon: 'portfolio',
    label: '盘点投放资产',
    description: '统一查看项目、计划与素材，快速接续当前工作。',
    prompt: '帮我盘点当前账号下的项目、投放计划和素材。',
    mode: 'chat' as const
  },
  {
    icon: 'launch',
    label: '启动增长项目',
    description: '从目标、市场和预算出发，创建清晰的投放草稿。',
    prompt: '帮我启动一个新的增长项目，先根据目标、市场和预算整理投放草稿。',
    mode: 'project' as const
  },
  {
    icon: 'diagnose',
    label: '发现增长机会',
    description: '结合消耗、转化与素材信号，定位扩量和止损机会。',
    prompt: '帮我诊断当前投放表现，找出值得扩量和需要止损的机会。',
    mode: 'chat' as const
  },
  {
    icon: 'creative',
    label: '生成创意方案',
    description: '将投放目标转成素材 Brief 与可执行创意方向。',
    prompt: '帮我把投放目标整理成素材 Brief 和可执行的创意方向。',
    mode: 'chat' as const
  }
]

const visibleMessages = computed(() => agent.visibleMessages.value)
const hasContent = computed(() => agent.loading.value || agent.hasAnyRunningRun.value || visibleMessages.value.length > 0 || Boolean(agent.streamingMessage.value) || Boolean(agent.error.value))
const sidebarSessions = computed(() => agent.sessions.value.map(session => ({
  id: session.id,
  name: session.title || session.id,
  active: agent.activeSession.value?.id === session.id
})))
const sidebarActivePanel = computed(() => agent.activeSession.value ? '__session__' : 'new-task')
const activeMode = computed(() => intentModes.find(item => item.key === activeIntentMode.value) || intentModes[0])
const activeRoute = computed(() => {
  const { titlePrefix: _titlePrefix, ...route } = activeMode.value.route
  return route
})
const activeSessionId = computed(() => agent.activeSession.value?.id || '')
const currentTask = computed(() => agent.currentTask.value)
const hasBusinessTask = computed(() => Boolean(currentTask.value?.task_type && currentTask.value.task_type !== 'conversation' && currentTask.value.task_type !== 'data_query'))
const hasWorkspaceToolResults = computed(() => Boolean(agent.workspaceProjection.value) || agent.workspaceToolResults.value.length > 0)
const taskPanelVisible = computed(() => true)
const taskStateVisible = computed(() => Boolean(currentTask.value || agent.commandStatus.value))
const taskStatusMeta = computed(() => taskStatusPresentation[taskStatus.value])
const taskStatusLabel = computed(() => taskStatusMeta.value.label)
const runningSession = computed(() => agent.sessions.value.find(session => session.id === agent.activeRunSessionId.value) || null)
const workspaceStyle = computed(() => ({
  width: workspaceCollapsed.value ? '56px' : `${workspaceWidth.value}px`
}))
const taskStatus = computed<TaskPanelStatus>(() => {
  if (currentTask.value?.status) return normalizeTaskPanelStatus(currentTask.value.status)
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
  if (taskStatus.value === 'waiting_user_input') return [{ key: 'focus', label: '补充所需信息', icon: 'edit_note', tone: 'primary' }]
  if (taskStatus.value === 'waiting_approval') return [{ key: 'open_approval', label: '查看并确认', icon: 'approval_delegation', tone: 'primary' }]
  if (taskStatus.value === 'applying' || taskStatus.value === 'canceled') return []
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
  if (taskPhaseLabel.value) tags.push(taskPhaseLabel.value)
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

function scrollToBottom() {
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
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
  if (!message || agent.loading.value || agent.hasAnyRunningRun.value) return
  if (!agent.activeSession.value) {
    await agent.createSession(activeRoute.value)
    const sessionId = activeSessionId.value
    if (!sessionId) return
    skippedRouteSessionId = sessionId
    await router.replace({ path: '/home', query: { session_id: sessionId } })
  }
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
  await handleSubmit()
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
  navigateTo(`/campaigns/create?projectId=${encodeURIComponent(projectId)}`)
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
  nextTick(() => document.querySelector<HTMLInputElement>('[data-agent-input="home"]')?.focus())
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
  if (action === 'open_approval') {
    workspaceCollapsed.value = false
    persistWorkspaceState()
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
  inputText.value = ''
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
  inputText.value = ''
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
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  sessionsReady.value = true
  await applyHomeSessionState()
})

onActivated(() => {
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  agent.resumeTypewriter?.()
  if (sessionsReady.value) void applyHomeSessionState()
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', handleWorkspacePointerMove)
  window.removeEventListener('pointerup', stopWorkspaceResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

onDeactivated(() => {
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
  () => taskStatus.value === 'waiting_approval' || agent.workspaceApprovalDraft.value?.status === 'pending',
  needsApproval => {
    if (!needsApproval || !workspaceCollapsed.value) return
    workspaceCollapsed.value = false
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
      <div class="home-main__scroll">
        <section v-if="!hasContent" class="landing-document">
          <img class="landing-visual" :src="aniforceWorkflowHero" alt="" aria-hidden="true" />
          <header class="landing-hero">
            <h1>从洞察到行动，让每一次投放更确定</h1>
            <p>ANIFORCE 连接项目、数据与素材，用 AI 帮你判断下一步，并把策略快速变成可执行任务。</p>
          </header>

          <section v-if="!hasInteracted" class="quick-start" aria-label="快捷入口">
            <div class="quick-grid">
              <button
                v-for="action in starterActions"
                :key="action.label"
                class="quick-card"
                type="button"
                @click="runStarterAction(action)"
              >
                <span class="quick-card__icon" aria-hidden="true">
                  <svg v-if="action.icon === 'portfolio'" class="quick-card__icon-svg" viewBox="0 0 32 32">
                    <path d="M5.5 10h7l2.4 2.5h11.6v13H5.5z" />
                    <path class="quick-card__icon-accent" d="M8.5 10V6.5h14.7a2.3 2.3 0 0 1 2.3 2.3v3.7" />
                  </svg>
                  <svg v-else-if="action.icon === 'launch'" class="quick-card__icon-svg" viewBox="0 0 32 32">
                    <circle cx="15.5" cy="16.5" r="10" />
                    <circle cx="15.5" cy="16.5" r="4" />
                    <path class="quick-card__icon-accent" d="m15.5 16.5 10-10m-4.5 0h4.5V11" />
                  </svg>
                  <svg v-else-if="action.icon === 'diagnose'" class="quick-card__icon-svg" viewBox="0 0 32 32">
                    <path d="m4.5 19 6-6 5 4 6.5-9" />
                    <path class="quick-card__icon-accent" d="M18 8h4v4" />
                    <circle cx="20.5" cy="22" r="5.5" />
                    <path d="m24.5 26 3.5 3.5" />
                  </svg>
                  <svg v-else class="quick-card__icon-svg" viewBox="0 0 32 32">
                    <rect x="5.5" y="7.5" width="21" height="18" rx="3" />
                    <path class="quick-card__icon-accent" d="m16 11 1.4 3.6L21 16l-3.6 1.4L16 21l-1.4-3.6L11 16l3.6-1.4z" />
                    <path d="M24 3.5v4M22 5.5h4" />
                  </svg>
                </span>
                <strong>{{ action.label }}</strong>
                <span>{{ action.description }}</span>
              </button>
            </div>
          </section>

          <div class="landing-input-dock">
            <div class="composer" role="search">
              <button class="composer__icon" type="button" aria-label="添加附件">
                <span class="material-symbols-outlined">attach_file</span>
              </button>
              <input
                v-model="inputText"
                data-agent-input="home"
                placeholder="继续输入任务或补充信息..."
                type="text"
                @keydown.enter="handleSubmit"
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
            <section v-if="agent.runningInAnotherSession.value" class="cross-session-run" aria-live="polite">
              <span class="material-symbols-outlined">sync</span>
              <div>
                <strong>另一个对话正在运行</strong>
                <p>{{ runningSession?.title || 'Agent 任务' }}仍在后台执行，完成或停止后才能发起新任务。</p>
              </div>
              <button type="button" @click="openRunningSession">查看任务</button>
            </section>

            <section v-if="taskStateVisible" class="task-state" :data-status="taskStatus">
              <div class="task-state__header">
                <span class="task-state__status">
                  <span class="material-symbols-outlined" :class="{ spinning: taskStatus === 'running' || taskStatus === 'applying' }">{{ taskStatusMeta.icon }}</span>
                  {{ taskStatusLabel }}
                </span>
                <span v-if="taskPhaseLabel" class="task-state__phase">{{ taskPhaseLabel }}</span>
              </div>
              <h2 v-if="currentTask">{{ currentTask.title }}</h2>
              <p>{{ agent.commandStatus.value || taskSummary }}</p>
              <div v-if="taskTags.length" class="task-state__tags">
                <span v-for="tag in taskTags" :key="tag">{{ tag }}</span>
              </div>
              <div v-if="currentTask && taskSteps.length" class="task-state__steps" aria-label="任务进度">
                <span v-for="step in taskSteps" :key="step.key" :data-step-status="step.status">
                  <i></i>{{ step.label }}
                </span>
              </div>
              <div v-if="taskActions.length" class="task-state__actions">
                <button
                  v-for="action in taskActions"
                  :key="action.key"
                  type="button"
                  :data-tone="action.tone || 'neutral'"
                  @click="handleTaskAction(action.key)"
                >
                  <span class="material-symbols-outlined">{{ action.icon }}</span>
                  {{ action.label }}
                </button>
              </div>
            </section>

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
            <input
              v-model="inputText"
              data-agent-input="home"
              placeholder="继续输入任务，或输入 @ 选择工作台上下文..."
              type="text"
              @keydown.enter="handleSubmit"
            />
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
        :projection="agent.workspaceProjection.value"
        :approval-draft="agent.workspaceApprovalDraft.value"
        @toggle-collapse="toggleWorkspaceCollapsed"
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
  display: flex;
  width: min(100%, 1080px);
  min-height: 100%;
  margin: 0 auto;
  padding: clamp(260px, 38vh, 720px) 36px 48px;
  box-sizing: border-box;
  align-items: center;
  flex-direction: column;
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

.landing-visual {
  display: block;
  width: 260px;
  height: auto;
  flex: 0 0 auto;
  margin-bottom: 28px;
  object-fit: contain;
}

.composer {
  display: grid;
  width: 100%;
  height: 60px;
  grid-template-columns: 36px minmax(0, 1fr) 36px 38px;
  grid-template-rows: 1fr;
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

.composer input {
  grid-row: 1;
  grid-column: 2;
  min-width: 0;
  width: 100%;
  align-self: center;
  padding: 0 8px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--notion-ink);
  font-size: 15px;
  line-height: 1.55;
}

.composer input::placeholder {
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
  margin: auto auto 0;
  padding-top: 32px;
}

.quick-start {
  width: min(100%, 860px);
  margin: 60px auto 0;
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
  display: block;
  width: 36px;
  height: 36px;
  place-items: center;
  margin-bottom: 18px;
  background: transparent;
  color: var(--notion-charcoal);
  box-shadow: none;
}

.quick-card__icon-svg {
  display: block;
  width: 36px;
  height: 36px;
  overflow: visible;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.quick-card__icon-accent {
  stroke: var(--notion-blue);
  stroke-width: 2.2;
}

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

.cross-session-run,
.task-state {
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

.cross-session-run button,
.task-state__actions button {
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

.task-state {
  padding: 14px 16px;
}

.task-state__header,
.task-state__status,
.task-state__steps,
.task-state__actions {
  display: flex;
  align-items: center;
}

.task-state__header {
  justify-content: space-between;
  gap: 12px;
}

.task-state__status {
  gap: 5px;
  color: var(--notion-blue);
  font-size: 11px;
  font-weight: 600;
}

.task-state__status .material-symbols-outlined {
  font-size: 15px;
}

.task-state__status .spinning {
  animation: home-spin 1s linear infinite;
}

.task-state[data-status="waiting_approval"] .task-state__status {
  color: #a16207;
}

.task-state[data-status="waiting_user_input"] .task-state__status {
  color: #6d28d9;
}

.task-state[data-status="applying"] .task-state__status,
.task-state[data-status="completed"] .task-state__status {
  color: var(--notion-green);
}

.task-state[data-status="failed"] .task-state__status {
  color: #b42318;
}

.task-state__phase {
  color: var(--notion-stone);
  font-size: 10px;
}

.task-state h2 {
  margin: 8px 0 0;
  color: var(--notion-ink);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0;
}

.task-state > p {
  margin: 5px 0 0;
  color: var(--notion-slate);
  font-size: 12px;
  line-height: 1.55;
}

.task-state__tags,
.task-state__steps,
.task-state__actions {
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.task-state__tags span {
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(55, 53, 47, 0.06);
  color: var(--notion-steel);
  font-size: 10px;
}

.task-state__steps {
  gap: 8px 12px;
  padding-top: 10px;
  border-top: 1px solid var(--notion-line);
}

.task-state__steps span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--notion-stone);
  font-size: 10px;
}

.task-state__steps i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d4d1cb;
}

.task-state__steps span[data-step-status="done"] i,
.task-state__steps span[data-step-status="active"] i {
  background: var(--notion-blue);
}

.task-state__steps span[data-step-status="active"] {
  color: var(--notion-charcoal);
  font-weight: 600;
}

.task-state__steps span[data-step-status="error"] i {
  background: #dc2626;
}

.task-state__actions button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 30px;
  padding: 5px 9px;
}

.task-state__actions button[data-tone="primary"] {
  border-color: var(--notion-blue);
  background: var(--notion-blue);
  color: #ffffff;
}

.task-state__actions button[data-tone="danger"] {
  border-color: #fecaca;
  color: #b42318;
}

.task-state__actions .material-symbols-outlined {
  font-size: 14px;
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
    padding-top: 48px;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
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
    padding-top: 24px;
  }

  .composer {
    height: 60px;
    grid-template-columns: 34px minmax(0, 1fr) 34px 38px;
    padding: 8px;
    border-radius: 18px;
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
