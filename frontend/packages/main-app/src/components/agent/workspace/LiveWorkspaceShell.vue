<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import CampaignDraftWorkspace from './CampaignDraftWorkspace.vue'
import CreativeWorkspace from './CreativeWorkspace.vue'
import EmbeddedTaskTimeline, { type WorkspaceStep } from './EmbeddedTaskTimeline.vue'
import ProjectWorkspaceDetail from './ProjectWorkspaceDetail.vue'
import ProjectListWorkspace from './ProjectListWorkspace.vue'
import type { TaskPanelAction, TaskPanelArtifact, TaskPanelStatus } from '../TaskStatusPanel.vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import CampaignCollectionView from '@/components/campaigns/CampaignCollectionView.vue'
import MaterialLibraryView from '@/components/materials/MaterialLibraryView.vue'
import type { Project } from '@/api/projects'
import type { Campaign } from '@/api/campaigns'
import type { Material } from '@/api/materials'

const props = defineProps<{
  visible: boolean
  collapsed?: boolean
  sessionId?: string
  title: string
  status: TaskPanelStatus
  summary: string
  tags: string[]
  steps: WorkspaceStep[]
  actions: TaskPanelAction[]
  taskTypeLabel?: string
  phaseLabel?: string
  artifacts?: TaskPanelArtifact[]
  toolResults?: Array<{ id: string; name: string; result?: unknown; isError?: boolean }>
}>()

const emit = defineEmits<{
  action: [key: string]
  toggleCollapse: []
  analyzeProject: [project: Project]
  openProject: [project: Project]
}>()

