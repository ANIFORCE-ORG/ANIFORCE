<script setup lang="ts">
/**
 * Workspace 投影渲染器
 * 按 projection.surface 分发到现有业务组件，不重新实现业务卡片
 */
import { computed, ref, watch } from 'vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import CampaignCollectionView from '@/components/campaigns/CampaignCollectionView.vue'
import MaterialLibraryView from '@/components/materials/MaterialLibraryView.vue'
import Dashboard from '@/pages/Dashboard.vue'
import WorkspaceProjectCreate from './WorkspaceProjectCreate.vue'
import CreateProjectForm from '@/components/projects/CreateProjectForm.vue'
import CreateCampaignModal from '@/components/campaigns/CreateCampaignModal.vue'
import type { WorkspaceProjection, WorkspaceApprovalDraft } from '@/store/workspace'
import { getProjectDetail, type Project } from '@/api/projects'
import { getCampaignDetail, type Campaign } from '@/api/campaigns'
import { getMaterialDetail, type Material } from '@/api/materials'
import { fromCreateProjectArgs, toCreateProjectPayload, type ProjectFormModel } from '@/components/projects/projectFormModel'
import type { MaterialRow } from '@/pages/creatives/materialsAdapter'

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

const approvalTitle = computed(() => approvalIntent.value.title)

const statusLabels: Record<string, string> = {
  active: '启用', running: '进行中', paused: '暂停', draft: '草稿', review: '审核中',
  ready: '待投放', fatigue: '已疲劳', archived: '已归档', deleted: '已删除',
}

const fieldLabels: Record<string, string> = {
  name: '名称', status: '状态', budget: '预算', total_budget: '总预算', platform: '平台',
  start_date: '开始日期', end_date: '结束日期', objective: '投放目标', bid_strategy: '出价策略',
  spend_limit: '花费上限', material_id: '素材', campaign_id: '广告计划', project_id: '项目',
}

const approvalIntent = computed(() => {
  const tool = props.approvalDraft?.toolName || ''
  const status = String(approvalArgs.value.status || '')
  if (tool === 'update_campaign_status') {
    const action = status === 'paused' ? '暂停' : status === 'running' || status === 'active' ? '启用' : '变更状态'
    return { title: `${action}广告计划`, summary: `将广告计划状态变更为“${statusLabels[status] || status}”`, confirm: `确认${action}` }
  }
  const relationshipActions: Record<string, { title: string; summary: string; confirm: string }> = {
    add_material_to_campaign: { title: '关联素材到广告计划', summary: '将指定素材加入该广告计划', confirm: '确认关联' },
    remove_material_from_campaign: { title: '从广告计划移除素材', summary: '解除素材与该广告计划的关联', confirm: '确认移除' },
    add_material_to_project: { title: '关联素材到项目', summary: '将指定素材加入该项目', confirm: '确认关联' },
    remove_material_from_project: { title: '从项目移除素材', summary: '解除素材与该项目的关联', confirm: '确认移除' },
  }
  if (relationshipActions[tool]) return relationshipActions[tool]
  const actionText = { create: '创建', update: '修改', delete: '删除', other: '执行' }[approvalAction.value]
  const domainText = { project: '项目', campaign: '广告计划', material: '素材', other: '业务操作' }[approvalDomain.value]
  return {
    title: `${actionText}${domainText}`,
    summary: `${actionText}${domainText}，确认前不会产生业务变更`,
    confirm: approvalAction.value === 'delete' ? '确认删除' : approvalAction.value === 'create' ? '确认创建' : approvalAction.value === 'update' ? '确认修改' : '确认执行',
  }
})

const approvalChanges = computed(() => {
  const args = approvalArgs.value
  const entity = displayEntity.value as unknown as Record<string, unknown> | null
  if (props.approvalDraft?.toolName === 'update_campaign_status') {
    return [{
      field: '状态',
      before: formatApprovalValue('status', entity?.status),
      after: formatApprovalValue('status', args.status),
    }]
  }
  if (approvalAction.value !== 'update') return []
  return Object.entries(args)
    .filter(([key]) => !key.endsWith('_id') && key !== 'raw')
    .filter(([key, value]) => !entity || entity[key] !== value)
    .map(([key, value]) => ({
      field: fieldLabels[key] || key,
      before: formatApprovalValue(key, entity?.[key]),
      after: formatApprovalValue(key, value),
    }))
})

