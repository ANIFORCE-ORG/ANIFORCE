<script lang="ts">
export default { name: 'Home' }
</script>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import MessageView from '@/components/agent/MessageView.vue'
import WorkspaceRenderer from '@/components/agent/workspace/WorkspaceRenderer.vue'
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
const workspaceWidth = ref(Number(localStorage.getItem('aniforce.workspace.width') || 560))
const workspaceDragging = ref(false)
const renameDialog = ref<{ id: string; name: string } | null>(null)
const renameValue = ref('')
const deleteDialog = ref<{ id: string; name: string } | null>(null)

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
    icon: 'folder_open',
    label: '查看现有项目',
    description: '拉取当前账号下的项目，并在右侧工作台打开项目列表。',
    prompt: '现在有哪些项目？',
    mode: 'chat' as const
  },
  {
    icon: 'add_task',
    label: '创建投放项目',
    description: '进入项目管理模式，先沉淀草稿再确认落库。',
    prompt: '帮我创建一个新的投放项目，需要先整理项目草稿。',
    mode: 'project' as const
  },
  {
    icon: 'monitoring',
    label: '分析投放表现',
    description: '结合项目、计划、素材和消耗数据做诊断。',
    prompt: '帮我分析当前投放项目和计划的表现。',
    mode: 'chat' as const
  },
  {
    icon: 'auto_awesome',
    label: '生成素材 Brief',
    description: '基于投放目标生成可交给素材流程的 Brief。',
    prompt: '帮我为一个投放项目生成素材 Brief。',
    mode: 'chat' as const
  }
]

const visibleMessages = computed(() => agent.visibleMessages.value)
const hasContent = computed(() => agent.loading.value || agent.agentRunning.value || visibleMessages.value.length > 0 || Boolean(agent.streamingMessage.value) || Boolean(agent.error.value))
const sidebarSessions = computed(() => agent.sessions.value.map(session => ({
  id: session.id,
  name: session.title || session.id,
  active: agent.activeSession.value?.id === session.id
})))
const currentSessionTitle = computed(() => agent.activeSession.value?.title || '新 Agent 任务')
const activeMode = computed(() => intentModes.find(item => item.key === activeIntentMode.value) || intentModes[0])
const activeRoute = computed(() => {
  const { titlePrefix: _titlePrefix, ...route } = activeMode.value.route
  return route
})
const currentTask = computed(() => agent.currentTask.value)
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
    { key: 'goal', label: '目标确认' },
    { key: 'data', label: '数据查询' },
    { key: 'analysis', label: '分析生成' },
    { key: 'approval', label: '等待确认' },
    { key: 'done', label: '完成' }
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
  const viewportMax = Math.max(520, Math.floor(window.innerWidth * 0.76))
  return Math.min(Math.max(value, 520), viewportMax)
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
  await agent.createSession(activeRoute.value)
}

async function createChatSession() {
  activeIntentMode.value = 'chat'
  const chatMode = intentModes[0]
  const { titlePrefix: _titlePrefix, ...route } = chatMode.route
  await agent.createSession(route)
}

const switchSession = (session: any) => {
  const target = agent.sessions.value.find(item => item.id === session.id)
  if (target) {
    hasInteracted.value = true
    void agent.selectSession(target)
  }
}

async function selectSessionFromRoute(): Promise<boolean> {
  const querySessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  if (!querySessionId) return false
  const target = agent.sessions.value.find(session => session.id === querySessionId)
  if (!target) return false
  hasInteracted.value = true
  await agent.selectSession(target)
  return true
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
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  if (await selectSessionFromRoute()) return
  const existing = agent.activeSession.value
  const savedSessionId = localStorage.getItem('aniforce.activeSessionId')
  const saved = savedSessionId ? agent.sessions.value.find(session => session.id === savedSessionId) : null
  if (existing && agent.sessions.value.some(session => session.id === existing.id)) return
  if (saved) await agent.selectSession(saved)
  else if (agent.sessions.value.length > 0) await agent.selectSession(agent.sessions.value[0])
  else await createSessionForActiveMode()
})

