<script setup lang="ts">
import WorkspaceRenderer from './WorkspaceRenderer.vue'
import type { WorkspaceApprovalDraft, WorkspaceProjection } from '@/store/workspace'

const props = defineProps<{
  visible: boolean
  collapsed?: boolean
  sessionId?: string
  projection: WorkspaceProjection | null
  approvalDraft: WorkspaceApprovalDraft | null
}>()

const emit = defineEmits<{
  toggleCollapse: []
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
</script>

<template>
  <aside class="hidden shrink-0 border-l border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 xl:flex">
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

      <WorkspaceRenderer
        class="min-h-0 flex-1"
        :projection="props.projection"
        :approval-draft="props.approvalDraft"
        :session-id="props.sessionId || ''"
        @approve="emit('approve', $event)"
        @reject="emit('reject', $event)"
        @update-approval-form="emit('updateApprovalForm', $event)"
        @select-entity="emit('selectEntity', $event)"
        @mention-entity="emit('mentionEntity', $event)"
        @view-project="emit('viewProject', $event)"
        @edit-project="emit('editProject', $event)"
        @create-project-task="emit('createProjectTask', $event)"
        @view-project-tasks="emit('viewProjectTasks', $event)"
        @view-campaign="emit('viewCampaign', $event)"
        @view-material="emit('viewMaterial', $event)"
      />
    </div>
  </aside>
</template>

<style scoped>
.writing-vertical {
  writing-mode: vertical-rl;
}
</style>
