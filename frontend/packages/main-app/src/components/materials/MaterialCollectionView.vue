<script setup lang="ts">
import MaterialLibraryView from './MaterialLibraryView.vue'
import type { Material } from '@/api/materials'
import type { MaterialRow } from '@/pages/creatives/materialsAdapter'

const props = defineProps<{
  materials: Material[]
  embedded?: boolean
}>()

const emit = defineEmits<{
  select: [material: Material]
  mention: [material: Material]
  preview: [material: Material]
}>()

function handleSelect(row: MaterialRow): void {
  emit('select', row.material)
  emit('preview', row.material)
}
</script>

<template>
  <div>
    <div
      v-if="materials.length"
      class="grid gap-4"
      :class="embedded ? 'grid-cols-1 2xl:grid-cols-2' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'"
    >
      <div
        v-for="creative in materials"
        :key="creative.id"
        class="group cursor-pointer overflow-hidden rounded-md border border-slate-200 bg-white transition-all hover:shadow-lg dark:border-slate-700 dark:bg-slate-800"
      >
        <div class="relative aspect-[9/16] overflow-hidden bg-slate-100 dark:bg-slate-800">
          <img
            v-if="getMaterialImageSrc(materialImages, creative.id)"
            :src="getMaterialImageSrc(materialImages, creative.id)"
            :alt="creative.name"
            class="h-full w-full object-cover"
          />
          <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800">
            <span class="material-symbols-outlined text-6xl text-slate-400 dark:text-slate-500">video_library</span>
          </div>
          <div class="absolute right-2 top-2">
            <span class="status-chip backdrop-blur-sm" :data-status="creative.status" :class="getStatusColor(creative.status)">
              {{ getStatusLabel(creative.status) }}
            </span>
          </div>
          <div class="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity group-hover:opacity-100">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-primary backdrop-blur-sm">
              <span class="material-symbols-outlined text-2xl">play_arrow</span>
            </div>
          </div>
        </div>

        <div class="p-3">
          <h3 class="mb-2 truncate text-xs font-bold text-slate-900 dark:text-white">{{ creative.name }}</h3>
          <div class="mb-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span v-if="creative.duration">{{ creative.duration }}s</span>
            <span v-if="creative.duration && creative.tags && creative.tags.length > 0">·</span>
            <span v-if="creative.tags && creative.tags.length > 0" class="truncate">{{ creative.tags[0] }}</span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div class="text-left">
              <div class="mb-0.5 text-[10px] text-slate-400">CTR预估</div>
              <div class="text-xs font-bold text-slate-900 dark:text-white">{{ creative.ctr_estimate?.toFixed(1) || 'N/A' }}%</div>
            </div>
            <div class="text-left">
              <div class="mb-0.5 text-[10px] text-slate-400">文件大小</div>
              <div class="text-xs font-bold text-slate-900 dark:text-white">{{ creative.file_size ? (creative.file_size / 1024).toFixed(0) + 'KB' : 'N/A' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined mb-4 text-6xl text-slate-300 dark:text-slate-700">video_library</span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无素材</p>
    </div>
  </div>
</template>
