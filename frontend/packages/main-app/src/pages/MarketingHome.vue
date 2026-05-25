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
    },
    why: {
      eyebrow: '为什么需要新的广告 AI 引擎',
      titleLines: ['从搭建一个增长团队，', '到一套可持续优化的工作流'],
    },
    capabilities: [
      {
        title: 'Real-time Creative',
        body: '实时生成、拆解和迭代广告素材，让创意测试跟上投放节奏。',
      },
      {
        title: 'Campaign Intelligence',
        body: '统一项目、账户、素材、计划和报表上下文，辅助判断预算、素材疲劳和转化异常。',
      },
      {
        title: 'Performance Loop',
        body: '把每一次投放结果沉淀为可复用的素材特征、渠道经验和复盘结论。',
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
    },
  },
  en: {
    hero: {
      eyebrow: 'aniforce',
      title: 'The next-generation RTC advertising AI engine',
      highlights: ['Cross-platform', 'Real-time creative', '24/7 monitoring', 'AI review attribution', 'Continuous optimization'],
    },
    why: {
      eyebrow: 'Why a new advertising AI engine',
      titleLines: ['From building a growth team,', 'to a continuously improving workflow'],
    },
    capabilities: [
      {
        title: 'Real-time Creative',
        body: 'Generate, deconstruct, and iterate ad creatives in real time so creative testing can keep pace with media buying.',
      },
      {
        title: 'Campaign Intelligence',
        body: 'Unify project, account, creative, campaign, and reporting context to support budget decisions, creative fatigue checks, and conversion anomaly detection.',
      },
      {
        title: 'Performance Loop',
        body: 'Turn every campaign result into reusable creative signals, channel experience, and review conclusions.',
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
    },
  },
}

const pageCopy = computed(() => copy[language.value])
</script>

<template>
  <main class="bg-background-light text-slate-950">
    <section class="px-6 pb-14 pt-16 lg:px-10 lg:pt-22">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-4xl">
          <p class="text-sm font-semibold uppercase tracking-[0.18em] text-primary">{{ pageCopy.hero.eyebrow }}</p>
          <h1 class="mt-5 text-4xl font-black leading-tight md:text-5xl lg:text-6xl">
            {{ pageCopy.hero.title }}
          </h1>
          <div class="mt-6 flex max-w-3xl flex-wrap gap-3">
            <span
              v-for="item in pageCopy.hero.highlights"
              :key="item"
              class="rounded-md border border-slate-300/80 bg-gradient-to-b from-white to-slate-100 px-4 py-2 text-sm font-bold text-slate-800 shadow-sm shadow-slate-200/70"
            >
              {{ item }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <section class="border-y border-slate-200 bg-white px-6 py-16 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl">
          <p class="text-sm font-semibold uppercase tracking-[0.18em] text-primary">{{ pageCopy.why.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-black leading-snug md:text-4xl">
            <span v-for="line in pageCopy.why.titleLines" :key="line" class="block">{{ line }}</span>
          </h2>
        </div>

        <div class="mt-10 grid gap-6 md:grid-cols-3">
          <article v-for="item in pageCopy.capabilities" :key="item.title" class="rounded-lg border border-slate-200 bg-slate-50 p-6">
            <h3 class="text-xl font-bold leading-snug">{{ item.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ item.body }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="px-6 py-16 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="max-w-3xl">
          <p class="text-sm font-semibold uppercase tracking-[0.18em] text-primary">{{ pageCopy.workflow.eyebrow }}</p>
          <h2 class="mt-4 text-3xl font-black leading-snug md:text-4xl">
            {{ pageCopy.workflow.title }}
          </h2>
          <p class="mt-5 text-base leading-8 text-slate-600">
            {{ pageCopy.workflow.subtitle }}
          </p>
        </div>

        <div class="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article v-for="(step, index) in pageCopy.workflow.steps" :key="step.title" class="rounded-lg border border-slate-200 bg-white p-5">
            <p class="text-xs font-semibold text-slate-400">0{{ index + 1 }}</p>
            <h3 class="mt-3 text-base font-bold">{{ step.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-slate-600">{{ step.body }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="border-t border-slate-200 bg-white px-6 py-16 lg:px-10">
      <div class="mx-auto max-w-7xl">
        <div class="rounded-lg border border-primary/20 bg-slate-50 px-6 py-10 md:px-10">
          <p class="text-sm font-semibold uppercase tracking-[0.18em] text-primary">{{ pageCopy.cta.eyebrow }}</p>
          <h2 class="mt-3 text-3xl font-black leading-snug md:text-4xl">
            {{ pageCopy.cta.title }}
          </h2>
          <RouterLink to="/contact" class="mt-7 inline-flex items-center justify-center rounded-md bg-slate-950 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800">
            {{ pageCopy.cta.button }}
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>
