<script setup lang="ts">
interface Props {
  show: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmButtonClass?: string
  variant?: 'default' | 'notion'
  tone?: 'primary' | 'danger'
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
  variant: 'default',
  tone: 'primary'
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
            <button class="confirm-button primary" :class="[confirmButtonClass, { danger: tone === 'danger' }]" type="button" @click="handleConfirm">{{ confirmText }}</button>
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
.confirm-button.primary.danger { border-color: #e03131; background: #e03131; color: #fff; }
.confirm-button.primary.danger:hover { border-color: #c92a2a; background: #c92a2a; }
.confirm-layer.notion { background: rgba(25,24,22,.48); }
.notion .confirm-dialog { border-color: #e5e3df; border-radius: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 48px -8px; font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
.notion .confirm-copy { padding: 20px 20px 18px; }
.notion .confirm-copy h2 { color: #1a1a1a; font-size: 15px; font-weight: 600; line-height: 1.4; }
.notion .confirm-copy p { margin-top: 7px; color: #787671; font-size: 13px; line-height: 1.55; }
.notion .confirm-actions { min-height: 58px; padding: 10px 20px; border-color: #ede9e4; background: #fafaf9; }
.notion .confirm-button { min-height: 36px; padding: 0 14px; border-radius: 8px; font-size: 13px; font-weight: 500; }
.notion .confirm-button.secondary { border-color: #c8c4be; color: #37352f; }
.notion .confirm-button.secondary:hover { background: #f6f5f4; }
.confirm-fade-enter-active,.confirm-fade-leave-active { transition: opacity .16s ease; }
.confirm-fade-enter-from,.confirm-fade-leave-to { opacity: 0; }
</style>
