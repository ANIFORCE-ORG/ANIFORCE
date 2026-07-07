<script setup lang="ts">
/**
 * Workspace 投影渲染器
 * 按 projection.surface 分发到现有业务组件，不重新实现业务卡片
 */
import { computed, ref } from 'vue'
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

const previewMaterial = ref<Material | null>(null)

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
  return []
})

const materials = computed<Material[]>(() => {
  if (!props.projection) return []
  const data = props.projection.payload
  if (Array.isArray(data.materials)) return data.materials as Material[]
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
  previewMaterial.value = material
  handleSelectMaterial(material)
}

function materialPreviewSrc(material: Material): string {
  return material.preview_url || material.thumbnail_url || material.poster_url || material.url || ''
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
    <div v-else-if="projection?.surface === 'campaign.list'" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">广告计划</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : `共 ${campaigns.length} 个计划` }}
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
    <div v-else-if="projection?.surface === 'material.list' && !previewMaterial" class="p-[16px]">
      <div class="mb-[12px] flex items-center justify-between">
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">素材库</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">
            {{ projection.mode === 'loading' ? '正在查询...' : `共 ${materials.length} 个素材` }}
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

    <div v-else-if="projection?.surface === 'material.list' && previewMaterial" class="p-[16px]">
      <button class="mb-[12px] flex items-center gap-[4px] text-[11px] font-medium text-slate-500 hover:text-primary" @click="previewMaterial = null">
        <span class="material-symbols-outlined text-[14px]">arrow_back</span>
        返回素材库
      </button>
      <div class="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div class="aspect-video bg-slate-100 dark:bg-slate-900">
          <video
            v-if="previewMaterial.media_kind === 'video' || previewMaterial.type === 'video'"
            :src="materialPreviewSrc(previewMaterial)"
            class="h-full w-full object-contain"
            controls
          />
          <img
            v-else-if="materialPreviewSrc(previewMaterial)"
            :src="materialPreviewSrc(previewMaterial)"
            :alt="previewMaterial.name"
            class="h-full w-full object-contain"
          />
          <div v-else class="flex h-full items-center justify-center">
            <span class="material-symbols-outlined text-[48px] text-slate-300">video_library</span>
          </div>
        </div>
        <div class="p-[14px]">
          <div class="mb-[10px] flex items-start justify-between gap-[10px]">
            <div>
              <h3 class="text-[14px] font-semibold text-slate-900 dark:text-white">{{ previewMaterial.name }}</h3>
              <p class="mt-[2px] text-[11px] text-slate-500">{{ previewMaterial.format || previewMaterial.type }} · {{ previewMaterial.width || '-' }}×{{ previewMaterial.height || '-' }}</p>
            </div>
            <span class="rounded-full bg-slate-100 px-[8px] py-[3px] text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">{{ previewMaterial.status }}</span>
          </div>
          <div class="mb-[12px] flex flex-wrap gap-[6px]">
            <span v-for="tag in previewMaterial.tags || []" :key="tag" class="rounded-full bg-primary/10 px-[8px] py-[3px] text-[10px] text-primary">{{ tag }}</span>
          </div>
          <div class="grid grid-cols-2 gap-[8px] text-[11px] text-slate-600 dark:text-slate-300">
            <div>文件大小：{{ previewMaterial.file_size ? `${Math.round(previewMaterial.file_size / 1024)}KB` : '-' }}</div>
            <div>CTR：{{ previewMaterial.ctr_estimate ?? 'N/A' }}</div>
            <div>平台：{{ (previewMaterial.platforms || []).join(', ') || '-' }}</div>
            <div>审核：{{ previewMaterial.review_status || '-' }}</div>
          </div>
          <div class="mt-[14px] flex gap-[8px]">
            <button class="flex-1 rounded border border-slate-200 px-[10px] py-[7px] text-[11px] font-medium text-slate-600 hover:border-primary hover:text-primary dark:border-slate-700 dark:text-slate-300" @click="handleMentionMaterial(previewMaterial)">@ 引用到对话</button>
            <button class="flex-1 rounded bg-primary px-[10px] py-[7px] text-[11px] font-semibold text-white hover:bg-primary/90" @click="emit('viewMaterial', previewMaterial.id)">打开完整页</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 项目创建审批（高风险工具，可编辑） -->
    <WorkspaceProjectCreate
      v-else-if="projection?.surface === 'project.create' && approvalDraft && approvalDraft.status !== 'completed'"
      :draft="approvalDraft"
      @approve="handleApprove"
      @reject="handleReject"
      @update-form="handleUpdateApprovalForm"
    />

    <div v-else-if="projection?.surface === 'project.create' && approvalDraft?.status === 'completed'" class="p-[16px]">
      <div class="flex items-center gap-[8px] mb-[12px]">
        <span class="material-symbols-outlined text-[18px] text-emerald-500">check_circle</span>
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">项目创建已完成</h3>
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
