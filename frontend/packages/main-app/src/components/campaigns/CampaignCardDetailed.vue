<script setup lang="ts">
import { computed } from 'vue'

interface Campaign {
  id: string
  name: string
  platform: string
  account_id?: string
  status: string
  buying_type?: string
  objective?: string
  start_date?: string
  end_date?: string
}

interface Props {
  campaign: Campaign
}

interface Emits {
  (e: 'view', id: string): void
  (e: 'addCreative', id: string): void
  (e: 'edit', campaign: Campaign): void
  (e: 'delete', id: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 获取状态 chip 样式类
const getStatusChipClass = (status: string) => {
  const classes: Record<string, string> = {
    'draft': 'campaign-status--draft',
    'running': '',
    'paused': '',
    'completed': 'campaign-status--completed'
  }
  return classes[status] || 'campaign-status--completed'
}

// 获取状态显示文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'draft': '草稿',
    'running': '进行中',
    'paused': '已暂停',
    'completed': '已完成'
  }
  return texts[status] || status
}

// 格式化日期
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return dateStr
  }
}

const handleView = () => {
  emit('view', props.campaign.id)
}

const handleEdit = () => {
  emit('edit', props.campaign)
}

const handleDelete = () => {
  emit('delete', props.campaign.id)
}
</script>

<template>
  <article class="campaign-card">
    <div class="campaign-top">
      <div class="campaign-copy">
        <div class="campaign-titleline">
          <h3 class="campaign-title">{{ campaign.name }}</h3>
          <span class="status-chip campaign-status" :data-status="campaign.status" :class="getStatusChipClass(campaign.status)">
            {{ getStatusText(campaign.status) }}
          </span>
        </div>
        <p class="campaign-subtitle">
          BuyingType - {{ campaign.buying_type }} · Objective - {{ campaign.objective }}
        </p>
      </div>
      <div class="campaign-actions">
        <button class="secondary-button" @click="handleView">
          查看
        </button>
        <button class="secondary-button" @click="handleEdit">
          编辑
        </button>
        <button class="danger-button" @click="handleDelete">
          删除
        </button>
      </div>
    </div>

    <div class="campaign-meta">
      <span class="meta-tag">
        平台: {{ campaign.platform }}
      </span>
      <span v-if="campaign.account_id" class="meta-tag">
        账户: {{ campaign.account_id }}
      </span>
      <span class="meta-tag">
        生效日期: {{ formatDate(campaign.start_date) }} - {{ formatDate(campaign.end_date) }}
      </span>
    </div>
  </article>
</template>

<style scoped>
.campaign-card {
  padding: 17px;
  border: 1px solid #e5e3df;
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.campaign-card:hover {
  border-color: #c8c4be;
  box-shadow: rgba(15, 15, 15, 0.04) 0 1px 2px;
}

.campaign-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.campaign-copy {
  min-width: 0;
  flex: 1;
}

.campaign-titleline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.campaign-title {
  margin: 0;
  color: #1a1a1a;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.2px;
}

.campaign-status {
  min-height: 22px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 9px;
  font-weight: 600;
}

.campaign-status--draft {
  background: #fff3d6;
  color: #805700;
}

.campaign-status--draft::before {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #b7791f;
  content: '';
}

.campaign-status--completed {
  background: #f6f5f4;
  color: #5d5b54;
}

.campaign-subtitle {
  margin: 8px 0 0;
  color: #5d5b54;
  font-size: 11px;
  line-height: 1.45;
}

.campaign-actions {
  display: flex;
  gap: 7px;
}

.secondary-button,
.danger-button {
  min-width: 74px;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 13px;
  border-radius: 8px;
  background: #fff;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}

.secondary-button {
  border: 1px solid #c8c4be;
  color: #37352f;
}

.secondary-button:hover {
  border-color: #37352f;
  color: #1a1a1a;
}

.danger-button {
  border: 1px solid #e8b8b5;
  color: #c93c37;
}

.danger-button:hover {
  border-color: #c93c37;
  background: #fbefee;
}

.campaign-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.meta-tag {
  padding: 4px 8px;
  border-radius: 6px;
  background: #f6f5f4;
  color: #5d5b54;
  font-size: 9px;
  font-weight: 500;
}

@media (max-width: 760px) {
  .campaign-top {
    flex-direction: column;
  }

  .campaign-actions {
    width: 100%;
  }

  .campaign-actions button {
    flex: 1;
  }
}

@media (max-width: 520px) {
  .campaign-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .campaign-actions .danger-button {
    grid-column: 1 / -1;
  }
}
</style>
