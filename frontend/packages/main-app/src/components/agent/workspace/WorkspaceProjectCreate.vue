<script setup lang="ts">
/**
 * Workspace 项目创建审核面板
 * 复用 CreateProjectForm，用户可编辑 Agent 给出的参数，点击确认即 HITL approve
 */
import { computed, ref, watch } from 'vue'
import CreateProjectForm from '@/components/projects/CreateProjectForm.vue'
import {
  type ProjectFormModel,
  type CreateProjectPayload,
  fromCreateProjectArgs,
  toCreateProjectPayload,
  diffProjectArgs,
} from '@/components/projects/projectFormModel'
import type { WorkspaceApprovalDraft } from '@/store/workspace'

const props = defineProps<{
  draft: WorkspaceApprovalDraft
}>()

const emit = defineEmits<{
  approve: [payload: { editedArguments: Record<string, unknown>; argumentDiff: Array<{ field: string; before: unknown; after: unknown }> }]
  reject: []
}>()

const formModel = ref<ProjectFormModel>(fromCreateProjectArgs(props.draft.originalArguments))

watch(
  () => props.draft.checkpointId,
  () => {
    formModel.value = fromCreateProjectArgs(props.draft.originalArguments)
  },
)

const diff = computed(() =>
  diffProjectArgs(props.draft.originalArguments, toCreateProjectPayload(formModel.value) as unknown as CreateProjectPayload),
)

const hasChanges = computed(() => diff.value.length > 0)
const isDisabled = computed(() => props.draft.status !== 'pending')

function handleApprove(): void {
  const editedArguments = toCreateProjectPayload(formModel.value) as Record<string, unknown>
  emit('approve', {
    editedArguments,
    argumentDiff: diff.value,
  })
}

function handleReject(): void {
  emit('reject')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 头部 -->
    <div class="flex items-center justify-between px-[16px] py-[12px] border-b border-slate-200 dark:border-slate-700">
      <div class="flex items-center gap-[8px]">
        <span class="material-symbols-outlined text-[18px] text-amber-500">approval</span>
        <div>
          <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">创建项目 - 待确认</h3>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">Agent 已生成项目参数，你可以编辑后确认</p>
        </div>
      </div>
      <span
        v-if="hasChanges"
        class="px-[8px] py-[2px] rounded-full bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 text-[10px] font-medium"
      >
        已修改 {{ diff.length }} 项
      </span>
    </div>

    <!-- 表单内容 -->
    <div class="flex-1 overflow-y-auto px-[16px] py-[12px]">
      <div v-if="hasChanges" class="mb-[12px] p-[8px] bg-amber-50 dark:bg-amber-900/20 rounded-md">
        <p class="text-[10px] text-amber-700 dark:text-amber-400 font-medium mb-[4px]">用户修改：</p>
        <ul class="space-y-[2px]">
          <li v-for="item in diff" :key="item.field" class="text-[10px] text-amber-600 dark:text-amber-500">
            {{ item.field }}: {{ item.before }} → {{ item.after }}
          </li>
        </ul>
      </div>
      <CreateProjectForm v-model="formModel" :errors="{}" />
    </div>

    <!-- 操作按钮 -->
    <div class="flex items-center justify-end gap-[8px] px-[16px] py-[12px] border-t border-slate-200 dark:border-slate-700">
      <button
        type="button"
        class="px-[12px] py-[6px] text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
        :disabled="isDisabled"
        @click="handleReject"
      >
        拒绝
      </button>
      <button
        type="button"
        class="px-[12px] py-[6px] text-[11px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="isDisabled"
        @click="handleApprove"
      >
        {{ draft.status === 'pending' ? '确认创建' : draft.status === 'approved' ? '已确认' : '处理中...' }}
      </button>
    </div>
  </div>
</template>
