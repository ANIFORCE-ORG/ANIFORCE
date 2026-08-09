<script setup lang="ts">
import { computed } from 'vue'
import type { Project } from '@/api/projects'

const props = defineProps<{
  result: Record<string, unknown>
}>()

const emit = defineEmits<{
  action: [action: string, payload: Record<string, unknown>]
}>()

const projects = computed<Project[]>(() => {
  const data = props.result
  if (data.type === 'project_list' && Array.isArray(data.projects)) {
    return data.projects as Project[]
  }
  return []
})

const summary = computed(() => String(props.result.summary || `共 ${projects.value.length} 个项目`))

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

function budgetProgress(project: Project): number {
  const total = Number(project.total_budget) || 0
  const spent = Number(project.spent) || 0
  if (total === 0) return 0
  return Math.min(Math.round((spent / total) * 100), 100)
}

function initials(name?: string): string {
  return String(name || 'P').trim().slice(0, 2).toUpperCase()
}
</script>

<template>
  <div class="workspace-project-list">
    <header>
      <div class="header-left">
        <div class="icon-badge">
          <span class="material-symbols-outlined">folder_managed</span>
        </div>
        <div>
          <h2>项目库</h2>
          <p>{{ summary }}</p>
        </div>
      </div>
    </header>

    <div v-if="projects.length" class="projects-grid">
      <article
        v-for="project in projects"
        :key="project.id"
        class="project-card"
      >
        <div class="card-header">
          <div class="project-avatar">{{ initials(project.name) }}</div>
          <div class="project-title">
            <h3>{{ project.name }}</h3>
            <span class="project-id">{{ project.id }}</span>
          </div>
          <span class="status-badge status-chip" :data-status="project.status" :class="statusTone(project.status)">
            {{ statusLabel(project.status) }}
          </span>
        </div>

        <p v-if="project.description" class="description">{{ project.description }}</p>

        <div class="budget-section">
          <div class="budget-row">
            <span class="label">预算使用</span>
            <span class="value">{{ money(project.spent) }} / {{ money(project.total_budget) }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${budgetProgress(project)}%` }"></div>
          </div>
        </div>

        <dl class="meta-grid">
          <div v-if="project.game_type">
            <dt>游戏类型</dt>
            <dd>{{ project.game_type }}</dd>
          </div>
          <div v-if="project.target_market">
            <dt>目标市场</dt>
            <dd>{{ project.target_market }}</dd>
          </div>
        </dl>

        <div class="card-actions">
          <button class="action-primary" @click="emit('action', 'open_project', { projectId: project.id, project })">
            <span class="material-symbols-outlined">arrow_forward</span>
            查看详情
          </button>
          <button class="action-secondary" @click="emit('action', 'create_campaign', { projectId: project.id, project })">
            <span class="material-symbols-outlined">campaign</span>
            创建投放计划
          </button>
        </div>
      </article>
    </div>

    <div v-else class="empty-workspace">
      <span class="material-symbols-outlined">inbox</span>
      <p>暂无项目数据</p>
    </div>
  </div>
</template>

<style scoped>
.workspace-project-list {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: rgb(248, 250, 252);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(59, 130, 246, 0.08));
}
.icon-badge .material-symbols-outlined {
  color: #2563eb;
  font-size: 22px;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
}
h2 {
  margin: 0;
  color: rgb(15, 23, 42);
  font-size: 16px;
  font-weight: 700;
}
header p {
  margin: 2px 0 0;
  color: rgb(100, 116, 139);
  font-size: 12px;
}
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.project-card {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  padding: 16px;
  background: white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
  transition: all .2s ease;
  animation: card-appear .3s cubic-bezier(.2, .8, .2, 1) both;
}
.project-card:hover {
  border-color: rgba(37, 99, 235, 0.2);
  box-shadow: 0 8px 24px rgba(15, 23, 42, .08);
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}
.project-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(59, 130, 246, 0.08));
  color: #4f46e5;
  font-size: 13px;
  font-weight: 800;
}
.project-title {
  min-width: 0;
  flex: 1;
}
h3 {
  margin: 0 0 3px;
  overflow: hidden;
  color: rgb(15, 23, 42);
  font-size: 14px;
  font-weight: 650;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-id {
  overflow: hidden;
  color: rgb(148, 163, 184);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
.status-badge {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 3px 9px;
  background: rgba(148, 163, 184, 0.1);
  color: rgb(100, 116, 139);
  font-size: 11px;
  font-weight: 650;
}
.status-badge.active {
  background: rgba(5, 150, 105, 0.12);
  color: #059669;
}
.status-badge.paused {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}
.status-badge.completed {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
}
.description {
  margin: 0 0 14px;
  color: rgb(71, 85, 105);
  font-size: 12px;
  line-height: 1.5;
}
.budget-section {
  margin-bottom: 14px;
}
.budget-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.budget-row .label {
  color: rgb(100, 116, 139);
  font-size: 11px;
  font-weight: 600;
}
.budget-row .value {
  color: rgb(30, 41, 59);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  font-weight: 650;
}
.progress-bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
}
.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
  transition: width .4s ease;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0;
}
.meta-grid div {
  min-width: 0;
}
dt {
  color: rgb(100, 116, 139);
  font-size: 10px;
  font-weight: 600;
}
dd {
  overflow: hidden;
  margin: 3px 0 0;
  color: rgb(30, 41, 59);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}
button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  flex: 1;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 8px 12px;
  background: white;
  color: rgb(71, 85, 105);
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
  transition: all .16s ease;
}
button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, .08);
}
button .material-symbols-outlined {
  font-size: 16px;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}
.action-primary {
  border-color: rgba(37, 99, 235, 0.24);
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}
.action-primary:hover {
  background: rgba(37, 99, 235, 0.14);
}
.empty-workspace {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60%;
  color: rgb(148, 163, 184);
}
.empty-workspace .material-symbols-outlined {
  margin-bottom: 12px;
  color: rgb(203, 213, 225);
  font-size: 48px;
}
.empty-workspace p {
  margin: 0;
  font-size: 13px;
}
@keyframes card-appear {
  from {
    opacity: 0;
    transform: scale(.98) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
:global(.dark) .workspace-project-list {
  background: rgb(15, 23, 42);
}
:global(.dark) header {
  border-bottom-color: rgba(148, 163, 184, 0.12);
}
:global(.dark) h2 {
  color: rgb(248, 250, 252);
}
:global(.dark) .project-card {
  border-color: rgba(148, 163, 184, 0.12);
  background: rgb(30, 41, 59);
}
:global(.dark) .project-card:hover {
  border-color: rgba(37, 99, 235, 0.3);
}
:global(.dark) h3 {
  color: rgb(226, 232, 240);
}
:global(.dark) .description {
  color: rgb(148, 163, 184);
}
:global(.dark) .budget-row .value {
  color: rgb(203, 213, 225);
}
:global(.dark) dd {
  color: rgb(203, 213, 225);
}
:global(.dark) .status-badge.active {
  background: rgba(5, 150, 105, 0.16);
  color: #6ee7b7;
}
:global(.dark) .status-badge.paused {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
}
:global(.dark) .status-badge.completed {
  background: rgba(37, 99, 235, 0.16);
  color: #93c5fd;
}
:global(.dark) .card-actions {
  border-top-color: rgba(148, 163, 184, 0.12);
}
:global(.dark) button {
  background: rgba(15, 23, 42, 0.6);
  color: rgb(203, 213, 225);
}
:global(.dark) .action-primary {
  background: rgba(37, 99, 235, 0.12);
  color: #93c5fd;
}
</style>
