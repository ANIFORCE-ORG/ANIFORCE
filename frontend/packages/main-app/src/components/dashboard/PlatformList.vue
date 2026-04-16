<script setup lang="ts">
import { computed } from 'vue'

interface Platform {
  name: string
  spend: number
  installs: number
  roi: number
  color: string
  icon: string
}

interface Props {
  campaigns?: any[]
}

const props = defineProps<Props>()

// 平台配置
const platformConfig: Record<string, { color: string; icon: string; label: string }> = {
  Meta: { color: 'bg-blue-500', icon: 'M', label: 'Meta Ads' },
  Google: { color: 'bg-red-500', icon: 'G', label: 'Google Ads' },
  TikTok: { color: 'bg-slate-900 dark:bg-white', icon: 'T', label: 'TikTok Ads' }
}

// 计算平台数据
const platforms = computed<Platform[]>(() => {
  if (!props.campaigns || props.campaigns.length === 0) {
    return []
  }

  const platformMap: Record<string, { spend: number; installs: number; roiSum: number; count: number }> = {}

  // 聚合数据（只统计运行中的广告）
  props.campaigns
    .filter(c => c.status === 'running')
    .forEach(c => {
      if (!platformMap[c.platform]) {
        platformMap[c.platform] = { spend: 0, installs: 0, roiSum: 0, count: 0 }
      }
      platformMap[c.platform].spend += c.spent || 0
      platformMap[c.platform].installs += c.installs || 0
      platformMap[c.platform].roiSum += c.roi || 0
      platformMap[c.platform].count++
    })

  // 转换为数组
  return Object.entries(platformMap).map(([name, data]) => ({
    name,
    spend: data.spend,
    installs: data.installs,
    roi: data.count > 0 ? data.roiSum / data.count : 0,
    color: platformConfig[name]?.color || 'bg-slate-500',
    icon: platformConfig[name]?.icon || name[0]
  }))
})

// 获取平台标签
const getPlatformLabel = (name: string): string => {
  return platformConfig[name]?.label || `${name} Ads`
}
</script>

<template>
  <div class="space-y-3">
    <div
      v-for="platform in platforms"
      :key="platform.name"
      class="flex items-center gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
    >
      <!-- 平台图标 -->
      <div
        class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
        :class="platform.color"
      >
        {{ platform.icon }}
      </div>

      <!-- 平台信息 -->
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-slate-900 dark:text-white mb-1">
          {{ getPlatformLabel(platform.name) }}
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400">
          ${{ platform.spend.toLocaleString() }} · {{ platform.installs.toLocaleString() }} 安装
        </div>
      </div>

      <!-- ROI -->
      <div class="text-right flex-shrink-0">
        <div class="text-lg font-bold text-slate-900 dark:text-white">
          {{ platform.roi.toFixed(1) }}x
        </div>
        <div class="text-xs text-slate-400">ROI</div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="platforms.length === 0" class="text-center py-8">
      <span class="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-700 mb-2">
        ads_click
      </span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无平台数据</p>
    </div>
  </div>
</template>
