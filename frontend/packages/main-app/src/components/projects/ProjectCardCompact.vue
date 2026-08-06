<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Project } from '@/api/projects'

interface Props {
  project: Project
  selected?: boolean
  viewType?: 'compact' | 'detailed'
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
  viewType: 'compact'
})
const emit = defineEmits<{
  edit: [project: Project]
  viewTasks: [project: Project]
  createTask: [project: Project]
  select: [project: Project, selected: boolean]
}>()

const router = useRouter()

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    running: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    paused: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600',
    completed: 'bg-slate-50 dark:bg-slate-900/30 text-slate-600',
    draft: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600'
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    running: '进行中',
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
  <article
    class="project-card"
    :class="{
      selected,
      'is-list': viewType === 'detailed'
    }"
  >
    <!-- Checkbox -->
    <label class="select-check">
      <input
        type="checkbox"
        :checked="selected"
        class="project-checkbox"
        @change="handleCheckboxChange"
      />
      <span>选择项目</span>
    </label>

    <!-- Project Header -->
    <div class="card-heading">
      <h2 class="project-name">{{ project.name }}</h2>
      <!-- Status Badge -->
      <span
        class="status-badge"
        :class="[getStatusColor(project.status), `status-${project.status}`]"
      >
        {{ getStatusLabel(project.status) }}
      </span>
    </div>

    <p class="project-info">
      <span>{{ project.game_type }}</span>
      <span>{{ project.target_market }}</span>
    </p>

    <!-- Tags / Chips -->
    <div class="tag-list">
      <span class="tag">Meta Campaign</span>
      <span class="tag">{{ project.tags[0] || '支付计划' }}</span>
      <span class="tag">App promotion</span>
    </div>

    <!-- Actions -->
    <div class="card-actions">
      <button class="card-button" type="button" @click="emit('createTask', project)">
        <span class="material-symbols-outlined text-[14px]">add_task</span>
        创建新任务
      </button>
      <button class="card-button edit" type="button" @click="emit('edit', project)">
        <span class="material-symbols-outlined text-[14px]">edit</span>
        编辑项目
      </button>
      <button class="card-button" type="button" @click="handleViewDetail">
        <span class="material-symbols-outlined text-[14px]">assignment</span>
        查看任务
      </button>
    </div>
  </article>
</template>

<style scoped>
.project-card {
  position: relative;
  min-width: 0;
  min-height: 242px;
  display: flex;
  flex-direction: column;
  padding: 17px;
  border: 1px solid #e5e3df;
  border-radius: 12px;
  background: #ffffff;
  transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
}

.project-card:hover {
  border-color: #c8c4be;
  box-shadow: rgba(15, 15, 15, .04) 0 1px 2px;
  transform: translateY(-1px);
}

.project-card.selected {
  border-color: #c8c4be;
  background: #fafaf9;
  box-shadow: inset 0 0 0 1px #e5e3df;
}

.select-check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #787671;
  font-size: 10px;
  cursor: pointer;
}

.select-check input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #37352f;
  cursor: pointer;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-top: 13px;
}

.project-name {
  margin: 0;
  overflow-wrap: anywhere;
  color: #1a1a1a;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -.2px;
}

.status-badge {
  min-height: 22px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eaf3ec;
  color: #2f6f41;
  font-size: 9px;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.status-paused {
  background: #fbf3db;
  color: #8a651b;
}

.status-badge.status-completed {
  background: #f1f1ef;
  color: #5d5b54;
}

.status-badge.status-draft {
  background: #eef4fb;
  color: #35658f;
}

.project-info {
  min-height: 42px;
  margin: 8px 0 0;
  color: #787671;
  font-size: 11px;
  line-height: 1.65;
}

.project-info span {
  display: block;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 13px;
}

.tag {
  padding: 3px 7px;
  border-radius: 6px;
  background: #f6f5f4;
  color: #5d5b54;
  font-size: 9px;
  font-weight: 600;
  white-space: nowrap;
}

.card-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: auto;
  padding-top: 22px;
}

.card-button {
  min-width: 0;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 8px;
  border: 1px solid #c8c4be;
  border-radius: 8px;
  background: #ffffff;
  color: #37352f;
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.card-button:hover {
  border-color: #37352f;
  color: #1a1a1a;
}

.card-button.edit {
  border-color: #c8c4be;
  background: #fafaf9;
  color: #37352f;
}

.project-card.is-list {
  min-height: 146px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(230px, 1fr) auto;
  grid-template-areas:
    'select info actions'
    'heading tags actions';
  align-items: center;
  gap: 18px;
}

.project-card.is-list .select-check {
  grid-area: select;
  position: absolute;
  margin: 0;
}

.project-card.is-list .card-heading {
  grid-area: heading;
  margin: 25px 0 0;
}

.project-card.is-list .project-info {
  grid-area: info;
  margin: 0;
}

.project-card.is-list .tag-list {
  grid-area: tags;
  margin-top: 7px;
}

.project-card.is-list .card-actions {
  grid-area: actions;
  min-width: 315px;
  margin: 0;
  padding: 0;
}

@media (max-width: 1180px) {
  .project-card.is-list {
    grid-template-columns: minmax(180px, 1fr) minmax(200px, 1fr);
    grid-template-areas:
      'select info'
      'heading tags'
      'actions actions';
  }

  .project-card.is-list .card-actions {
    min-width: 0;
  }
}

@media (max-width: 720px) {
  .project-card.is-list {
    display: flex;
    min-height: 242px;
  }

  .project-card.is-list .select-check {
    position: static;
  }

  .project-card.is-list .card-heading {
    margin-top: 13px;
  }

  .project-card.is-list .project-info {
    margin-top: 8px;
  }

  .project-card.is-list .tag-list {
    margin-top: 13px;
  }

  .project-card.is-list .card-actions {
    min-width: 0;
    margin-top: auto;
    padding-top: 22px;
  }
}

@media (max-width: 520px) {
  .project-card {
    padding: 15px;
  }

  .card-actions {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .project-card,
  .card-button {
    transition-duration: .01ms !important;
  }
}
</style>
