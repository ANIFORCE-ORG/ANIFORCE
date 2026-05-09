<script setup lang="ts">
import type { Campaign } from '@/api/campaigns'

interface Props {
  campaigns?: Campaign[]
}

defineProps<Props>()
const emit = defineEmits<{
  (e: 'view', campaignId: string): void
  (e: 'toggle-status', campaign: Campaign): void
  (e: 'select', campaignId: string): void
  (e: 'add-material', campaign: Campaign): void
}>()

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    draft: '草稿',
    running: '进行中',
    review: '审核中',
    paused: '已暂停',
    completed: '已完成'
  }
  return statusMap[status] || status
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    draft: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30',
    running: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30',
    review: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30',
    paused: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30',
    completed: 'text-slate-600 bg-slate-50 dark:bg-slate-900/30'
  }
  return colors[status] || 'text-slate-600 bg-slate-50'
}

const formatMoney = (value?: number) => `$${Math.round(value || 0).toLocaleString()}`
const formatRate = (value?: number) => `${Math.round((value || 0) * 100)}%`

const getPacingText = (status?: string) => {
  const labels: Record<string, string> = {
    fast: '偏快',
    slow: '偏慢',
    normal: '正常'
  }
  return labels[status || 'normal'] || '正常'
}

const handleView = (campaignId: string) => {
  emit('view', campaignId)
}

const handleToggleStatus = (campaign: Campaign) => {
  emit('toggle-status', campaign)
}

const handleSelect = (campaignId: string) => {
  emit('select', campaignId)
}

const handleAddMaterial = (campaign: Campaign) => {
  emit('add-material', campaign)
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <tr>
          <th class="px-4 py-3 text-left">
            <input
              type="checkbox"
              class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
            />
          </th>
          <th class="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">广告名称</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">项目</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">平台</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">状态</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">预算</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">消耗/进度</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">剩余</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">安装数</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">CPI</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">ROI</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">Agent建议</th>
          <th class="px-4 py-3 text-right font-semibold text-slate-700 dark:text-slate-300">素材数</th>
          <th class="px-4 py-3 text-center font-semibold text-slate-700 dark:text-slate-300">操作</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
        <tr
          v-for="campaign in campaigns"
          :key="campaign.id"
          class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
        >
          <td class="px-4 py-3">
            <input
              type="checkbox"
              class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
              @change="handleSelect(campaign.id)"
            />
          </td>
          <td class="px-4 py-3">
            <div class="font-medium text-slate-900 dark:text-white">{{ campaign.name }}</div>
            <div v-if="campaign.external_campaign_id" class="text-xs text-blue-600 mt-1">
              ID {{ campaign.external_campaign_id }}
            </div>
            <div v-if="campaign.start_date" class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {{ campaign.start_date }} - {{ campaign.end_date || '持续' }}
            </div>
          </td>
          <td class="px-4 py-3 text-slate-700 dark:text-slate-300">{{ campaign.project_name }}</td>
          <td class="px-4 py-3">
            <span class="text-xs font-medium px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
              {{ campaign.platform }}
            </span>
          </td>
          <td class="px-4 py-3">
            <span class="text-xs font-semibold px-2 py-1 rounded" :class="getStatusColor(campaign.status)">
              {{ getStatusText(campaign.status) }}
            </span>
          </td>
          <td class="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
            {{ formatMoney(campaign.budget) }}
          </td>
          <td class="px-4 py-3 text-right">
            <div class="font-semibold text-slate-900 dark:text-white">{{ formatMoney(campaign.spent) }}</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">
              {{ formatRate(campaign.budget_usage_rate) }} · {{ getPacingText(campaign.pacing_status) }}
            </div>
          </td>
          <td class="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
            {{ formatMoney(campaign.budget_remaining) }}
          </td>
          <td class="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
            {{ campaign.installs?.toLocaleString() || 0 }}
          </td>
          <td class="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
            ${{ campaign.cpi?.toFixed(2) || '0.00' }}
          </td>
          <td class="px-4 py-3 text-right font-semibold"
            :class="campaign.roi && campaign.target_cpa && campaign.cpi && campaign.cpi <= campaign.target_cpa
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-red-600 dark:text-red-400'"
          >
            {{ campaign.roi ? `${campaign.roi.toFixed(2)}x` : '-' }}
          </td>
          <td class="px-4 py-3 max-w-[220px]">
            <div class="text-xs font-semibold text-slate-900 dark:text-white truncate">
              {{ campaign.agent_action?.label || '保持观察' }}
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400 truncate">
              {{ campaign.agent_action?.reason || '暂无动作建议' }}
            </div>
          </td>
          <td class="px-4 py-3 text-right font-semibold text-slate-900 dark:text-white">
            {{ campaign.material_ids?.length || 0 }}
          </td>
          <td class="px-4 py-3">
            <div class="flex items-center justify-center gap-2">
              <button
                class="px-3 py-1 text-xs font-medium rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                @click="handleView(campaign.id)"
              >
                详情
              </button>
              <button
                class="px-3 py-1 text-xs font-medium rounded bg-primary/10 text-primary hover:bg-primary/15 transition-colors"
                @click="handleAddMaterial(campaign)"
              >
                添加素材
              </button>
              <button
                class="px-3 py-1 text-xs font-semibold rounded transition-colors"
                :class="campaign.status === 'running'
                  ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 hover:bg-orange-100 dark:hover:bg-orange-900/30'
                  : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30'"
                @click="handleToggleStatus(campaign)"
              >
                {{ campaign.status === 'running' ? '暂停' : '启动' }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 空状态 -->
    <div v-if="!campaigns || campaigns.length === 0" class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">
        table_chart
      </span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无数据</p>
    </div>
  </div>
</template>
