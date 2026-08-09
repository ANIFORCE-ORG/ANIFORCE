<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Project } from '@/api/projects'

interface Props {
  project: Project
}

const props = defineProps<Props>()
const emit = defineEmits<{
  edit: [project: Project]
  viewDetail: [project: Project]
  viewTasks: [project: Project]
  createTask: [project: Project]
  select: [project: Project, selected: boolean]
}>()

const router = useRouter()

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600',
    draft: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    paused: '已暂停',
    completed: '已完成',
    draft: '草稿'
  }
  return labels[status] || status
}

const handleCheckboxChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('select', props.project, target.checked)
}

const handleViewDetail = () => {
  router.push(`/projects/${props.project.id}`)
}
</script>

<template>
  <article class="project-card">
    <!-- Checkbox -->
    <label class="select-check">
      <input
        type="checkbox"
        class="w-[12px] h-[12px] rounded border-slate-300 text-primary focus:ring-primary/20"
        @change="handleCheckboxChange"
      />
      <span class="ml-[6px] text-[10px] text-slate-500 dark:text-slate-400">选择项目</span>
    </label>

    <!-- Project Header -->
    <div class="project-card-head">
      <div class="project-card-title">
        <h3 class="text-[13px] font-semibold leading-tight text-slate-900 dark:text-white mb-[6px]">
          {{ project.name }}
        </h3>
        <p class="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
          {{ project.game_type }}<br>{{ project.target_market }}
        </p>
      </div>
      <!-- Status Badge -->
      <span
        class="status-badge text-[10px] font-semibold px-[6px] py-[2px] rounded-full whitespace-nowrap"
        :class="getStatusColor(project.status)"
      >
        {{ getStatusLabel(project.status) }}
      </span>
    </div>

    <!-- Tags / Chips -->
    <div class="scope-list">
      <span class="chip">Meta Campaign</span>
      <span class="chip">{{ project.tags[0] || '支付计划' }}</span>
      <span class="chip">App promotion</span>
    </div>

    <!-- Actions -->
    <div class="project-card-actions">
      <button class="btn-soft" type="button" @click="emit('createTask', project)">
        <span class="material-symbols-outlined text-[14px]">add_task</span>
        创建新任务
      </button>
      <button class="btn-primary" type="button" @click="emit('edit', project)">
        <span class="material-symbols-outlined text-[14px]">edit</span>
        编辑项目
      </button>
      <button class="btn-soft" type="button" @click="handleViewDetail">
        <span class="material-symbols-outlined text-[14px]">assignment</span>
        查看任务
      </button>
    </div>
  </article>
</template>

<style scoped>
/* Project Card */
.project-card {
  position: relative;
  min-height: 228px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 17px;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.project-card:hover {
  border-color: #b9d3f5;
  box-shadow: 0 11px 25px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.dark .project-card {
  background: #1e293b;
  border-color: #334155;
}

.dark .project-card:hover {
  border-color: #475569;
  box-shadow: 0 11px 25px rgba(0, 0, 0, 0.2);
}

/* Select Checkbox */
.select-check {
  display: flex;
  align-items: center;
  align-self: flex-start;
  margin-bottom: 9px;
  cursor: pointer;
}

/* Project Card Head */
.project-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 9px;
}

.project-card-title {
  min-width: 0;
  flex: 1;
}

.status-badge {
  flex-shrink: 0;
  align-self: flex-start;
}

.project-card-title h3 {
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.35;
  letter-spacing: 0;
}

.project-card-title p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.dark .project-card-title p {
  color: #94a3b8;
}

/* Scope List / Chips */
.scope-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
  margin-bottom: auto;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 3px;
  background: #f1f5f9;
  color: #475569;
  font-size: 9px;
  font-weight: 600;
  white-space: nowrap;
}

.dark .chip {
  background: #334155;
  color: #cbd5e1;
}

/* Project Card Actions */
.project-card-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 19px;
}

/* Button Styles */
.btn-soft,
.btn-primary,
.btn-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 100%;
  min-width: 0;
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  background: #fff;
  color: #1e293b;
  font-size: 9px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-soft:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
  color: #137fec;
}

.btn-primary {
  background: #137fec;
  border-color: #137fec;
  color: #fff;
}

.btn-primary:hover {
  background: #0c6cd4;
  border-color: #0c6cd4;
}

.btn-ghost {
  border-color: transparent;
  background: transparent;
  color: #1f2a44;
}

.btn-ghost:hover {
  border-color: #d9e8ff;
  background: #f8fbff;
  color: #137fec;
}

.dark .btn-soft,
.dark .btn-ghost {
  background: #1e293b;
  border-color: #334155;
  color: #e2e8f0;
}

.dark .btn-soft:hover,
.dark .btn-ghost:hover {
  background: #334155;
  border-color: #475569;
  color: #60a5fa;
}

.dark .btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
}

.dark .btn-primary:hover {
  background: #2563eb;
  border-color: #2563eb;
}

/* Responsive */
@media (max-width: 768px) {
  .project-card-actions {
    grid-template-columns: 1fr;
  }
}
</style>
