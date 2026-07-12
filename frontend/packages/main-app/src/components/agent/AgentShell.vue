<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAgentSession } from '@/composables/useAgentSession'
import ChatWindow from './ChatWindow.vue'

const agent = useAgentSession()
const renamingId = ref<string | null>(null)
const renameValue = ref('')
const pendingDeleteId = ref<string | null>(null)
const stats = computed(() => agent.sessionStats.value)
const ctx = computed(() => agent.contextUsage.value)

function fmt(n: number): string {
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(n)
}

function sessionTitle(session: { title?: string; id: string }): string {
  return session.title || session.id
}

function startRename(session: { id: string; title?: string }): void {
  renamingId.value = session.id
  renameValue.value = session.title || ''
}

async function commitRename(sessionId: string): Promise<void> {
  const title = renameValue.value.trim()
  renamingId.value = null
  if (title) await agent.renameSession(sessionId, title)
}

async function confirmDelete(): Promise<void> {
  const sessionId = pendingDeleteId.value
  pendingDeleteId.value = null
  if (!sessionId) return
  await agent.deleteSession(sessionId)
}

onMounted(async () => {
  await Promise.all([agent.refreshModels(), agent.refreshSessions()])
  if (agent.sessions.value.length > 0) await agent.selectSession(agent.sessions.value[0])
  else await agent.createSession()
})
</script>

