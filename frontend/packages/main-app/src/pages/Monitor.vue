<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { navItems } from '@/config/navigation'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const workspaceSessions = useWorkspaceSessions('reports')

const quickHints = [
  '分析投放效果',
  '优化建议',
  '数据对比',
  '趋势预测'
]

const timeRange = ref('7d')
const platform = ref('all')
const selectedProject = ref('all')

const trendRowsByRange = {
  '7d': [
    { date: '05-21', spend: 2840, conversions: 428, roas: 2.12 },
    { date: '05-22', spend: 3160, conversions: 506, roas: 2.24 },
    { date: '05-23', spend: 3510, conversions: 582, roas: 2.38 },
    { date: '05-24', spend: 3920, conversions: 631, roas: 2.31 },
    { date: '05-25', spend: 4310, conversions: 746, roas: 2.52 },
    { date: '05-26', spend: 5120, conversions: 891, roas: 2.64 },
    { date: '05-27', spend: 5600, conversions: 1048, roas: 2.71 },
  ],
  '30d': [
    { date: 'W1', spend: 12840, conversions: 2180, roas: 2.18 },
    { date: 'W2', spend: 15620, conversions: 2564, roas: 2.26 },
    { date: 'W3', spend: 18430, conversions: 3086, roas: 2.39 },
    { date: 'W4', spend: 22310, conversions: 3742, roas: 2.54 },
    { date: 'W5', spend: 24680, conversions: 4210, roas: 2.62 },
  ],
  '90d': [
    { date: 'Mar', spend: 42800, conversions: 7020, roas: 2.04 },
    { date: 'Apr', spend: 58700, conversions: 9860, roas: 2.28 },
    { date: 'May', spend: 81200, conversions: 13740, roas: 2.51 },
  ],
}

type TrendRange = keyof typeof trendRowsByRange

const trendRows = computed(() => trendRowsByRange[timeRange.value as TrendRange])

const totalSpend = computed(() => trendRows.value.reduce((sum, row) => sum + row.spend, 0))
const totalConversions = computed(() => trendRows.value.reduce((sum, row) => sum + row.conversions, 0))
const avgCpi = computed(() => totalSpend.value / Math.max(1, totalConversions.value))
const avgRoas = computed(() => trendRows.value.reduce((sum, row) => sum + row.roas, 0) / trendRows.value.length)

const metrics = computed(() => [
  { label: '总消耗', value: `$${totalSpend.value.toLocaleString()}`, delta: timeRange.value === '7d' ? '+12.4%' : timeRange.value === '30d' ? '+18.1%' : '+26.7%', tone: 'default' },
  { label: '转化数', value: totalConversions.value.toLocaleString(), delta: timeRange.value === '7d' ? '+8.7%' : timeRange.value === '30d' ? '+15.2%' : '+21.4%', tone: 'default' },
  { label: 'CPI', value: `$${avgCpi.value.toFixed(2)}`, delta: '-6.2%', tone: 'good' },
  { label: 'ROAS', value: `${avgRoas.value.toFixed(2)}x`, delta: '+0.18x', tone: 'good' },
])

const platformRows = [
  { name: 'Meta', project: 'Candy Blast 全球推广', account: 'Candy Blast Meta UA', campaigns: 5, spend: '$12,840', installs: '2,180', cpi: '$5.89', roas: '2.31x', trend: 68 },
  { name: 'Google', project: 'DramaBox 北美订阅转化', account: 'DramaBox Google Ads', campaigns: 3, spend: '$8,620', installs: '1,426', cpi: '$6.04', roas: '2.12x', trend: 54 },
  { name: 'TikTok', project: 'Candy Blast 全球推广', account: 'Candy Blast TikTok US', campaigns: 4, spend: '$7,000', installs: '1,226', cpi: '$5.71', roas: '2.86x', trend: 78 },
]

const insights = [
  { title: '素材疲劳提醒', text: 'Meta 两组高消耗素材 CTR 连续 3 天下降，建议替换首屏钩子和前 3 秒节奏。', level: '高' },
  { title: '预算迁移建议', text: 'TikTok 近 7 天 ROAS 高于均值 17%，可从低效 Google 组迁移 10%-15% 日预算。', level: '中' },
  { title: '受众扩量机会', text: '美国 Android 18-34 人群 CPI 稳定低于账户均值，适合新增相似受众测试。', level: '中' },
]

