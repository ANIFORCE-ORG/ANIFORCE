<script setup lang="ts">
import type { Material } from '@/api/materials'

defineProps<{
  materials: Material[]
  materialImages?: Map<string, string>
  embedded?: boolean
}>()

const emit = defineEmits<{
  select: [material: Material]
  mention: [material: Material]
  preview: [material: Material]
}>()

function getMaterialImageSrc(materialImages: Map<string, string> | undefined, materialId: string): string | undefined {
  return materialImages?.get(materialId)
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    running: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600',
    ready: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600',
    fatigue: 'bg-orange-50 dark:bg-orange-900/30 text-orange-600'
  }
  return colors[status] || 'bg-slate-50 dark:bg-slate-800 text-slate-600'
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    running: '投放中',
    ready: '待投放',
    fatigue: '已疲劳'
  }
  return labels[status] || status
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
        @click="emit('preview', creative)"
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
          <div class="absolute right-2 top-2 flex items-center gap-2">
            <button
              v-if="embedded"
              class="rounded-md bg-white/90 px-2 py-1 text-xs font-semibold text-primary opacity-0 shadow-sm backdrop-blur-sm transition-opacity group-hover:opacity-100"
              title="引用到对话"
              @click.stop="emit('mention', creative)"
            >
              @ 引用
            </button>
            <span class="rounded-md px-2 py-1 text-xs font-semibold backdrop-blur-sm" :class="getStatusColor(creative.status)">
              {{ getStatusLabel(creative.status) }}
            </span>
          </div>
          <div class="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity group-hover:opacity-100">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-primary backdrop-blur-sm">
              <span class="material-symbols-outlined text-2xl">visibility</span>
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
          <div v-if="embedded" class="mt-3 flex gap-2 border-t border-slate-100 pt-3 dark:border-slate-700" @click.stop>
            <button class="flex-1 rounded bg-primary/10 px-2 py-1.5 text-[11px] font-semibold text-primary hover:bg-primary/15" @click="emit('preview', creative)">
              预览
            </button>
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
