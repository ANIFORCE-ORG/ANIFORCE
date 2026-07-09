<script setup lang="ts">
/**
 * Workspace 投影渲染器
 * 按 projection.surface 分发到现有业务组件，不重新实现业务卡片
 */
import { computed, ref, watch } from 'vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import CampaignCollectionView from '@/components/campaigns/CampaignCollectionView.vue'
import MaterialCollectionView from '@/components/materials/MaterialCollectionView.vue'
import WorkspaceProjectCreate from './WorkspaceProjectCreate.vue'
import CreateProjectForm from '@/components/projects/CreateProjectForm.vue'
import CreateCampaignModal from '@/components/campaigns/CreateCampaignModal.vue'
import type { WorkspaceProjection, WorkspaceApprovalDraft } from '@/store/workspace'
import { getProjectDetail, type Project } from '@/api/projects'
import { getCampaignDetail, type Campaign } from '@/api/campaigns'
import { getMaterialDetail, type Material } from '@/api/materials'
import { fromCreateProjectArgs, toCreateProjectPayload, type ProjectFormModel } from '@/components/projects/projectFormModel'

const props = defineProps<{
  projection: WorkspaceProjection | null
  approvalDraft: WorkspaceApprovalDraft | null
  sessionId: string
}>()

const emit = defineEmits<{
  approve: [payload: { checkpointId: string; editedArguments: Record<string, unknown>; argumentDiff: Array<{ field: string; before: unknown; after: unknown }> }]
  reject: [checkpointId: string]
  updateApprovalForm: [payload: { checkpointId: string; formModel: import('@/components/projects/projectFormModel').ProjectFormModel }]
  selectEntity: [entity: { type: 'project' | 'campaign' | 'material'; id: string; name?: string }]
  mentionEntity: [entity: { type: 'project' | 'campaign' | 'material'; id: string; name?: string }]
  viewProject: [projectId: string]
  editProject: [projectId: string]
  createProjectTask: [projectId: string]
  viewProjectTasks: [projectId: string]
  viewCampaign: [campaignId: string]
  viewMaterial: [materialId: string]
}>()

const projects = computed<Project[]>(() => {
  if (!props.projection) return []
  const data = props.projection.payload
  if (Array.isArray(data.projects)) return data.projects as Project[]
  const project = data.project
  if (project && typeof project === 'object') return [project as Project]
  return []
})

const campaigns = computed<Campaign[]>(() => {
  if (!props.projection) return []
  const data = props.projection.payload
  if (Array.isArray(data.campaigns)) return data.campaigns as Campaign[]
  const campaign = data.campaign
  if (campaign && typeof campaign === 'object') return [campaign as Campaign]
  return []
})

const materials = computed<Material[]>(() => {
  if (!props.projection) return []
  const data = props.projection.payload
  if (Array.isArray(data.materials)) return data.materials as Material[]
  const material = data.material
  if (material && typeof material === 'object') return [material as Material]
  return []
})

const materialImage = computed<Record<string, unknown> | null>(() => {
  if (!props.projection || props.projection.surface !== 'material.image') return null
  const image = props.projection.payload.image
  return image && typeof image === 'object' ? image as Record<string, unknown> : null
})

const approvalEntity = ref<Project | Campaign | Material | null>(null)
const approvalEntitySnapshot = ref<Project | Campaign | Material | null>(null)
const approvalEntityLoading = ref(false)
const approvalEntityError = ref('')
const projectEditForm = ref<ProjectFormModel | null>(null)

const approvalArgs = computed<Record<string, unknown>>(() => {
  if (!props.approvalDraft) return {}
  return props.approvalDraft.editedArguments || props.approvalDraft.originalArguments || {}
})

const approvalAction = computed<'create' | 'update' | 'delete' | 'other'>(() => {
  const toolName = props.approvalDraft?.toolName || ''
  if (toolName.startsWith('create_')) return 'create'
  if (toolName.startsWith('update_')) return 'update'
  if (toolName.startsWith('delete_')) return 'delete'
  return 'other'
})

const approvalDomain = computed<'project' | 'campaign' | 'material' | 'other'>(() => {
  const toolName = props.approvalDraft?.toolName || ''
  if (toolName.includes('_project')) return 'project'
  if (toolName.includes('_campaign')) return 'campaign'
  if (toolName.includes('_material')) return 'material'
  return 'other'
})