const statusMeta: Record<TaskPanelStatus, { label: string; icon: string; badge: string }> = {
  created: { label: '已创建', icon: 'radio_button_unchecked', badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300' },
  running: { label: '进行中', icon: 'progress_activity', badge: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300' },
  waiting_user_input: { label: '等待补充', icon: 'edit_note', badge: 'bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300' },
  waiting_approval: { label: '等待确认', icon: 'approval_delegation', badge: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' },
  applying: { label: '执行中', icon: 'bolt', badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' },
  completed: { label: '已完成', icon: 'check_circle', badge: 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300' },
  failed: { label: '失败', icon: 'error', badge: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300' },
  canceled: { label: '已取消', icon: 'do_not_disturb_on', badge: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' }
}

const artifacts = computed(() => props.artifacts || [])
const toolResults = computed(() => props.toolResults || [])
const workspaceHasContent = computed(() => artifacts.value.length > 0 || toolResults.value.length > 0)
const workspaceKind = computed(() => {
  const artifactTypes = artifacts.value.map(item => item.type)
  const label = props.taskTypeLabel || ''
  if (artifactTypes.includes('campaign_draft') || label.includes('投放')) return 'campaign'
  if (
    artifactTypes.some(type => ['creative_brief', 'image_asset', 'video_asset'].includes(String(type))) ||
    label.includes('素材')
  ) return 'creative'
  return 'empty'
})

function latestToolResult(toolName: string) {
  return [...toolResults.value].reverse().find(tool => tool.name === toolName && tool.result !== undefined && !tool.isError)
}

function unwrapToolPayload(result: unknown): Record<string, unknown> | null {
  if (!result || typeof result !== 'object') return null
  const record = result as Record<string, unknown>
  const details = record.details
  if (details && typeof details === 'object') return details as Record<string, unknown>
  return record
}

const projectPayload = computed<Record<string, unknown> | null>(() => {
  return unwrapToolPayload(latestToolResult('listProjects')?.result)
})

const projectItems = computed<Project[]>(() => {
  const record = projectPayload.value
  if (!record) return []
  const items = record.items || record.list || record.projects
  return Array.isArray(items) ? items as Project[] : []
})

const hasProjectResult = computed(() => Boolean(projectPayload.value))
const selectedProject = ref<Project | null>(null)
const selectedProjectStorageKey = computed(() => `aniforce.workspace.selectedProject.${props.sessionId || props.title}`)
const legacySelectedProjectId = ref<string | null>(null)

function readStoredSelectedProject(): Project | null {
  const raw = sessionStorage.getItem(selectedProjectStorageKey.value)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed === 'string') {
      legacySelectedProjectId.value = parsed
      return null
    }
    return parsed && typeof parsed === 'object' && typeof parsed.id === 'string' ? parsed as Project : null
  } catch {
    legacySelectedProjectId.value = raw
    return null
  }
}

watch(projectItems, items => {
  const storedProject = readStoredSelectedProject()
  const rememberedId = selectedProject.value?.id || storedProject?.id || legacySelectedProjectId.value
  if (!rememberedId) return
  const next = items.find(item => item.id === rememberedId)
  selectedProject.value = next || storedProject
}, { immediate: true })

function selectProject(project: Project) {
  selectedProject.value = project
  sessionStorage.setItem(selectedProjectStorageKey.value, JSON.stringify(project))
}

function clearSelectedProject() {
  selectedProject.value = null
  sessionStorage.removeItem(selectedProjectStorageKey.value)
}

function handleProjectListWorkspaceAction(action: string, payload: Record<string, unknown>) {
  const project = payload.project as Project | undefined
  const projectId = String(payload.projectId || project?.id || '')
  if (action === 'open_project' && projectId) {
    emit('openProject', project || ({ id: projectId } as Project))
    return
  }
  if (action === 'create_campaign' && projectId) {
    window.location.href = `/campaign/create?project_id=${encodeURIComponent(projectId)}`
  }
}

const campaignPayload = computed<Record<string, unknown> | null>(() => {
  return unwrapToolPayload(latestToolResult('listCampaigns')?.result)
})

const campaignItems = computed<Campaign[]>(() => {
  const record = campaignPayload.value
  if (!record) return []
  const items = record.campaigns || record.items || record.list
  return Array.isArray(items) ? items as Campaign[] : []
})

const hasCampaignResult = computed(() => Boolean(campaignPayload.value))

const materialPayload = computed<Record<string, unknown> | null>(() => {
  return unwrapToolPayload(latestToolResult('listMaterials')?.result)
})

const materialItems = computed<Material[]>(() => {
  const record = materialPayload.value
  if (!record) return []
  const items = record.materials || record.items || record.list
  return Array.isArray(items) ? items as Material[] : []
})

const hasMaterialResult = computed(() => Boolean(materialPayload.value))

const projectListPayload = computed<Record<string, unknown> | null>(() => {
  const tool = latestToolResult('project_list')
  if (!tool) return null
  const result = tool.result
  if (!result || typeof result !== 'object') return null
  return result as Record<string, unknown>
})

const hasProjectListResult = computed(() => Boolean(projectListPayload.value))
const hasStructuredBusinessResult = computed(() => hasProjectResult.value || hasCampaignResult.value || hasMaterialResult.value || hasProjectListResult.value || workspaceKind.value !== 'empty')

function formatToolResult(value: unknown): string {
  if (value === undefined) return '运行中...'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}
</script>

<template>
  <aside class="hidden xl:flex shrink-0 border-l border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
    <div v-if="collapsed" class="flex h-full w-full flex-col items-center gap-3 py-4">
      <button
        class="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:text-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        title="展开工作台"
        @click="emit('toggleCollapse')"
      >
        <span class="material-symbols-outlined text-lg">left_panel_open</span>
      </button>
      <div class="h-px w-8 bg-slate-200 dark:bg-slate-800"></div>
      <span class="material-symbols-outlined text-lg" :class="{ 'animate-spin text-blue-600': status === 'running' || status === 'applying', 'text-slate-400': status !== 'running' && status !== 'applying' }">
        {{ statusMeta[status].icon }}
      </span>
      <div class="writing-vertical text-xs font-semibold text-slate-400">Workspace</div>
    </div>

    <div v-else class="flex h-full w-full flex-col overflow-hidden">
      <header class="border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-950">
        <div class="flex items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-2">
            <span class="material-symbols-outlined text-base text-slate-400">dashboard_customize</span>
            <h2 class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">Workspace</h2>
          </div>
          <button
            class="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            title="收起工作台"
            @click="emit('toggleCollapse')"
          >
            <span class="material-symbols-outlined text-lg">right_panel_close</span>
          </button>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-2">
          <span class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold" :class="statusMeta[status].badge">
            <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': status === 'running' || status === 'applying' }">
              {{ statusMeta[status].icon }}
            </span>
            {{ statusMeta[status].label }}
          </span>
          <span v-if="taskTypeLabel" class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {{ taskTypeLabel }}
          </span>
          <span v-if="phaseLabel" class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {{ phaseLabel }}
          </span>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
        <section class="border-b border-slate-100 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-950">
          <p class="text-sm leading-6 text-slate-500 dark:text-slate-400">{{ summary }}</p>
          <div v-if="tags.length" class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="tag in tags"
              :key="tag"
              class="rounded-md bg-white px-2 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200 dark:bg-slate-950 dark:text-slate-300 dark:ring-slate-800"
            >
              {{ tag }}
            </span>
          </div>
        </section>

        <main class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <section class="min-h-full">
            <ProjectWorkspaceDetail
              v-if="selectedProject"
              :project="selectedProject"
              @back="clearSelectedProject"
              @analyze="emit('analyzeProject', $event)"
              @open-full-page="emit('openProject', $event)"
            />
            <CampaignDraftWorkspace v-else-if="workspaceKind === 'campaign'" :artifacts="artifacts" />
            <CreativeWorkspace v-else-if="workspaceKind === 'creative'" :artifacts="artifacts" />
            <div v-else-if="hasProjectResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">项目管理</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">选择项目后可在画布内继续分析，复杂操作可打开完整页面。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ projectItems.length }} 个项目
                </span>
              </div>
              <ProjectCollectionView
                :projects="projectItems"
                view="detailed"
                mode="workspace"
                embedded
                @view-detail="selectProject"
              />
            </div>
            <div v-else-if="hasProjectListResult" class="h-full">
              <ProjectListWorkspace
                :result="projectListPayload || {}"
                @action="handleProjectListWorkspaceAction"
              />
            </div>
            <div v-else-if="hasCampaignResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">广告投放</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">与广告投放页使用同一套计划模板。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ campaignItems.length }} 个计划
                </span>
              </div>
              <CampaignCollectionView
                :campaigns="campaignItems"
                embedded
              />
            </div>
            <div v-else-if="hasMaterialResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">创意素材</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">与创意素材页使用同一套素材模板。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ materialItems.length }} 个素材
                </span>
              </div>
              <MaterialLibraryView
                :materials="materialItems"
                embedded
              />
            </div>
            <div v-else-if="toolResults.length" class="space-y-4">
              <section
                v-for="tool in toolResults"
                :key="tool.id"
                class="rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              >
                <div class="flex items-center justify-between border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                  <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-base text-primary">database</span>
                    <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ tool.name }}</span>
                  </div>
                  <span class="rounded-md px-2 py-0.5 text-xs font-medium" :class="tool.isError ? 'bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-300' : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'">
                    {{ tool.result === undefined ? 'running' : (tool.isError ? 'error' : 'done') }}
                  </span>
                </div>
                <pre class="max-h-[420px] overflow-auto p-3 text-xs leading-5 text-slate-700 dark:text-slate-300">{{ formatToolResult(tool.result) }}</pre>
              </section>
            </div>
            <div v-else class="flex min-h-[360px] items-center justify-center">
              <section class="w-full max-w-sm text-center">
                <div class="mx-auto flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 dark:border-slate-800 dark:bg-slate-900">
                  <span class="material-symbols-outlined">dashboard_customize</span>
                </div>
                <h3 class="mt-4 text-sm font-semibold text-slate-950 dark:text-white">等待业务对象</h3>
                <p class="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">项目、投放计划、素材或数据结果会在需要时展开。</p>
              </section>
            </div>
          </section>
        </main>

        <footer class="border-t border-slate-100 bg-slate-50/70 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/40">
          <div class="grid gap-3" :class="actions.length ? '2xl:grid-cols-[minmax(0,1fr)_200px]' : ''">
            <section class="min-w-0">
              <div class="mb-2 flex items-center justify-between gap-3">
                <h3 class="text-xs font-medium text-slate-500 dark:text-slate-400">活动</h3>
                <span v-if="hasStructuredBusinessResult" class="text-xs text-slate-400">业务结果已同步到画布</span>
              </div>
              <EmbeddedTaskTimeline :steps="steps" compact />
            </section>
            <section v-if="actions.length" class="min-w-0">
              <h3 class="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">下一步</h3>
              <div class="grid gap-2">
              <button
                v-for="action in actions"
                :key="action.key"
                class="flex h-9 w-full items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors"
                :class="{
                  'border-slate-900 bg-slate-900 text-white hover:bg-slate-800 dark:border-white dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100': action.tone === 'primary',
                  'border-red-200 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300': action.tone === 'danger',
                  'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800': !action.tone || action.tone === 'neutral'
                }"
                @click="emit('action', action.key)"
              >
                <span class="material-symbols-outlined text-base">{{ action.icon }}</span>
                {{ action.label }}
              </button>
              </div>
            </section>
          </div>
        </footer>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.writing-vertical {
  writing-mode: vertical-rl;
}
</style>
