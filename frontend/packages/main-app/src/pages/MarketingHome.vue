<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    hero: {
      eyebrow: 'aniforce',
      title: '新一代 RTC 广告 AI 引擎',
      highlights: ['跨平台', '实时素材创作', '7x24盯盘', 'AI复盘归因', '可持续优化'],
      primaryCta: '马上体验',
      secondary: '连接广告账户、生成素材、创建计划、监控复盘，放在一个持续优化的投放工作台里。',
      previewTitle: '广告工作台',
      live: '实时运行',
    },
    why: {
      eyebrow: '为什么需要新的广告 AI 引擎',
      titleLines: ['从搭建一个增长团队，', '到一套可持续优化的工作流'],
    },
    capabilities: [
      {
        title: 'Real-time Creative',
        body: '实时生成、拆解和迭代广告素材，让创意测试跟上投放节奏。',
        points: ['素材拆解', '批量变体', '创意复用'],
      },
      {
        title: 'Campaign Intelligence',
        body: '统一项目、账户、素材、计划和报表上下文，辅助判断预算、素材疲劳和转化异常。',
        points: ['账户上下文', '预算异常', '素材疲劳'],
      },
      {
        title: 'Performance Loop',
        body: '把每一次投放结果沉淀为可复用的素材特征、渠道经验和复盘结论。',
        points: ['指标回流', '复盘结论', '经验沉淀'],
      },
    ],
    workflow: {
      eyebrow: '跨平台广告引擎',
      title: '智能投放策略保障广告生意效果',
      subtitle: '你把生意做好，其他事情交给aniforce',
      steps: [
        {
          title: 'Campaign Brief',
          body: '明确产品目标、受众、预算和区域。',
        },
        {
          title: 'Creative Production',
          body: '实时自动生成创意、管理和复用广告素材。',
        },
        {
          title: 'Media Execution',
          body: '统一管理跨平台账户，组织计划、素材、预算和状态。',
        },
        {
          title: 'Monitor & Performance Review',
          body: '聚合监控各项广告指标，提出下一步优化动作，并完成工作复盘。',
        },
      ],
    },
    cta: {
      eyebrow: 'aniforce',
      title: '让广告投放进入实时智能时代',
      button: '马上体验',
      body: '从第一个广告账户开始，把素材、计划和复盘结果沉淀为可持续优化的工作流。',
    },
    product: {
      demo: {
        nav: ['新任务', '项目管理', '广告投放', '创意素材', '数据概览'],
        cards: [
          { label: '消耗', value: '$28.4K', note: '节奏正常' },
          { label: 'CPA', value: '-18%', note: '持续改善' },
          { label: '素材', value: '2 条预警', note: '需要复盘' },
        ],
        performanceTitle: '跨平台投放表现',
        period: '近 7 天',
        agentTitle: 'ANIFORCE Agent',
        alertTitle: '提醒',
        alertBody: 'Meta 两条素材出现疲劳，建议替换前三秒 Hook。',
        suggestionTitle: '交互建议',
        suggestionBody: '是否生成 3 个新素材方向，并同步到测试计划？',
        inputPlaceholder: '询问 agent...',
      },
      platforms: [
        { name: 'Meta', status: '已授权', value: '3 accounts' },
        { name: 'Google', status: '待同步', value: '1 account' },
        { name: 'TikTok', status: '配置中', value: 'OAuth' },
      ],
      stages: ['Brief', 'Creative', 'Media', 'Review'],
      monitorTitle: '7x24 盯盘',
      monitorItems: ['预算消耗正常', '2 条素材疲劳预警', '转化成本下降 18%'],
      reviewTitle: 'AI 复盘归因',
      reviewBody: 'US 市场短视频素材点击率提升，建议复用前 3 秒利益点和强 CTA 结构。',
      metrics: [
        { label: 'CTR', value: '+21%' },
        { label: 'CPA', value: '-18%' },
        { label: 'ROAS', value: '1.7x' },
      ],
    },
  },
  en: {
    hero: {
      eyebrow: 'aniforce',
      title: 'The next-generation RTC advertising AI engine',
      highlights: ['Cross-platform', 'Real-time creative', '24/7 monitoring', 'AI review attribution', 'Continuous optimization'],
      primaryCta: 'Start now',
      secondary: 'Connect ad accounts, create assets, launch campaigns, monitor performance, and review results in one improving workspace.',
      previewTitle: 'Advertising workspace',
      live: 'Live',
    },
    why: {
      eyebrow: 'Why a new advertising AI engine',
      titleLines: ['From building a growth team,', 'to a continuously improving workflow'],
    },
    capabilities: [
      {
        title: 'Real-time Creative',
        body: 'Generate, deconstruct, and iterate ad creatives in real time so creative testing can keep pace with media buying.',
        points: ['Creative parsing', 'Asset variants', 'Reusable ideas'],
      },
      {
        title: 'Campaign Intelligence',
        body: 'Unify project, account, creative, campaign, and reporting context to support budget decisions, creative fatigue checks, and conversion anomaly detection.',
        points: ['Account context', 'Budget signals', 'Fatigue checks'],
      },
      {
        title: 'Performance Loop',
        body: 'Turn every campaign result into reusable creative signals, channel experience, and review conclusions.',
        points: ['Metric feedback', 'Review notes', 'Channel memory'],
      },
    ],
    workflow: {
      eyebrow: 'Cross-platform advertising engine',
      title: 'Intelligent media strategy for advertising outcomes',
      subtitle: 'You focus on the business. aniforce handles the rest.',
      steps: [
        {
          title: 'Campaign Brief',
          body: 'Define product goals, audience, budget, and regions.',
        },
        {
          title: 'Creative Production',
          body: 'Generate creatives in real time, manage assets, and reuse proven materials.',
        },
        {
          title: 'Media Execution',
          body: 'Manage cross-platform accounts, campaigns, creatives, budgets, and status in one place.',
        },
        {
          title: 'Monitor & Performance Review',
          body: 'Monitor advertising metrics, suggest the next optimization actions, and complete campaign reviews.',
        },
      ],
    },
    cta: {
      eyebrow: 'aniforce',
      title: 'Bring advertising into the RTC intelligence era',
      button: 'Start now',
      body: 'Start with the first ad account and turn assets, campaigns, and review results into a workflow that keeps improving.',
    },
    product: {
      demo: {
        nav: ['New task', 'Projects', 'Campaigns', 'Creatives', 'Overview'],
        cards: [
          { label: 'Spend', value: '$28.4K', note: 'On pace' },
          { label: 'CPA', value: '-18%', note: 'Improving' },
          { label: 'Creative', value: '2 alerts', note: 'Needs review' },
        ],
        performanceTitle: 'Cross-platform performance',
        period: 'Last 7 days',
        agentTitle: 'ANIFORCE Agent',
        alertTitle: 'Alert',
        alertBody: 'Two Meta creatives show fatigue. Replace the first-three-second hook.',
        suggestionTitle: 'Suggested action',
        suggestionBody: 'Generate 3 new creative directions and sync them to the test campaign?',
        inputPlaceholder: 'Ask agent...',
      },
      platforms: [
        { name: 'Meta', status: 'Authorized', value: '3 accounts' },
        { name: 'Google', status: 'Sync pending', value: '1 account' },
        { name: 'TikTok', status: 'Configuring', value: 'OAuth' },
      ],
      stages: ['Brief', 'Creative', 'Media', 'Review'],
      monitorTitle: '24/7 monitoring',
      monitorItems: ['Budget pacing on track', '2 creative fatigue alerts', 'CPA down 18%'],
      reviewTitle: 'AI review attribution',
      reviewBody: 'Short video assets improved CTR in the US. Reuse the first-three-second hook and stronger CTA structure.',
      metrics: [
        { label: 'CTR', value: '+21%' },
        { label: 'CPA', value: '-18%' },
        { label: 'ROAS', value: '1.7x' },
      ],
    },
  },
}

