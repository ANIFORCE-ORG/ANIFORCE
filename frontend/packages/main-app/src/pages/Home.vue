<script lang="ts">
export default { name: 'Home' }
</script>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import MessageView from '@/components/agent/MessageView.vue'
import LiveWorkspaceShell from '@/components/agent/workspace/LiveWorkspaceShell.vue'
import type { TaskPanelAction, TaskPanelArtifact, TaskPanelStatus, TaskPanelStep } from '@/components/agent/TaskStatusPanel.vue'
import { useAgentSession, type AgentPhase, type AgentRouteContext } from '@/composables/useAgentSession'
import type { AgentMessage } from '@/api/agent'
import { navItems } from '@/config/navigation'

const router = useRouter()
const agent = useAgentSession()
const inputText = ref('')
const hasInteracted = ref(false)
const modelMenuOpen = ref(false)
const activeIntentMode = ref<'chat' | 'project'>('chat')
const workspaceCollapsed = ref(localStorage.getItem('aniforce.workspace.collapsed') === '1')
const workspaceWidth = ref(Number(localStorage.getItem('aniforce.workspace.width') || 560))
const workspaceDragging = ref(false)

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
  const mode = activeMode.value
  await agent.createSession({
    ...activeRoute.value,
    title: `${mode.route.titlePrefix} ${agent.sessions.value.length + 1}`
  })
}

async function createChatSession() {
  activeIntentMode.value = 'chat'
  const chatMode = intentModes[0]
  const { titlePrefix: _titlePrefix, ...route } = chatMode.route
  await agent.createSession({
    ...route,
    title: `${chatMode.route.titlePrefix} ${agent.sessions.value.length + 1}`
  })
}

