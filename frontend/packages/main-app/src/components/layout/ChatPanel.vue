<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { agentService } from '@/services/agentService'
import type { AGUIEventHandlers } from '@/services/agentService'
import { agentConfig } from '@/config/agent'
import type {
  EnhancedMessage,
  ExecutionPlan,
  ToolCall,
  HITLConfirmationRequest,
} from '@/types/agui'
import PlanView from '@/components/agent/PlanView.vue'
import ToolCallView from '@/components/agent/ToolCallView.vue'
import HITLDialog from '@/components/agent/HITLDialog.vue'

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
const messages = ref<EnhancedMessage[]>([])
const isLoading = ref(false)
const currentSessionId = ref(props.sessionId || '')
const messagesContainer = ref<HTMLElement | null>(null)

// AG-UI 状态
const currentPlan = ref<ExecutionPlan | null>(null)
const activeTool = ref<ToolCall | null>(null)
const hitlRequest = ref<HITLConfirmationRequest | null>(null)
const showHITLDialog = ref(false)

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
      id: msg.id,
      role: msg.role,
      author: msg.role === 'user' ? '用户' : 'AI助手',
      time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : getCurrentTime(),
      content: msg.content,
      type: 'text' as const,
    }))
    scrollToBottom()
  } catch (error) {
    console.log('会话历史加载失败或会话不存在,开始新会话')
    messages.value = []
  }
}

// 发送消息 - 使用 AG-UI 协议
const handleSendMessage = async () => {
  if (!localChatInput.value.trim() || isLoading.value) return

  const userMessage = localChatInput.value.trim()
  localChatInput.value = ''

  // 添加用户消息
  const userMsgId = `msg_user_${Date.now()}`
  messages.value.push({
    id: userMsgId,
    role: 'user',
    author: '用户',
    time: getCurrentTime(),
    content: userMessage,
    type: 'text',
  })
  scrollToBottom()

  // 添加AI消息占位符
  const aiMessageIndex = messages.value.length
  const aiMsgId = `msg_ai_${Date.now()}`
  messages.value.push({
    id: aiMsgId,
    role: 'assistant',
    author: 'AI助手',
    time: getCurrentTime(),
    content: '',
    type: 'text',
    isStreaming: true,
  })

  isLoading.value = true
  currentPlan.value = null
  activeTool.value = null

  try {
    if (!currentSessionId.value) {
      const session = await agentService.createChatSession(userMessage.slice(0, 30) || '新对话')
      currentSessionId.value = session.id
      emit('session-change', session.id)
    }

    // 定义 AG-UI 事件处理器
    const handlers: AGUIEventHandlers = {
      onTextMessage: (content: string) => {
        messages.value[aiMessageIndex].content += content
        scrollToBottom()
      },

      onMessageCompleted: (content: string) => {
        if (content) {
          messages.value[aiMessageIndex].content = content
        }
        messages.value[aiMessageIndex].isStreaming = false
        scrollToBottom()
      },

      onToolCall: (tool: ToolCall) => {
        // 更新或创建 Tool Call 消息
        const existingToolMsg = messages.value.find(
          (m) => m.type === 'tool_call' && m.metadata?.tool?.tool_name === tool.tool_name
        )

        if (existingToolMsg && existingToolMsg.metadata?.tool) {
          // 更新现有工具调用
          Object.assign(existingToolMsg.metadata.tool, tool)
        } else {
          // 创建新的工具调用消息
          messages.value.splice(aiMessageIndex, 0, {
            id: `msg_tool_${Date.now()}`,
            role: 'assistant',
            author: 'AI助手',
            time: getCurrentTime(),
            content: `正在调用工具：${tool.tool_name}`,
            type: 'tool_call',
            metadata: { tool },
          })
        }
        activeTool.value = tool
        scrollToBottom()
      },

      onPlanCreated: (plan: ExecutionPlan) => {
        currentPlan.value = plan
        
        // 在消息流中插入 Plan
        messages.value.splice(aiMessageIndex, 0, {
          id: `msg_plan_${Date.now()}`,
          role: 'assistant',
          author: 'AI助手',
          time: getCurrentTime(),
          content: '已创建执行计划',
          type: 'plan',
          metadata: { plan },
        })
        scrollToBottom()
      },

      onTodoUpdated: (todoId: string, status: string) => {
        if (currentPlan.value) {
          const todo = currentPlan.value.todos.find((t) => t.id === todoId)
          if (todo) {
            todo.status = status as any
          }
        }
      },

      onHITLRequest: (request: HITLConfirmationRequest) => {
        hitlRequest.value = request
        showHITLDialog.value = true
        
        // 暂停流式输出
        messages.value[aiMessageIndex].isStreaming = false
      },

      onError: (error: any) => {
        console.error('AG-UI 错误:', error)
        messages.value[aiMessageIndex].content = `抱歉，出现错误：${error.message || '未知错误'}`
        messages.value[aiMessageIndex].isStreaming = false
        messages.value[aiMessageIndex].type = 'error'
      },
    }

    // 使用 AG-UI 增强的流式对话
    for await (const event of agentService.streamChatWithHandlers(
      currentSessionId.value,
      userMessage,
      handlers
    )) {
      // 事件已由 handlers 处理
    }
    
    scrollToBottom()
  } catch (error: any) {
    console.error('对话失败:', error)
    messages.value[aiMessageIndex].content = '抱歉,对话出现错误,请稍后重试。'
    messages.value[aiMessageIndex].isStreaming = false
    messages.value[aiMessageIndex].type = 'error'
  } finally {
    isLoading.value = false
  }
}