const approvalTitle = computed(() => {
  const actionText = { create: '创建', update: '修改', delete: '删除', other: '执行' }[approvalAction.value]
  const domainText = { project: '项目', campaign: '广告计划', material: '素材', other: '操作' }[approvalDomain.value]
  return `${actionText}${domainText}`
})

const approvalStatusText = computed(() => {
  const status = props.approvalDraft?.status || 'pending'
  if (status === 'executing' || status === 'approved') return '执行中'
  if (status === 'completed') return '已完成'
  if (status === 'rejected') return '已拒绝'
  return '待确认'
})

const approvalStatusClass = computed(() => {
  const status = props.approvalDraft?.status || 'pending'
  if (status === 'completed') return 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-300'
  if (status === 'rejected') return 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'
  if (status === 'executing' || status === 'approved') return 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300'
  return 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300'
})

const approvalDescription = computed(() => {
  const status = props.approvalDraft?.status || 'pending'
  if (status === 'executing' || status === 'approved') return `已确认，正在执行 ${props.approvalDraft?.toolName || '操作'}`
  if (status === 'completed') return '操作已完成，业务结果已返回对话区'
  if (status === 'rejected') return '你已拒绝，本次操作不会执行'
  return `请审阅右侧业务内容，确认后才会执行 ${props.approvalDraft?.toolName || '操作'}`
})

const displayEntity = computed(() => approvalEntity.value || approvalEntitySnapshot.value)
const entityList = computed(() => displayEntity.value ? [displayEntity.value] : [])
const materialApprovalList = computed<Material[]>(() => {
  const base = displayEntity.value && approvalDomain.value === 'material' ? displayEntity.value as Material : {}
  const merged = { ...base, ...approvalArgs.value } as Material
  return merged.name || merged.id ? [merged] : []
})

const deletedEntityFallback = computed(() => {
  if (approvalAction.value !== 'delete' || props.approvalDraft?.status !== 'completed') return null
  const id = String(approvalArgs.value.project_id || approvalArgs.value.campaign_id || approvalArgs.value.material_id || '')
  if (!id || displayEntity.value) return null
  const domainText = { project: '项目', campaign: '广告计划', material: '素材', other: '对象' }[approvalDomain.value]
  return { id, domainText }
})

function projectToFormArgs(project: Project, args: Record<string, unknown>): Record<string, unknown> {
  return {
    name: project.name,
    product: project.product,
    target_market: project.target_market,
    status: project.status,
    start_date: project.start_date,
    end_date: project.end_date,
    total_budget: project.total_budget,
    description: project.description,
    ...args,
  }
}

watch(
  () => [props.approvalDraft?.checkpointId, props.approvalDraft?.toolName, props.approvalDraft?.status, JSON.stringify(approvalArgs.value)],
  async () => {
    approvalEntityError.value = ''
    projectEditForm.value = null
    if (!props.approvalDraft) return

    const args = approvalArgs.value
    const id = String(args.project_id || args.campaign_id || args.material_id || '')
    const status = props.approvalDraft.status
    if (approvalAction.value === 'delete' && status === 'completed') {
      approvalEntity.value = approvalEntitySnapshot.value
      return
    }
    approvalEntity.value = null
    if (!id || approvalAction.value === 'create') {
      if (approvalDomain.value === 'project' && approvalAction.value === 'update') {
        projectEditForm.value = fromCreateProjectArgs(args)
      }
      return
    }

    approvalEntityLoading.value = true
    try {
      if (approvalDomain.value === 'project') {
        const project = await getProjectDetail(id)
        approvalEntity.value = project
        approvalEntitySnapshot.value = project
        if (approvalAction.value === 'update') {
          projectEditForm.value = fromCreateProjectArgs(projectToFormArgs(project, args))
        }
      }
      if (approvalDomain.value === 'campaign') {
        const campaign = await getCampaignDetail(id)
        approvalEntity.value = campaign
        approvalEntitySnapshot.value = campaign
      }
      if (approvalDomain.value === 'material') {
        const material = await getMaterialDetail(id)
        approvalEntity.value = material
        approvalEntitySnapshot.value = material
      }
    } catch (error) {
      if (approvalAction.value === 'delete' && (status === 'executing' || status === 'approved' || status === 'completed')) {
        approvalEntity.value = approvalEntitySnapshot.value
        approvalEntityError.value = ''
      } else {
        approvalEntityError.value = error instanceof Error ? error.message : '加载详情失败'
      }
    } finally {
      approvalEntityLoading.value = false
    }
  },
  { immediate: true },
)

