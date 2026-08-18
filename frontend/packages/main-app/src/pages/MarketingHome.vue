<script setup lang="ts">
import { computed } from 'vue'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    hero: {
      eyebrow: '新一代 RTC 广告 AI 引擎',
      title: '智能营销，自动增长',
      highlights: ['实时素材创作', '7x24盯盘', 'AI复盘归因', '可持续优化'],
      primaryCta: '免费体验',
      secondaryCta: '产品功能',
      secondary: 'ANIFORCE 利用 AI 技术自动规划、执行和优化广告投放策略。从策略制定到创意生成，从预算分配到效果监控，让增长变得简单高效。',
      previewTitle: '广告工作台',
      live: '实时运行',
      optimization: {
        title: 'AI 优化建议',
        items: [
          { label: '转移预算至高转化素材', value: '+12%' },
          { label: '降低冷启动计划出价', value: '-8%' },
          { label: '新增相似用户包', value: 'Ready' },
        ],
      },
    },
    featureSection: {
      title: '强大的功能特性',
      subtitle: 'AI驱动的全流程营销自动化，覆盖分析、生产、投放与监控。',
      items: [
        { icon: 'auto_awesome', title: 'AI智能优化', body: '自动分析投放数据，实时优化广告策略，帮助团队提升预算使用效率和整体 ROI。' },
        { icon: 'trending_up', title: '数据驱动增长', body: '深度洞察市场趋势，精准定位目标用户，加速业务增长并降低试错成本。' },
        { icon: 'psychology', title: '创意生成', body: 'AI辅助创意素材生成，快速产出高质量广告内容，并根据表现进行持续迭代。' },
        { icon: 'speed', title: '自动化投放', body: '一键启动广告投放，自动调整预算和出价策略，让执行链路更轻、更稳。' },
      ],
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
      button: '免费体验',
      body: '从第一个广告账户开始，把素材、计划和复盘结果沉淀为可持续优化的工作流。',
    },
    contact: {
      eyebrow: '免费体验',
      title: '让你的投放团队先少开 5 个后台。',
      body: '留下联系方式，ANIFORCE将为你升级现有的广告投放流程。',
      contactNote: '公司与产品咨询：support@aniforce.cc',
      marks: [
        { value: '30 min', label: '快速梳理投放流程' },
        { value: 'API', label: '确认渠道字段与权限' },
        { value: 'Demo', label: '按团队角色演示闭环' },
      ],
      fields: {
        name: '姓名',
        namePlaceholder: '你的称呼',
        company: '公司 / 团队',
        companyPlaceholder: '增长团队名称',
        contact: '联系方式',
        contactPlaceholder: '邮箱或微信',
        submit: '提交体验需求',
      },
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
      eyebrow: 'The next-generation RTC advertising AI engine',
      title: 'Intelligent marketing, automatic growth',
      highlights: ['Real-time creative', '24/7 monitoring', 'AI review attribution', 'Continuous optimization'],
      primaryCta: 'Free trial',
      secondaryCta: 'Product',
      secondary: 'ANIFORCE uses AI to plan, execute, and optimize advertising strategies. From strategy and creative generation to budget allocation and performance monitoring, growth becomes simpler and more efficient.',
      previewTitle: 'Advertising workspace',
      live: 'Live',
      optimization: {
        title: 'AI optimization',
        items: [
          { label: 'Move budget to high-converting creatives', value: '+12%' },
          { label: 'Lower bids for cold-start campaigns', value: '-8%' },
          { label: 'Add lookalike audiences', value: 'Ready' },
        ],
      },
    },
    featureSection: {
      title: 'Powerful product features',
      subtitle: 'AI-driven marketing automation across analysis, creative production, media execution, and monitoring.',
      items: [
        { icon: 'auto_awesome', title: 'AI optimization', body: 'Analyze delivery data and improve advertising strategies in real time to increase budget efficiency and ROI.' },
        { icon: 'trending_up', title: 'Data-driven growth', body: 'Identify market trends and target audiences more precisely to accelerate growth and reduce testing costs.' },
        { icon: 'psychology', title: 'Creative generation', body: 'Produce quality advertising assets quickly with AI and continuously iterate based on performance.' },
        { icon: 'speed', title: 'Automated delivery', body: 'Launch campaigns quickly and continuously adjust budgets and bid strategies with less manual work.' },
      ],
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
      button: 'Free trial',
      body: 'Start with the first ad account and turn assets, campaigns, and review results into a workflow that keeps improving.',
    },
    contact: {
      eyebrow: 'Free trial',
      title: 'Let your media team open 5 fewer dashboards.',
      body: 'Leave your contact information. ANIFORCE will upgrade your existing advertising workflow.',
      contactNote: 'Company and product inquiries: support@aniforce.cc',
      marks: [
        { value: '30 min', label: 'Map your media workflow' },
        { value: 'API', label: 'Review channel fields and access' },
        { value: 'Demo', label: 'Demo by team role' },
      ],
      fields: {
        name: 'Name',
        namePlaceholder: 'Your name',
        company: 'Company / Team',
        companyPlaceholder: 'Growth team name',
        contact: 'Contact',
        contactPlaceholder: 'Email or WeChat',
        submit: 'Submit request',
      },
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
  <main class="bg-background-light text-slate-950">
    <section id="top" class="relative isolate overflow-hidden border-b border-slate-200 bg-white px-5 pb-14 pt-12 sm:px-6 lg:px-10 lg:pb-18 lg:pt-16">
      <div class="signal-field" aria-hidden="true">
        <span v-for="index in 28" :key="index" class="signal-dot"></span>
      </div>
      <div class="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p class="inline-flex rounded-md bg-primary/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-primary">{{ pageCopy.hero.eyebrow }}</p>
          <h1 class="mt-5 max-w-3xl text-4xl font-bold leading-tight tracking-tight md:text-5xl lg:text-[56px]">
            {{ pageCopy.hero.title }}
          </h1>
          <p class="mt-5 max-w-2xl text-base leading-8 text-slate-600">
            {{ pageCopy.hero.secondary }}
          </p>
          <div class="mt-6 flex max-w-3xl flex-wrap gap-2.5">
            <span
              v-for="item in pageCopy.hero.highlights"
              :key="item"
              class="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-semibold text-slate-700"
            >
              <span class="h-2 w-2 rounded-full bg-primary"></span>
              {{ item }}
            </span>
          </div>
          <div class="mt-8 flex flex-wrap gap-3">
            <a
              href="#contact"
              class="inline-flex items-center justify-center rounded-md bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-slate-800"
            >
              {{ pageCopy.hero.primaryCta }}
            </a>
            <a
              href="#features"
              class="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-800 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-primary"
            >
              {{ pageCopy.hero.secondaryCta }}
            </a>
          </div>
        </div>

        <div class="relative">
        <div class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl shadow-blue-100/80">
          <div class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
            <div class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full bg-red-400"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-amber-400"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </div>
            <p class="text-xs font-semibold text-slate-500">{{ pageCopy.hero.previewTitle }} · {{ pageCopy.hero.live }}</p>
          </div>

          <div class="bg-[#eef6ff] p-3">
            <div class="grid min-h-[390px] overflow-hidden rounded-md border border-blue-100 bg-white shadow-sm lg:grid-cols-[156px_minmax(0,1fr)_258px]">
              <aside class="hidden min-w-[156px] border-r border-blue-100 bg-primary p-3 text-white lg:block">
                <p class="whitespace-nowrap text-sm font-black">aniforce</p>
                <div class="mt-7 space-y-2 text-xs">
                  <div
                    v-for="(item, index) in pageCopy.product.demo.nav"
                    :key="item"
                    class="whitespace-nowrap rounded-md px-3 py-2"
                    :class="index === pageCopy.product.demo.nav.length - 1 ? 'bg-white/20 font-bold' : 'text-blue-100'"
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
                    class="rounded-md bg-primary p-3 text-white"
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
                    <div class="rounded-md bg-primary px-3 py-2 text-[11px] leading-5 text-white">
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
                      <span class="h-5 w-5 rounded-full bg-primary"></span>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
          </div>
          <div class="ai-float-card">
            <h3><span class="material-symbols-outlined">psychology</span>{{ pageCopy.hero.optimization.title }}</h3>
            <div v-for="item in pageCopy.hero.optimization.items" :key="item.label" class="optimization-row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="features" class="border-b border-slate-200 bg-white px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl">
          <p class="text-sm font-semibold uppercase text-primary">{{ pageCopy.featureSection.title }}</p>
          <h2 class="mt-4 text-3xl font-bold leading-snug tracking-tight md:text-4xl">
            {{ pageCopy.featureSection.subtitle }}
          </h2>
        </div>

        <div class="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <article
            v-for="item in pageCopy.featureSection.items"
            :key="item.title"
            class="min-h-56 rounded-md border border-slate-200 bg-slate-50 p-6 transition-all hover:-translate-y-1 hover:border-primary/40 hover:bg-white hover:shadow-lg hover:shadow-slate-200/70"
          >
            <div class="mb-5 grid h-12 w-12 place-items-center rounded-md bg-primary/10 text-primary">
              <span class="material-symbols-outlined text-[26px]">{{ item.icon }}</span>
            </div>
            <h3 class="text-lg font-semibold leading-snug">{{ item.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ item.body }}</p>
          </article>
        </div>
      </div>
    </section>

    <section id="automation" class="border-b border-slate-200 bg-background-light px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl">
          <p class="text-sm font-semibold uppercase text-primary">{{ pageCopy.why.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-bold leading-snug tracking-tight md:text-4xl">
            <span v-for="line in pageCopy.why.titleLines" :key="line" class="block">{{ line }}</span>
          </h2>
        </div>

        <div class="mt-10 grid gap-6 md:grid-cols-3">
          <article v-for="item in pageCopy.capabilities" :key="item.title" class="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
            <h3 class="text-xl font-semibold leading-snug">{{ item.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ item.body }}</p>
            <div class="mt-5 flex flex-wrap gap-2">
              <span
                v-for="point in item.points"
                :key="point"
                class="rounded-md border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-primary"
              >
                {{ point }}
              </span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section id="performance" class="bg-white px-5 py-16 sm:px-6 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl">
          <p class="text-sm font-semibold uppercase text-primary">{{ pageCopy.workflow.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-bold leading-snug tracking-tight md:text-4xl">
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
            class="rounded-md border border-slate-200 bg-slate-50 p-5"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs font-bold text-slate-400">0{{ index + 1 }}</p>
              <span class="h-1.5 w-10 rounded-full bg-primary"></span>
            </div>
            <h3 class="mt-4 text-base font-semibold">{{ step.title }}</h3>
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

    <section id="contact" class="bg-slate-950 px-5 py-20 text-white sm:px-6 lg:px-10">
      <div class="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.75fr)]">
        <div>
          <p class="text-sm font-semibold uppercase text-blue-200">{{ pageCopy.contact.eyebrow }}</p>
          <h2 class="mt-4 max-w-3xl text-3xl font-bold leading-snug md:text-4xl">
            {{ pageCopy.contact.title }}
          </h2>
          <p class="mt-5 max-w-2xl text-base leading-8 text-slate-300">{{ pageCopy.contact.body }}</p>
          <div class="mt-8 grid gap-3 sm:grid-cols-3">
            <div
              v-for="mark in pageCopy.contact.marks"
              :key="mark.value"
              class="rounded-md border border-white/15 bg-white/10 p-4"
            >
              <strong class="block text-2xl">{{ mark.value }}</strong>
              <span class="mt-2 block text-xs text-slate-300">{{ mark.label }}</span>
            </div>
          </div>
          <p class="mt-5 text-xs leading-5 text-slate-400">{{ pageCopy.contact.contactNote }}</p>
        </div>

        <form class="rounded-md border border-white/15 bg-white/10 p-5" @submit.prevent>
          <label class="mb-4 block">
            <span class="mb-2 block text-sm text-slate-300">{{ pageCopy.contact.fields.name }}</span>
            <input class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300" :placeholder="pageCopy.contact.fields.namePlaceholder" autocomplete="name" />
          </label>
          <label class="mb-4 block">
            <span class="mb-2 block text-sm text-slate-300">{{ pageCopy.contact.fields.company }}</span>
            <input class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300" :placeholder="pageCopy.contact.fields.companyPlaceholder" autocomplete="organization" />
          </label>
          <label class="mb-4 block">
            <span class="mb-2 block text-sm text-slate-300">{{ pageCopy.contact.fields.contact }}</span>
            <input class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300" :placeholder="pageCopy.contact.fields.contactPlaceholder" autocomplete="email" />
          </label>
          <button class="w-full rounded-md bg-white px-5 py-3 text-sm font-semibold text-slate-950 shadow-[6px_6px_0_rgba(19,127,236,0.9)] transition-all hover:-translate-y-0.5" type="submit">
            {{ pageCopy.contact.fields.submit }}
          </button>
        </form>
      </div>
    </section>
  </main>
</template>

<style scoped>
.ai-float-card {
  position: absolute;
  right: -22px;
  bottom: 34px;
  width: min(260px, 48%);
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.15);
  animation: hoverFloat 4.5s ease-in-out infinite;
}

.ai-float-card h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 800;
}

.ai-float-card .material-symbols-outlined {
  color: #137fec;
  font-size: 20px;
}

.optimization-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 32px;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.optimization-row strong {
  color: #059669;
}

.signal-field {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  background:
    linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px);
  background-size: 54px 54px;
  opacity: 0.9;
}

.signal-field::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0.76) 44%, rgba(255, 255, 255, 0.34) 100%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), #fff 94%);
}