const creativeRows = [
  { name: 'UGC_FailMoment_15s', project: 'Candy Blast', type: '视频', ctr: '4.8%', cvr: '11.2%', roas: '3.1x' },
  { name: 'Puzzle_LevelReward_30s', project: 'Candy Blast', type: '视频', ctr: '3.9%', cvr: '9.8%', roas: '2.6x' },
  { name: 'Character_Static_A', project: 'DramaBox', type: '图片', ctr: '2.7%', cvr: '7.4%', roas: '1.9x' },
]

const projectRows = [
  { name: 'Candy Blast 全球推广', budget: '$68,000', spend: '$19,840', pacing: '29.2%', campaigns: 9, alerts: 2, roas: '2.56x' },
  { name: 'DramaBox 北美订阅转化', budget: '$92,000', spend: '$8,620', pacing: '9.4%', campaigns: 3, alerts: 1, roas: '2.12x' },
  { name: 'DTC 新品黑五预热', budget: '$45,000', spend: '$0', pacing: '0%', campaigns: 0, alerts: 0, roas: '-' },
]

const filteredPlatformRows = computed(() => {
  return platformRows.filter((row) => {
    const platformMatched = platform.value === 'all' || row.name.toLowerCase() === platform.value
    const projectMatched = selectedProject.value === 'all' || row.project === selectedProject.value
    return platformMatched && projectMatched
  })
})

const displayPlatformRows = computed(() =>
  filteredPlatformRows.value.length > 0 ? filteredPlatformRows.value : platformRows
)

const displayProjectRows = computed(() => {
  if (selectedProject.value === 'all') return projectRows
  return projectRows.filter((project) => project.name === selectedProject.value)
})

const displayCreativeRows = computed(() => {
  if (selectedProject.value === 'all') return creativeRows
  return creativeRows.filter((creative) => creative.project === selectedProject.value.split(' ')[0])
})

