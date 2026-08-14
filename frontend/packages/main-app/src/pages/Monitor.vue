<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const activeSession = ref('sess_m001')
const timeFilter = ref('today')
const sessions = ref([
  { id: 'sess_m001', name: '实时投放监控', active: true },
  { id: 'sess_m002', name: '成本异常诊断', active: false },
  { id: 'sess_m003', name: '素材疲劳追踪', active: false },
])

const metrics = [
  { label: '今日消耗', value: '$12,486', change: '+8.4%', icon: 'payments', tone: 'text-blue-600 bg-blue-50' },
  { label: '转化数', value: '3,842', change: '+12.1%', icon: 'task_alt', tone: 'text-emerald-600 bg-emerald-50' },
  { label: '平均 CPA', value: '$3.25', change: '-6.2%', icon: 'price_check', tone: 'text-violet-600 bg-violet-50' },
  { label: '整体 ROAS', value: '2.18x', change: '+0.24', icon: 'trending_up', tone: 'text-orange-600 bg-orange-50' },
]

const campaignRows = [
  { name: 'Meta · UGC 通关挑战', platform: 'Meta', spend: '$4,820', conversions: '1,684', cpa: '$2.86', roas: '2.46x', status: '投放中', trend: 74 },
  { name: 'Google · 高价值用户扩量', platform: 'Google', spend: '$3,940', conversions: '1,232', cpa: '$3.20', roas: '2.21x', status: '投放中', trend: 66 },
  { name: 'TikTok · 霸总短剧钩子测试', platform: 'TikTok', spend: '$2,876', conversions: '782', cpa: '$3.68', roas: '1.94x', status: '投放中', trend: 52 },
  { name: 'Meta · Boss 战老用户召回', platform: 'Meta', spend: '$850', conversions: '144', cpa: '$5.90', roas: '1.31x', status: '已暂停', trend: 28 },
]

const alerts = [
  { level: '高', title: 'Boss 战召回 CPA 超出目标 31%', detail: '建议保持暂停，并替换疲劳度 88% 的旧素材。', color: 'text-red-600 bg-red-50', icon: 'error' },
  { level: '中', title: 'TikTok 短剧素材频次接近阈值', detail: '预计 18 小时后达到疲劳线，建议提前补充 2 条反转素材。', color: 'text-amber-600 bg-amber-50', icon: 'warning' },
  { level: '机会', title: 'Meta UGC 组连续 6 小时 ROAS > 2.4', detail: '当前学习稳定，可将日预算分两次上调 15%。', color: 'text-emerald-600 bg-emerald-50', icon: 'lightbulb' },
]

const switchPanel = (item: any) => item.path && router.push(item.path)
const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(item => { item.active = item.id === session.id })
}
</script>

<template>
  <div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">
    <SidebarNav :nav-items="navItems" :sessions="sessions" @switch-panel="switchPanel" @switch-session="switchSession" />
    <main class="flex flex-1 flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">
      <div class="flex h-[58px] items-center justify-between border-b border-slate-200 bg-white px-6 dark:border-slate-800 dark:bg-slate-900">
        <div class="flex items-center gap-2"><span class="material-symbols-outlined text-xl text-primary">monitoring</span><h1 class="text-lg font-bold text-slate-900 dark:text-white">投放实时监控</h1><span class="ml-2 flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-600"><i class="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500"></i>DEMO 实时</span></div>
        <select v-model="timeFilter" class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800"><option value="today">今日</option><option value="7d">近 7 日</option><option value="30d">近 30 日</option></select>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-7xl space-y-5">
          <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <article v-for="metric in metrics" :key="metric.label" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div class="flex items-center justify-between"><span class="text-xs text-slate-500">{{ metric.label }}</span><span class="material-symbols-outlined rounded-lg p-2 text-lg" :class="metric.tone">{{ metric.icon }}</span></div><div class="mt-3 flex items-end gap-2"><strong class="text-2xl text-slate-900 dark:text-white">{{ metric.value }}</strong><span class="mb-1 text-xs font-semibold text-emerald-600">{{ metric.change }}</span></div></article>
          </section>

          <section class="grid gap-5 xl:grid-cols-[1.45fr_.55fr]">
            <div class="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <div class="border-b border-slate-100 px-5 py-4 dark:border-slate-800"><h2 class="font-semibold text-slate-900 dark:text-white">计划实时表现</h2><p class="mt-1 text-xs text-slate-500">最近刷新：刚刚</p></div>
              <div class="overflow-x-auto"><table class="w-full text-left text-xs"><thead class="bg-slate-50 text-slate-500 dark:bg-slate-800/50"><tr><th class="px-5 py-3">广告计划</th><th class="px-4 py-3">消耗</th><th class="px-4 py-3">转化</th><th class="px-4 py-3">CPA</th><th class="px-4 py-3">ROAS</th><th class="px-4 py-3">预算进度</th><th class="px-4 py-3">状态</th></tr></thead><tbody class="divide-y divide-slate-100 dark:divide-slate-800"><tr v-for="row in campaignRows" :key="row.name"><td class="px-5 py-4"><div class="font-medium text-slate-800 dark:text-slate-100">{{ row.name }}</div><div class="mt-1 text-[10px] text-slate-400">{{ row.platform }}</div></td><td class="px-4 py-4 font-medium">{{ row.spend }}</td><td class="px-4 py-4">{{ row.conversions }}</td><td class="px-4 py-4">{{ row.cpa }}</td><td class="px-4 py-4 font-semibold text-emerald-600">{{ row.roas }}</td><td class="min-w-[120px] px-4 py-4"><div class="h-1.5 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-primary" :style="{ width: `${row.trend}%` }"></div></div><div class="mt-1 text-[9px] text-slate-400">{{ row.trend }}%</div></td><td class="px-4 py-4"><span class="status-chip" :data-status="row.status === '投放中' ? 'running' : 'paused'">{{ row.status }}</span></td></tr></tbody></table></div>
            </div>

            <div class="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"><div class="flex items-center justify-between"><h2 class="font-semibold text-slate-900 dark:text-white">智能告警</h2><span class="rounded-full bg-red-50 px-2 py-1 text-[10px] font-semibold text-red-600">3 条</span></div><div class="mt-4 space-y-3"><article v-for="alert in alerts" :key="alert.title" class="rounded-lg border border-slate-100 p-3 dark:border-slate-800"><div class="flex items-start gap-2"><span class="material-symbols-outlined rounded-md p-1.5 text-base" :class="alert.color">{{ alert.icon }}</span><div><div class="text-xs font-semibold text-slate-800 dark:text-slate-100">{{ alert.title }}</div><p class="mt-1 text-[10px] leading-4 text-slate-500">{{ alert.detail }}</p><button class="mt-2 text-[10px] font-semibold text-primary">查看建议 →</button></div></div></article></div></div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>
