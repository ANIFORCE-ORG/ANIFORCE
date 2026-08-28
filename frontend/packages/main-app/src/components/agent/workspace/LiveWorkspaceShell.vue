<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import WorkspaceRenderer from './WorkspaceRenderer.vue'
import type { WorkspaceApprovalDraft, WorkspaceProjection } from '@/store/workspace'

type WorkspaceAttention = 'idle' | 'updating' | 'new' | 'approval' | 'executing' | 'error'

const props = defineProps<{
  visible: boolean
  collapsed?: boolean
  mobile?: boolean
  canExpand?: boolean
  sessionId?: string
  projection: WorkspaceProjection | null
  approvalDraft: WorkspaceApprovalDraft | null
  attention?: WorkspaceAttention
  statusLabel?: string
}>()

const emit = defineEmits<{
  toggleCollapse: []
  opened: []
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

const mobileOpen = ref(false)

const surfaceTitle = computed(() => {
  if (props.approvalDraft) return '操作确认'
  const labels: Record<string, string> = {
    'project.list': '项目列表',
    'project.detail': '项目详情',
    'campaign.list': '广告计划',
    'campaign.detail': '广告计划详情',
    'campaign.materials': '广告计划素材',
    'material.list': '素材库',
    'material.detail': '素材详情',
    'material.image': '素材预览',
    'dashboard': 'Meta 投放表现',
    'approval.review': '操作确认',
  }
  return labels[props.projection?.surface || ''] || '任务空间'
})

const attentionIcon = computed(() => ({
  idle: 'dashboard_customize',
  updating: 'progress_activity',
  new: 'dashboard_customize',
  approval: 'verified_user',
  executing: 'progress_activity',
  error: 'error',
})[props.attention || 'idle'])

const statusIcon = computed(() => ({
  idle: '',
  updating: 'progress_activity',
  new: '',
  approval: 'verified_user',
  executing: 'progress_activity',
  error: 'error',
})[props.attention || 'idle'])

const attentionLabel = computed(() => props.statusLabel || (props.attention === 'new' ? '有新内容' : ''))
const mobileLabel = computed(() => attentionLabel.value
  ? `${surfaceTitle.value}，${attentionLabel.value}`
  : `打开${surfaceTitle.value}`)

function openMobileWorkspace(): void {
  if (props.canExpand === false) return
  mobileOpen.value = true
  emit('opened')
}

watch(() => props.visible, visible => {
  if (!visible) mobileOpen.value = false
})
</script>

<template>
  <template v-if="mobile">
    <button
      v-if="visible"
      class="workspace-mobile-trigger"
      :data-attention="attention || 'idle'"
      type="button"
      :disabled="canExpand === false"
      :aria-label="canExpand === false ? '工作台将在有任务内容时展开' : mobileLabel"
      :title="canExpand === false ? '工作台将在有任务内容时展开' : mobileLabel"
      @click="openMobileWorkspace"
    >
      <span class="material-symbols-outlined" :class="{ spinning: attention === 'updating' || attention === 'executing' }">{{ attentionIcon }}</span>
      <i v-if="attention === 'new' || attention === 'approval' || attention === 'error'"></i>
    </button>

    <Teleport to="body">
      <div v-if="mobileOpen" class="workspace-mobile-layer" role="dialog" aria-modal="true" :aria-label="surfaceTitle">
        <button class="workspace-mobile-backdrop" type="button" aria-label="关闭工作台" @click="mobileOpen = false"></button>
        <section class="workspace-mobile-sheet">
          <header class="workspace-mobile-header">
            <div>
              <small>工作台</small>
              <strong>{{ surfaceTitle }}</strong>
            </div>
            <div class="workspace-mobile-header__actions">
              <span v-if="statusLabel" class="workspace-status" :data-attention="attention || 'idle'" role="status" aria-live="polite">
                <span class="material-symbols-outlined" :class="{ spinning: attention === 'updating' || attention === 'executing' }">{{ statusIcon }}</span>
                {{ statusLabel }}
              </span>
              <button type="button" aria-label="关闭工作台" @click="mobileOpen = false">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
          </header>
          <WorkspaceRenderer
            class="workspace-mobile-content"
            :projection="projection"
            :approval-draft="approvalDraft"
            :session-id="sessionId || ''"
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
        </section>
      </div>
    </Teleport>
  </template>

  <aside
    v-else
    class="workspace-shell hidden shrink-0 border-l border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950 xl:flex"
    :class="{ 'is-collapsed': collapsed }"
  >
    <div v-if="collapsed" class="workspace-rail">
      <button
        class="workspace-rail__open"
        type="button"
        :data-attention="attention || 'idle'"
        :disabled="canExpand === false"
        :aria-label="canExpand === false ? '工作台将在有任务内容时展开' : (attentionLabel ? `展开工作台，${attentionLabel}` : '展开工作台')"
        :title="canExpand === false ? '工作台将在有任务内容时展开' : (attentionLabel || '展开工作台')"
        @click="canExpand !== false && emit('toggleCollapse')"
      >
        <span class="material-symbols-outlined" :class="{ spinning: attention === 'updating' || attention === 'executing' }">dashboard_customize</span>
        <i v-if="attention === 'new' || attention === 'approval' || attention === 'error'"></i>
        <span class="workspace-rail__tooltip" role="tooltip">{{ attentionLabel || '打开工作台' }}</span>
      </button>
    </div>

    <div v-else class="flex h-full w-full flex-col overflow-hidden">
      <header class="workspace-desktop-header">
        <div class="workspace-desktop-title">
          <span class="material-symbols-outlined">dashboard_customize</span>
          <div>
            <small>工作台</small>
            <h2>{{ surfaceTitle }}</h2>
          </div>
        </div>
        <div class="workspace-desktop-actions">
          <span v-if="statusLabel" class="workspace-status" :data-attention="attention || 'idle'" role="status" aria-live="polite">
            <span class="material-symbols-outlined" :class="{ spinning: attention === 'updating' || attention === 'executing' }">{{ statusIcon }}</span>
            {{ statusLabel }}
          </span>
          <button type="button" title="收起工作台" aria-label="收起工作台" @click="emit('toggleCollapse')">
            <span class="material-symbols-outlined">right_panel_close</span>
          </button>
        </div>
      </header>

      <WorkspaceRenderer
        class="min-h-0 flex-1"
        :projection="projection"
        :approval-draft="approvalDraft"
        :session-id="sessionId || ''"
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
/* Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V4 */
/* Hallmark · component: workspace trigger · genre: modern-minimal · theme: project Notion system
 * states: default · hover · focus · active · disabled · loading · error · success
 * contrast: project-token aligned
 */
.workspace-shell,
.workspace-mobile-trigger,
.workspace-mobile-layer {
  --workspace-trigger-canvas: var(--workspace-content-surface);
  --workspace-trigger-surface: var(--workspace-metric-surface);
  --workspace-trigger-line: var(--workspace-hairline);
  --workspace-trigger-ink: var(--workspace-muted);
  --workspace-trigger-active: var(--workspace-action-primary);
  --workspace-trigger-warning: #dd5b00;
  --workspace-trigger-error: #e03131;
  --workspace-trigger-shadow: rgba(15, 15, 15, 0.08) 0 4px 14px;
  --workspace-trigger-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

.spinning { animation: workspace-spin 1s linear infinite; }

.workspace-shell.is-collapsed {
  position: fixed;
  z-index: 35;
  top: 20px;
  right: 20px;
  width: 44px !important;
  height: 44px !important;
  overflow: visible;
  border: 0 !important;
  background: transparent !important;
}

.workspace-rail {
  display: flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
}

.workspace-rail__open,
.workspace-desktop-actions button,
.workspace-mobile-header__actions button {
  display: grid;
  width: 34px;
  height: 34px;
  position: relative;
  place-items: center;
  border: 1px solid var(--workspace-trigger-line);
  border-radius: 8px;
  background: var(--workspace-trigger-canvas);
  color: var(--workspace-trigger-ink);
  cursor: pointer;
}

.workspace-rail__open {
  width: 44px;
  height: 44px;
  box-shadow: var(--workspace-trigger-shadow);
  transition: background-color 180ms var(--workspace-trigger-ease-out), color 180ms var(--workspace-trigger-ease-out), transform 120ms var(--workspace-trigger-ease-out), box-shadow 180ms var(--workspace-trigger-ease-out);
}

.workspace-rail__open > .material-symbols-outlined {
  font-size: 20px;
}

.workspace-rail__open:hover:not(:disabled) {
  background: var(--workspace-trigger-surface);
  color: var(--workspace-trigger-active);
  transform: translateX(-2px);
}

.workspace-desktop-actions button:hover,
.workspace-mobile-header__actions button:hover {
  background: var(--workspace-trigger-surface);
  color: var(--workspace-trigger-active);
}

.workspace-rail__open:active:not(:disabled) {
  transform: translateX(0);
}

.workspace-rail__open:focus-visible {
  outline: 2px solid var(--workspace-trigger-active);
  outline-offset: 3px;
}

.workspace-rail__open:disabled {
  border-color: var(--workspace-trigger-line);
  background: var(--workspace-trigger-surface);
  color: var(--workspace-trigger-ink);
  box-shadow: none;
  cursor: not-allowed;
  opacity: 0.55;
}

.workspace-rail__open i,
.workspace-mobile-trigger i {
  position: absolute;
  width: 8px;
  height: 8px;
  border: 2px solid var(--workspace-trigger-canvas);
  border-radius: 50%;
  background: var(--workspace-trigger-active);
}

.workspace-rail__open i { top: -2px; right: -2px; }
.workspace-rail__open[data-attention="new"] i::after {
  position: absolute;
  inset: -4px;
  border: 1px solid var(--workspace-trigger-active);
  border-radius: 50%;
  animation: workspace-notice 1.2s var(--workspace-trigger-ease-out) 1;
  content: '';
}
.workspace-rail__open[data-attention="approval"] i,
.workspace-mobile-trigger[data-attention="approval"] i { background: var(--workspace-trigger-warning); }
.workspace-rail__open[data-attention="error"] i,
.workspace-mobile-trigger[data-attention="error"] i { background: var(--workspace-trigger-error); }

.workspace-rail__tooltip {
  position: absolute;
  top: 50%;
  right: calc(100% + 10px);
  padding: 6px 9px;
  border: 1px solid var(--workspace-trigger-line);
  border-radius: 6px;
  background: var(--workspace-trigger-canvas);
  color: var(--workspace-ink);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  opacity: 0;
  box-shadow: var(--workspace-trigger-shadow);
  pointer-events: none;
  transform: translate(4px, -50%);
  transition: opacity 150ms var(--workspace-trigger-ease-out), transform 150ms var(--workspace-trigger-ease-out);
}

.workspace-rail__open:hover .workspace-rail__tooltip {
  opacity: 1;
  transform: translate(0, -50%);
  transition-delay: 800ms;
}

.workspace-rail__open:focus-visible .workspace-rail__tooltip {
  opacity: 1;
  transform: translate(0, -50%);
  transition-delay: 0ms;
}

.workspace-desktop-header,
.workspace-mobile-header {
  display: flex;
  min-height: 52px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  padding: 8px 12px;
}

.workspace-desktop-title,
.workspace-desktop-actions,
.workspace-mobile-header__actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.workspace-desktop-title > .material-symbols-outlined { color: #94a3b8; font-size: 17px; }
.workspace-desktop-title small,
.workspace-mobile-header small { display: block; color: #94a3b8; font-size: 9px; line-height: 1.2; }
.workspace-desktop-title h2,
.workspace-mobile-header strong { display: block; overflow: hidden; margin: 1px 0 0; color: #1e293b; font-size: 12px; font-weight: 650; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap; }
.workspace-desktop-actions button,
.workspace-mobile-header__actions button { width: 30px; height: 30px; border: 0; }
.workspace-desktop-actions button .material-symbols-outlined,
.workspace-mobile-header__actions button .material-symbols-outlined { font-size: 18px; }

.workspace-status {
  display: inline-flex;
  overflow: hidden;
  max-width: 112px;
  align-items: center;
  gap: 4px;
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-status .material-symbols-outlined { flex: 0 0 auto; font-size: 13px; }
.workspace-status[data-attention="updating"],
.workspace-status[data-attention="executing"],
.workspace-status[data-attention="new"] { color: #2563eb; }
.workspace-status[data-attention="approval"] { color: #b45309; }
.workspace-status[data-attention="error"] { color: #b91c1c; }

.workspace-mobile-trigger {
  display: grid;
  position: fixed;
  z-index: 35;
  right: 16px;
  bottom: 86px;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #ffffff;
  color: #475569;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.12);
}
.workspace-mobile-trigger > .material-symbols-outlined { font-size: 20px; }
.workspace-mobile-trigger:disabled { color: #94a3b8; box-shadow: none; cursor: default; }
.workspace-mobile-trigger i { top: -3px; right: -3px; }

.workspace-mobile-layer { position: fixed; z-index: 80; inset: 0; }
.workspace-mobile-backdrop { position: absolute; inset: 0; width: 100%; border: 0; background: rgba(15, 23, 42, 0.28); }
.workspace-mobile-sheet {
  display: flex;
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  max-height: 84dvh;
  min-height: 52dvh;
  flex-direction: column;
  overflow: hidden;
  border-radius: 8px 8px 0 0;
  background: #ffffff;
  box-shadow: 0 -12px 36px rgba(15, 23, 42, 0.16);
}
.workspace-mobile-header > div:first-child { min-width: 0; }
.workspace-mobile-content { min-height: 0; flex: 1; overflow: auto; }

@keyframes workspace-spin { to { transform: rotate(360deg); } }
@keyframes workspace-notice {
  from { opacity: 0.65; transform: scale(0.75); }
  to { opacity: 0; transform: scale(1.5); }
}

@media (min-width: 1280px) {
  .workspace-mobile-trigger,
  .workspace-mobile-layer { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .spinning { animation-duration: 1.8s; }
  .workspace-rail__open,
  .workspace-rail__tooltip { transition-duration: 0.01ms; }
  .workspace-rail__open[data-attention="new"] i::after { animation: none; }
}
</style>
