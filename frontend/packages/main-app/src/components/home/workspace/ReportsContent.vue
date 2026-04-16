<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProjectsStore } from '@/store/projects'
import { useCampaignsStore } from '@/store/campaigns'
import { useCreativesStore } from '@/store/creatives'

const projectsStore = useProjectsStore()
const campaignsStore = useCampaignsStore()
const creativesStore = useCreativesStore()

const timeRange = ref('weekly')
const timeRangeOptions = [
  { value: 'daily', label: '日报' },
  { value: 'weekly', label: '周报' },
  { value: 'monthly', label: '月报' }
]

// Mock insights data
const reportInsights = ref([
  {
    level: 'high',
    text: 'UGC素材CTR比品牌素材高45%，Candy Blast的UGC_FailMoment表现最佳',
    confidence: 92,
    basis: '基于16个素材样本分析'
  },
  {
    level: 'high',
    text: 'TikTok平台ROI表现最佳达2.45x，建议将更多预算从Meta迁移到TikTok',
    confidence: 88,
    basis: '基于30天投放数据'
  },
  {
    level: 'medium',
    text: 'DramaBox霸总题材CTR 7.1%远超均值，建议加大该题材素材产出',
    confidence: 82,
    basis: '基于剧情类素材对比'
  }
])

// Computed aggregated data
const aggregatedData = computed(() => {
  const campaigns = campaignsStore.campaigns
  const projects = projectsStore.projects

  let totalSpend = 0
  let totalInstalls = 0
  let totalBudget = 0
  let roiSum = 0
  let count = 0

  campaigns.forEach(c => {
    totalSpend += c.spend || 0
    totalInstalls += c.installs || 0
    roiSum += c.roi || 0
    count++
  })

  projects.forEach(p => {
    totalBudget += p.budget || 0
  })

  const avgRoi = count > 0 ? roiSum / count : 0
  const cpi = totalInstalls > 0 ? totalSpend / totalInstalls : 0
  const budgetRate = totalBudget > 0 ? (totalSpend / totalBudget) * 100 : 0

  return {
    totalSpend,
    totalInstalls,
    avgRoi,
    cpi,
    budgetRate
  }
})

// Top performing creatives
const topCreatives = computed(() => {
  return creativesStore.creatives
    .filter(c => c.status === 'running')
    .sort((a, b) => (b.roi || 0) - (a.roi || 0))
    .slice(0, 10)
})

// Platform comparison data
const platformData = computed(() => {
  const platforms: Record<string, { spend: number; installs: number; roi: number; count: number }> = {}

  campaignsStore.campaigns.forEach(c => {
    if (!platforms[c.platform]) {
      platforms[c.platform] = { spend: 0, installs: 0, roi: 0, count: 0 }
    }
    platforms[c.platform].spend += c.spend || 0
    platforms[c.platform].installs += c.installs || 0
    platforms[c.platform].roi += c.roi || 0
    platforms[c.platform].count++
  })

  return Object.entries(platforms).map(([name, data]) => ({
    name,
    spend: data.spend,
    installs: data.installs,
    avgRoi: data.count > 0 ? data.roi / data.count : 0,
    cpi: data.installs > 0 ? data.spend / data.installs : 0
  }))
})

const exportCSV = () => {
  const campaigns = campaignsStore.campaigns
  const projects = projectsStore.projects

  const header = '计划名称,所属分组,平台,状态,预算,消耗,安装数,目标CPA,实际CPI,ROI,阶段\n'
  const rows = campaigns.map(c => {
    const project = projects.find(p => p.id === c.project_id)
    const cpi = c.installs && c.installs > 0 ? (c.spend / c.installs).toFixed(2) : '-'
    const status = c.status === 'running' ? '投放中' : c.status === 'paused' ? '已暂停' : c.status === 'ended' ? '已结束' : c.status
    return [
      c.name,
      project?.name || '-',
      c.platform,
      status,
      c.budget,
      c.spend,
      c.installs,
      c.target_cpa || '-',
      cpi,
      (c.roi || 0) + 'x',
      c.pipeline_step || '-'
    ].join(',')
  }).join('\n')

  const csv = '\uFEFF' + header + rows
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ANIFORCE_Report_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await Promise.all([
    projectsStore.fetchProjects(),
    campaignsStore.fetchCampaigns(),
    creativesStore.fetchCreatives()
  ])
})
</script>

