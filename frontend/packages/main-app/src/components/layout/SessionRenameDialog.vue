<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

interface Props {
  show: boolean
  modelValue: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  confirm: []
  close: []
}>()

const inputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.show,
  async shown => {
    if (!shown) return
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select()
  },
)

const handleInput = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}

const handleConfirm = () => {
  if (props.modelValue.trim()) emit('confirm')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="session-dialog-fade">
      <div v-if="show" class="session-dialog-layer" @click.self="emit('close')">
        <section class="session-dialog" role="dialog" aria-modal="true" aria-labelledby="session-rename-title">
          <header class="session-dialog-copy">
            <h2 id="session-rename-title">重命名对话</h2>
            <p>修改后将用于历史会话列表展示。</p>
          </header>

          <div class="session-dialog-body">
            <input
              ref="inputRef"
              data-session-rename-input
              data-sidebar-session-rename-input
              :value="modelValue"
              maxlength="80"
              type="text"
              aria-label="会话名称"
              placeholder="输入会话名称"
              @input="handleInput"
              @keydown.enter.prevent="handleConfirm"
              @keydown.esc.prevent="emit('close')"
            />
          </div>

          <footer class="session-dialog-actions">
            <button class="session-dialog-button secondary" type="button" @click="emit('close')">取消</button>
            <button class="session-dialog-button primary" type="button" :disabled="!modelValue.trim()" @click="handleConfirm">保存</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.session-dialog-layer {
  position: fixed;
  z-index: 110;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(25, 24, 22, 0.48);
}

.session-dialog {
  width: min(420px, 100%);
  overflow: hidden;
  border: 1px solid #e5e3df;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: rgba(15, 15, 15, 0.16) 0 16px 48px -8px;
  color: #37352f;
  font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.session-dialog-copy {
  padding: 20px 20px 14px;
}

.session-dialog-copy h2 {
  margin: 0;
  color: #1a1a1a;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: -0.1px;
}

.session-dialog-copy p {
  margin: 5px 0 0;
  color: #787671;
  font-size: 13px;
  line-height: 1.5;
}

.session-dialog-body {
  padding: 0 20px 20px;
}

.session-dialog-body input {
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid #c8c4be;
  border-radius: 8px;
  outline: none;
  background: #ffffff;
  color: #1a1a1a;
  font: inherit;
  font-size: 14px;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.session-dialog-body input:focus {
  border-color: var(--workspace-action-primary, #137fec);
  box-shadow: 0 0 0 3px rgba(19, 127, 236, 0.14);
}

.session-dialog-actions {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 20px;
  border-top: 1px solid #ede9e4;
  background: #fafaf9;
}

.session-dialog-button {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.session-dialog-button.secondary {
  border: 1px solid #c8c4be;
  background: #ffffff;
  color: #37352f;
}

.session-dialog-button.secondary:hover {
  background: #f6f5f4;
}

.session-dialog-button.primary {
  border: 1px solid var(--workspace-action-primary, #137fec);
  background: var(--workspace-action-primary, #137fec);
  color: #ffffff;
}

.session-dialog-button.primary:hover {
  border-color: var(--workspace-action-primary-hover, #0f6fcf);
  background: var(--workspace-action-primary-hover, #0f6fcf);
}

.session-dialog-button:disabled {
  border-color: #e5e3df;
  background: #e5e3df;
  color: #a4a097;
  cursor: not-allowed;
}

.session-dialog-fade-enter-active,
.session-dialog-fade-leave-active {
  transition: opacity 0.16s ease;
}

.session-dialog-fade-enter-from,
.session-dialog-fade-leave-to {
  opacity: 0;
}

:global(.dark) .session-dialog {
  border-color: #373737;
  background: #202020;
  color: #e6e6e5;
}

:global(.dark) .session-dialog-copy h2 {
  color: #f3f3f2;
}

:global(.dark) .session-dialog-copy p {
  color: #a4a097;
}

:global(.dark) .session-dialog-body input {
  border-color: #4a4a4a;
  background: #191919;
  color: #f3f3f2;
}

:global(.dark) .session-dialog-actions {
  border-color: #373737;
  background: #252525;
}

:global(.dark) .session-dialog-button.secondary {
  border-color: #4a4a4a;
  background: #202020;
  color: #e6e6e5;
}
</style>
