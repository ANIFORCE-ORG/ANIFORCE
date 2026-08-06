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
  min-width: 0;
  min-height: 242px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e3e1dd;
  border-radius: 12px;
  padding: 17px;
  background: #fff;
  color: #37352f;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease, transform 0.16s ease;
}

.project-card:hover {
  border-color: #c8c5c0;
  box-shadow: 0 8px 24px rgba(15, 15, 15, 0.055);
  transform: translateY(-1px);
}

.project-card.selected {
  border-color: #98c3f0;
  background: #f7fbff;
  box-shadow: 0 0 0 1px rgba(19, 127, 236, 0.08);
}

.dark .project-card {
  background: #242424;
  border-color: #464646;
}

.dark .project-card:hover {
  border-color: #5b5b5b;
  box-shadow: 0 11px 25px rgba(0, 0, 0, 0.2);
}

.dark .project-card.selected {
  border-color: #4f9ae8;
  background: #202b36;
}

/* Select Checkbox */
.select-check {
  display: flex;
  align-items: center;
  align-self: flex-start;
  min-height: 22px;
  margin-bottom: 11px;
  cursor: pointer;
}

.select-check span {
  color: #787774;
  font-size: 11px;
}

/* Project Card Head */
.project-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
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
  display: -webkit-box;
  min-height: 40px;
  margin: 0 0 8px;
  overflow: hidden;
  color: #191919;
  font-size: 15px;
  line-height: 1.38;
  letter-spacing: -0.012em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.project-card-title p {
  margin: 0;
  color: #787774;
  font-size: 11px;
  line-height: 1.6;
}

.dark .project-card-title p {
  color: #a6a6a2;
}

.dark .project-card-title h3 {
  color: #f3f3f2;
}

/* Scope List / Chips */
.scope-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
  margin-bottom: auto;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f2f1ef;
  color: #5f5e5a;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.2;
  white-space: nowrap;
}

.dark .chip {
  background: #373737;
  color: #d1d1cf;
}

/* Project Card Actions */
.project-card-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: center;
  gap: 7px;
  margin-top: auto;
  padding-top: 18px;
  border-top: 1px solid #efeeec;
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
  min-height: 32px;
  padding: 6px 8px;
  border: 1px solid #dedbd7;
  border-radius: 6px;
  background: #fff;
  color: #37352f;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-soft:hover {
  border-color: #c8c5c0;
  background: #f7f7f5;
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
  background: #242424;
  border-color: #464646;
  color: #e8e8e6;
}

.dark .btn-soft:hover,
.dark .btn-ghost:hover {
  background: #303030;
  border-color: #5b5b5b;
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

/* Reference list-view logic: keep the same card content and actions. */
.project-card.is-list {
  min-height: 146px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(230px, 1fr) minmax(320px, auto);
  grid-template-areas:
    "select scope actions"
    "head scope actions";
  align-items: start;
  column-gap: 24px;
  row-gap: 4px;
}

.project-card.is-list .select-check {
  grid-area: select;
  margin: 0;
}

.project-card.is-list .project-card-head {
  grid-area: head;
  margin: 0;
}

.project-card.is-list .project-card-title h3 {
  min-height: auto;
  -webkit-line-clamp: 1;
}

.project-card.is-list .scope-list {
  grid-area: scope;
  align-content: flex-start;
  margin: 28px 0 0;
}

.project-card.is-list .project-card-actions {
  grid-area: actions;
  align-self: stretch;
  min-width: 320px;
  margin: 0;
  padding: 28px 0 0;
  border-top: 0;
}

/* Responsive */
@media (max-width: 1180px) {
  .project-card.is-list {
    grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr);
    grid-template-areas:
      "select scope"
      "head scope"
      "actions actions";
  }

  .project-card.is-list .project-card-actions {
    min-width: 0;
    padding-top: 14px;
    border-top: 1px solid #efeeec;
  }
}

@media (max-width: 720px) {
  .project-card.is-list {
    display: flex;
    min-height: 242px;
  }

  .project-card.is-list .select-check {
    margin-bottom: 11px;
  }

  .project-card.is-list .project-card-head {
    margin-bottom: 10px;
  }

  .project-card.is-list .project-card-title h3 {
    min-height: 40px;
    -webkit-line-clamp: 2;
  }

  .project-card.is-list .scope-list {
    margin-top: 10px;
  }

  .project-card.is-list .project-card-actions {
    margin-top: auto;
    padding-top: 18px;
  }
}

@media (max-width: 520px) {
  .project-card-actions {
    grid-template-columns: 1fr;
  }
}
</style>
