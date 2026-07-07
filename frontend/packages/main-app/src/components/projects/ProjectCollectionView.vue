<script setup lang="ts">
import ProjectCardCompact from './ProjectCardCompact.vue'
import ProjectCardDetailed from './ProjectCardDetailed.vue'
import type { Project } from '@/api/projects'

const props = withDefaults(defineProps<{
  projects: Project[]
  view?: 'compact' | 'detailed'
  mode?: 'page' | 'workspace' | 'readonly'
  embedded?: boolean
}>(), {
  view: 'compact',
  mode: 'page',
  embedded: false
})

const emit = defineEmits<{
  edit: [project: Project]
  viewDetail: [project: Project]
  viewTasks: [project: Project]
  createTask: [project: Project]
  select: [project: Project, selected: boolean]
  mention: [project: Project]
}>()

function handleSelect(project: Project, selected: boolean) {
  emit('select', project, selected)
}
</script>

<template>
  <div>
    <div v-if="projects.length && view === 'compact'" class="grid gap-4" :class="embedded ? 'grid-cols-1' : 'md:grid-cols-2 lg:grid-cols-3'">
      <ProjectCardCompact
        v-for="project in projects"
        :key="project.id"
        :project="project"
        :embedded="embedded"
        @edit="emit('edit', $event)"
        @view-detail="emit('viewDetail', $event)"
        @mention="emit('mention', $event)"
        @view-tasks="emit('viewTasks', $event)"
        @create-task="emit('createTask', $event)"
        @select="handleSelect"
      />
    </div>

    <div v-else-if="projects.length" class="grid gap-4">
      <ProjectCardDetailed
        v-for="project in projects"
        :key="project.id"
        :project="project"
        :mode="mode"
        @view-detail="emit('viewDetail', $event)"
      />
    </div>

    <div v-else class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined mb-4 text-6xl text-slate-300 dark:text-slate-700">folder_off</span>
      <p class="text-sm text-slate-500 dark:text-slate-400">未找到匹配的项目</p>
    </div>
  </div>
</template>
