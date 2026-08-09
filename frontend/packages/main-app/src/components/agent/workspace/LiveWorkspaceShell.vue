<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import CampaignDraftWorkspace from './CampaignDraftWorkspace.vue'
import CreativeWorkspace from './CreativeWorkspace.vue'
import ProjectWorkspaceDetail from './ProjectWorkspaceDetail.vue'
import ProjectListWorkspace from './ProjectListWorkspace.vue'
import type { TaskPanelArtifact } from '../TaskStatusPanel.vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import CampaignCollectionView from '@/components/campaigns/CampaignCollectionView.vue'
import MaterialCollectionView from '@/components/materials/MaterialCollectionView.vue'
import DashboardPage from '@/pages/Dashboard.vue'
import { getProjects, type Project } from '@/api/projects'
import { getCampaigns, type Campaign } from '@/api/campaigns'
import { getMaterials, type Material } from '@/api/materials'

const props = defineProps<{
  visible: boolean
  collapsed?: boolean
  sessionId?: string
  moduleHint?: 'auto' | 'dashboard' | 'projects' | 'campaigns' | 'materials'
  artifacts?: TaskPanelArtifact[]
  toolResults?: Array<{ id: string; name: string; result?: unknown; isError?: boolean }>
}>()

const emit = defineEmits<{
  toggleCollapse: []
  analyzeProject: [project: Project]
  openProject: [project: Project]
}>()