const trendChartOption = computed(() => {
  return {
    color: ['#2563eb', '#10b981', '#f59e0b'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f172a',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      valueFormatter: (value: number | string) => typeof value === 'number' ? value.toLocaleString() : value,
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#64748b', fontSize: 12 },
      data: ['消耗', '转化', 'ROAS'],
    },
    grid: { left: 42, right: 24, top: 48, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendRows.value.map((row) => row.date),
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: '消耗 / 转化',
        nameTextStyle: { color: '#94a3b8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#eef2f7' } },
        axisLabel: { color: '#64748b', fontSize: 11 },
      },
      {
        type: 'value',
        name: 'ROAS',
        nameTextStyle: { color: '#94a3b8', fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: '#64748b', fontSize: 11 },
      },
    ],
    series: [
      {
        name: '消耗',
        type: 'line',
        smooth: true,
        symbolSize: 7,
        lineStyle: { width: 3 },
        areaStyle: { opacity: 0.08 },
        data: trendRows.value.map((row) => row.spend),
      },
      {
        name: '转化',
        type: 'bar',
        barWidth: timeRange.value === '90d' ? 28 : 16,
        itemStyle: { borderRadius: [4, 4, 0, 0], opacity: 0.78 },
        data: trendRows.value.map((row) => row.conversions),
      },
      {
        name: 'ROAS',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        lineStyle: { width: 2 },
        data: trendRows.value.map((row) => row.roas),
      },
    ],
  }
})

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="workspaceSessions.sessions.value"
      @switch-panel="switchPanel"
      @switch-session="workspaceSessions.switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
        <div>
          <h1 class="text-base font-bold text-slate-900 dark:text-white">数据复盘</h1>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">按时间段复盘消耗、转化、平台表现、素材排行和策略洞察</p>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model="timeRange"
            class="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <option value="7d">近 7 天</option>
            <option value="30d">近 30 天</option>
            <option value="90d">近 90 天</option>
          </select>
          <select
            v-model="platform"
            class="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <option value="all">全部平台</option>
            <option value="meta">Meta</option>
            <option value="google">Google</option>
            <option value="tiktok">TikTok</option>
          </select>
          <select
            v-model="selectedProject"
            class="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <option value="all">全部项目</option>
            <option v-for="project in projectRows" :key="project.name" :value="project.name">{{ project.name }}</option>
          </select>
          <button class="inline-flex h-9 w-9 items-center justify-center rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
            <span class="material-symbols-outlined text-lg">download</span>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-7xl space-y-5">
          <div class="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-800">
            当前为前端 Demo 复盘数据，用于验证时间段、Project / Platform Account / Campaign / Material / Metrics 的展示结构。后续将替换为后端报表接口。
          </div>

          <section class="grid gap-3 md:grid-cols-4">
            <div
              v-for="metric in metrics"
              :key="metric.label"
              class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950"
            >
              <p class="text-xs font-medium text-slate-500 dark:text-slate-400">{{ metric.label }}</p>
              <div class="mt-2 flex items-end justify-between gap-3">
                <span class="text-2xl font-bold text-slate-950 dark:text-white">{{ metric.value }}</span>
                <span
                  class="whitespace-nowrap rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold dark:bg-slate-800"
                  :class="metric.tone === 'good' ? 'text-emerald-600' : 'text-slate-600 dark:text-slate-300'"
                >
                  {{ metric.delta }}
                </span>
              </div>
            </div>
          </section>

          <section class="rounded-md border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <div class="mb-5 flex items-center justify-between">
              <div>
                <h2 class="text-sm font-bold text-slate-900 dark:text-white">时间段复盘趋势</h2>
                <p class="mt-1 text-xs text-slate-500">消耗曲线和转化柱状随顶部时间段切换实时调整</p>
              </div>
              <span class="rounded bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {{ timeRange === '7d' ? '近 7 天' : timeRange === '30d' ? '近 30 天' : '近 90 天' }}
              </span>
            </div>
            <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
              <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
                <VChart class="h-72 w-full" :option="trendChartOption" autoresize />
              </div>
              <div class="grid gap-3">
                <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
                  <p class="text-xs font-semibold text-slate-500">消耗</p>
                  <p class="mt-2 text-2xl font-bold text-slate-950 dark:text-white">${{ totalSpend.toLocaleString() }}</p>
                  <p class="mt-1 text-xs text-slate-500">所选时间段总消耗</p>
                </div>
                <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
                  <p class="text-xs font-semibold text-slate-500">转化</p>
                  <p class="mt-2 text-2xl font-bold text-slate-950 dark:text-white">{{ totalConversions.toLocaleString() }}</p>
                  <p class="mt-1 text-xs text-slate-500">安装 / 注册 / 购买合计</p>
                </div>
                <div class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
                  <p class="text-xs font-semibold text-slate-500">平均 ROAS</p>
                  <p class="mt-2 text-2xl font-bold text-emerald-600">{{ avgRoas.toFixed(2) }}x</p>
                  <p class="mt-1 text-xs text-slate-500">按周期点位均值计算</p>
                </div>
              </div>
            </div>
          </section>

          <section class="space-y-5">
            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div class="mb-4 flex items-center justify-between">
                <h2 class="text-sm font-bold text-slate-900 dark:text-white">平台表现</h2>
                <span class="text-xs text-slate-500">消耗 / 转化 / 回报</span>
              </div>
              <div class="overflow-hidden rounded-md border border-slate-200 dark:border-slate-800">
                <table class="w-full text-left text-sm">
                  <thead class="bg-slate-50 text-xs font-semibold text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                    <tr>
                      <th class="px-3 py-2">平台</th>
                      <th class="px-3 py-2">账户</th>
                      <th class="px-3 py-2">Campaign</th>
                      <th class="px-3 py-2">消耗</th>
                      <th class="px-3 py-2">转化</th>
                      <th class="px-3 py-2">CPI</th>
                      <th class="px-3 py-2">ROAS</th>
                      <th class="px-3 py-2">趋势</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-200 dark:divide-slate-800">
                    <tr v-for="row in displayPlatformRows" :key="row.name" class="text-slate-700 dark:text-slate-300">
                      <td class="px-3 py-3 font-semibold text-slate-950 dark:text-white">{{ row.name }}</td>
                      <td class="px-3 py-3">{{ row.account }}</td>
                      <td class="px-3 py-3">{{ row.campaigns }}</td>
                      <td class="px-3 py-3">{{ row.spend }}</td>
                      <td class="px-3 py-3">{{ row.installs }}</td>
                      <td class="px-3 py-3">{{ row.cpi }}</td>
                      <td class="px-3 py-3 font-semibold text-emerald-600">{{ row.roas }}</td>
                      <td class="px-3 py-3">
                        <div class="h-2 w-24 rounded-full bg-slate-100 dark:bg-slate-800">
                          <div class="h-2 rounded-full bg-primary" :style="{ width: `${row.trend}%` }"></div>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div class="mb-4 flex items-center justify-between">
                <h2 class="text-sm font-bold text-slate-900 dark:text-white">AI 策略洞察</h2>
                <span class="text-xs text-slate-500">异常提醒 / 预算建议 / 受众机会</span>
              </div>
              <div class="grid gap-3 lg:grid-cols-3">
                <article
                  v-for="item in insights"
                  :key="item.title"
                  class="flex min-h-[150px] flex-col rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div class="flex items-center justify-between gap-3">
                    <h3 class="text-sm font-semibold text-slate-900 dark:text-white">{{ item.title }}</h3>
                    <span class="whitespace-nowrap rounded bg-blue-50 px-2 py-0.5 text-xs font-semibold text-primary">置信度 {{ item.level }}</span>
                  </div>
                  <p class="mt-2 flex-1 text-xs leading-5 text-slate-600 dark:text-slate-400">{{ item.text }}</p>
                  <button class="mt-3 inline-flex h-8 w-8 items-center justify-center rounded-md bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-slate-800">
                    <span class="material-symbols-outlined text-base">arrow_forward</span>
                  </button>
                </article>
              </div>
            </div>
          </section>

          <section class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 dark:text-white">项目预算与效果</h2>
              <span class="text-xs text-slate-500">Project / Campaign / Alert</span>
            </div>
            <div class="grid gap-3 lg:grid-cols-3">
              <article
                v-for="project in displayProjectRows"
                :key="project.name"
                class="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-slate-950 dark:text-white">{{ project.name }}</p>
                    <p class="mt-1 text-xs text-slate-500">Budget {{ project.budget }} · Spend {{ project.spend }}</p>
                  </div>
                  <span class="whitespace-nowrap rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {{ project.roas }}
                  </span>
                </div>
                <div class="mt-4 grid grid-cols-3 gap-2 text-xs">
                  <div class="rounded bg-white p-2 dark:bg-slate-950">
                    <p class="text-slate-500">Pacing</p>
                    <p class="mt-1 font-bold text-slate-900 dark:text-white">{{ project.pacing }}</p>
                  </div>
                  <div class="rounded bg-white p-2 dark:bg-slate-950">
                    <p class="text-slate-500">Campaign</p>
                    <p class="mt-1 font-bold text-slate-900 dark:text-white">{{ project.campaigns }}</p>
                  </div>
                  <div class="rounded bg-white p-2 dark:bg-slate-950">
                    <p class="text-slate-500">Alert</p>
                    <p class="mt-1 font-bold text-amber-600">{{ project.alerts }}</p>
                  </div>
                </div>
              </article>
            </div>
          </section>

          <section class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 dark:text-white">素材表现排行</h2>
              <span class="text-xs text-slate-500">按 ROAS 排序</span>
            </div>
            <div class="grid gap-3 lg:grid-cols-3">
              <article
                v-for="creative in displayCreativeRows"
                :key="creative.name"
                class="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-slate-950 dark:text-white">{{ creative.name }}</p>
                    <p class="mt-1 text-xs text-slate-500">{{ creative.project }} · {{ creative.type }}</p>
                  </div>
                  <span class="rounded bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-600">{{ creative.roas }}</span>
                </div>
                <div class="mt-4 grid grid-cols-2 gap-2 text-xs">
                  <div class="rounded bg-white p-2 dark:bg-slate-950">
                    <p class="text-slate-500">CTR</p>
                    <p class="mt-1 font-bold text-slate-900 dark:text-white">{{ creative.ctr }}</p>
                  </div>
                  <div class="rounded bg-white p-2 dark:bg-slate-950">
                    <p class="text-slate-500">CVR</p>
                    <p class="mt-1 font-bold text-slate-900 dark:text-white">{{ creative.cvr }}</p>
                  </div>
                </div>
              </article>
            </div>
            <div v-if="displayCreativeRows.length === 0" class="rounded-md border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500 dark:border-slate-800">
              当前筛选条件下暂无素材表现数据，后续接入 `GET /reports/materials` 后按真实数据展示。
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- 右侧对话区 -->
    <ChatPanel
      :session-id="workspaceSessions.activeSessionId.value"
      :quick-hints="quickHints"
    />
  </div>
</template>