// HITL 确认处理
const handleHITLConfirm = async (feedback?: string) => {
  if (!hitlRequest.value) return
  
  try {
    await agentService.sendHITLResponse(
      currentSessionId.value,
      hitlRequest.value.request_id,
      true,
      feedback
    )
    showHITLDialog.value = false
    hitlRequest.value = null
    
    // 继续对话流
    // TODO: 恢复流式输出
  } catch (error) {
    console.error('HITL 确认失败:', error)
  }
}

const handleHITLCancel = async (feedback?: string) => {
  if (!hitlRequest.value) return
  
  try {
    await agentService.sendHITLResponse(
      currentSessionId.value,
      hitlRequest.value.request_id,
      false,
      feedback
    )
    showHITLDialog.value = false
    hitlRequest.value = null
    
    // 添加取消消息
    messages.value.push({
      id: `msg_cancel_${Date.now()}`,
      role: 'assistant',
      author: 'AI助手',
      time: getCurrentTime(),
      content: '操作已取消。',
      type: 'text',
    })
  } catch (error) {
    console.error('HITL 取消失败:', error)
  }
}

const handleHITLClose = () => {
  showHITLDialog.value = false
}

// 快捷提示点击
const handleHintClick = (hint: string) => {
  localChatInput.value = hint
}