const artifacts = computed(() => props.artifacts || [])
const toolResults = computed(() => props.toolResults || [])
const workspaceKind = computed(() => {
  const artifactTypes = artifacts.value.map(item => item.type)
  if (artifactTypes.includes('campaign_draft')) return 'campaign'
  if (
    artifactTypes.some(type => ['creative_brief', 'image_asset', 'video_asset'].includes(String(type)))
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
const fallbackProjects = ref<Project[]>([])
const displayedProjectItems = computed(() => projectItems.value.length ? projectItems.value : fallbackProjects.value)
const selectedProject = ref<Project | null>(null)
const selectedProjectStorageKey = computed(() => `aniforce.workspace.selectedProject.${props.sessionId || props.moduleHint || 'default'}`)
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

watch(displayedProjectItems, items => {
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
const fallbackCampaigns = ref<Campaign[]>([])
const displayedCampaignItems = computed(() => campaignItems.value.length ? campaignItems.value : fallbackCampaigns.value)

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
const fallbackMaterials = ref<Material[]>([])
const displayedMaterialItems = computed(() => materialItems.value.length ? materialItems.value : fallbackMaterials.value)

const projectListPayload = computed<Record<string, unknown> | null>(() => {
  const tool = latestToolResult('project_list')
  if (!tool) return null
  const result = tool.result
  if (!result || typeof result !== 'object') return null
  return result as Record<string, unknown>
})

const hasProjectListResult = computed(() => Boolean(projectListPayload.value))
const hasStructuredBusinessResult = computed(() => hasProjectResult.value || hasCampaignResult.value || hasMaterialResult.value || hasProjectListResult.value || workspaceKind.value !== 'empty')
const moduleLoading = ref(false)
const moduleLoadError = ref('')
let moduleLoadVersion = 0

watch(
  () => props.moduleHint,
  async moduleHint => {
    const loadVersion = ++moduleLoadVersion
    moduleLoadError.value = ''
    if (!moduleHint || moduleHint === 'auto' || moduleHint === 'dashboard') {
      moduleLoading.value = false
      return
    }

    moduleLoading.value = true
    try {
      if (moduleHint === 'projects' && !projectItems.value.length) {
        fallbackProjects.value = await getProjects({ limit: 50 })
      }
      if (moduleHint === 'campaigns' && !campaignItems.value.length) {
        fallbackCampaigns.value = await getCampaigns({ limit: 50 })
      }
      if (moduleHint === 'materials' && !materialItems.value.length) {
        fallbackMaterials.value = await getMaterials({ limit: 50 })
      }
    } catch (error) {
      moduleLoadError.value = error instanceof Error ? error.message : '工作区模块加载失败'
    } finally {
      if (loadVersion === moduleLoadVersion) moduleLoading.value = false
    }
  },
  { immediate: true },
)

const dashboardIsActive = computed(() => (
  props.moduleHint === 'dashboard' &&
  !selectedProject.value &&
  workspaceKind.value === 'empty' &&
  !hasStructuredBusinessResult.value
))

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
      <span class="material-symbols-outlined text-lg text-slate-400">dashboard_customize</span>
      <div class="writing-vertical text-xs font-semibold text-slate-400">工作台</div>
    </div>

    <div v-else class="flex h-full w-full flex-col overflow-hidden">
      <header class="border-b border-slate-200 bg-white px-4 py-2.5 dark:border-slate-800 dark:bg-slate-950">
        <div class="flex items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-2">
            <span class="material-symbols-outlined text-base text-slate-400">dashboard_customize</span>
            <h2 class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">工作台</h2>
          </div>
          <button
            class="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            title="收起工作台"
            @click="emit('toggleCollapse')"
          >
            <span class="material-symbols-outlined text-lg">right_panel_close</span>
          </button>
        </div>
      </header>

      <main
        class="min-h-0 flex-1 overflow-y-auto"
        :class="dashboardIsActive ? 'p-0' : 'px-5 py-5'"
      >
        <section v-if="dashboardIsActive" class="h-full min-h-0">
          <DashboardPage embedded />
        </section>
        <section v-else class="min-h-full">
            <ProjectWorkspaceDetail
              v-if="selectedProject"
              :project="selectedProject"
              @back="clearSelectedProject"
              @analyze="emit('analyzeProject', $event)"
              @open-full-page="emit('openProject', $event)"
            />
            <CampaignDraftWorkspace v-else-if="workspaceKind === 'campaign'" :artifacts="artifacts" />
            <CreativeWorkspace v-else-if="workspaceKind === 'creative'" :artifacts="artifacts" />
            <div v-else-if="hasProjectListResult" class="h-full">
              <ProjectListWorkspace
                :result="projectListPayload || {}"
                @action="handleProjectListWorkspaceAction"
              />
            </div>
            <div v-else-if="hasProjectResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">项目管理</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">复用项目管理模块，选择项目后可继续分析。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ displayedProjectItems.length }} 个项目
                </span>
              </div>
              <ProjectCollectionView
                :projects="displayedProjectItems"
                view="detailed"
                mode="workspace"
                embedded
                @view-detail="selectProject"
              />
            </div>
            <div v-else-if="hasCampaignResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">广告投放</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">复用广告投放模块展示 Campaign。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ displayedCampaignItems.length }} 个计划
                </span>
              </div>
              <CampaignCollectionView
                :campaigns="displayedCampaignItems"
                embedded
              />
            </div>
            <div v-else-if="hasMaterialResult" class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-slate-950 dark:text-white">创意素材</h3>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">复用创意素材模块展示关联素材。</p>
                </div>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {{ displayedMaterialItems.length }} 个素材
                </span>
              </div>

              <MaterialCollectionView
                :materials="displayedMaterialItems"
                embedded
              />
            </div>
            <div v-else-if="moduleLoading" class="flex min-h-[320px] items-center justify-center gap-2 text-sm text-slate-500">
              <span class="material-symbols-outlined animate-spin text-base text-primary">progress_activity</span>
              正在加载工作区模块…
            </div>
            <div v-else-if="moduleLoadError" class="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ moduleLoadError }}
            </div>
            <div v-else-if="moduleHint === 'projects'" class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-base font-semibold text-slate-950 dark:text-white">项目管理</h3>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">{{ displayedProjectItems.length }} 个项目</span>
              </div>
              <ProjectCollectionView
                :projects="displayedProjectItems"
                view="detailed"
                mode="workspace"
                embedded
                @view-detail="selectProject"
              />
            </div>
            <div v-else-if="moduleHint === 'campaigns'" class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-base font-semibold text-slate-950 dark:text-white">广告投放</h3>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">{{ displayedCampaignItems.length }} 个计划</span>
              </div>
              <CampaignCollectionView :campaigns="displayedCampaignItems" embedded />
            </div>
            <div v-else-if="moduleHint === 'materials'" class="space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-base font-semibold text-slate-950 dark:text-white">创意素材</h3>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">{{ displayedMaterialItems.length }} 个素材</span>
              </div>
              <MaterialCollectionView :materials="displayedMaterialItems" embedded />
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
    </div>
  </aside>
</template>

<style scoped>
.writing-vertical {
  writing-mode: vertical-rl;
}
</style>
