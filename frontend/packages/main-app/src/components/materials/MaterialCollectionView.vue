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
  <MaterialLibraryView
    :materials="props.materials"
    :embedded="props.embedded"
    @select="handleSelect"
    @mention="emit('mention', $event)"
  />
</template>
