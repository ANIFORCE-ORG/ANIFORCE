<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export interface TimeRange {
  value: string
  label: string
}

interface Props {
  modelValue?: string
  options?: TimeRange[]
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: 'today',
  options: () => [
    { value: 'realtime', label: '实时' },
    { value: 'today', label: '今日' },
    { value: 'yesterday', label: '昨日' },
    { value: '7days', label: '近7日' },
    { value: '30days', label: '近30日' }
  ]
})

const emit = defineEmits<Emits>()

const selectedValue = ref(props.modelValue)

watch(() => props.modelValue, (newValue) => {
  selectedValue.value = newValue
})

const handleChange = (value: string) => {
  selectedValue.value = value
  emit('update:modelValue', value)
  emit('change', value)
}

const currentLabel = computed(() => {
  const option = props.options.find(opt => opt.value === selectedValue.value)
  return option?.label || '今日'
})
</script>

<template>
  <div class="time-range-selector">
    <select
      v-model="selectedValue"
      class="text-sm px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer transition-colors hover:border-slate-300 dark:hover:border-slate-600"
      @change="handleChange(selectedValue)"
    >
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.time-range-selector select {
  min-width: 100px;
}
</style>
