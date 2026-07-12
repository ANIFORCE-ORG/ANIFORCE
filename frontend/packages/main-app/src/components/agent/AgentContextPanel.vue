<script setup lang="ts">
import { onMounted } from 'vue'
import { useAgentSession, type AgentRouteContext } from '@/composables/useAgentSession'
import ChatWindow from './ChatWindow.vue'

const props = defineProps<{
  context: AgentRouteContext
}>()

const agent = useAgentSession()

onMounted(async () => {
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  if (agent.activeSession.value) return
  if (agent.sessions.value.length) await agent.selectSession(agent.sessions.value[0])
  else await agent.createSession(props.context)
})

function send(message: string, images?: unknown): void {
  void agent.send(message, images, props.context)
}
</script>

<template>
  <aside class="agent-context-panel">
    <ChatWindow
      :messages="agent.messages.value"
      :streaming-message="agent.streamingMessage.value"
      :is-streaming="agent.agentRunning.value"
      :agent-phase="agent.agentPhase.value"
      :models="agent.models.value"
      :selected-model="agent.selectedModel.value"
      :model-names="agent.modelNames.value"
      :retry-info="agent.retryInfo.value"
      :command-status="agent.commandStatus.value"
      :timeline-blocks="agent.timelineBlocks.value"
      :loading="agent.loading.value"
      :error="agent.error.value"
      @timeline-action="agent.handleTimelineAction"
      @send="send"
      @abort="agent.abort"
      @model-change="agent.changeModel"
    />
  </aside>
</template>

<style scoped>
.agent-context-panel {
  width: 420px;
  min-width: 360px;
  height: calc(100vh - 64px);
  border-left: 1px solid #e2e8f0;
  background: #fff;
  overflow: hidden;
}

@media (max-width: 1100px) {
  .agent-context-panel {
    width: 360px;
    min-width: 320px;
  }
}
</style>
