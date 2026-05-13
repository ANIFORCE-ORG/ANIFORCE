<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { agentService } from '@/services/agentService'
import { agentConfig } from '@/config/agent'

interface Message {
  role: 'user' | 'assistant' | 'system'
  author: string
  time: string
  content: string
  isStreaming?: boolean
}

interface Props {
  sessionId?: string
  quickHints?: string[]
  autoFocus?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  sessionId: '',
  quickHints: () => [
    '分析RPG游戏市场',
    '生成广告素材',
    '优化投放策略',
    '查看数据报表'
  ],
  autoFocus: false
})

const emit = defineEmits<{
  'session-change': [sessionId: string]
}>()

// 状态管理
const localChatInput = ref('')
const messages = ref<Message[]>([])
const isLoading = ref(false)
const currentSessionId = ref(props.sessionId || agentService.generateSessionId('chat'))
const messagesContainer = ref<HTMLElement | null>(null)

// 折叠状态 - 从localStorage读取初始值
const CHATPANEL_COLLAPSED_KEY = 'aniforce_chatpanel_collapsed'
const isCollapsed = ref(localStorage.getItem(CHATPANEL_COLLAPSED_KEY) === 'true')

// 监听sessionId变化
watch(() => props.sessionId, (newSessionId) => {
  if (newSessionId && newSessionId !== currentSessionId.value) {
    currentSessionId.value = newSessionId
    loadSessionHistory()
  }
})

// 计算当前时间
const getCurrentTime = () => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 加载会话历史
const loadSessionHistory = async () => {
  try {
    const sessionDetail = await agentService.getSessionDetail(currentSessionId.value)
    messages.value = sessionDetail.messages.map(msg => ({
      role: msg.role,
      author: msg.role === 'user' ? '用户' : 'AI助手',
      time: msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : getCurrentTime(),
      content: msg.content
    }))
    scrollToBottom()
  } catch (error) {
    console.log('会话历史加载失败或会话不存在,开始新会话')
    messages.value = []
  }
}

// 发送消息 - 根据配置使用流式或非流式对话
const handleSendMessage = async () => {
  if (!localChatInput.value.trim() || isLoading.value) return

  const userMessage = localChatInput.value.trim()
  localChatInput.value = ''

  // 添加用户消息
  messages.value.push({
    role: 'user',
    author: '用户',
    time: getCurrentTime(),
    content: userMessage
  })
  scrollToBottom()

  // 添加AI消息占位符
  const aiMessageIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    author: 'AI助手',
    time: getCurrentTime(),
    content: '',
    isStreaming: true
  })

  isLoading.value = true

  try {
    if (agentConfig.chatMode === 'stream') {
      // 流式对话 - 逐字显示
      for await (const chunk of agentService.chatStream(currentSessionId.value, userMessage)) {
        messages.value[aiMessageIndex].content += chunk
        scrollToBottom()
      }
      messages.value[aiMessageIndex].isStreaming = false
    } else {
      // 非流式对话 - 一次性显示
      const response = await agentService.chat(currentSessionId.value, userMessage)
      messages.value[aiMessageIndex].content = response.message
      messages.value[aiMessageIndex].isStreaming = false
      messages.value[aiMessageIndex].time = new Date(response.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    
    scrollToBottom()
  } catch (error: any) {
    console.error('对话失败:', error)
    messages.value[aiMessageIndex].content = '抱歉,对话出现错误,请稍后重试。'
    messages.value[aiMessageIndex].isStreaming = false
  } finally {
    isLoading.value = false
  }
}

// 快捷提示点击
const handleHintClick = (hint: string) => {
  localChatInput.value = hint
}

// 创建新对话
const handleNewChat = () => {
  currentSessionId.value = agentService.generateSessionId('chat')
  messages.value = []
  emit('session-change', currentSessionId.value)
}

// 折叠/展开
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem(CHATPANEL_COLLAPSED_KEY, String(isCollapsed.value))
}

// 组件挂载时加载历史
if (props.sessionId) {
  loadSessionHistory()
}
</script>

<template>
  <!-- 右侧对话区 -->
  <aside 
    class="bg-slate-50 dark:bg-slate-900/50 border-l border-slate-200 dark:border-slate-800 flex flex-col transition-all duration-300 relative"
    :class="isCollapsed ? 'w-16' : 'w-96'"
  >
    <!-- Collapsed State - Vertical Expand Button -->
    <div v-if="isCollapsed" class="flex-1 flex items-center justify-center">
      <button
        class="writing-mode-vertical-rl p-4 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors rounded-lg flex items-center gap-2"
        @click="toggleCollapse"
      >
        <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 rotate-180">chevron_left</span>
        <span class="text-sm font-medium text-slate-600 dark:text-slate-400">AI助手</span>
      </button>
    </div>

    <!-- Expanded State -->
    <template v-else>
      <!-- Chat Header -->
      <div class="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">chat</span>
          <span class="font-semibold text-slate-900 dark:text-white">AI智能助手</span>
        </div>
        <div class="flex items-center gap-2">
          <!-- 创建新对话按钮暂时屏蔽
          <button 
            class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="handleNewChat"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">add</span>
          </button>
          -->
          <button 
            class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="toggleCollapse"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">chevron_right</span>
          </button>
        </div>
      </div>

      <!-- Chat Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6">
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">chat</span>
          <p class="text-sm text-slate-500 dark:text-slate-400">开始对话,我会帮助您解决问题</p>
        </div>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="mb-6 flex gap-4"
        >
          <!-- Avatar -->
          <div 
            class="h-10 w-10 rounded-md flex items-center justify-center flex-shrink-0"
            :class="message.role === 'user' ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-primary/10'"
          >
            <span class="material-symbols-outlined text-sm" :class="message.role === 'user' ? 'text-blue-600 dark:text-blue-400' : 'text-primary'">
              {{ message.role === 'user' ? 'person' : 'auto_awesome' }}
            </span>
          </div>
          <!-- Message Content -->
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ message.author }}</span>
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ message.time }}</span>
              <span v-if="message.isStreaming" class="text-xs text-primary flex items-center gap-1">
                <span class="inline-block h-1 w-1 rounded-full bg-primary animate-pulse"></span>
                生成中...
              </span>
            </div>
            <div class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
              {{ message.content }}
              <span v-if="message.isStreaming" class="inline-block w-1 h-4 bg-primary animate-pulse ml-1"></span>
            </div>
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
              class="flex-1 resize-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="输入您的问题或需求..."
              rows="1"
              :disabled="isLoading"
              @keydown.enter.prevent="handleSendMessage"
            ></textarea>
            <button
              class="h-10 w-10 rounded-md bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isLoading"
              @click="handleSendMessage"
            >
              <span v-if="isLoading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span v-else class="material-symbols-outlined text-xl">send</span>
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
    </template>
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

/* 垂直文字 */
.writing-mode-vertical-rl {
  writing-mode: vertical-rl;
  text-orientation: mixed;
}
</style>
