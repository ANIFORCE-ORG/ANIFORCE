<script setup lang="ts">
import { ref } from 'vue'

interface Message {
  role: string
  author: string
  time: string
  content: string
}

interface Props {
  messages?: Message[]
  quickHints?: string[]
  chatInput?: string
}

const props = withDefaults(defineProps<Props>(), {
  messages: () => [],
  quickHints: () => [],
  chatInput: ''
})

const emit = defineEmits<{
  'send-message': [message: string]
  'hint-click': [hint: string]
  'new-chat': []
  'update:chatInput': [value: string]
}>()

const localChatInput = ref(props.chatInput)

const handleSendMessage = () => {
  if (!localChatInput.value.trim()) return
  emit('send-message', localChatInput.value)
  localChatInput.value = ''
  emit('update:chatInput', '')
}

const handleHintClick = (hint: string) => {
  emit('hint-click', hint)
}

const handleNewChat = () => {
  emit('new-chat')
}
</script>

<template>
  <!-- 右侧对话区 -->
  <aside class="w-96 bg-slate-50 dark:bg-slate-900/50 border-l border-slate-200 dark:border-slate-800 flex flex-col">
    <!-- Chat Header -->
    <div class="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary">chat</span>
        <span class="font-semibold text-slate-900 dark:text-white">AI智能助手</span>
      </div>
      <button 
        class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
        @click="handleNewChat"
      >
        <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">add</span>
      </button>
    </div>

    <!-- Chat Messages -->
    <div class="flex-1 overflow-y-auto p-6">
      <div
        v-for="(message, index) in messages"
        :key="index"
        class="mb-6 flex gap-4"
      >
        <!-- Avatar -->
        <div class="h-10 w-10 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
        </div>
        <!-- Message Content -->
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ message.author }}</span>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ message.time }}</span>
          </div>
          <div class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">{{ message.content }}</div>
        </div>
      </div>
    </div>

    <!-- Chat Input Area -->
    <div class="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-4">
      <div class="space-y-3">
        <!-- Input Wrapper -->
        <div class="flex items-end gap-3">
          <textarea
            v-model="localChatInput"
            class="flex-1 resize-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
            placeholder="输入您的问题或需求..."
            rows="1"
            @keydown.enter.prevent="handleSendMessage"
          ></textarea>
          <button
            class="h-10 w-10 rounded-md bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors flex-shrink-0"
            @click="handleSendMessage"
          >
            <span class="material-symbols-outlined text-xl">send</span>
          </button>
        </div>
        <!-- Quick Hints -->
        <div v-if="quickHints.length > 0" class="flex items-center gap-2 flex-wrap">
          <span class="text-xs text-slate-500 dark:text-slate-400">试试：</span>
          <button
            v-for="hint in quickHints"
            :key="hint"
            class="text-xs px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            @click="handleHintClick(hint)"
          >
            {{ hint }}
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: rgb(203 213 225);
  border-radius: 2px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background-color: rgb(148 163 184);
}
</style>
