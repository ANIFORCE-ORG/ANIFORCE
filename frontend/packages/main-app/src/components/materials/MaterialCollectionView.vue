<script setup lang="ts">
import { computed } from 'vue'
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

const materialImages = computed(() => new Map(
  props.materials
    .map(material => [
      material.id,
      material.poster_url || material.preview_url || material.thumbnail_url || material.url || '',
    ] as const)
    .filter(([, source]) => Boolean(source))
))

function getMaterialImageSrc(images: Map<string, string>, materialId: string): string {
  return images.get(materialId) || ''
}

function getStatusLabel(status?: string): string {
  const labels: Record<string, string> = {
    active: '进行中',
    running: '进行中',
    ready: '可用',
    fatigue: '疲劳',
    archived: '已归档',
    paused: '已暂停',
    draft: '草稿',
    failed: '失败',
  }
  return status ? labels[status] || status : '未知'
}

function getStatusColor(status?: string): string {
  const classes: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    running: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    ready: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    fatigue: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    archived: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    paused: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  }
  return status ? classes[status] || classes.draft : classes.draft
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