// 创建新对话
const handleNewChat = () => {
  currentSessionId.value = ''
  messages.value = []
  emit('session-change', '')
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
    :class="isCollapsed ? 'w-[50px]' : 'w-[300px]'"
  >
    <!-- Collapsed State - Vertical Expand Button -->
    <div v-if="isCollapsed" class="flex-1 flex items-center justify-center">
      <button
        class="writing-mode-vertical-rl p-[12px] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors rounded-lg flex items-center gap-[6px]"
        @click="toggleCollapse"
      >
        <span class="material-symbols-outlined text-[17px] text-slate-600 dark:text-slate-400 rotate-180">chevron_left</span>
        <span class="text-[11px] font-medium text-slate-600 dark:text-slate-400">AI助手</span>
      </button>
    </div>

    <!-- Expanded State -->
    <template v-else>
      <!-- Chat Header -->
      <div class="h-[50px] bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[19px]">
        <div class="flex items-center gap-[6px]">
          <span class="material-symbols-outlined text-[17px] text-primary">chat</span>
          <span class="font-semibold text-[13px] text-slate-900 dark:text-white">AI智能助手</span>
        </div>
        <div class="flex items-center gap-[6px]">
          <!-- 创建新对话按钮暂时屏蔽
          <button 
            class="h-9 w-9 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="handleNewChat"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">add</span>
          </button>
          -->
          <button 
            class="h-[28px] w-[28px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="toggleCollapse"
          >
            <span class="material-symbols-outlined text-[17px] text-slate-600 dark:text-slate-400">chevron_right</span>
          </button>
        </div>
      </div>

      <!-- Chat Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-[19px]">
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
          <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">chat</span>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">开始对话,我会帮助您解决问题</p>
        </div>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="mb-[19px] flex gap-[12px]"
        >
          <!-- Avatar -->
          <div 
            class="h-[31px] w-[31px] rounded-md flex items-center justify-center flex-shrink-0"
            :class="message.role === 'user' ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-primary/10'"
          >
            <span class="material-symbols-outlined text-[11px]" :class="message.role === 'user' ? 'text-blue-600 dark:text-blue-400' : 'text-primary'">
              {{ message.role === 'user' ? 'person' : 'auto_awesome' }}
            </span>
          </div>
          <!-- Message Content -->
          <div class="flex-1">
            <div class="flex items-center gap-[6px] mb-[6px]">
              <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ message.author }}</span>
              <span class="text-[10px] text-slate-500 dark:text-slate-400">{{ message.time }}</span>
              <span v-if="message.isStreaming" class="text-[10px] text-primary flex items-center gap-[4px]">
                <span class="inline-block h-[3px] w-[3px] rounded-full bg-primary animate-pulse"></span>
                生成中...
              </span>
            </div>
            <!-- 消息内容 - 根据类型渲染 -->
            <div class="space-y-2">
              <!-- 文本消息 -->
              <div v-if="message.type === 'text'" class="text-[11px] text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
                {{ message.content }}
                <span v-if="message.isStreaming" class="inline-block w-[3px] h-[12px] bg-primary animate-pulse ml-[4px]"></span>
              </div>

              <!-- 执行计划 -->
              <PlanView v-if="message.type === 'plan' && message.metadata?.plan" :plan="message.metadata.plan" />

              <!-- 工具调用 -->
              <ToolCallView v-if="message.type === 'tool_call' && message.metadata?.tool" :tool="message.metadata.tool" />

              <!-- 错误消息 -->
              <div v-if="message.type === 'error'" class="text-[11px] text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-2">
                ⚠️ {{ message.content }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Chat Input Area -->
      <div class="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-[12px]">
        <div class="space-y-[9px]">
          <!-- Input Wrapper -->
          <div class="flex items-end gap-[9px]">
            <textarea
              v-model="localChatInput"
              class="flex-1 resize-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-[12px] py-[9px] text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="输入您的问题或需求..."
              rows="1"
              :disabled="isLoading"
              @keydown.enter.prevent="handleSendMessage"
            ></textarea>
            <button
              class="h-[31px] w-[31px] rounded-md bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isLoading"
              @click="handleSendMessage"
            >
              <span v-if="isLoading" class="h-[16px] w-[16px] border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span v-else class="material-symbols-outlined text-[17px]">send</span>
            </button>
          </div>
          <!-- Quick Hints -->
          <div v-if="quickHints.length > 0" class="flex items-center gap-[6px] flex-wrap">
            <span class="text-[10px] text-slate-500 dark:text-slate-400">试试：</span>
            <button
              v-for="hint in quickHints"
              :key="hint"
              class="text-[10px] px-[9px] py-[4px] rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              @click="handleHintClick(hint)"
            >
              {{ hint }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- HITL 确认对话框 -->
    <HITLDialog
      v-if="hitlRequest"
      :request="hitlRequest"
      :visible="showHITLDialog"
      @confirm="handleHITLConfirm"
      @cancel="handleHITLCancel"
      @close="handleHITLClose"
    />
  </aside>
</template>

<style scoped>
/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 3px;
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
