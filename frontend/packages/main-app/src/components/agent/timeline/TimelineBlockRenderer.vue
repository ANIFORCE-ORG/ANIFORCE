<script setup lang="ts">
import type { AgentTimelineBlock } from '@/composables/useHomeAgentSession'
import ToolActivityBlock from './ToolActivityBlock.vue'
import ProjectListBlock from './ProjectListBlock.vue'
import PlanTimelineBlock from './PlanTimelineBlock.vue'

const props = defineProps<{
  block: AgentTimelineBlock
}>()

const emit = defineEmits<{
  action: [action: string, payload: Record<string, unknown>]
}>()
</script>

<template>
  <ToolActivityBlock v-if="props.block.type === 'tool_activity'" :block="props.block" />
  <ProjectListBlock
    v-else-if="props.block.type === 'project_list'"
    :block="props.block"
    @action="(action, payload) => emit('action', action, payload)"
  />
  <PlanTimelineBlock v-else-if="props.block.type === 'plan'" :block="props.block" />
</template>
