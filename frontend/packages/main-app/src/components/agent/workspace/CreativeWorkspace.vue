<script setup lang="ts">
import type { TaskPanelArtifact } from '../TaskStatusPanel.vue'

const props = defineProps<{
  artifacts: TaskPanelArtifact[]
}>()

const creativeArtifacts = props.artifacts.length
  ? props.artifacts
  : [
      { type: 'creative_brief', title: '领土扩张卖点方向' },
      { type: 'image_asset', title: '联盟战争视觉方向' },
      { type: 'video_asset', title: '高爆发成长短视频脚本' }
    ]
</script>

<template>
  <div class="space-y-4">
    <section>
      <p class="text-xs font-medium text-slate-400">Creative Workspace</p>
      <h3 class="mt-1 text-base font-semibold text-slate-950 dark:text-white">素材创作画布</h3>
      <p class="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
        图文、脚本、视频方向会在这里沉淀为可审核的素材草稿。你可以继续在左侧用自然语言调整风格、平台规格和卖点。
      </p>
    </section>

    <div class="space-y-2">
      <article
        v-for="artifact in creativeArtifacts"
        :key="`${artifact.type || 'creative'}-${artifact.title || artifact.label}`"
        class="rounded-md border border-slate-100 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-950/45"
      >
        <div class="flex items-start gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
            <span class="material-symbols-outlined text-lg">
              {{ artifact.type === 'video_asset' ? 'movie' : artifact.type === 'image_asset' ? 'image' : 'auto_awesome' }}
            </span>
          </div>
          <div class="min-w-0">
            <h4 class="truncate text-sm font-semibold text-slate-900 dark:text-white">
              {{ artifact.title || artifact.label || '创意方向' }}
            </h4>
            <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
              {{ artifact.type || 'creative_brief' }} · 等待生成预览和审核动作
            </p>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
