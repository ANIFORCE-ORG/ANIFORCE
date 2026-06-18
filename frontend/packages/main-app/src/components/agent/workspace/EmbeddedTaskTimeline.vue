<script setup lang="ts">
export interface WorkspaceStep {
  key: string
  label: string
  status: 'done' | 'active' | 'pending' | 'error'
}

withDefaults(defineProps<{
  steps: WorkspaceStep[]
  compact?: boolean
}>(), {
  compact: false
})
</script>

<template>
  <section :class="compact ? '' : 'border-t border-slate-100 px-4 py-3 dark:border-slate-800'">
    <div v-if="!compact" class="mb-3 flex items-center justify-between">
      <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400">执行进度</h3>
      <span class="text-[11px] text-slate-400">实时更新</span>
    </div>
    <ol :class="compact ? 'flex min-w-0 items-center gap-1 overflow-hidden' : 'space-y-2'">
      <li
        v-for="step in steps"
        :key="step.key"
        class="flex items-center gap-2.5 text-xs"
        :class="compact ? 'min-w-0 flex-1 gap-1.5 rounded-md px-1.5 py-1.5' : ''"
      >
        <span
          class="flex shrink-0 items-center justify-center rounded-full border"
          :class="[
            compact ? 'h-3.5 w-3.5' : 'h-4 w-4',
            {
              'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-950': step.status === 'done',
              'border-primary bg-white text-primary dark:bg-slate-950': step.status === 'active',
              'border-red-300 bg-red-50 text-red-600 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300': step.status === 'error',
              'border-slate-200 bg-slate-50 text-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500': step.status === 'pending'
            }
          ]"
        >
          <span v-if="step.status === 'done'" class="material-symbols-outlined" :class="compact ? 'text-[11px]' : 'text-[13px]'">check</span>
          <span v-else-if="step.status === 'error'" class="material-symbols-outlined" :class="compact ? 'text-[11px]' : 'text-[13px]'">close</span>
          <span v-else class="h-1.5 w-1.5 rounded-full bg-current"></span>
        </span>
        <span
          class="truncate"
          :class="{
            'font-medium text-slate-950 dark:text-white': step.status === 'active',
            'text-slate-500 dark:text-slate-400': step.status !== 'active'
          }"
        >
          {{ step.label }}
        </span>
        <span
          v-if="compact"
          class="h-px flex-1 bg-slate-200 dark:bg-slate-800"
        ></span>
      </li>
    </ol>
  </section>
</template>