const approvalTargetName = computed(() => {
  const entity = displayEntity.value as unknown as Record<string, unknown> | null
  return String(entity?.name || approvalArgs.value.name || '')
})

function formatApprovalValue(field: string, value: unknown): string {
  if (value === undefined || value === null || value === '') return '未设置'
  if (field === 'status') return statusLabels[String(value)] || String(value)
  if (['budget', 'total_budget', 'spend_limit'].includes(field) && typeof value === 'number') {
    return value.toLocaleString()
  }
  if (Array.isArray(value)) return value.join('、') || '空'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

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
  if (status === 'executing' || status === 'approved') return `已确认，正在${approvalIntent.value.title}`
  if (status === 'completed') return '操作已完成，实际业务结果已返回对话区'
  if (status === 'rejected') return '你已拒绝，本次操作不会执行'
  return `${approvalIntent.value.summary}。确认后才会执行`
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

function handleMaterialRowSelect(row: MaterialRow): void {
  handlePreviewMaterial(row.material)
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <Dashboard
      v-if="projection?.surface === 'dashboard'"
      embedded
      :workspace-overview="(projection.payload.overview as any) || null"
    />

    <!-- 项目列表（查询类工具，无需审批） -->
    <div v-else-if="projection?.surface === 'project.list' || projection?.surface === 'project.detail'" class="p-[16px]">
      <div class="mb-[10px] flex items-center justify-between">
        <p class="text-[10px] text-slate-500 dark:text-slate-400">
          {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'project.detail' ? '1 个项目' : `共 ${projects.length} 个项目` }}
        </p>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-600">数据有更新</span>
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
      <div class="mb-[10px] flex items-center justify-between">
        <p class="text-[10px] text-slate-500 dark:text-slate-400">
          {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'campaign.detail' ? '1 个计划' : `共 ${campaigns.length} 个计划` }}
        </p>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-600">数据有更新</span>
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
      <div class="mb-[10px] flex items-center justify-between">
        <p class="text-[10px] text-slate-500 dark:text-slate-400">
          {{ projection.mode === 'loading' ? '正在查询...' : projection.surface === 'material.detail' ? '1 个素材' : `共 ${materials.length} 个素材` }}
        </p>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-600">数据有更新</span>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <MaterialLibraryView
        v-else
        :materials="materials"
        embedded
        @select="handleMaterialRowSelect"
        @mention="handleMentionMaterial"
      />
    </div>

    <div v-else-if="projection?.surface === 'performance.overview' || projection?.surface === 'performance.accounts' || projection?.surface === 'performance.campaigns'" class="p-[16px]">
      <div class="mb-[10px] flex items-center justify-between">
        <p class="text-[10px] text-slate-500 dark:text-slate-400">{{ projection.surface === 'performance.accounts' ? 'Meta 账号消耗' : projection.surface === 'performance.campaigns' ? 'Meta Campaign / AdSet 表现' : 'Meta 投放表现' }}</p>
        <span v-if="projection.mode === 'stale'" class="text-[10px] text-amber-600">数据有更新</span>
      </div>
      <div v-if="projection.mode === 'loading'" class="flex items-center justify-center py-[40px]">
        <div class="h-[16px] w-[16px] border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
      <div v-else class="space-y-[10px]">
        <div class="grid grid-cols-2 gap-[8px]">
          <div class="rounded-md border border-slate-200 p-[10px] dark:border-slate-700"><small class="block text-[10px] text-slate-500">花费</small><strong class="text-[16px]">{{ (projection.payload.kpis as any)?.spend ?? '—' }}</strong></div>
          <div class="rounded-md border border-slate-200 p-[10px] dark:border-slate-700"><small class="block text-[10px] text-slate-500">结果</small><strong class="text-[16px]">{{ (projection.payload.kpis as any)?.conversions ?? '—' }}</strong></div>
        </div>
        <pre class="max-h-[420px] overflow-auto rounded-md bg-slate-50 p-[10px] text-[10px] leading-relaxed text-slate-600 dark:bg-slate-900 dark:text-slate-300">{{ JSON.stringify(projection.payload, null, 2) }}</pre>
      </div>
    </div>

    <div v-else-if="projection?.surface === 'material.image'" class="p-[16px]">
      <p class="mb-[10px] text-[10px] text-slate-500 dark:text-slate-400">{{ projection.mode === 'loading' ? '正在查询...' : '预览资源' }}</p>
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
          v-if="approvalDraft.status === 'pending'"
          class="mb-[12px] rounded-md border border-amber-200 bg-amber-50 p-[12px] dark:border-amber-900/40 dark:bg-amber-950/20"
        >
          <div class="flex items-start gap-[9px]">
            <span class="material-symbols-outlined mt-[1px] text-[17px] text-amber-600 dark:text-amber-400">warning</span>
            <div class="min-w-0">
              <p class="text-[12px] font-semibold text-slate-900 dark:text-white">准备执行：{{ approvalIntent.title }}</p>
              <p v-if="approvalTargetName" class="mt-[3px] text-[11px] text-slate-600 dark:text-slate-300">影响对象：{{ approvalTargetName }}</p>
              <p class="mt-[3px] text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">{{ approvalIntent.summary }}</p>
            </div>
          </div>
          <div v-if="approvalChanges.length" class="mt-[10px] overflow-hidden rounded-md border border-amber-200/80 bg-white dark:border-amber-900/40 dark:bg-slate-900">
            <div v-for="change in approvalChanges" :key="change.field" class="grid grid-cols-[72px_1fr_auto_1fr] items-center gap-[6px] border-b border-slate-100 px-[10px] py-[8px] text-[11px] last:border-b-0 dark:border-slate-800">
              <span class="text-slate-500 dark:text-slate-400">{{ change.field }}</span>
              <span class="truncate font-medium text-slate-700 dark:text-slate-300">{{ change.before }}</span>
              <span class="material-symbols-outlined text-[14px] text-slate-400">arrow_forward</span>
              <span class="truncate font-semibold text-amber-700 dark:text-amber-300">{{ change.after }}</span>
            </div>
          </div>
          <p class="mt-[9px] text-[10px] font-medium text-amber-700 dark:text-amber-300">批准前不会修改业务数据</p>
        </div>
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

        <MaterialLibraryView
          v-else-if="approvalDomain === 'material' && materialApprovalList.length"
          :materials="materialApprovalList"
          embedded
          @select="handleMaterialRowSelect"
          @mention="handleMentionMaterial"
        />

        <MaterialLibraryView
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
          {{ approvalIntent.confirm }}
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="flex h-full flex-col items-center justify-center px-[32px] py-[60px] text-center">
      <div class="mb-[16px] grid h-[40px] w-[40px] place-items-center rounded-md border border-slate-200 bg-white text-slate-400 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <span class="material-symbols-outlined text-[21px]">dashboard_customize</span>
      </div>
      <h3 class="text-[13px] font-semibold text-slate-800 dark:text-slate-100">任务内容将在这里展开</h3>
      <p class="mt-[6px] max-w-[250px] text-[11px] leading-[1.6] text-slate-500 dark:text-slate-400">
        工作台会随当前任务同步查询结果和需要确认的操作
      </p>
      <div class="mt-[22px] w-full max-w-[260px] space-y-[8px]" aria-hidden="true">
        <div class="flex items-center gap-[8px]"><span class="h-[22px] w-[22px] rounded bg-slate-100 dark:bg-slate-800"></span><span class="h-[6px] w-[62%] rounded bg-slate-100 dark:bg-slate-800"></span></div>
        <div class="flex items-center gap-[8px]"><span class="h-[22px] w-[22px] rounded bg-slate-100 dark:bg-slate-800"></span><span class="h-[6px] w-[78%] rounded bg-slate-100 dark:bg-slate-800"></span></div>
        <div class="flex items-center gap-[8px]"><span class="h-[22px] w-[22px] rounded bg-slate-100 dark:bg-slate-800"></span><span class="h-[6px] w-[48%] rounded bg-slate-100 dark:bg-slate-800"></span></div>
      </div>
    </div>
  </div>
</template>
