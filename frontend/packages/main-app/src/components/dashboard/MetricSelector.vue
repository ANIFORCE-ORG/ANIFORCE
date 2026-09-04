<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import type { TrendMetric, TrendMetricOption } from '@/data/trendMetrics'

const props = withDefaults(defineProps<{
  modelValue: TrendMetric[]
  options: TrendMetricOption[]
  label?: string
}>(), {
  label: '自定义指标',
})

const emit = defineEmits<{
  'update:modelValue': [metrics: TrendMetric[]]
}>()

const detailsRef = ref<HTMLDetailsElement | null>(null)

function closeOnOutsidePointer(event: PointerEvent) {
  const details = detailsRef.value
  const target = event.target

  if (details?.open && target instanceof Node && !details.contains(target)) {
    details.open = false
  }
}

function closeOnEscape(event: KeyboardEvent) {
  const details = detailsRef.value

  if (event.key === 'Escape' && details?.open) {
    details.open = false
    details.querySelector<HTMLElement>('summary')?.focus()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', closeOnOutsidePointer, true)
  document.addEventListener('keydown', closeOnEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeOnOutsidePointer, true)
  document.removeEventListener('keydown', closeOnEscape)
})

const toggleMetric = (metric: TrendMetric, event: Event) => {
  const checked = (event.currentTarget as HTMLInputElement).checked
  if (!checked && props.modelValue.length === 1) return
  const selected = new Set(props.modelValue)
  if (checked) selected.add(metric)
  else selected.delete(metric)
  emit('update:modelValue', props.options.map(option => option.key).filter(key => selected.has(key)))
}
</script>

<template>
  <details ref="detailsRef" class="metric-selector">
    <summary>
      <span class="material-symbols-outlined" aria-hidden="true">view_column</span>
      <span>{{ props.label }}</span>
      <b>{{ props.modelValue.length }}</b>
      <span class="material-symbols-outlined chevron" aria-hidden="true">expand_more</span>
    </summary>
    <div class="metric-selector-menu">
      <header><strong>选择展示指标</strong><small>所选指标将显示在下方表格</small></header>
      <div class="metric-selector-options" role="group" aria-label="选择展示指标">
        <label v-for="option in props.options" :key="option.key">
          <input
            type="checkbox"
            :checked="props.modelValue.includes(option.key)"
            :disabled="props.modelValue.length === 1 && props.modelValue[0] === option.key"
            @change="toggleMetric(option.key, $event)"
          >
          <i :style="{ backgroundColor: option.color }" aria-hidden="true"></i>
          <span>{{ option.label }}</span>
        </label>
      </div>
    </div>
  </details>
</template>

<style scoped>
.metric-selector { position: relative; z-index: 5; order: 999; flex: 0 0 auto; margin-left: auto; }
.metric-selector summary { height: 32px; display: inline-flex; align-items: center; gap: 5px; padding: 0 9px; border: 1px solid #c8c4be; border-radius: 7px; background: #fff; color: #56534f; font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; list-style: none; white-space: nowrap; }
.metric-selector summary::-webkit-details-marker { display: none; }
.metric-selector summary:hover,.metric-selector[open] summary { border-color: #a9cef8; background: #f7fbff; color: #1769aa; }
.metric-selector summary:focus-visible { outline: 2px solid #9dc8f5; outline-offset: 2px; }
.metric-selector summary .material-symbols-outlined { font-size: 16px; }
.metric-selector summary .chevron { margin-left: 1px; transition: transform .16s ease; }
.metric-selector[open] summary .chevron { transform: rotate(180deg); }
.metric-selector summary b { min-width: 18px; height: 18px; display: grid; place-items: center; border-radius: 999px; background: #eef6ff; color: #1769aa; font-size: 10px; }
.metric-selector-menu { position: absolute; top: calc(100% + 7px); right: 0; z-index: 20; width: 250px; padding: 10px; border: 1px solid #d8d5d0; border-radius: 10px; background: #fff; box-shadow: 0 12px 30px rgba(28, 28, 26, .14); }
.metric-selector-menu header { padding: 2px 4px 9px; border-bottom: 1px solid #ede9e4; }
.metric-selector-menu header strong,.metric-selector-menu header small { display: block; }
.metric-selector-menu header strong { color: #202020; font-size: 12px; }
.metric-selector-menu header small { margin-top: 3px; color: #787774; font-size: 10px; font-weight: 400; }
.metric-selector-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 3px; padding-top: 8px; }
.metric-selector-options label { min-width: 0; height: 30px; display: flex; align-items: center; gap: 7px; padding: 0 7px; border-radius: 6px; color: #56534f; font-size: 11px; cursor: pointer; }
.metric-selector-options label:hover { background: #f6f5f4; }
.metric-selector-options input { width: 14px; height: 14px; margin: 0; accent-color: #137fec; }
.metric-selector-options i { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; }
.metric-selector-options span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 700px) { .metric-selector-menu { right: auto; left: 0; } }
</style>
