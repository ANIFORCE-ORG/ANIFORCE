<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { AgentModel } from '@/api/agent'

const props = defineProps<{
  isStreaming: boolean
  models: AgentModel[]
  selectedModel?: { provider: string; modelId: string } | null
  retryInfo?: { attempt: number; maxAttempts: number; errorMessage?: string } | null
  commandStatus?: string | null
}>()
const emit = defineEmits<{
  send: [message: string, images?: Array<{ type: 'image'; data: string; mimeType: string }>]
  abort: []
  modelChange: [provider: string, modelId: string]
}>()

const value = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)
const modelOpen = ref(false)
const menuRect = ref<{ left: number; bottom: number; width: number } | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const images = ref<Array<{ type: 'image'; data: string; mimeType: string; previewUrl: string }>>([])

function autosize(): void {
  const ta = textarea.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`
}
function handleSend(): void {
  const msg = value.value.trim()
  if ((!msg && images.value.length === 0) || props.isStreaming) return
  emit('send', msg, images.value.map(image => ({ type: 'image', data: image.data, mimeType: image.mimeType })))
  value.value = ''
  images.value.forEach(image => URL.revokeObjectURL(image.previewUrl))
  images.value = []
  nextTick(autosize)
}
function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    handleSend()
  }
}
function currentModelName(): string {
  if (!props.selectedModel) return props.models[0]?.name || 'Model'
  const model = props.models.find(m => m.provider === props.selectedModel?.provider && m.id === props.selectedModel?.modelId)
  return model?.name || props.selectedModel.modelId
}
function selectedModelSupportsImages(): boolean {
  const selected = props.selectedModel
  const model = selected ? props.models.find(item => item.provider === selected.provider && item.id === selected.modelId) : props.models[0]
  const input = (model as AgentModel & { input?: string[] })?.input
  // models.json is the source of truth. If input is present and excludes image,
  // block it. If input is missing, do not guess; let Pi/model handle it.
  return Array.isArray(input) ? input.includes('image') : true
}

function openMenu(kind: 'model', event: MouseEvent): void {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  menuRect.value = { left: rect.left, bottom: window.innerHeight - rect.top + 6, width: rect.width }
  modelOpen.value = kind === 'model' ? !modelOpen.value : false
}
function selectModel(model: AgentModel): void {
  modelOpen.value = false
  emit('modelChange', model.provider, model.id)
}
function removeImage(index: number): void {
  const image = images.value[index]
  if (image) URL.revokeObjectURL(image.previewUrl)
  images.value.splice(index, 1)
}

function handleFiles(files: FileList | null): void {
  if (!files) return
  for (const file of Array.from(files)) {
    if (!file.type.startsWith('image/')) continue
    if (!selectedModelSupportsImages()) {
      window.dispatchEvent(new CustomEvent('agent-ui-notify', { detail: '当前模型不支持图片，请先切换到支持图片输入的模型。' }))
      continue
    }
    const reader = new FileReader()
    reader.onload = () => {
      const raw = String(reader.result || '')
      const data = raw.includes(',') ? raw.split(',')[1] : raw
      images.value.push({ type: 'image', data, mimeType: file.type, previewUrl: URL.createObjectURL(file) })
    }
    reader.readAsDataURL(file)
  }
}
watch(value, () => nextTick(autosize))
defineExpose({
  insertIfEmpty(text: string) {
    if (value.value.trim()) return
    value.value = text
    nextTick(() => { textarea.value?.focus(); autosize() })
  },
  insertText(text: string) {
    value.value += `${value.value ? ' ' : ''}${text}`
    nextTick(() => { textarea.value?.focus(); autosize() })
  }
})
</script>

<template>
  <div class="chat-input-wrap">
    <div v-if="retryInfo" class="retry-banner">
      Retrying ({{ retryInfo.attempt }}/{{ retryInfo.maxAttempts }})…
      <span v-if="retryInfo.errorMessage">— {{ retryInfo.errorMessage }}</span>
    </div>
    <div v-if="commandStatus" class="command-status">{{ commandStatus }}</div>

    <input ref="fileInput" type="file" accept="image/*" multiple class="hidden-file" @change="handleFiles(($event.target as HTMLInputElement).files)" />
    <div v-if="images.length" class="image-previews">
      <div v-for="(image, index) in images" :key="image.previewUrl" class="image-preview">
        <img :src="image.previewUrl" alt="" />
        <button @click="removeImage(index)">×</button>
      </div>
    </div>

    <div class="input-box" :class="{ streaming: isStreaming }">
      <textarea
        ref="textarea"
        v-model="value"
        rows="1"
        :placeholder="isStreaming ? 'Agent is running…' : 'Message…'"
        :disabled="isStreaming"
        @keydown="handleKeydown"
        @input="autosize"
      />
      <button v-if="isStreaming" class="stop-button" @click="emit('abort')">
        <span class="stop-icon"></span>
        Stop
      </button>
      <button v-else class="send-button" :disabled="!value.trim() && images.length === 0" @click="handleSend">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="2" y1="7" x2="11" y2="7" />
          <polyline points="7.5 3 12 7 7.5 11" />
        </svg>
        Send
      </button>
    </div>

    <div class="toolbar">
      <button class="chip icon-chip" title="Attach image" :disabled="isStreaming" @click="fileInput?.click()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </button>

      <div class="dropdown">
        <button class="chip" :class="{ active: modelOpen }" :disabled="isStreaming || models.length === 0" @click="openMenu('model', $event)">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" />
          </svg>
          <span>{{ currentModelName() }}</span>
        </button>
        <div v-if="modelOpen" class="menu model-menu" :style="menuRect ? { left: `${menuRect.left}px`, bottom: `${menuRect.bottom}px`, minWidth: `${menuRect.width}px` } : undefined">
          <template v-for="model in models" :key="`${model.provider}:${model.id}`">
            <button :class="{ active: selectedModel?.provider === model.provider && selectedModel?.modelId === model.id }" @click="selectModel(model)">
              <span>{{ model.name }}</span>
              <small>{{ model.provider }}</small>
            </button>
          </template>
        </div>
      </div>

      <div class="spacer"></div>
    </div>
  </div>
</template>

<style scoped>
.chat-input-wrap { flex-shrink: 0; background: transparent; padding: 0 16px 12px; padding-right: 52px; }
.retry-banner, .command-status { max-width: 820px; margin: 0 auto 8px; padding: 5px 10px; border-radius: 6px; font-size: 12px; }
.retry-banner { border: 1px solid rgba(234,179,8,.25); background: rgba(234,179,8,.08); color: rgba(180,130,0,.9); }
.command-status { border: 1px solid var(--outline-variant); background: var(--surface-container); color: var(--text-muted); }
.hidden-file { display: none; }
.image-previews { display: flex; gap: 6px; flex-wrap: wrap; max-width: 820px; margin: 0 auto 6px; }
.image-preview { position: relative; width: 56px; height: 56px; }
.image-preview img { width: 56px; height: 56px; object-fit: cover; border: 1px solid var(--border); border-radius: 6px; display: block; }
.image-preview button { position: absolute; top: -5px; right: -5px; display: grid; place-items: center; width: 17px; height: 17px; border: 1px solid var(--border); border-radius: 50%; background: var(--surface); color: var(--text-muted); cursor: pointer; }
.input-box { display: flex; align-items: center; gap: 8px; max-width: 820px; margin: 0 auto; border: 1px solid var(--outline-variant); border-radius: 18px; padding: 12px 12px 12px 16px; background: var(--surface); box-shadow: 0 1px 2px rgba(60,64,67,.10), 0 6px 18px -14px rgba(60,64,67,.45); }
.input-box.streaming { border-color: color-mix(in srgb, var(--warning) 55%, var(--outline)); }
textarea { flex: 1; min-height: 24px; max-height: 200px; resize: none; overflow: auto; border: 0; outline: 0; background: none; color: var(--text); font-size: 14px; line-height: 1.6; font-family: inherit; }
.send-button, .stop-button { flex-shrink: 0; align-self: flex-end; display: flex; align-items: center; gap: 6px; border: 0; border-radius: 8px; padding: 7px 14px; font-size: 13px; font-weight: 600; cursor: pointer; }
.send-button { background: var(--accent); color: white; box-shadow: 0 1px 3px rgba(37,99,235,.25); }
.send-button:disabled { background: var(--bg-panel); color: var(--text-dim); box-shadow: none; cursor: not-allowed; }
.stop-button { background: color-mix(in srgb, var(--error) 12%, transparent); color: var(--error); border: 1px solid color-mix(in srgb, var(--error) 35%, var(--outline)); }
.stop-icon { width: 9px; height: 9px; border-radius: 2px; background: currentColor; }
.toolbar { display: flex; align-items: center; gap: 2px; overflow-x: auto; max-width: 820px; margin: 8px auto 0; padding: 4px 2px; }
.spacer { flex: 1; }
.chip { display: inline-flex; align-items: center; gap: 6px; height: 28px; border: 1px solid var(--outline-variant); border-radius: 999px; padding: 0 10px; background: var(--surface-container); color: var(--text-muted); font-size: 12px; cursor: pointer; white-space: nowrap; }
.icon-chip { width: 34px; justify-content: center; padding: 0; }
.chip:hover:not(:disabled), .chip.active { background: var(--bg-hover); color: var(--text); border-color: var(--accent); }
.chip:disabled { opacity: .45; cursor: not-allowed; }
.dropdown { position: relative; }
.menu { position: fixed; z-index: 1000; overflow: hidden; min-width: 180px; max-height: min(360px, 60vh); overflow-y: auto; border: 1px solid var(--outline-variant); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow-popover); }
.model-menu { min-width: 260px; }
.menu button { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; border: 0; background: none; color: var(--text-muted); cursor: pointer; padding: 7px 12px; text-align: left; font-size: 12px; }
.menu button:hover, .menu button.active { background: var(--bg-selected); color: var(--text); }
.menu small { color: var(--text-dim); }
.small-menu { min-width: 130px; }
</style>