<template>
  <div class="space-y-4">
    <!-- Header with Time Range Selector -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <select
          v-model="timeRange"
          class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option v-for="option in timeRangeOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>

      <button
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
        @click="exportCSV"
      >
        <span class="material-symbols-outlined text-[16px]">download</span>
        导出
      </button>
    </div>

    <!-- Executive Summary -->
    <div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-800 p-4">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-3">执行摘要</h3>

      <!-- Stats Grid -->
      <div class="grid grid-cols-4 gap-3 mb-3">
        <div class="p-3 rounded-lg bg-white dark:bg-slate-900">
          <div class="text-xs text-slate-600 dark:text-slate-400 mb-1">总消耗</div>
          <div class="text-lg font-bold text-slate-900 dark:text-white">
            ${{ aggregatedData.totalSpend.toLocaleString() }}
          </div>
        </div>
        <div class="p-3 rounded-lg bg-white dark:bg-slate-900">
          <div class="text-xs text-slate-600 dark:text-slate-400 mb-1">总安装</div>
          <div class="text-lg font-bold text-slate-900 dark:text-white">
            {{ aggregatedData.totalInstalls.toLocaleString() }}
          </div>
        </div>
        <div class="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
          <div class="text-xs text-emerald-700 dark:text-emerald-400 mb-1">整体ROI</div>
          <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
            {{ aggregatedData.avgRoi.toFixed(2) }}x
          </div>
        </div>
        <div class="p-3 rounded-lg bg-white dark:bg-slate-900">
          <div class="text-xs text-slate-600 dark:text-slate-400 mb-1">预算完成率</div>
          <div class="text-lg font-bold text-slate-900 dark:text-white">
            {{ aggregatedData.budgetRate.toFixed(1) }}%
          </div>
        </div>
      </div>

      <!-- Key Findings -->
      <div class="space-y-2">
        <div
          v-for="(insight, index) in reportInsights"
          :key="index"
          class="flex items-start gap-2 p-2 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800"
        >
          <span class="material-symbols-outlined text-amber-600 dark:text-amber-400 text-base">lightbulb</span>
          <span class="text-xs text-amber-900 dark:text-amber-200">{{ insight.text }}</span>
        </div>
      </div>
    </div>

    <!-- Platform Comparison -->
    <div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-800 p-4">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-3">平台对比</h3>
      <div class="space-y-2">
        <div
          v-for="platform in platformData"
          :key="platform.name"
          class="flex items-center justify-between p-3 rounded-lg bg-white dark:bg-slate-900"
        >
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <span class="text-xs font-bold text-primary">{{ platform.name.charAt(0) }}</span>
            </div>
            <div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ platform.name }}</div>
              <div class="text-xs text-slate-600 dark:text-slate-400">
                消耗 ${{ platform.spend.toLocaleString() }} · 安装 {{ platform.installs.toLocaleString() }}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-xs text-slate-600 dark:text-slate-400">ROI</div>
              <div class="text-sm font-bold text-slate-900 dark:text-white">{{ platform.avgRoi.toFixed(2) }}x</div>
            </div>
            <div class="text-right">
              <div class="text-xs text-slate-600 dark:text-slate-400">CPI</div>
              <div class="text-sm font-bold text-slate-900 dark:text-white">${{ platform.cpi.toFixed(2) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Creative Ranking -->
    <div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-800 p-4">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-3">素材排行</h3>
      <div class="space-y-2">
        <div
          v-for="(creative, index) in topCreatives"
          :key="creative.id"
          class="flex items-center gap-2 p-2 rounded-lg hover:bg-white dark:hover:bg-slate-900 transition-colors"
        >
          <div
            class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
            :class="index < 3 ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'"
          >
            {{ index + 1 }}
          </div>
          <div class="w-10 h-10 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800">
            <img v-if="creative.thumb" :src="creative.thumb" :alt="creative.name" class="w-full h-full object-cover" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-slate-900 dark:text-white truncate">{{ creative.name }}</div>
            <div class="text-xs text-slate-600 dark:text-slate-400">
              CTR {{ ((creative.ctr || 0) * 100).toFixed(1) }}% · 消耗 ${{ (creative.spend || 0).toLocaleString() }}
            </div>
          </div>
          <div
            class="text-sm font-bold"
            :class="(creative.roi || 0) < 2 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'"
          >
            {{ (creative.roi || 0).toFixed(1) }}x
          </div>
        </div>
      </div>
    </div>

    <!-- Strategy Insights -->
    <div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-800 p-4">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-3">策略洞察</h3>
      <div class="space-y-2">
        <div
          v-for="(insight, index) in reportInsights"
          :key="index"
          class="p-3 rounded-lg border"
          :class="insight.level === 'high'
            ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800'
            : 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800'"
        >
          <div class="flex items-start gap-2 mb-2">
            <div
              class="px-2 py-0.5 rounded text-xs font-semibold"
              :class="insight.level === 'high'
                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'"
            >
              {{ insight.level === 'high' ? '高置信度' : '中置信度' }}
            </div>
          </div>
          <div class="text-sm text-slate-900 dark:text-white mb-1">{{ insight.text }}</div>
          <div class="text-xs text-slate-600 dark:text-slate-400">
            置信度 {{ insight.confidence }}% · {{ insight.basis }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