<template>
  <div class="webui-shell">
    <aside class="sidebar">
      <div class="sidebar-head">
        <div class="brand">ANIFORCE</div>
        <div class="sidebar-actions">
          <button title="Refresh sessions" @click="agent.refreshSessions">↻</button>
          <button title="New session" @click="agent.createSession">+</button>
        </div>
      </div>
      <div class="session-list">
        <div
          v-for="session in agent.sessions.value"
          :key="session.id"
          class="session-item"
          :class="{ active: agent.activeSession.value?.id === session.id }"
          @click="renamingId === session.id ? undefined : agent.selectSession(session)"
        >
          <template v-if="renamingId === session.id">
            <input
              v-model="renameValue"
              class="rename-input"
              autofocus
              @click.stop
              @keydown.enter.stop.prevent="commitRename(session.id)"
              @keydown.esc.stop.prevent="renamingId = null"
              @blur="commitRename(session.id)"
            />
          </template>
          <template v-else>
            <span>{{ sessionTitle(session) }}</span>
            <small>{{ session.id.slice(0, 16) }}</small>
            <div class="session-actions" @click.stop>
              <button title="Rename" @click="startRename(session)">✎</button>
              <button title="Delete" @click="pendingDeleteId = session.id">⌫</button>
            </div>
          </template>
        </div>
      </div>
    </aside>

    <main class="main-pane">
      <header class="topbar">
        <button class="icon-button" title="Toggle sidebar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
        <span class="top-title">Home Agent Chat</span>
        <div class="top-spacer"></div>
        <template v-if="stats">
          <span v-if="stats.tokens.input" class="stat-chip">↑ {{ fmt(stats.tokens.input) }}</span>
          <span v-if="stats.tokens.output" class="stat-chip">↓ {{ fmt(stats.tokens.output) }}</span>
          <span v-if="stats.cost" class="stat-chip selected">{{ stats.cost >= 0.01 ? `$${stats.cost.toFixed(2)}` : '<$0.01' }}</span>
        </template>
        <span v-if="ctx?.contextWindow" class="stat-chip">
          {{ ctx.percent !== null ? `${ctx.percent?.toFixed(0)}%` : '?' }} / {{ fmt(ctx.contextWindow) }}
        </span>
      </header>
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
        @send="agent.send"
        @abort="agent.abort"
        @model-change="agent.changeModel"
      />
    </main>

    <div v-if="pendingDeleteId" class="modal-backdrop" @click="pendingDeleteId = null">
      <div class="confirm-modal" @click.stop>
        <h3>Delete session?</h3>
        <p>This removes the local in-memory session from the Home chat list.</p>
        <div class="confirm-actions">
          <button @click="pendingDeleteId = null">Cancel</button>
          <button class="danger" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.webui-shell {
  --bg: #ffffff;
  --surface: #ffffff;
  --surface-container: #f8fafc;
  --bg-panel: #f1f5f9;
  --bg-hover: #f1f5f9;
  --bg-selected: #eaf2ff;
  --assistant-bg: transparent;
  --user-bg: #f8fbff;
  --border: #e2e8f0;
  --outline: #cbd5e1;
  --outline-variant: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --text-dim: #94a3b8;
  --accent: #2563eb;
  --success: #059669;
  --warning: #d97706;
  --error: #dc2626;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --shadow-popover: 0 14px 32px rgba(15, 23, 42, .14);
  display: flex;
  height: calc(100vh - 100px);
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.sidebar { width: 320px; min-width: 260px; display: flex; flex-direction: column; height: 100%; border-right: 1px solid var(--border); background: var(--surface-container); }
.sidebar-head { display: flex; align-items: center; justify-content: space-between; height: 44px; padding: 0 10px 0 14px; border-bottom: 1px solid var(--outline-variant); background: var(--surface); }
.brand { color: var(--text-muted); font-size: 12px; font-weight: 700; letter-spacing: .12em; }
.sidebar-actions { display: flex; align-items: center; gap: 2px; }
.sidebar-head button { width: 28px; height: 28px; border: 0; border-radius: 8px; background: transparent; color: var(--text-muted); cursor: pointer; font-size: 16px; }
.sidebar-head button:hover { background: var(--bg-hover); color: var(--text); }
.session-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item { position: relative; display: flex; flex-direction: column; gap: 4px; width: 100%; border: 0; border-radius: 10px; padding: 9px 54px 9px 10px; background: transparent; color: var(--text-muted); cursor: pointer; text-align: left; }
.session-item:hover { background: var(--bg-hover); color: var(--text); }
.session-item.active { background: var(--bg-selected); color: var(--text); }
.session-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.session-item small { color: var(--text-dim); font-size: 10px; font-family: var(--font-mono); }
.session-actions { position: absolute; top: 6px; right: 6px; display: flex; gap: 2px; opacity: 0; transition: opacity .12s; }
.session-item:hover .session-actions, .session-item.active .session-actions { opacity: 1; }
.session-actions button { display: grid; place-items: center; width: 22px; height: 22px; border: 0; border-radius: 6px; background: transparent; color: var(--text-dim); cursor: pointer; font-size: 12px; }
.session-actions button:hover { background: var(--surface); color: var(--text); }
.rename-input { width: 100%; border: 1px solid var(--accent); border-radius: 7px; padding: 5px 7px; background: var(--surface); color: var(--text); font-size: 13px; outline: none; }
.main-pane { display: flex; flex: 1; min-width: 0; flex-direction: column; height: 100%; overflow: hidden; }
.topbar { display: flex; align-items: center; flex-shrink: 0; height: 44px; gap: 8px; padding: 0 8px; border-bottom: 1px solid var(--outline-variant); background: var(--surface); }
.icon-button { width: 32px; height: 32px; display: grid; place-items: center; border: 0; border-radius: 8px; background: transparent; color: var(--text-muted); cursor: pointer; }
.icon-button:hover { background: var(--bg-hover); color: var(--text); }
.top-title { color: var(--text-muted); font-size: 12px; font-weight: 600; }
.top-spacer { flex: 1; }
.stat-chip { display: inline-flex; align-items: center; gap: 4px; height: 24px; border: 1px solid var(--outline-variant); border-radius: 999px; padding: 0 8px; color: var(--text-muted); background: var(--surface-container); font-size: 11px; font-variant-numeric: tabular-nums; }
.stat-chip.selected { color: var(--accent); background: var(--bg-selected); }
.modal-backdrop { position: fixed; inset: 0; z-index: 2000; display: grid; place-items: center; background: rgba(15, 23, 42, .28); backdrop-filter: blur(2px); }
.confirm-modal { width: min(360px, calc(100vw - 32px)); border: 1px solid var(--outline-variant); border-radius: 14px; padding: 16px; background: var(--surface); box-shadow: var(--shadow-popover); }
.confirm-modal h3 { margin: 0 0 6px; color: var(--text); font-size: 16px; }
.confirm-modal p { margin: 0; color: var(--text-muted); font-size: 13px; line-height: 1.5; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.confirm-actions button { height: 32px; border: 1px solid var(--outline-variant); border-radius: 8px; padding: 0 12px; background: var(--surface-container); color: var(--text-muted); cursor: pointer; font-size: 13px; }
.confirm-actions button.danger { border-color: color-mix(in srgb, var(--error) 35%, var(--outline)); background: color-mix(in srgb, var(--error) 9%, var(--surface)); color: var(--error); }
@media (max-width: 860px) { .sidebar { display: none; } .webui-shell { height: calc(100vh - 100px); } }
</style>