.signal-field::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(12deg, transparent 0 76px, rgba(19, 127, 236, 0.12) 77px 78px, transparent 79px 154px),
    repeating-linear-gradient(-9deg, transparent 0 90px, rgba(16, 185, 129, 0.1) 91px 92px, transparent 93px 170px);
  animation: signalFlow 16s linear infinite;
}

.signal-dot {
  position: absolute;
  z-index: 1;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: #137fec;
  box-shadow: 0 0 0 10px rgba(19, 127, 236, 0.12);
  animation: signalBlink 2.4s ease-in-out infinite, signalDrift 10s linear infinite;
}

.signal-dot:nth-child(4n + 1) {
  background: #10b981;
  box-shadow: 0 0 0 10px rgba(16, 185, 129, 0.13);
}

.signal-dot:nth-child(4n + 2) {
  background: #f59e0b;
  box-shadow: 0 0 0 10px rgba(245, 158, 11, 0.13);
}

.signal-dot:nth-child(4n + 3) {
  background: #466c78;
  box-shadow: 0 0 0 10px rgba(70, 108, 120, 0.13);
}

.signal-dot:nth-child(1) { left: 8%; top: 18%; animation-delay: -0.2s; }
.signal-dot:nth-child(2) { left: 18%; top: 72%; animation-delay: -1.1s; }
.signal-dot:nth-child(3) { left: 28%; top: 34%; animation-delay: -1.8s; }
.signal-dot:nth-child(4) { left: 38%; top: 78%; animation-delay: -0.6s; }
.signal-dot:nth-child(5) { left: 48%; top: 22%; animation-delay: -1.4s; }
.signal-dot:nth-child(6) { left: 58%; top: 62%; animation-delay: -2.1s; }
.signal-dot:nth-child(7) { left: 68%; top: 30%; animation-delay: -0.9s; }
.signal-dot:nth-child(8) { left: 78%; top: 70%; animation-delay: -1.7s; }
.signal-dot:nth-child(9) { left: 88%; top: 26%; animation-delay: -2.5s; }
.signal-dot:nth-child(10) { left: 12%; top: 46%; animation-delay: -0.4s; }
.signal-dot:nth-child(11) { left: 22%; top: 14%; animation-delay: -1.9s; }
.signal-dot:nth-child(12) { left: 32%; top: 58%; animation-delay: -2.7s; }
.signal-dot:nth-child(13) { left: 42%; top: 42%; animation-delay: -1.2s; }
.signal-dot:nth-child(14) { left: 52%; top: 82%; animation-delay: -2.2s; }
.signal-dot:nth-child(15) { left: 62%; top: 18%; animation-delay: -0.8s; }
.signal-dot:nth-child(16) { left: 72%; top: 50%; animation-delay: -1.6s; }
.signal-dot:nth-child(17) { left: 82%; top: 38%; animation-delay: -2.4s; }
.signal-dot:nth-child(18) { left: 92%; top: 66%; animation-delay: -0.7s; }
.signal-dot:nth-child(19) { left: 6%; top: 84%; animation-delay: -2.8s; }
.signal-dot:nth-child(20) { left: 16%; top: 28%; animation-delay: -1.3s; }
.signal-dot:nth-child(21) { left: 26%; top: 88%; animation-delay: -2.6s; }
.signal-dot:nth-child(22) { left: 36%; top: 12%; animation-delay: -0.5s; }
.signal-dot:nth-child(23) { left: 46%; top: 68%; animation-delay: -1.5s; }
.signal-dot:nth-child(24) { left: 56%; top: 36%; animation-delay: -2.3s; }
.signal-dot:nth-child(25) { left: 66%; top: 88%; animation-delay: -0.1s; }
.signal-dot:nth-child(26) { left: 76%; top: 16%; animation-delay: -1s; }
.signal-dot:nth-child(27) { left: 86%; top: 54%; animation-delay: -2s; }
.signal-dot:nth-child(28) { left: 96%; top: 34%; animation-delay: -2.9s; }

@keyframes signalBlink {
  0%,
  100% {
    opacity: 0.32;
    transform: scale(0.82);
  }
  45% {
    opacity: 0.9;
    transform: scale(1);
  }
}

@keyframes signalDrift {
  0% {
    translate: -14px 0;
  }
  100% {
    translate: 18px 0;
  }
}

@keyframes signalFlow {
  from {
    background-position: 0 0, 0 0;
  }
  to {
    background-position: 220px 120px, -180px 90px;
  }
}

@keyframes hoverFloat {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@media (max-width: 768px) {
  .ai-float-card {
    position: relative;
    right: auto;
    bottom: auto;
    width: auto;
    margin-top: 12px;
  }
}
</style>