onActivated(() => {
  workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value)
  window.addEventListener('pointermove', handleWorkspacePointerMove)
  window.addEventListener('pointerup', stopWorkspaceResize)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  agent.resumeTypewriter?.()
  void selectSessionFromRoute()
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
  () => {
    void selectSessionFromRoute()
  }
)
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sidebarSessions"
      session-actions
      session-create
      @switch-panel="switchPanel"
      @switch-session="switchSession"
      @create-session="createSessionForActiveMode"
      @rename-session="openRenameSession"
      @delete-session="openDeleteSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="flex-1 overflow-y-auto">
        <div class="flex flex-col items-center px-4 pb-8">
    <!-- Top spacer: pushes content to center when no output -->
    <div v-if="!hasContent" class="flex-1 min-h-[94px]"></div>

    <!-- Greeting -->
    <div
      v-if="!hasContent"
      class="max-w-[624px] w-full text-center space-y-[19px] mb-[37px]"
    >
      <h1 class="text-slate-900 dark:text-white text-[28px] md:text-[34px] font-poppins font-semibold tracking-tight">
        又见面啦！有新的投放计划吗？
      </h1>
      <p class="text-slate-500 dark:text-slate-400 text-[15px]">
        利用 AI 驱动的见解和素材生成，快速启动您的下一个全球营销活动。
      </p>
    </div>

    <!-- Output Content Area (above the input bar, only when has content) -->
    <div v-if="hasContent" class="max-w-[842px] w-full px-[12px] space-y-[19px] mb-[19px]">
      <!-- Loading State -->
      <div v-if="agent.loading.value" class="flex items-center justify-center gap-[9px] py-[25px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span class="text-slate-500 text-[11px]">AI 正在分析中，请稍候...</span>
      </div>

      <!-- Error State -->
      <div v-else-if="agent.error.value" class="bg-white dark:bg-slate-900 rounded-2xl border border-red-200 dark:border-red-800 p-[19px] shadow-sm">
        <div class="flex items-start gap-[9px]">
          <div class="h-[25px] w-[25px] rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-red-600 dark:text-red-400 text-[11px]">error</span>
          </div>
          <p class="text-red-700 dark:text-red-300 text-[13px] leading-relaxed">{{ agent.error.value }}</p>
        </div>
      </div>

      <!-- Agent Messages -->
      <template v-else>
        <template v-for="(message, index) in agent.visibleMessages.value" :key="message.id || `${message.role}-${message.timestamp}-${index}`">
          <MessageView
            :message="message"
            :tool-results="toolResults"
            :model-names="agent.modelNames.value"
            :prev-timestamp="index > 0 ? Number(agent.visibleMessages.value[index - 1].timestamp || 0) : undefined"
            @approval="payload => agent.resolveApproval(payload.runId, payload.checkpointId, payload.decision)"
          />
        </template>

        <MessageView
          v-if="agent.streamingMessage.value"
          :message="agent.streamingMessage.value"
          is-streaming
          :tool-results="toolResults"
          :model-names="agent.modelNames.value"
          @approval="payload => agent.resolveApproval(payload.runId, payload.checkpointId, payload.decision)"
        />
        
        <div v-if="agent.agentRunning.value && !agent.streamingMessage.value" class="flex items-center justify-center gap-[9px] py-[19px]">
          <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span class="text-slate-500 text-[11px]">{{ phaseLabel(agent.agentPhase.value) }}</span>
        </div>
      </template>
    </div>

    <!-- Floating Command Bar (always below output content) -->
    <div class="max-w-[671px] w-full px-[12px] mb-[19px]">
      <div class="relative group">
        <!-- Glow effect -->
        <div class="absolute -inset-1 bg-gradient-to-r from-primary/20 to-blue-400/20 rounded-full blur opacity-25 group-focus-within:opacity-100 transition duration-1000 group-hover:duration-200"></div>
        <!-- Input bar -->
        <div class="relative flex items-center bg-white dark:bg-slate-900 rounded-full border border-slate-200 dark:border-slate-700 shadow-xl shadow-slate-200/50 dark:shadow-none p-[6px] focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
          <button class="flex items-center justify-center p-[9px] text-slate-400 hover:text-primary transition-colors">
            <span class="material-symbols-outlined text-[19px]">attach_file</span>
          </button>
          <input
            v-model="inputText"
            data-agent-input="home"
            class="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-[15px] text-slate-800 dark:text-slate-200 placeholder:text-slate-400 py-[9px] px-[6px]"
            placeholder="描述您的投放目标或上传素材..."
            type="text"
            @keydown.enter="handleSubmit"
          />
          <div class="flex items-center gap-[6px] pr-[6px]">
            <button class="flex items-center justify-center p-[9px] text-slate-400 hover:text-primary transition-colors">
              <span class="material-symbols-outlined text-[19px]">mic</span>
            </button>
            <button
              class="bg-primary text-white h-[37px] w-[37px] rounded-full flex items-center justify-center hover:bg-primary/90 transition-all shadow-lg shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="agent.loading.value || agent.agentRunning.value || !inputText.trim()"
              @click="handleSubmit"
            >
              <span v-if="agent.loading.value || agent.agentRunning.value" class="h-[16px] w-[16px] border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span v-else class="material-symbols-outlined text-[19px]">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Quick Tags (hide after interaction) -->
      <div v-if="!hasContent" class="flex flex-wrap justify-center gap-[9px] mt-[19px]">
        <button
          v-for="(mode, index) in intentModes"
          :key="mode.key"
          class="flex items-center gap-[6px] px-[16px] py-[6px] rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-primary hover:text-primary transition-all shadow-sm"
          :class="activeIntentMode === mode.key ? 'border-primary text-primary' : ''"
          @click="activeIntentMode = mode.key"
        >
          <span class="text-[15px]">{{ index === 0 ? '💬' : '📁' }}</span>
          <span class="text-[11px] font-medium">{{ mode.label }}</span>
        </button>
      </div>
    </div>

    <!-- Tool Cards (only show when no content) -->
    <div v-if="!hasContent && !hasInteracted" class="w-full max-w-[842px] mt-[25px]">
      <div class="flex items-center justify-between px-[19px] mb-[19px]">
        <h3 class="text-[15px] font-bold dark:text-white">快速开始</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[19px] px-[12px]">
        <div
          v-for="action in starterActions"
          :key="action.label"
          class="group bg-white dark:bg-slate-900 p-[19px] rounded-xl border border-slate-200 dark:border-slate-800 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all cursor-pointer"
          @click="runStarterAction(action)"
        >
          <div
            class="h-[37px] w-[37px] rounded-lg flex items-center justify-center mb-[12px] group-hover:scale-110 transition-transform"
            :class="action.mode === 'project' ? 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' : 'bg-blue-50 dark:bg-blue-900/30 text-primary'"
          >
            <span class="material-symbols-outlined text-[19px]">{{ action.icon }}</span>
          </div>
          <h4 class="font-bold text-[13px] text-slate-900 dark:text-white mb-[6px]">{{ action.label }}</h4>
          <p class="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">{{ action.description }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom spacer: pushes content to center when no output -->
    <div v-if="!hasContent" class="flex-1"></div>
        </div>
      </div>
    </main>

    <!-- 右侧 Workspace 投影栏 -->
    <aside
      class="flex-shrink-0 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden"
      :style="workspaceStyle"
    >
      <div class="flex items-center justify-between px-[12px] py-[8px] border-b border-slate-200 dark:border-slate-700">
        <div class="flex items-center gap-[6px]">
          <span class="material-symbols-outlined text-[16px] text-slate-500">workspaces</span>
          <span class="text-[11px] font-medium text-slate-700 dark:text-slate-300">工作台</span>
        </div>
        <div class="flex items-center gap-[2px]">
          <button
            class="p-[4px] rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            @click="toggleWorkspaceCollapsed"
          >
            <span class="material-symbols-outlined text-[14px] text-slate-400">{{ workspaceCollapsed ? 'left_panel_open' : 'right_panel_close' }}</span>
          </button>
          <div
            v-if="!workspaceCollapsed"
            class="w-[4px] h-[24px] cursor-col-resize flex items-center"
            @pointerdown="startWorkspaceResize"
          >
            <div class="w-[1px] h-[16px] bg-slate-300 dark:bg-slate-600"></div>
          </div>
        </div>
      </div>
      <div v-show="!workspaceCollapsed" class="flex-1 overflow-hidden">
        <WorkspaceRenderer
          :projection="agent.workspaceProjection.value"
          :approval-draft="agent.workspaceApprovalDraft.value"
          :session-id="agent.activeSession.value?.id || ''"
          @approve="payload => agent.resolveWorkspaceApproval({ ...payload, runId: agent.workspaceApprovalDraft.value?.runId || '' })"
          @reject="checkpointId => agent.rejectWorkspaceApproval(checkpointId, agent.workspaceApprovalDraft.value?.runId || '')"
          @update-approval-form="payload => agent.updateApprovalDraftForm(payload.checkpointId, payload.formModel)"
          @select-entity="entity => agent.selectWorkspaceEntity(entity)"
          @view-project="(projectId: string) => openProject({ id: projectId })"
        />
      </div>
    </aside>
  </div>

  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="renameDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
        @click.self="renameDialog = null"
      >
        <div class="w-full max-w-md overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
          <div class="border-b border-slate-100 px-6 py-5 dark:border-slate-800">
            <h3 class="text-base font-semibold text-slate-950 dark:text-white">重命名对话</h3>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">为这条历史会话设置一个更容易识别的名称。</p>
          </div>
          <div class="px-6 py-5">
            <input
              v-model="renameValue"
              data-session-rename-input
              class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              maxlength="80"
              placeholder="输入会话名称"
              @keydown.enter.prevent="confirmRenameSession"
              @keydown.esc.prevent="renameDialog = null"
            />
          </div>
          <div class="flex justify-end gap-2 border-t border-slate-100 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-950/60">
            <button class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800" @click="renameDialog = null">取消</button>
            <button class="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50" :disabled="!renameValue.trim()" @click="confirmRenameSession">保存</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <ConfirmDialog
    :show="Boolean(deleteDialog)"
    title="删除对话"
    :message="`确定删除对话「${deleteDialog?.name || ''}」吗？删除后会从历史列表移除。`"
    confirm-text="删除"
    cancel-text="取消"
    confirm-button-class="bg-red-600 hover:bg-red-700"
    @confirm="confirmDeleteSession"
    @close="deleteDialog = null"
  />
</template>
