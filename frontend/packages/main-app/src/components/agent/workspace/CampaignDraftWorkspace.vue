<script setup lang="ts">
import type { TaskPanelArtifact } from '../TaskStatusPanel.vue'

const props = defineProps<{
  artifacts: TaskPanelArtifact[]
}>()

const draft = props.artifacts.find(item => item.type === 'campaign_draft') || props.artifacts[0]
const data = (draft?.data && typeof draft.data === 'object' ? draft.data : {}) as Record<string, unknown>

function textValue(key: string, fallback: string): string {
  const value = data[key]
  if (Array.isArray(value)) return value.join(' · ')
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  return fallback
}
</script>

<template>
  <div class="space-y-4">
    <section>
      <div class="mb-3 flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-medium text-slate-400">Campaign Draft</p>
          <h3 class="mt-1 text-base font-semibold text-slate-950 dark:text-white">
            {{ draft?.title || 'Meta 测试投放计划草稿' }}
          </h3>
        </div>
        <span class="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
          草稿
        </span>
      </div>
      <p class="text-sm leading-6 text-slate-500 dark:text-slate-400">
        Agent 会把对话中的预算、地区、素材组合和投放目标沉淀到这里。你可以继续用自然语言调整，也可以通过下方动作确认。
      </p>
    </section>

    <dl class="grid grid-cols-2 gap-2">
      <div class="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5 dark:border-slate-800 dark:bg-slate-950/50">
        <dt class="text-[11px] font-medium text-slate-400">平台</dt>
        <dd class="mt-1 truncate text-sm font-medium text-slate-800 dark:text-slate-200">{{ textValue('platform', 'Meta Ads') }}</dd>
      </div>
      <div class="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5 dark:border-slate-800 dark:bg-slate-950/50">
        <dt class="text-[11px] font-medium text-slate-400">预算</dt>
        <dd class="mt-1 truncate text-sm font-medium text-slate-800 dark:text-slate-200">
          {{ data.daily_budget ? `$${data.daily_budget} / day` : '$500 / day' }}
        </dd>
      </div>
      <div class="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5 dark:border-slate-800 dark:bg-slate-950/50">
        <dt class="text-[11px] font-medium text-slate-400">地区</dt>
        <dd class="mt-1 truncate text-sm font-medium text-slate-800 dark:text-slate-200">{{ textValue('geo', 'US · CA · AU') }}</dd>
      </div>
      <div class="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5 dark:border-slate-800 dark:bg-slate-950/50">
        <dt class="text-[11px] font-medium text-slate-400">目标</dt>
        <dd class="mt-1 truncate text-sm font-medium text-slate-800 dark:text-slate-200">{{ textValue('objective', 'Install / Purchase') }}</dd>
      </div>
    </dl>

    <section class="rounded-md border border-slate-100 p-3 dark:border-slate-800">
      <div class="mb-2 flex items-center gap-2">
        <span class="material-symbols-outlined text-base text-slate-400">image</span>
        <h4 class="text-sm font-semibold text-slate-900 dark:text-white">素材组合</h4>
      </div>
      <p class="text-sm leading-6 text-slate-500 dark:text-slate-400">
        当前草稿会优先使用已审核素材；如果素材不足，Agent 会建议先进入素材生成工作流。
      </p>
    </section>
  </div>
</template>
