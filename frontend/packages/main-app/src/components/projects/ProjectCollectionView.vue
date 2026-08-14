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
      <div v-for="project in projects" :key="project.id" class="group relative">
        <ProjectCardCompact
          :project="project"
          @edit="emit('edit', $event)"
          @view-detail="emit('viewDetail', $event)"
          @view-tasks="emit('viewTasks', $event)"
          @create-task="emit('createTask', $event)"
          @select="handleSelect"
        />
        <button
          v-if="embedded"
          class="mention-btn absolute top-[12px] right-[12px] z-10 rounded-md border border-primary/20 bg-white/95 px-[8px] py-[5px] text-[10px] font-semibold text-primary opacity-0 shadow-sm transition-all hover:bg-primary/10 group-hover:opacity-100 dark:bg-slate-900/95"
          title="引用到对话"
          @click="emit('mention', project)"
        >
          @mention
        </button>
      </div>
    </div>

    <div v-else-if="projects.length" class="grid gap-4">
      <div v-for="project in projects" :key="project.id" class="group relative">
        <ProjectCardDetailed
          :project="project"
          :mode="mode"
          @view-detail="emit('viewDetail', $event)"
        />
        <button
          v-if="embedded"
          class="mention-btn absolute right-[12px] top-[12px] z-10 rounded-md border border-primary/20 bg-white/95 px-[8px] py-[5px] text-[10px] font-semibold text-primary opacity-0 shadow-sm transition-all hover:bg-primary/10 group-hover:opacity-100 dark:bg-slate-900/95"
          title="引用到对话"
          @click="emit('mention', project)"
        >
          @mention
        </button>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined mb-4 text-6xl text-slate-300 dark:text-slate-700">folder_off</span>
      <p class="text-sm text-slate-500 dark:text-slate-400">未找到匹配的项目</p>
    </div>
  </div>
</template>

<style scoped>
.mention-btn {
  cursor: pointer;
}

.mention-btn:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
  background: white !important;
  border-color: rgb(var(--color-primary)) !important;
}

.mention-btn:active {
  transform: translateY(0) scale(0.95);
  transition-duration: 0.1s;
}
</style>
