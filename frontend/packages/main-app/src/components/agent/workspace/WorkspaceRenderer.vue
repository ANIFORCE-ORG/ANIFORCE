<script setup lang="ts">
/**
 * Workspace 投影渲染器
 * 按 projection.surface 分发到现有业务组件，不重新实现业务卡片
 */
import { computed } from 'vue'
import ProjectCollectionView from '@/components/projects/ProjectCollectionView.vue'
import WorkspaceProjectCreate from './WorkspaceProjectCreate.vue'
import type { WorkspaceProjection, WorkspaceApprovalDraft } from '@/store/workspace'
import type { Project } from '@/api/projects'

const props = defineProps<{
  projection: WorkspaceProjection | null
  approvalDraft: WorkspaceApprovalDraft | null
  sessionId: string
}>()

const emit = defineEmits<{
  approve: [payload: { checkpointId: string; editedArguments: Record<string, unknown>; argumentDiff: Array<{ field: string; before: unknown; after: unknown }> }]
  reject: [checkpointId: string]
  selectEntity: [entity: { type: 'project' | 'campaign' | 'material'; id: string; name?: string }]
  viewProject: [projectId: string]
}>()

const projects = computed<Project[]>(() => {
  if (!props.projection) return []
  const data = props.projection.payload
  if (Array.isArray(data.projects)) return data.projects as Project[]
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

function handleViewDetail(project: Project): void {
  emit('viewProject', project.id)
  emit('selectEntity', { type: 'project', id: project.id, name: project.name })
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
      />
    </div>

    <!-- 项目创建审批（高风险工具，可编辑） -->
    <WorkspaceProjectCreate
      v-else-if="projection?.surface === 'project.create' && approvalDraft"
      :draft="approvalDraft"
      @approve="handleApprove"
      @reject="handleReject"
    />

    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center h-full py-[60px] px-[20px] text-center">
      <span class="material-symbols-outlined text-[40px] text-slate-300 dark:text-slate-700 mb-[12px]">workspaces</span>
      <p class="text-[12px] text-slate-500 dark:text-slate-400">
        Agent 正在工作，操作结果会在这里实时呈现
      </p>
    </div>
  </div>
</template>
