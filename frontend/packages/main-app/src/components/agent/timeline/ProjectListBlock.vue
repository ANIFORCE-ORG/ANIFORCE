<script setup lang="ts">
import { computed } from 'vue'
import type { Project } from '@/api/projects'
import type { AgentTimelineBlock } from '@/composables/useHomeAgentSession'

type ProjectListTimelineBlock = Extract<AgentTimelineBlock, { type: 'project_list' }>

const props = defineProps<{
  block: ProjectListTimelineBlock
}>()

const emit = defineEmits<{
  action: [action: string, payload: Record<string, unknown>]
}>()

const projects = computed<Project[]>(() => props.block.projects as unknown as Project[])
const previewProjects = computed(() => projects.value.slice(0, 4))
const hiddenProjectCount = computed(() => Math.max(projects.value.length - previewProjects.value.length, 0))
const summary = computed(() => String(props.block.summary || `共 ${projects.value.length} 个项目`))

function money(value: unknown): string {
  const number = typeof value === 'number' ? value : Number(value || 0)
  if (!Number.isFinite(number)) return '¥0'
  return `¥${number.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function statusLabel(status?: string): string {
  if (status === 'active' || status === 'running') return '进行中'
  if (status === 'draft') return '草稿'
  if (status === 'paused') return '暂停'
  if (status === 'completed') return '已完成'
  return '未设置'
}

function statusTone(status?: string): string {
  if (status === 'active' || status === 'running') return 'active'
  if (status === 'paused') return 'paused'
  if (status === 'completed') return 'completed'
  return 'default'
}

function openInWorkspace(): void {
  emit('action', 'open_in_workspace', { 
    type: 'project_list',
    projects: projects.value,
    summary: summary.value
  })
}
</script>

<template>
  <section class="project-list-compact">
    <header>
      <div class="header-icon">
        <span class="material-symbols-outlined">folder_open</span>
      </div>
      <div class="header-copy">
        <h3>你的项目</h3>
        <p>{{ summary }}</p>
      </div>
    </header>

    <div v-if="projects.length" class="project-rows">
      <div
        v-for="(project, index) in previewProjects"
        :key="project.id"
        class="project-row"
        :style="{ animationDelay: `${index * 32}ms` }"
      >
        <div class="project-name">
          <strong>{{ project.name }}</strong>
        </div>
        <div class="project-meta">
          <span class="budget">{{ money(project.total_budget) }}</span>
          <span class="status status-chip" :data-status="project.status" :class="statusTone(project.status)">{{ statusLabel(project.status) }}</span>
        </div>
      </div>
      
      <button v-if="hiddenProjectCount" class="more-hint" type="button" @click="openInWorkspace">
        还有 {{ hiddenProjectCount }} 个项目，打开 Workspace 查看全部
      </button>
    </div>

    <div v-else class="empty-state">
      <span class="material-symbols-outlined">inbox</span>
      当前账号还没有项目
    </div>

    <button class="workspace-button" @click="openInWorkspace">
      <span class="material-symbols-outlined">open_in_new</span>
      在 Workspace 查看详情
    </button>
  </section>
</template>

<style scoped>
.project-list-compact {
  overflow: hidden;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 14px;
  padding: 12px;
  background: 
    linear-gradient(135deg, rgba(239, 246, 255, 0.7) 0%, rgba(243, 244, 246, 0.5) 100%),
    rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  animation: fade-in .26s ease both;
}
header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}
.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(59, 130, 246, 0.08));
}
.header-icon .material-symbols-outlined {
  color: #2563eb;
  font-size: 18px;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}
.header-copy {
  min-width: 0;
  flex: 1;
}
h3 {
  margin: 0;
  color: rgb(30, 41, 59);
  font-size: 13px;
  font-weight: 650;
}
header p {
  margin: 2px 0 0;
  color: rgb(100, 116, 139);
  font-size: 11px;
}
.project-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}
.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-radius: 8px;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.6);
  transition: all .14s ease;
  animation: row-enter .22s cubic-bezier(.2, .8, .2, 1) both;
}
.project-row:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(15, 23, 42, .04);
}
.project-name {
  min-width: 0;
  flex: 1;
}
.project-name strong {
  overflow: hidden;
  color: rgb(30, 41, 59);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.budget {
  color: rgb(71, 85, 105);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 650;
}
.status {
  border-radius: 999px;
  padding: 2px 7px;
  background: rgba(148, 163, 184, 0.1);
  color: rgb(100, 116, 139);
  font-size: 10px;
  font-weight: 650;
}
.status.active {
  background: rgba(5, 150, 105, 0.12);
  color: #059669;
}
.status.paused {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}
.status.completed {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
}
.more-hint {
  width: 100%;
  border: 0;
  border-radius: 8px;
  padding: 6px 8px;
  background: rgba(148, 163, 184, 0.08);
  color: rgb(100, 116, 139);
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  transition: all .16s ease;
}
.more-hint:hover {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: rgb(148, 163, 184);
  font-size: 12px;
}
.empty-state .material-symbols-outlined {
  color: rgb(203, 213, 225);
  font-size: 20px;
}
.workspace-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 10px;
  padding: 8px 12px;
  background: rgba(37, 99, 235, 0.06);
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
  transition: all .16s ease;
}
.workspace-button:hover {
  background: rgba(37, 99, 235, 0.12);
  box-shadow: 0 4px 12px rgba(37, 99, 235, .12);
  transform: translateY(-1px);
}
.workspace-button .material-symbols-outlined {
  font-size: 16px;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes row-enter {
  from {
    opacity: 0;
    transform: translateX(-4px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
:global(.dark) .project-list-compact {
  border-color: rgba(37, 99, 235, 0.2);
  background: 
    linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.7) 100%),
    rgba(15, 23, 42, 0.6);
}
:global(.dark) header {
  border-bottom-color: rgba(148, 163, 184, 0.16);
}
:global(.dark) h3 {
  color: rgb(226, 232, 240);
}
:global(.dark) .project-row {
  background: rgba(15, 23, 42, 0.4);
}
:global(.dark) .project-row:hover {
  background: rgba(30, 41, 59, 0.6);
}
:global(.dark) .project-name strong {
  color: rgb(226, 232, 240);
}
:global(.dark) .budget {
  color: rgb(148, 163, 184);
}
:global(.dark) .status.active {
  background: rgba(5, 150, 105, 0.16);
  color: #6ee7b7;
}
:global(.dark) .status.paused {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
}
:global(.dark) .status.completed {
  background: rgba(37, 99, 235, 0.16);
  color: #93c5fd;
}
:global(.dark) .workspace-button {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.24);
  color: #93c5fd;
}
:global(.dark) .workspace-button:hover {
  background: rgba(37, 99, 235, 0.18);
}
</style>