function handleApprove(payload: { editedArguments: Record<string, unknown>; argumentDiff: Array<{ field: string; before: unknown; after: unknown }> }): void {
  if (!props.approvalDraft) return
  emit('approve', {
    checkpointId: props.approvalDraft.checkpointId,
    editedArguments: payload.editedArguments,
    argumentDiff: payload.argumentDiff,
  })
}

function handleReject(): void {
  if (!props.approvalDraft) return
  emit('reject', props.approvalDraft.checkpointId)
}

function handleUpdateApprovalForm(formModel: import('@/components/projects/projectFormModel').ProjectFormModel): void {
  if (!props.approvalDraft) return
  emit('updateApprovalForm', { checkpointId: props.approvalDraft.checkpointId, formModel })
}

function handleApproveRaw(): void {
  if (!props.approvalDraft) return
  emit('approve', {
    checkpointId: props.approvalDraft.checkpointId,
    editedArguments: approvalArgs.value,
    argumentDiff: [],
  })
}

function handleApproveProjectEdit(): void {
  if (!props.approvalDraft || !projectEditForm.value) return
  const projectId = String(approvalArgs.value.project_id || '')
  emit('approve', {
    checkpointId: props.approvalDraft.checkpointId,
    editedArguments: { project_id: projectId, ...toCreateProjectPayload(projectEditForm.value) },
    argumentDiff: [],
  })
}

function handleCampaignSubmit(data: unknown): void {
  if (!props.approvalDraft) return
  const submitted = data && typeof data === 'object' ? data as Record<string, unknown> : {}
  emit('approve', {
    checkpointId: props.approvalDraft.checkpointId,
    editedArguments: { ...approvalArgs.value, ...submitted },
    argumentDiff: [],
  })
}

function handleViewDetail(project: Project): void {
  emit('viewProject', project.id)
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
}

function handleEditProject(project: Project): void {
  emit('editProject', project.id)
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
}

function handleCreateProjectTask(project: Project): void {
  emit('createProjectTask', project.id)
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
}

function handleViewProjectTasks(project: Project): void {
  emit('viewProjectTasks', project.id)
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
}

function handleSelectProject(project: Project): void {
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
}

function handleMentionProject(project: Project): void {
  emit('mentionEntity', { type: 'project', id: project.id, name: project.name })
}

function handleSelectCampaign(campaign: Campaign): void {
  emit('selectEntity', { type: 'campaign', id: campaign.id, name: campaign.name })
}

function handleMentionCampaign(campaign: Campaign): void {
  emit('mentionEntity', { type: 'campaign', id: campaign.id, name: campaign.name })
}

function handleSelectMaterial(material: Material): void {
  emit('selectEntity', { type: 'material', id: material.id, name: material.name })
}

function handleMentionMaterial(material: Material): void {
  emit('mentionEntity', { type: 'material', id: material.id, name: material.name })
}

