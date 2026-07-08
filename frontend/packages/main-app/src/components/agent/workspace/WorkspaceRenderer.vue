<script setup lang="ts">
/**
 * Workspace 投影渲染器
 * 按 projection.surface 分发到现有业务组件，不重新实现业务卡片
 */
import { computed } from 'vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import CampaignCollectionView from '@/components/campaigns/CampaignCollectionView.vue'
import MaterialCollectionView from '@/components/materials/MaterialCollectionView.vue'
import WorkspaceProjectCreate from './WorkspaceProjectCreate.vue'
import type { WorkspaceProjection, WorkspaceApprovalDraft } from '@/store/workspace'
import type { Project } from '@/api/projects'
import type { Campaign } from '@/api/campaigns'
import type { Material } from '@/api/materials'

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

function handleViewDetail(project: Project): void {
  emit('viewProject', project.id)
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
    <div v-if="projection?.surface === 'project.list'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">项目库</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : `共 ${projects.length} 个项目` }}
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
        @view-detail="handleViewDetail"
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
    <div v-else-if="projection?.surface === 'material.list' || projection?.surface === 'material.detail'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">{{ projection.surface === 'material.detail' ? '素材详情' : '素材库' }}</h3>
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

    <!-- 项目创建审批（高风险工具，可编辑） -->
    <WorkspaceProjectCreate
      v-else-if="projection?.surface === 'project.create' && approvalDraft && approvalDraft.status !== 'completed'"
      :draft="approvalDraft"
      @approve="handleApprove"
      @reject="handleReject"
      @update-form="handleUpdateApprovalForm"
    />

    <div v-else-if="approvalDraft && ['campaign.create', 'campaign.status', 'campaign.delete', 'project.delete'].includes(projection?.surface || '') && approvalDraft.status !== 'completed'" class="p-[16px]">
      <div class="rounded-md border border-slate-200 bg-white p-[14px] dark:border-slate-700 dark:bg-slate-800">
        <div class="mb-[12px] flex items-start justify-between gap-[12px]">
          <div>
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">操作确认</h3>
            <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">{{ approvalDraft.toolName }}</p>
          </div>
          <span class="rounded-full bg-amber-50 px-[8px] py-[3px] text-[10px] font-medium text-amber-600 dark:bg-amber-900/20 dark:text-amber-300">待确认</span>
        </div>
        <pre class="max-h-[260px] overflow-auto rounded bg-slate-50 p-[10px] text-[10px] leading-relaxed text-slate-600 dark:bg-slate-900 dark:text-slate-300">{{ JSON.stringify(approvalDraft.editedArguments || approvalDraft.originalArguments, null, 2) }}</pre>
        <div class="mt-[12px] flex gap-[8px]">
          <button class="flex-1 rounded-md border border-slate-200 px-[10px] py-[7px] text-[11px] font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700" @click="handleReject">拒绝</button>
          <button class="flex-1 rounded-md bg-primary px-[10px] py-[7px] text-[11px] font-semibold text-white hover:bg-primary/90" @click="emit('approve', { checkpointId: approvalDraft.checkpointId, editedArguments: approvalDraft.editedArguments, argumentDiff: [] })">确认执行</button>
        </div>
      </div>
    </div>

    <div v-else-if="approvalDraft?.status === 'completed'" class="p-[16px]">
      <div class="flex items-center gap-[8px] mb-[12px]">
        <span class="material-symbols-outlined text-[18px] text-emerald-500">check_circle</span>
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">操作已完成</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">审批已执行，结果已返回对话区</p>
        </div>
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
