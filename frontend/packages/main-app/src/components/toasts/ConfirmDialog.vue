<script setup lang="ts">
interface Props {
  show: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmButtonClass?: string
  variant?: 'default' | 'notion'
}

interface Emits {
  (e: 'confirm'): void
  (e: 'cancel'): void
  (e: 'close'): void
}

withDefaults(defineProps<Props>(), {
  title: '确认操作',
  confirmText: '确定',
  cancelText: '取消',
  confirmButtonClass: 'bg-blue-500 hover:bg-blue-600',
  variant: 'default'
})

const emit = defineEmits<Emits>()

const handleConfirm = () => {
  emit('confirm')
  emit('close')
}

const handleCancel = () => {
  emit('cancel')
  emit('close')
}

const handleBackdropClick = (event: MouseEvent) => {
  if (event.target === event.currentTarget) handleCancel()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="show"
        class="confirm-layer"
        :class="{ notion: variant === 'notion' }"
        @click="handleBackdropClick"
      >
        <section class="confirm-dialog" role="alertdialog" aria-modal="true">
          <div class="confirm-copy">
            <h2>{{ title }}</h2>
            <p>{{ message }}</p>
          </div>
          <footer class="confirm-actions">
            <button class="confirm-button secondary" type="button" @click="handleCancel">{{ cancelText }}</button>
            <button class="confirm-button primary" :class="confirmButtonClass" type="button" @click="handleConfirm">{{ confirmText }}</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-layer { position: fixed; z-index: 110; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(15,23,42,.6); backdrop-filter: blur(3px); }
.confirm-dialog { width: min(420px,100%); overflow: hidden; border: 1px solid #e2e8f0; border-radius: 10px; background: #fff; box-shadow: rgba(15,23,42,.2) 0 20px 56px -12px; }
.confirm-copy { padding: 22px 20px 18px; }
.confirm-copy h2 { margin: 0; color: #0f172a; font-size: 15px; font-weight: 650; }
.confirm-copy p { margin: 10px 0 0; color: #475569; font-size: 11px; line-height: 1.6; }
.confirm-actions { min-height: 58px; display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding: 0 18px; border-top: 1px solid #e2e8f0; background: #f8fafc; }
.confirm-button { min-height: 36px; padding: 0 13px; border-radius: 8px; font-size: 10px; font-weight: 500; cursor: pointer; }
.confirm-button.secondary { border: 1px solid #cbd5e1; background: #fff; color: #334155; }
.confirm-button.primary { border: 1px solid #2383e2; background: #2383e2; color: #fff; }
.confirm-layer.notion { background: rgba(25,24,22,.48); }
.notion .confirm-dialog { border-color: #e5e3df; border-radius: 12px; }
.notion .confirm-copy h2 { color: #1a1a1a; }
.notion .confirm-copy p { color: #5d5b54; }
.notion .confirm-actions { border-color: #e5e3df; background: #fafaf9; }
.notion .confirm-button.secondary { border-color: #c8c4be; color: #37352f; }
.confirm-fade-enter-active,.confirm-fade-leave-active { transition: opacity .16s ease; }
.confirm-fade-enter-from,.confirm-fade-leave-to { opacity: 0; }
</style>