function handlePreviewMaterial(material: Material): void {
  handleSelectMaterial(material)
  emit('viewMaterial', material.id)
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <!-- 项目列表（查询类工具，无需审批） -->
    <div v-if="projection?.surface === 'project.list' || projection?.surface === 'project.detail'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ projection.surface === 'project.detail' ? '项目详情' : '项目库' }}</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'project.detail' ? '已加载 1 个项目' : `共 ${projects.length} 个项目` }}
          </p>
        </div>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-500">数据已更新，可刷新</span>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <ProjectCollectionView
        v-else
        :projects="projects"
        mode="workspace"
        embedded
        @edit="handleEditProject"
        @view-detail="handleViewDetail"
        @view-tasks="handleViewProjectTasks"
        @create-task="handleCreateProjectTask"
        @select="(project: Project) => handleSelectProject(project)"
        @mention="handleMentionProject"
      />
    </div>

    <!-- 广告计划列表（查询类工具，无需审批） -->
    <div v-else-if="projection?.surface === 'campaign.list' || projection?.surface === 'campaign.detail'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ projection.surface === 'campaign.detail' ? '广告计划详情' : '广告计划' }}</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'campaign.detail' ? '已加载 1 个计划' : `共 ${campaigns.length} 个计划` }}
          </p>
        </div>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-500">数据已更新，可刷新</span>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <CampaignCollectionView
        v-else
        :campaigns="campaigns"
        embedded
        @select="handleSelectCampaign"
        @mention="handleMentionCampaign"
        @view="campaignId => emit('viewCampaign', campaignId)"
      />
    </div>

    <!-- 素材列表（查询类工具，无需审批） -->
    <div v-else-if="projection?.surface === 'material.list' || projection?.surface === 'material.detail' || projection?.surface === 'campaign.materials'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ projection.surface === 'campaign.materials' ? '广告计划素材' : projection.surface === 'material.detail' ? '素材详情' : '素材库' }}</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'material.detail' ? '已加载 1 个素材' : `共 ${materials.length} 个素材` }}
          </p>
        </div>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-500">数据已更新，可刷新</span>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <MaterialCollectionView
        v-else
        :materials="materials"
        embedded
        @select="handleSelectMaterial"
        @mention="handleMentionMaterial"
        @preview="handlePreviewMaterial"
      />
    </div>

    <div v-else-if="projection?.surface === 'material.image'" class="p-[16px]">
      <div class="mb-[12px]">
        <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">素材预览资源</h3>
        <p class="text-[10px] text-slate-500 dark:text-slate-400">{{ projection.mode === 'loading' ? '正在查询...' : '已加载预览资源信息' }}</p>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <div v-else class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-700 dark:bg-slate-800">
        <img v-if="typeof materialImage?.url === 'string'" :src="materialImage.url" class="mb-[12px] max-h-[360px] w-full rounded object-contain bg-slate-100 dark:bg-slate-900" />
        <pre class="max-h-[260px] overflow-auto rounded bg-slate-50 p-[10px] text-[10px] leading-relaxed text-slate-600 dark:bg-slate-900 dark:text-slate-300">{{ JSON.stringify(materialImage || projection.payload, null, 2) }}</pre>
      </div>
    </div>

    <!-- 审批确认：只复用现有 SaaS 业务组件，Workspace 只提供审批外壳 -->
    <WorkspaceProjectCreate
      v-else-if="projection?.surface === 'approval.review' && approvalDraft?.toolName === 'create_project' && approvalDraft.status === 'pending'"
      :draft="approvalDraft"
      @approve="handleApprove"
      @reject="handleReject"
      @update-form="handleUpdateApprovalForm"
    />

    <!-- 项目创建已完成：显示创建的项目详情 -->
    <div
      v-else-if="projection?.surface === 'approval.review' && approvalDraft?.toolName === 'create_project' && (approvalDraft.status === 'completed' || approvalDraft.status === 'executing' || approvalDraft.status === 'approved')"
      class="flex h-full flex-col"
    >
      <div class="flex items-center justify-between border-b border-slate-200 px-[16px] py-[12px] dark:border-slate-700">
        <div class="flex items-center gap-[8px]">
          <span class="material-symbols-outlined text-[18px] text-emerald-500">
            {{ approvalDraft.status === 'completed' ? 'check_circle' : 'progress_activity' }}
          </span>
          <div>
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ approvalTitle }}</h3>
            <p class="text-[10px] text-slate-500 dark:text-slate-400">{{ approvalDescription }}</p>
          </div>
        </div>
        <span class="rounded-full px-[8px] py-[3px] text-[10px] font-medium" :class="approvalStatusClass">{{ approvalStatusText }}</span>
      </div>

      <div class="flex-1 overflow-y-auto p-[16px]">
        <div
          v-if="approvalDraft.status === 'executing' || approvalDraft.status === 'approved'"
          class="mb-[12px] flex items-center gap-[8px] rounded-md border border-blue-100 bg-blue-50 p-[10px] text-[11px] text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300"
        >
          <span class="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
          正在创建项目...
        </div>

        <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-700 dark:bg-slate-800">
          <div class="mb-[12px]">
            <h4 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ approvalArgs.name || '新项目' }}</h4>
            <p v-if="approvalArgs.description" class="mt-[4px] text-[11px] text-slate-600 dark:text-slate-300">{{ approvalArgs.description }}</p>
          </div>

          <div class="space-y-[8px] text-[11px]">
            <div v-if="approvalArgs.target_market" class="flex items-center justify-between">
              <span class="text-slate-500 dark:text-slate-400">目标市场</span>
              <span class="font-medium text-slate-900 dark:text-white">{{ approvalArgs.target_market }}</span>
            </div>
            <div v-if="approvalArgs.product" class="flex items-center justify-between">
              <span class="text-slate-500 dark:text-slate-400">产品</span>
              <span class="font-medium text-slate-900 dark:text-white">{{ approvalArgs.product }}</span>
            </div>
            <div v-if="approvalArgs.total_budget" class="flex items-center justify-between">
              <span class="text-slate-500 dark:text-slate-400">总预算</span>
              <span class="font-medium text-emerald-600 dark:text-emerald-400">¥{{ Number(approvalArgs.total_budget).toLocaleString() }}</span>
            </div>
            <div v-if="approvalArgs.status" class="flex items-center justify-between">
              <span class="text-slate-500 dark:text-slate-400">状态</span>
              <span class="rounded-full bg-emerald-50 px-[8px] py-[2px] text-[10px] font-medium text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400">
                {{ approvalArgs.status === 'active' ? '活跃' : approvalArgs.status }}
              </span>
            </div>
            <div v-if="approvalArgs.start_date || approvalArgs.end_date" class="flex items-center justify-between">
              <span class="text-slate-500 dark:text-slate-400">时间范围</span>
              <span class="text-slate-600 dark:text-slate-300">
                {{ approvalArgs.start_date ? String(approvalArgs.start_date).split('T')[0] : '—' }}
                至
                {{ approvalArgs.end_date ? String(approvalArgs.end_date).split('T')[0] : '—' }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="approvalDraft.status === 'completed'" class="mt-[12px] rounded-md border border-emerald-200 bg-emerald-50 p-[10px] text-[11px] text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300">
          <span class="material-symbols-outlined mr-[4px] inline-block align-middle text-[14px]">info</span>
          项目已创建，详细结果见对话区
        </div>
      </div>
    </div>

    <div v-else-if="projection?.surface === 'approval.review' && approvalDraft" class="flex h-full flex-col">
      <div class="flex items-center justify-between border-b border-slate-200 px-[16px] py-[12px] dark:border-slate-700">
        <div class="flex items-center gap-[8px]">
          <span class="material-symbols-outlined text-[18px]" :class="approvalAction === 'delete' ? 'text-red-500' : 'text-amber-500'">
            {{ approvalDraft.status === 'completed' ? 'check_circle' : approvalAction === 'delete' ? 'delete' : 'approval' }}
          </span>
          <div>
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ approvalTitle }}</h3>
            <p v-if="approvalDraft.status !== 'completed'" class="text-[10px] text-slate-500 dark:text-slate-400">{{ approvalDescription }}</p>
          </div>
        </div>
        <span class="rounded-full px-[8px] py-[3px] text-[10px] font-medium" :class="approvalStatusClass">{{ approvalStatusText }}</span>
      </div>

      <div class="flex-1 overflow-y-auto p-[16px]">
        <div
          v-if="approvalDraft.status === 'executing' || approvalDraft.status === 'approved'"
          class="mb-[12px] flex items-center gap-[8px] rounded-md border border-blue-100 bg-blue-50 p-[10px] text-[11px] text-blue-700 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-300"
        >
          <span class="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
          正在执行，业务内容已锁定
        </div>
        <div
          v-else-if="approvalDraft.status === 'rejected'"
          class="mb-[12px] flex items-center gap-[8px] rounded-md border border-slate-200 bg-slate-50 p-[10px] text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          <span class="material-symbols-outlined text-[16px]">block</span>
          已拒绝，本次操作未执行
        </div>

        <div v-if="approvalEntityLoading" class="flex items-center justify-center py-[40px]">
          <div class="h-[16px] w-[16px] animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
        </div>
        <div v-else-if="approvalEntityError" class="rounded-md border border-red-200 bg-red-50 p-[12px] text-[11px] text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
          {{ approvalEntityError }}
        </div>

        <div v-else-if="deletedEntityFallback" class="rounded-md border border-emerald-200 bg-white p-[14px] dark:border-emerald-900/40 dark:bg-slate-800">
          <div class="mb-[10px] flex items-center gap-[8px]">
            <span class="material-symbols-outlined text-[18px] text-emerald-500">check_circle</span>
            <div>
              <h4 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ deletedEntityFallback.domainText }}已删除</h4>
              <p class="text-[10px] text-slate-500 dark:text-slate-400">ID: {{ deletedEntityFallback.id }}</p>
            </div>
          </div>
          <p class="text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">
            最终影响见对话区返回结果。
          </p>
        </div>

        <CreateProjectForm
          v-else-if="approvalDraft.toolName === 'update_project' && projectEditForm"
          v-model="projectEditForm"
          edit-mode
          :errors="{}"
        />

        <CreateCampaignModal
          v-else-if="approvalDraft.toolName === 'create_campaign' || approvalDraft.toolName === 'update_campaign'"
          show
          embedded
          :embedded-readonly="approvalDraft.status !== 'pending'"
          :initial-data="approvalDraft.toolName === 'update_campaign' ? { ...(approvalEntity || {}), ...approvalArgs } : approvalArgs"
          @submit="handleCampaignSubmit"
          @close="handleReject"
        />

        <ProjectCollectionView
          v-else-if="approvalDomain === 'project' && approvalEntity"
          :projects="entityList as Project[]"
          view="detailed"
          mode="readonly"
          embedded
        />

        <CampaignCollectionView
          v-else-if="approvalDomain === 'campaign' && approvalEntity"
          :campaigns="entityList as Campaign[]"
          embedded
          @view="campaignId => emit('viewCampaign', campaignId)"
        />

        <MaterialCollectionView
          v-else-if="approvalDomain === 'material' && materialApprovalList.length"
          :materials="materialApprovalList"
          embedded
          @preview="handlePreviewMaterial"
          @select="handleSelectMaterial"
          @mention="handleMentionMaterial"
        />

        <MaterialCollectionView
          v-else-if="approvalDomain === 'material' && approvalAction === 'create' && materialApprovalList.length"
          :materials="materialApprovalList"
          embedded
        />

        <div v-else class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-700 dark:bg-slate-800">
          <p class="mb-[8px] text-[11px] text-slate-500 dark:text-slate-400">未找到可复用的业务组件，以下仅作为调试兜底。</p>
          <pre class="max-h-[260px] overflow-auto rounded bg-slate-50 p-[10px] text-[10px] leading-relaxed text-slate-600 dark:bg-slate-900 dark:text-slate-300">{{ JSON.stringify(approvalArgs, null, 2) }}</pre>
        </div>
      </div>

      <div v-if="approvalDraft.status === 'pending' && !(approvalDraft.toolName === 'create_campaign' || approvalDraft.toolName === 'update_campaign')" class="flex items-center justify-end gap-[8px] border-t border-slate-200 px-[16px] py-[12px] dark:border-slate-700">
        <button class="rounded-md border border-slate-200 px-[12px] py-[7px] text-[11px] font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700" @click="handleReject">拒绝</button>
        <button
          class="rounded-md px-[12px] py-[7px] text-[11px] font-semibold text-white"
          :class="approvalAction === 'delete' ? 'bg-red-600 hover:bg-red-700' : 'bg-primary hover:bg-primary/90'"
          @click="approvalDraft.toolName === 'update_project' ? handleApproveProjectEdit() : handleApproveRaw()"
        >
          {{ approvalAction === 'delete' ? '确认删除' : approvalAction === 'update' ? '确认修改' : '确认执行' }}
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center h-full py-[60px] px-[20px] text-center">
      <span class="material-symbols-outlined text-[40px] text-slate-300 dark:text-slate-700 mb-[12px]">workspaces</span>
      <p class="text-[12px] text-slate-500 dark:text-slate-400">
        Agent 正在工作，操作结果会在这里实时呈现
      </p>
    </div>
  </div>
</template>
