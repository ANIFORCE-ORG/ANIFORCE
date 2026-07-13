<script setup lang="ts">
import { computed } from 'vue'

interface ActivityContent {
  activityType?: string
  toolName: string
  status: 'running' | 'completed' | 'error'
  title: string
  arguments?: Record<string, unknown>
}

const props = defineProps<{
  content: ActivityContent
}>()

const statusDotClass = computed(() => {
  if (props.content.status === 'completed') return 'status-dot-completed'
  if (props.content.status === 'error') return 'status-dot-error'
  return 'status-dot-running'
})

const businessTitle = computed(() => {
  const toolName = props.content.toolName || ''
  if (toolName === 'load_business_skill') return props.content.status === 'completed' ? '已选择合适的处理方式' : '正在选择处理方式'
  if (toolName === 'update_business_skill_state') return props.content.status === 'completed' ? '任务信息已更新' : '正在整理任务信息'
  if (toolName === 'request_workspace_projection') return props.content.status === 'completed' ? '结果已展示到工作台' : '正在整理工作台结果'
  const isWrite = /^(create_|update_|delete_|add_|remove_)/.test(toolName)
  if (props.content.status === 'error') return isWrite ? '业务操作失败' : '业务数据查询失败'
  if (props.content.status === 'completed') return isWrite ? '业务操作已完成' : '业务数据已获取'
  return isWrite ? '正在执行业务操作' : '正在查询业务数据'
})

const durationText = computed(() => {
  // 可以后续从 props 传入实际耗时
  if (props.content.status === 'running') return '...'
  return ''
})
</script>

<template>
  <div class="activity-card">
    <div class="activity-content">
      <!-- 状态圆点（8px） -->
      <div class="status-dot" :class="statusDotClass"></div>

      <!-- 工具信息 -->
      <div class="flex-1 min-w-0">
        <span class="activity-title">{{ businessTitle }}</span>
      </div>

      <!-- 耗时/状态 -->
      <span class="activity-duration">{{ durationText }}</span>
    </div>
  </div>
</template>

<style scoped>
.activity-card {
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 1rem;
  transition: border-color 0.16s ease;
  margin: 8px 0;
}

.activity-card:hover {
  border-color: rgba(19, 127, 236, 0.3);
}

.activity-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 状态圆点 - 8px，扁平设计 */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot-running {
  background: #137fec;
  animation: pulse-dot 2s ease-in-out infinite;
}

.status-dot-completed {
  background: #10b981;
}

.status-dot-error {
  background: #ef4444;
}

/* 柔和的脉动动画（只有圆点动） */
@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.activity-title {
  font-size: 14px;
  font-weight: 500;
  color: #0f172a;
}

.activity-tool {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 8px;
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
}

.activity-duration {
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}

/* Dark mode */
.dark .activity-card {
  background: rgba(30, 41, 59, 0.5);
  border-color: #334155;
}

.dark .activity-card:hover {
  border-color: rgba(59, 130, 246, 0.5);
}

.dark .activity-title {
  color: #f8fafc;
}

.dark .activity-tool,
.dark .activity-duration {
  color: #cbd5e1;
}
</style>
