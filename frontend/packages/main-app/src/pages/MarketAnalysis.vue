<script setup lang="ts">
const summaryCards = [
  { label: '市场热度指数', value: '86.4', change: '+12.8%', icon: 'local_fire_department', tone: 'text-orange-500 bg-orange-50' },
  { label: '预估市场规模', value: '$2.48B', change: '+18.2%', icon: 'public', tone: 'text-blue-600 bg-blue-50' },
  { label: '平均素材 CTR', value: '2.73%', change: '+0.41%', icon: 'ads_click', tone: 'text-emerald-600 bg-emerald-50' },
  { label: '活跃竞品', value: '148', change: '+16', icon: 'groups', tone: 'text-violet-600 bg-violet-50' },
]

const trends = [
  { rank: 1, name: '失败一步 / 差一点通关', category: '休闲游戏', growth: 68, heat: 94, tags: ['挑战', '反差', '高互动'] },
  { rank: 2, name: '豪门身份反转', category: '短剧应用', growth: 54, heat: 88, tags: ['情绪冲突', '悬念'] },
  { rank: 3, name: 'AI 前后效果对比', category: '工具应用', growth: 47, heat: 82, tags: ['功能展示', '强视觉'] },
  { rank: 4, name: 'Boss 狂暴阶段实录', category: 'RPG', growth: 35, heat: 76, tags: ['高光', '召回'] },
]

const opportunities = [
  { market: '美国', channel: 'Meta', audience: '女性 25–44', cpi: '$2.86', roas: '2.31x', level: '优先扩量' },
  { market: '日本', channel: 'TikTok', audience: '女性 18–34', cpi: '$3.12', roas: '2.08x', level: '继续测试' },
  { market: '韩国', channel: 'Google', audience: '全性别 18–34', cpi: '$2.44', roas: '1.92x', level: '控制成本' },
  { market: '加拿大', channel: 'Meta', audience: '全性别 25–44', cpi: '$2.69', roas: '2.18x', level: '小步扩量' },
]
</script>

<template>
  <main class="flex-1 bg-slate-50 px-6 py-8 dark:bg-slate-950 md:px-10">
    <div class="mx-auto max-w-7xl space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-3xl text-primary">trending_up</span>
            <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">市场分析</h1>
            <span class="rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold text-blue-600">DEMO 数据</span>
          </div>
          <p class="mt-2 text-sm text-slate-500">聚合热门题材、渠道基准和市场扩量机会</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900">数据周期：近 30 日</div>
      </div>

      <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article v-for="card in summaryCards" :key="card.label" class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-500">{{ card.label }}</span>
            <span class="material-symbols-outlined rounded-lg p-2 text-lg" :class="card.tone">{{ card.icon }}</span>
          </div>
          <div class="mt-4 flex items-end gap-2"><strong class="text-2xl text-slate-900 dark:text-white">{{ card.value }}</strong><span class="mb-1 text-xs font-semibold text-emerald-600">{{ card.change }}</span></div>
        </article>
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.1fr_.9fr]">
        <div class="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div class="border-b border-slate-100 px-5 py-4 dark:border-slate-800"><h2 class="font-semibold text-slate-900 dark:text-white">热门创意趋势</h2><p class="mt-1 text-xs text-slate-500">按增长速度与互动热度综合排序</p></div>
          <div class="divide-y divide-slate-100 dark:divide-slate-800">
            <div v-for="trend in trends" :key="trend.rank" class="grid grid-cols-[34px_1fr_90px] items-center gap-3 px-5 py-4">
              <span class="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">{{ trend.rank }}</span>
              <div><div class="font-medium text-slate-800 dark:text-slate-100">{{ trend.name }}</div><div class="mt-1 flex flex-wrap gap-1.5"><span class="text-[10px] text-slate-400">{{ trend.category }}</span><span v-for="tag in trend.tags" :key="tag" class="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] text-slate-500">{{ tag }}</span></div></div>
              <div class="text-right"><div class="text-sm font-bold text-emerald-600">+{{ trend.growth }}%</div><div class="mt-1 text-[10px] text-slate-400">热度 {{ trend.heat }}</div></div>
            </div>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <h2 class="font-semibold text-slate-900 dark:text-white">AI 市场洞察</h2>
          <div class="mt-4 space-y-3">
            <div class="rounded-lg bg-blue-50 p-4 dark:bg-blue-950/30"><div class="flex items-center gap-2 text-sm font-semibold text-blue-700"><span class="material-symbols-outlined text-lg">auto_awesome</span>创意机会</div><p class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">“差一步通关”题材近 7 日增长最快，建议为 Candy Match 扩展 3–5 个不同失败节点的 UGC 变体。</p></div>
            <div class="rounded-lg bg-emerald-50 p-4 dark:bg-emerald-950/30"><div class="flex items-center gap-2 text-sm font-semibold text-emerald-700"><span class="material-symbols-outlined text-lg">rocket_launch</span>渠道机会</div><p class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">美国 Meta 女性 25–44 人群回收最佳，可在当前预算基础上分两次各提升 15%。</p></div>
            <div class="rounded-lg bg-amber-50 p-4 dark:bg-amber-950/30"><div class="flex items-center gap-2 text-sm font-semibold text-amber-700"><span class="material-symbols-outlined text-lg">warning</span>竞争预警</div><p class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">日韩短剧素材密度持续上升，建议缩短素材测试窗口并提高首日淘汰率。</p></div>
          </div>
        </div>
      </section>

      <section class="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div class="border-b border-slate-100 px-5 py-4 dark:border-slate-800"><h2 class="font-semibold text-slate-900 dark:text-white">市场与渠道机会</h2></div>
        <div class="overflow-x-auto"><table class="w-full text-left text-xs"><thead class="bg-slate-50 text-slate-500 dark:bg-slate-800/50"><tr><th class="px-5 py-3">市场</th><th class="px-5 py-3">渠道</th><th class="px-5 py-3">核心人群</th><th class="px-5 py-3">基准 CPI</th><th class="px-5 py-3">预估 ROAS</th><th class="px-5 py-3">建议</th></tr></thead><tbody class="divide-y divide-slate-100 dark:divide-slate-800"><tr v-for="item in opportunities" :key="`${item.market}-${item.channel}`"><td class="px-5 py-3 font-medium text-slate-800 dark:text-slate-100">{{ item.market }}</td><td class="px-5 py-3">{{ item.channel }}</td><td class="px-5 py-3">{{ item.audience }}</td><td class="px-5 py-3">{{ item.cpi }}</td><td class="px-5 py-3 font-semibold text-emerald-600">{{ item.roas }}</td><td class="px-5 py-3"><span class="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-medium text-blue-600">{{ item.level }}</span></td></tr></tbody></table></div>
      </section>
    </div>
  </main>
</template>
