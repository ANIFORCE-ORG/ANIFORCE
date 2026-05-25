<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { navItems } from '@/config/navigation'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'

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

const metrics = [
  { label: '总消耗', value: '$28,460', delta: '+12.4%', tone: 'default' },
  { label: '转化数', value: '4,832', delta: '+8.7%', tone: 'default' },
  { label: 'CPI', value: '$5.89', delta: '-6.2%', tone: 'good' },
  { label: 'ROAS', value: '2.43x', delta: '+0.18x', tone: 'good' },
]

const platformRows = [
  { name: 'Meta', spend: '$12,840', installs: '2,180', cpi: '$5.89', roas: '2.31x', trend: 68 },
  { name: 'Google', spend: '$8,620', installs: '1,426', cpi: '$6.04', roas: '2.12x', trend: 54 },
  { name: 'TikTok', spend: '$7,000', installs: '1,226', cpi: '$5.71', roas: '2.86x', trend: 78 },
]

const insights = [
  { title: '素材疲劳提醒', text: 'Meta 两组高消耗素材 CTR 连续 3 天下降，建议替换首屏钩子和前 3 秒节奏。', level: '高' },
  { title: '预算迁移建议', text: 'TikTok 近 7 天 ROAS 高于均值 17%，可从低效 Google 组迁移 10%-15% 日预算。', level: '中' },
  { title: '受众扩量机会', text: '美国 Android 18-34 人群 CPI 稳定低于账户均值，适合新增相似受众测试。', level: '中' },
]

const creativeRows = [
  { name: 'UGC_FailMoment_15s', type: '视频', ctr: '4.8%', cvr: '11.2%', roas: '3.1x' },
  { name: 'Puzzle_LevelReward_30s', type: '视频', ctr: '3.9%', cvr: '9.8%', roas: '2.6x' },
  { name: 'Character_Static_A', type: '图片', ctr: '2.7%', cvr: '7.4%', roas: '1.9x' },
]

const filteredPlatformRows = computed(() => {
  if (platform.value === 'all') return platformRows
  return platformRows.filter(row => row.name.toLowerCase() === platform.value)
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
          <h1 class="text-base font-bold text-slate-900 dark:text-white">数据报表</h1>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">汇总消耗、转化、平台对比、素材排行和策略洞察</p>
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
          <button class="inline-flex h-9 w-9 items-center justify-center rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
            <span class="material-symbols-outlined text-lg">download</span>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-7xl space-y-5">
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

          <section class="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
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
                      <th class="px-3 py-2">消耗</th>
                      <th class="px-3 py-2">转化</th>
                      <th class="px-3 py-2">CPI</th>
                      <th class="px-3 py-2">ROAS</th>
                      <th class="px-3 py-2">趋势</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-200 dark:divide-slate-800">
                    <tr v-for="row in filteredPlatformRows" :key="row.name" class="text-slate-700 dark:text-slate-300">
                      <td class="px-3 py-3 font-semibold text-slate-950 dark:text-white">{{ row.name }}</td>
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
              <h2 class="text-sm font-bold text-slate-900 dark:text-white">AI 策略洞察</h2>
              <div class="mt-4 space-y-3">
                <article
                  v-for="item in insights"
                  :key="item.title"
                  class="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div class="flex items-center justify-between gap-3">
                    <h3 class="text-sm font-semibold text-slate-900 dark:text-white">{{ item.title }}</h3>
                    <span class="whitespace-nowrap rounded bg-blue-50 px-2 py-0.5 text-xs font-semibold text-primary">置信度 {{ item.level }}</span>
                  </div>
                  <p class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-400">{{ item.text }}</p>
                  <button class="mt-3 inline-flex h-8 w-8 items-center justify-center rounded-md bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-slate-800">
                    <span class="material-symbols-outlined text-base">arrow_forward</span>
                  </button>
                </article>
              </div>
            </div>
          </section>

          <section class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="text-sm font-bold text-slate-900 dark:text-white">素材表现排行</h2>
              <span class="text-xs text-slate-500">按 ROAS 排序</span>
            </div>
            <div class="grid gap-3 lg:grid-cols-3">
              <article
                v-for="creative in creativeRows"
                :key="creative.name"
                class="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-slate-950 dark:text-white">{{ creative.name }}</p>
                    <p class="mt-1 text-xs text-slate-500">{{ creative.type }}</p>
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