const switchSession = (session: any) => {
  const target = agent.sessions.value.find(item => item.id === session.id)
  if (target) {
    hasInteracted.value = true
    void agent.selectSession(target)
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
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sidebarSessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="h-11 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4">
        <div class="flex min-w-0 items-center gap-2">
          <span class="material-symbols-outlined text-base text-slate-400">chat</span>
          <h3 class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{{ currentSessionTitle }}</h3>
        </div>
        <div class="flex items-center gap-1">
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            :disabled="agent.loading.value"
            title="新任务"
            @click="createSessionForActiveMode()"
          >
            <span class="material-symbols-outlined text-lg">add</span>
          </button>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div class="flex min-h-full flex-col items-center px-4 pb-8">
    <div v-if="!hasContent" class="flex-1 min-h-[48px]"></div>

    <section
      v-if="!hasContent"
      class="w-full max-w-[760px]"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="min-w-0">
          <h1 class="text-xl font-semibold text-slate-950 dark:text-white">今天要推进什么？</h1>
        </div>
        <button
          class="hidden h-8 items-center gap-2 rounded-md px-2.5 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white sm:inline-flex"
          @click="createSessionForActiveMode()"
        >
          <span class="material-symbols-outlined text-base">add</span>
          新任务
        </button>
      </div>
      <div class="mt-4 divide-y divide-slate-100 overflow-hidden rounded-md border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
        <button
          v-for="action in starterActions"
          :key="action.label"
          class="group flex min-h-[52px] w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800"
          @click="runStarterAction(action)"
        >
          <span class="material-symbols-outlined text-lg text-slate-400 group-hover:text-primary">{{ action.icon }}</span>
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-medium text-slate-900 dark:text-white">{{ action.label }}</span>
            <span class="block truncate text-xs text-slate-500 dark:text-slate-400">{{ action.description }}</span>
          </span>
          <span class="material-symbols-outlined text-base text-slate-300 group-hover:text-slate-500">arrow_forward</span>
        </button>
      </div>
    </section>

    <!-- Agent conversation output -->
    <div v-if="hasContent" class="agent-output max-w-[860px] w-full px-4 space-y-2 mb-6">
      <div v-if="agent.loading.value" class="flex items-center justify-center gap-3 py-8">
        <div class="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span class="text-slate-500 text-sm">正在加载 Agent 会话...</span>
      </div>

      <div v-else-if="agent.error.value" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
        {{ agent.error.value }}
      </div>

      <template v-else>
        <!-- 消息列表：user / assistant / activity 都在这里 -->
        <template v-for="(message, index) in agent.visibleMessages.value" :key="message.id || `${message.role}-${message.timestamp}-${index}`">
          <MessageView
            :message="message"
            :tool-results="toolResults"
            :model-names="agent.modelNames.value"
            :prev-timestamp="index > 0 ? Number(agent.visibleMessages.value[index - 1].timestamp || 0) : undefined"
          />
        </template>

        <!-- 流式消息 -->
        <MessageView
          v-if="agent.streamingMessage.value"
          :message="agent.streamingMessage.value"
          is-streaming
          :tool-results="toolResults"
          :model-names="agent.modelNames.value"
        />
        
        <!-- Agent 运行中提示 -->
        <div v-if="agent.agentRunning.value && !agent.streamingMessage.value" class="flex items-center gap-2 py-4 text-sm text-slate-500">
          <div class="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span>{{ phaseLabel(agent.agentPhase.value) }}</span>
        </div>
      </template>
    </div>

    <!-- Floating Command Bar (always below output content) -->
    <div class="max-w-[860px] w-full px-4 mb-6">
      <div class="relative group">
        <!-- Input bar -->
        <div class="relative flex items-center rounded-lg border border-slate-200 bg-white p-2 shadow-sm shadow-slate-200/70 transition-all focus-within:border-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:shadow-none dark:focus-within:border-slate-500">
          <button class="flex items-center justify-center p-3 text-slate-400 hover:text-primary transition-colors" title="上传素材">
            <span class="material-symbols-outlined">attach_file</span>
          </button>
          <input
            v-model="inputText"
            data-agent-input="home"
            class="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-base text-slate-800 dark:text-slate-200 placeholder:text-slate-400 py-3 px-2"
            placeholder="描述您的投放目标或上传素材..."
            type="text"
            @keydown.enter="handleSubmit"
          />
          <div class="flex items-center gap-2 pr-2">
            <button
              v-if="agent.agentRunning.value"
              class="inline-flex h-10 items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 text-sm font-medium text-red-600 hover:bg-red-100 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300"
              @click="agent.abort()"
            >
              <span class="material-symbols-outlined text-base">stop</span>
              停止
            </button>
            <button
              v-else
              class="bg-primary text-white h-10 px-4 rounded-md flex items-center gap-2 justify-center hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="agent.loading.value || agent.agentRunning.value || !inputText.trim()"
              @click="handleSubmit"
            >
              <span class="text-sm font-medium">发送</span>
              <span class="material-symbols-outlined text-base">arrow_forward</span>
            </button>
          </div>
        </div>
        <div class="mt-2 flex items-center justify-between gap-3 px-1 text-xs text-slate-500 dark:text-slate-400">
          <div class="relative">
            <button
              class="inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-xs font-medium hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50 dark:hover:bg-slate-800 dark:hover:text-white"
              :disabled="agent.agentRunning.value || agent.models.value.length === 0"
              @click="modelMenuOpen = !modelMenuOpen"
            >
              <span class="material-symbols-outlined text-sm">memory</span>
              <span class="max-w-[180px] truncate">{{ currentModel?.name || '选择模型' }}</span>
              <span class="material-symbols-outlined text-sm">expand_more</span>
            </button>
            <div
              v-if="modelMenuOpen"
              class="absolute bottom-full left-0 z-30 mb-2 w-72 overflow-hidden rounded-md border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
            >
              <button
                v-for="model in agent.models.value"
                :key="`${model.provider}:${model.id}`"
                class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                :class="currentModel?.provider === model.provider && currentModel?.id === model.id ? 'text-primary bg-primary/5' : 'text-slate-700 dark:text-slate-300'"
                @click="selectModel(model)"
              >
                <span class="min-w-0">
                  <span class="block truncate font-medium">{{ model.name }}</span>
                  <span class="block truncate text-xs text-slate-500">{{ model.provider }}</span>
                </span>
                <span v-if="currentModel?.provider === model.provider && currentModel?.id === model.id" class="material-symbols-outlined text-base">check</span>
              </button>
            </div>
          </div>
          <span class="hidden sm:inline">系统会根据目标自动选择合适能力</span>
        </div>
      </div>

    </div>

    <!-- Bottom spacer: pushes content to center when no output -->
    <div v-if="!hasContent" class="flex-1"></div>
        </div>
      </div>
    </main>
    <div
      v-if="taskPanelVisible && !workspaceCollapsed"
      class="hidden xl:flex w-1 shrink-0 cursor-col-resize items-stretch justify-center bg-slate-100 hover:bg-primary/20 dark:bg-slate-900 dark:hover:bg-primary/20"
      @pointerdown="startWorkspaceResize"
    >
      <div class="my-5 w-px bg-slate-300 dark:bg-slate-700"></div>
    </div>
    <LiveWorkspaceShell
      v-if="taskPanelVisible"
      :visible="taskPanelVisible"
      :collapsed="workspaceCollapsed"
      :session-id="agent.activeSession.value?.id"
      :style="workspaceStyle"
      :title="currentSessionTitle"
      :status="taskStatus"
      :summary="taskSummary"
      :tags="taskTags"
      :steps="taskSteps"
      :actions="taskActions"
      :task-type-label="taskTypeLabel"
      :phase-label="taskPhaseLabel"
      :artifacts="taskArtifacts"
      :tool-results="agent.workspaceToolResults.value"
      @toggle-collapse="toggleWorkspaceCollapsed"
      @action="handleTaskAction"
      @analyze-project="analyzeProject"
      @open-project="openProject"
    />
  </div>
</template>

<style scoped>
.agent-output {
  --bg: #ffffff;
  --surface: #ffffff;
  --surface-container: #f8fafc;
  --bg-panel: #f1f5f9;
  --bg-hover: #f1f5f9;
  --bg-selected: #eaf2ff;
  --assistant-bg: transparent;
  --user-bg: #f8fbff;
  --border: #e2e8f0;
  --outline: #cbd5e1;
  --outline-variant: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --text-dim: #94a3b8;
  --accent: #2563eb;
  --success: #059669;
  --warning: #d97706;
  --error: #dc2626;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 助手消息区域 - 移除左侧 border，增加间距 */
.agent-output :deep(.assistant-message) {
  margin-bottom: 32px;
  padding: 0;
}

.agent-output :deep(.assistant-model-row) {
  min-height: 18px;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 11px;
}

.agent-output :deep(.stream-stat),
.agent-output :deep(.tps-badge) {
  border-radius: 999px;
  padding: 2px 8px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 10px;
}

.agent-output :deep(.assistant-block-list) {
  gap: 12px;
}

.agent-output :deep(.markdown-body) {
  color: #334155;
  font-size: 15px;
  line-height: 1.75;
}

.agent-output :deep(.user-bubble) {
  max-width: min(72%, 620px);
  border: 1px solid rgba(37, 99, 235, .12);
  border-radius: 14px 14px 4px 14px;
  background: #eff6ff;
  color: #0f172a;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}

.agent-output :deep(.thinking-block),
.agent-output :deep(.tool-call-block) {
  border-color: #dbeafe;
  background: #f8fafc;
  border-radius: 10px;
}

.agent-output :deep(.thinking-block > button),
.agent-output :deep(.tool-call-block > button) {
  padding: 7px 10px;
}

.agent-output :deep(.tool-name) {
  color: #2563eb;
}

.agent-output :deep(.tool-status) {
  border-radius: 999px;
  padding: 1px 7px;
  background: #e0f2fe;
  color: #0369a1;
}

.agent-output :deep(.code-block) {
  border-radius: 10px;
  border-color: #e2e8f0;
  background: #f8fafc;
}

.agent-output :deep(.assistant-footer) {
  margin-top: 6px;
  color: #94a3b8;
}

.agent-inline-timeline {
  display: grid;
  gap: 12px;
  margin: 10px 0 18px 14px;
}

.timeline-flow-enter-active,
.timeline-flow-leave-active,
.timeline-flow-move {
  transition: opacity .26s ease, transform .26s ease, filter .26s ease;
}

.timeline-flow-enter-from,
.timeline-flow-leave-to {
  opacity: 0;
  filter: blur(4px);
  transform: translateY(10px) scale(.985);
}

.timeline-flow-leave-active {
  position: absolute;
}

@media (max-width: 640px) {
  .agent-inline-timeline {
    margin-left: 0;
  }
}

:global(.dark) .agent-output {
  --bg: #0f172a;
  --surface: #0f172a;
  --surface-container: #111827;
  --bg-panel: #1e293b;
  --bg-hover: #1e293b;
  --bg-selected: rgba(37, 99, 235, .2);
  --assistant-bg: transparent;
  --user-bg: rgba(30, 41, 59, .72);
  --border: #334155;
  --outline: #475569;
  --outline-variant: #334155;
  --text: #f8fafc;
  --text-muted: #cbd5e1;
  --text-dim: #94a3b8;
}

:global(.dark) .agent-output :deep(.markdown-body) {
  color: #e2e8f0;
}

:global(.dark) .agent-output :deep(.assistant-message) {
  border-left-color: rgba(96, 165, 250, .24);
}

:global(.dark) .agent-output :deep(.user-bubble) {
  border-color: rgba(96, 165, 250, .24);
  background: rgba(37, 99, 235, .18);
  color: #f8fafc;
}

:global(.dark) .agent-output :deep(.stream-stat),
:global(.dark) .agent-output :deep(.tps-badge),
:global(.dark) .agent-output :deep(.thinking-block),
:global(.dark) .agent-output :deep(.tool-call-block),
:global(.dark) .agent-output :deep(.code-block) {
  background: rgba(15, 23, 42, .72);
  border-color: #334155;
}

</style>