const pageCopy = computed(() => copy[language.value])
</script>

<template>
  <main class="bg-[#f5f7f4] text-slate-950">
    <section class="px-5 pb-14 pt-12 sm:px-6 lg:px-10 lg:pb-20 lg:pt-18">
      <div class="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p class="text-sm font-semibold uppercase text-emerald-700">{{ pageCopy.hero.eyebrow }}</p>
          <h1 class="mt-5 max-w-3xl text-4xl font-black leading-tight md:text-5xl lg:text-6xl">
            {{ pageCopy.hero.title }}
          </h1>
          <p class="mt-5 max-w-2xl text-base leading-8 text-slate-600 md:text-lg">
            {{ pageCopy.hero.secondary }}
          </p>
          <div class="mt-6 flex max-w-3xl flex-wrap gap-2.5">
            <span
              v-for="item in pageCopy.hero.highlights"
              :key="item"
              class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white/80 px-3.5 py-2 text-sm font-bold text-slate-800 shadow-sm"
            >
              <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
              {{ item }}
            </span>
          </div>
          <RouterLink
            to="/contact"
            class="mt-8 inline-flex items-center justify-center rounded-md bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-slate-800"
          >
            {{ pageCopy.hero.primaryCta }}
          </RouterLink>
        </div>

        <div class="overflow-hidden rounded-lg border border-slate-300 bg-[#0f172a] shadow-2xl shadow-slate-300/50">
          <div class="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full bg-red-400"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-amber-400"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </div>
            <p class="text-xs font-semibold text-slate-400">{{ pageCopy.hero.previewTitle }} · {{ pageCopy.hero.live }}</p>
          </div>

          <div class="bg-[#eaf1ff] p-3">
            <div class="grid min-h-[390px] overflow-hidden rounded-md border border-blue-100 bg-white shadow-sm lg:grid-cols-[148px_minmax(0,1fr)_250px]">
              <aside class="hidden min-w-[148px] border-r border-blue-100 bg-[#0b4a9f] p-3 text-white lg:block">
                <p class="whitespace-nowrap text-sm font-black">aniforce</p>
                <div class="mt-7 space-y-2 text-xs">
                  <div
                    v-for="(item, index) in pageCopy.product.demo.nav"
                    :key="item"
                    class="whitespace-nowrap rounded-md px-3 py-2"
                    :class="index === pageCopy.product.demo.nav.length - 1 ? 'bg-white/18 font-bold' : 'text-blue-100'"
                  >
                    {{ item }}
                  </div>
                </div>
              </aside>

              <div class="bg-[#f8fbff] p-4">
                <div class="grid gap-2 sm:grid-cols-3">
                  <div
                    v-for="(card, index) in pageCopy.product.demo.cards"
                    :key="card.label"
                    class="rounded-md border border-blue-100 bg-white p-3"
                  >
                    <p class="text-[11px] font-semibold text-slate-500">{{ card.label }}</p>
                    <p class="mt-1 whitespace-nowrap font-black text-slate-950" :class="index === 2 ? 'text-base' : 'text-lg'">
                      {{ card.value }}
                    </p>
                    <p class="mt-1 text-[11px] font-bold" :class="index === 2 ? 'text-amber-600' : 'text-emerald-600'">
                      {{ card.note }}
                    </p>
                  </div>
                </div>

                <div class="mt-4 rounded-md border border-blue-100 bg-white p-4">
                  <div class="flex items-center justify-between">
                    <p class="text-xs font-black text-slate-950">{{ pageCopy.product.demo.performanceTitle }}</p>
                    <p class="text-[11px] font-bold text-blue-600">{{ pageCopy.product.demo.period }}</p>
                  </div>
                  <div class="mt-4 space-y-3">
                    <div class="grid grid-cols-[58px_1fr_42px] items-center gap-3">
                      <span class="text-xs font-bold text-slate-700">Meta</span>
                      <span class="h-2 rounded-full bg-blue-100"><span class="block h-2 w-[78%] rounded-full bg-blue-600"></span></span>
                      <span class="text-right text-xs font-bold text-slate-700">78%</span>
                    </div>
                    <div class="grid grid-cols-[58px_1fr_42px] items-center gap-3">
                      <span class="text-xs font-bold text-slate-700">Google</span>
                      <span class="h-2 rounded-full bg-blue-100"><span class="block h-2 w-[62%] rounded-full bg-blue-500"></span></span>
                      <span class="text-right text-xs font-bold text-slate-700">62%</span>
                    </div>
                    <div class="grid grid-cols-[58px_1fr_42px] items-center gap-3">
                      <span class="text-xs font-bold text-slate-700">TikTok</span>
                      <span class="h-2 rounded-full bg-blue-100"><span class="block h-2 w-[54%] rounded-full bg-blue-400"></span></span>
                      <span class="text-right text-xs font-bold text-slate-700">54%</span>
                    </div>
                  </div>
                </div>

                <div class="mt-4 grid gap-2 sm:grid-cols-3">
                  <div
                    v-for="metric in pageCopy.product.metrics"
                    :key="metric.label"
                    class="rounded-md bg-[#0b4a9f] p-3 text-white"
                  >
                    <p class="text-[11px] font-semibold text-slate-300">{{ metric.label }}</p>
                    <p class="mt-1 whitespace-nowrap text-lg font-black">{{ metric.value }}</p>
                  </div>
                </div>
              </div>

              <aside class="border-t border-blue-100 bg-white p-3 lg:border-l lg:border-t-0">
                <div class="flex h-full flex-col rounded-md border border-blue-100 bg-[#f8fbff]">
                  <div class="border-b border-blue-100 p-3">
                    <p class="whitespace-nowrap text-xs font-black text-slate-950">{{ pageCopy.product.demo.agentTitle }}</p>
                    <p class="mt-1 whitespace-nowrap text-[11px] text-slate-500">{{ pageCopy.product.monitorTitle }}</p>
                  </div>
                  <div class="flex-1 space-y-2 p-3">
                    <div class="rounded-md bg-blue-600 px-3 py-2 text-[11px] leading-5 text-white">
                      <p class="font-bold">{{ pageCopy.product.demo.alertTitle }}</p>
                      <p class="mt-1">{{ pageCopy.product.demo.alertBody }}</p>
                    </div>
                    <div class="rounded-md border border-blue-100 bg-white px-3 py-2 text-[11px] leading-5 text-slate-700">
                      <p class="font-bold text-slate-950">{{ pageCopy.product.demo.suggestionTitle }}</p>
                      <p class="mt-1">{{ pageCopy.product.demo.suggestionBody }}</p>
                    </div>
                    <div
                      v-for="item in pageCopy.product.monitorItems"
                      :key="item"
                      class="rounded-md border border-blue-100 bg-white px-3 py-2 text-[11px] leading-5 text-slate-700"
                    >
                      {{ item }}
                    </div>
                  </div>
                  <div class="border-t border-blue-100 p-3">
                    <div class="flex items-center justify-between gap-2 rounded-full border border-blue-100 bg-white px-3 py-2 text-[11px] text-slate-400">
                      <span class="whitespace-nowrap">{{ pageCopy.product.demo.inputPlaceholder }}</span>
                      <span class="h-5 w-5 rounded-full bg-blue-600"></span>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="border-y border-slate-200 bg-white px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl">
          <p class="text-sm font-semibold uppercase text-emerald-700">{{ pageCopy.why.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-black leading-snug md:text-4xl">
            <span v-for="line in pageCopy.why.titleLines" :key="line" class="block">{{ line }}</span>
          </h2>
        </div>

        <div class="mt-10 grid gap-6 md:grid-cols-3">
          <article v-for="item in pageCopy.capabilities" :key="item.title" class="rounded-lg border border-slate-200 bg-slate-50 p-6">
            <h3 class="text-xl font-bold leading-snug">{{ item.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ item.body }}</p>
            <div class="mt-5 flex flex-wrap gap-2">
              <span
                v-for="point in item.points"
                :key="point"
                class="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700"
              >
                {{ point }}
              </span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl">
          <p class="text-sm font-semibold uppercase text-emerald-700">{{ pageCopy.workflow.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-black leading-snug md:text-4xl">
            {{ pageCopy.workflow.title }}
          </h2>
          <p class="mt-5 text-base leading-8 text-slate-600">
            {{ pageCopy.workflow.subtitle }}
          </p>
        </div>

        <div class="mt-10 grid gap-3 lg:grid-cols-4">
          <article
            v-for="(step, index) in pageCopy.workflow.steps"
            :key="step.title"
            class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs font-black text-slate-400">0{{ index + 1 }}</p>
              <span class="h-1.5 w-10 rounded-full bg-emerald-500"></span>
            </div>
            <h3 class="mt-4 text-base font-black">{{ step.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ step.body }}</p>
            <div v-if="step.title === 'Media Execution'" class="mt-4 flex flex-wrap gap-2">
              <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">Meta</span>
              <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">Google</span>
              <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">TikTok</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="border-t border-slate-200 bg-white px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="rounded-lg border border-slate-200 bg-slate-950 px-6 py-10 text-white md:px-10">
          <p class="text-sm font-semibold uppercase text-emerald-300">{{ pageCopy.cta.eyebrow }}</p>
          <h2 class="mt-3 text-3xl font-black leading-snug md:text-4xl">
            {{ pageCopy.cta.title }}
          </h2>
          <p class="mt-4 max-w-2xl text-sm leading-7 text-slate-300">{{ pageCopy.cta.body }}</p>
          <RouterLink to="/contact" class="mt-7 inline-flex items-center justify-center rounded-md bg-white px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-slate-100">
            {{ pageCopy.cta.button }}
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>
