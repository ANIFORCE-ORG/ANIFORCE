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
        <span class="activity-title">{{ content.title }}</span>
        <span v-if="content.toolName" class="activity-tool">{{ content.toolName }}</span>
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
}

.status-dot-completed {
  background: #10b981;
}

.status-dot-error {
  background: #ef4444;
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
