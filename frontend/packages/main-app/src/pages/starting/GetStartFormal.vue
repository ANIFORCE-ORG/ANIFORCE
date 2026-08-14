<script setup lang="ts">
import { ref, computed } from 'vue'
import { submitContact } from '@/api/contact'
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

// --- Bilingual Copy ---
const copy = {
  cn: {
    hero: {
      eyebrow: '新一代 RTC 广告 AI 引擎',
      title: '智能营销，自动增长',
      description: 'ANIFORCE 利用 AI 技术自动规划、执行和优化广告投放策略。从策略制定到创意生成，从预算分配到效果监控，让增长变得简单高效。',
      tags: ['实时素材创作', '7x24盯盘', 'AI复盘归因', '可持续优化'],
      primaryCta: '免费体验',
      secondaryCta: '查看功能',
      previewTitle: '广告工作台',
      live: '实时运行'
    },
    features: {
      title: '强大的功能特性',
      subtitle: 'AI驱动的全流程营销自动化，覆盖分析、投放与监控复盘',
      items: [
        { icon: 'auto_awesome', title: 'AI智能优化', description: '自动分析投放数据，实时优化广告策略，帮助团队提升预算使用效率和整体 ROI。' },
        { icon: 'trending_up', title: '数据驱动增长', description: '深度洞察市场趋势，精准定位目标用户，加速业务增长并降低试错成本。' },
        { icon: 'psychology', title: '创意生成', description: 'AI辅助创意素材生成，快速产出高质量广告内容，并根据表现进行持续迭代。' },
        { icon: 'speed', title: '自动化投放', description: '一键启动广告投放，自动调整预算和出价策略，让执行链路更轻、更稳。' }
      ]
    },
    automation: {
      eyebrow: '为什么需要新的广告 AI 引擎',
      title: ['从搭建一个增长团队，', '到一套可持续优化的工作流'],
      cards: [
        { title: 'Real-time Creative', description: '实时生成、拆解和迭代广告素材，让创意测试跟上投放节奏。', tags: ['视频拆解', '脚本生成', '多语言适配'] },
        { title: 'Campaign Intelligence', description: '统一项目、账户、素材、计划和报表上下文，辅助判断预算、素材疲劳和转化异常。', tags: ['账户上下文', '素材疲劳', '转化异常'] },
        { title: 'Performance Loop', description: '把每一次投放结果沉淀为可复用的素材特征、渠道经验和复盘结论。', tags: ['指标回流', '复盘结论', '经验沉淀'] }
      ]
    },
    workflow: {
      eyebrow: '跨平台广告引擎',
      title: '智能投放策略保障广告生意效果',
      subtitle: '你把生意做好，其他事情交给aniforce',
      steps: [
        { title: 'Campaign Brief', description: '明确产品目标、受众、预算和区域。' },
        { title: 'Creative Production', description: '实时自动生成创意、管理和复用广告素材。' },
        { title: 'Media Execution', description: '统一管理跨平台账户，组织计划、素材、预算和状态。', platforms: ['Meta', 'Google', 'TikTok'] },
        { title: 'Monitor & Performance Review', description: '聚合监控各项广告指标，提出下一步优化动作，并完成工作复盘。' }
      ]
    },
    contact: {
      eyebrow: '免费体验',
      title: '让你的投放团队先少开 5 个后台。',
      description: '留下联系方式，ANIFORCE将为你升级现有的广告投放流程。',
      cards: [
        { value: '30 min', label: '快速梳理投放流程' },
        { value: 'API', label: '确认渠道字段与权限' },
        { value: 'Demo', label: '按团队角色演示闭环' }
      ],
      form: {
        name: '姓名',
        namePlaceholder: '你的姓名',
        company: '公司 / 团队',
        companyPlaceholder: '公司或团队名称',
        contact: '联系方式',
        contactPlaceholder: '手机号或微信',
        submit: '提交体验需求',
        submitting: '提交中...',
        success: '✓ 提交成功！我们会尽快与您联系。',
        errorRequired: '请填写所有必填字段',
        errorDefault: '提交失败，请稍后重试'
      }
    },
    dashboard: {
      sidebar: ['新任务', '项目管理', '广告投放', '创意素材', '数据概览'],
      stats: [
        { label: '消耗', value: '$28.4K', hint: '节奏正常', hintColor: 'text-emerald-600' },
        { label: 'CPA', value: '-18%', hint: '持续改善', hintColor: 'text-emerald-600' },
        { label: '素材', value: '2 条预警', hint: '需要复盘', hintColor: 'text-amber-600' }
      ],
      performanceTitle: '跨平台投放表现',
      period: '近 7 天',
      agentTitle: 'ANIFORCE Agent',
      agentSubtitle: '7x24 盯盘',
      agentMessages: [
        { role: 'agent', text: 'Meta 两条素材出现疲劳，建议替换前三秒 Hook。' },
        { role: 'agent', text: '是否生成 3 个新素材方向，并同步到测试计划？' }
      ],
      agentInsights: ['预算消耗正常', '2 条素材疲劳预警', '转化成本下降 18%'],
      agentPlaceholder: '询问 agent...',
      aiOptimization: 'AI 优化建议',
      aiSuggestions: ['转移预算至高转化素材', '降低冷启动计划出价', '新增相似用户包']
    }
  },
  en: {
    hero: {
      eyebrow: 'The next-generation RTC advertising AI engine',
      title: 'Intelligent marketing, automatic growth',
      description: 'ANIFORCE uses AI to plan, execute, and optimize advertising strategies. From strategy and creative generation to budget allocation and performance monitoring, growth becomes simpler and more efficient.',
      tags: ['Real-time creative', '24/7 monitoring', 'AI review attribution', 'Continuous optimization'],
      primaryCta: 'Free trial',
      secondaryCta: 'View features',
      previewTitle: 'Advertising workspace',
      live: 'Live'
    },
    features: {
      title: 'Powerful product features',
      subtitle: 'AI-driven marketing automation across analysis, delivery, and monitoring',
      items: [
        { icon: 'auto_awesome', title: 'AI optimization', description: 'Analyze delivery data and improve advertising strategies in real time to increase budget efficiency and ROI.' },
        { icon: 'trending_up', title: 'Data-driven growth', description: 'Identify market trends and target audiences more precisely to accelerate growth and reduce testing costs.' },
        { icon: 'psychology', title: 'Creative generation', description: 'Produce quality advertising assets quickly with AI and continuously iterate based on performance.' },
        { icon: 'speed', title: 'Automated delivery', description: 'Launch campaigns quickly and continuously adjust budgets and bid strategies with less manual work.' }
      ]
    },
    automation: {
      eyebrow: 'Why a new advertising AI engine',
      title: ['From building a growth team,', 'to a continuously improving workflow'],
      cards: [
        { title: 'Real-time Creative', description: 'Generate, deconstruct, and iterate ad creatives in real time so creative testing can keep pace with media buying.', tags: ['Creative parsing', 'Asset variants', 'Reusable ideas'] },
        { title: 'Campaign Intelligence', description: 'Unify project, account, creative, campaign, and reporting context to support budget decisions, creative fatigue checks, and conversion anomaly detection.', tags: ['Account context', 'Budget signals', 'Fatigue checks'] },
        { title: 'Performance Loop', description: 'Turn every campaign result into reusable creative signals, channel experience, and review conclusions.', tags: ['Metric feedback', 'Review notes', 'Channel memory'] }
      ]
    },
    workflow: {
      eyebrow: 'Cross-platform advertising engine',
      title: 'Intelligent media strategy for advertising outcomes',
      subtitle: 'You focus on the business. aniforce handles the rest.',
      steps: [
        { title: 'Campaign Brief', description: 'Define product goals, audience, budget, and regions.' },
        { title: 'Creative Production', description: 'Generate creatives in real time, manage assets, and reuse proven materials.' },
        { title: 'Media Execution', description: 'Manage cross-platform accounts, campaigns, creatives, budgets, and status in one place.', platforms: ['Meta', 'Google', 'TikTok'] },
        { title: 'Monitor & Performance Review', description: 'Monitor advertising metrics, suggest the next optimization actions, and complete campaign reviews.' }
      ]
    },
    contact: {
      eyebrow: 'Free trial',
      title: 'Let your media team open 5 fewer dashboards.',
      description: 'Leave your contact information. ANIFORCE will upgrade your existing advertising workflow.',
      cards: [
        { value: '30 min', label: 'Map your media workflow' },
        { value: 'API', label: 'Review channel fields and access' },
        { value: 'Demo', label: 'Demo by team role' }
      ],
      form: {
        name: 'Name',
        namePlaceholder: 'Your name',
        company: 'Company / Team',
        companyPlaceholder: 'Company or team name',
        contact: 'Contact',
        contactPlaceholder: 'Phone or WeChat',
        submit: 'Submit request',
        submitting: 'Submitting...',
        success: '✓ Submitted successfully! We will contact you soon.',
        errorRequired: 'Please fill in all required fields',
        errorDefault: 'Submission failed, please try again later'
      }
    },
    dashboard: {
      sidebar: ['New task', 'Projects', 'Campaigns', 'Creatives', 'Overview'],
      stats: [
        { label: 'Spend', value: '$28.4K', hint: 'On pace', hintColor: 'text-emerald-600' },
        { label: 'CPA', value: '-18%', hint: 'Improving', hintColor: 'text-emerald-600' },
        { label: 'Creative', value: '2 alerts', hint: 'Needs review', hintColor: 'text-amber-600' }
      ],
      performanceTitle: 'Cross-platform performance',
      period: 'Last 7 days',
      agentTitle: 'ANIFORCE Agent',
      agentSubtitle: '24/7 monitoring',
      agentMessages: [
        { role: 'agent', text: 'Two Meta creatives show fatigue. Replace the first-three-second hook.' },
        { role: 'agent', text: 'Generate 3 new creative directions and sync them to the test campaign?' }
      ],
      agentInsights: ['Budget pacing on track', '2 creative fatigue alerts', 'CPA down 18%'],
      agentPlaceholder: 'Ask agent...',
      aiOptimization: 'AI optimization',
      aiSuggestions: ['Move budget to high-converting creatives', 'Lower bids for cold-start campaigns', 'Add lookalike audiences']
    }
  }
}

const t = computed(() => copy[language.value])

// --- Hero Section ---
const heroTags = computed(() => t.value.hero.tags)

// --- Signal Dots (28 fixed positions) ---
const signalDots = [
  { left: '8%', top: '18%', delay: '-0.2s' },
  { left: '18%', top: '72%', delay: '-1.1s' },
  { left: '28%', top: '34%', delay: '-1.8s' },
  { left: '38%', top: '78%', delay: '-0.6s' },
  { left: '48%', top: '22%', delay: '-1.4s' },
  { left: '58%', top: '62%', delay: '-2.1s' },
  { left: '68%', top: '30%', delay: '-0.9s' },
  { left: '78%', top: '70%', delay: '-1.7s' },
  { left: '88%', top: '26%', delay: '-2.5s' },
  { left: '12%', top: '46%', delay: '-0.4s' },
  { left: '22%', top: '14%', delay: '-1.9s' },
  { left: '32%', top: '58%', delay: '-2.7s' },
  { left: '42%', top: '42%', delay: '-1.2s' },
  { left: '52%', top: '82%', delay: '-2.2s' },
  { left: '62%', top: '18%', delay: '-0.8s' },
  { left: '72%', top: '50%', delay: '-1.6s' },
  { left: '82%', top: '38%', delay: '-2.4s' },
  { left: '92%', top: '66%', delay: '-0.7s' },
  { left: '6%', top: '84%', delay: '-2.8s' },
  { left: '16%', top: '28%', delay: '-1.3s' },
  { left: '26%', top: '88%', delay: '-2.6s' },
  { left: '36%', top: '12%', delay: '-0.5s' },
  { left: '46%', top: '68%', delay: '-1.5s' },
  { left: '56%', top: '36%', delay: '-2.3s' },
  { left: '66%', top: '88%', delay: '-0.1s' },
  { left: '76%', top: '16%', delay: '-1.0s' },
  { left: '86%', top: '54%', delay: '-2.0s' },
  { left: '96%', top: '34%', delay: '-2.9s' }
]

// --- Dashboard Mock Data ---
const dashboardStats = computed(() => t.value.dashboard.stats)

const platformBars = [
  { name: 'Meta', width: '78%', color: 'bg-blue-600', percent: '78%' },
  { name: 'Google', width: '62%', color: 'bg-blue-500', percent: '62%' },
  { name: 'TikTok', width: '54%', color: 'bg-blue-400', percent: '54%' }
]

const bottomMetrics = [
  { label: 'CTR', value: '+21%' },
  { label: 'CPA', value: '-18%' },
  { label: 'ROAS', value: '1.7x' }
]

const sidebarMenus = computed(() => t.value.dashboard.sidebar)
const agentMessages = computed(() => t.value.dashboard.agentMessages)
const agentInsights = computed(() => t.value.dashboard.agentInsights)
const aiSuggestions = computed(() => t.value.dashboard.aiSuggestions)

// --- Features Section ---
const features = computed(() => t.value.features.items)

// --- Automation Section ---
const automationCards = computed(() => t.value.automation.cards)

// --- Workflow Section ---
const workflowSteps = computed(() => t.value.workflow.steps)

// --- CTA Section ---
const ctaCards = computed(() => t.value.contact.cards)

const contactForm = ref({
  name: '',
  company: '',
  contact: ''
})

const submitting = ref(false)
const submitSuccess = ref(false)
const submitError = ref('')

const handleSubmitContact = async () => {
  // 验证表单
  if (!contactForm.value.name || !contactForm.value.company || !contactForm.value.contact) {
    submitError.value = t.value.contact.form.errorRequired
    return
  }

  submitting.value = true
  submitError.value = ''
  submitSuccess.value = false

  try {
    await submitContact({
      name: contactForm.value.name,
      company: contactForm.value.company,
      contact: contactForm.value.contact
    })

    // 提交成功
    submitSuccess.value = true
    
    // 重置表单
    contactForm.value = {
      name: '',
      company: '',
      contact: ''
    }

    // 3秒后隐藏成功消息
    setTimeout(() => {
      submitSuccess.value = false
    }, 3000)
  } catch (err: any) {
    console.error('提交联系信息失败:', err)
    submitError.value = err.message || t.value.contact.form.errorDefault
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light font-display text-slate-900 transition-colors duration-300">
    <!-- Main Content -->
    <main class="bg-background-light text-slate-950">
      <!-- Hero Section -->
      <section
        id="top"
        class="relative isolate overflow-hidden border-b border-slate-200 bg-white px-[18px] pb-[50px] pt-[43px] sm:px-[22px] lg:px-[36px] lg:pb-[65px] lg:pt-[58px]"
      >
        <!-- Signal Field Background -->
        <div class="signal-field" aria-hidden="true">
          <span
            v-for="(dot, index) in signalDots"
            :key="index"
            class="signal-dot"
            :style="{ left: dot.left, top: dot.top, animationDelay: dot.delay }"
          />
        </div>

        <div class="relative z-10 mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <!-- Left Content -->
          <div>
            <p class="inline-flex rounded-md bg-primary/10 px-[11px] py-[5px] text-[11px] font-semibold uppercase tracking-wide text-primary">
              {{ t.hero.eyebrow }}
            </p>
            <h1 class="mt-[18px] max-w-3xl text-[32px] font-bold leading-tight tracking-tight md:text-[40px] lg:text-[50px]">
              {{ t.hero.title }}
            </h1>
            <p class="mt-[18px] max-w-2xl text-[14px] leading-[29px] text-slate-600">
              {{ t.hero.description }}
            </p>

            <!-- Hero Tags -->
            <div class="mt-[22px] flex max-w-3xl flex-wrap gap-[9px]">
              <span
                v-for="tag in heroTags"
                :key="tag"
                class="inline-flex items-center gap-[7px] rounded-md border border-slate-200 bg-slate-50 px-[13px] py-[7px] text-[13px] font-semibold text-slate-700"
              >
                <span class="h-[7px] w-[7px] rounded-full bg-primary" />
                {{ tag }}
              </span>
            </div>

            <!-- CTA Buttons -->
            <div class="mt-[29px] flex flex-wrap gap-[11px]">
              <a
                href="#contact"
                class="inline-flex items-center justify-center rounded-md bg-slate-950 px-[22px] py-[11px] text-[13px] font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-slate-800"
              >
                {{ t.hero.primaryCta }}
              </a>
              <a
                href="#features"
                class="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-[22px] py-[11px] text-[13px] font-semibold text-slate-800 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-primary"
              >
                {{ t.hero.secondaryCta }}
              </a>
            </div>
          </div>

          <!-- Right: Dashboard Mockup -->
          <div class="relative">
            <div class="overflow-hidden rounded-md border border-slate-200 bg-white shadow-2xl shadow-blue-100/80">
              <!-- Window Chrome -->
              <div class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-[14px] py-[11px]">
                <div class="flex items-center gap-[7px]">
                  <span class="h-[9px] w-[9px] rounded-full bg-red-400" />
                  <span class="h-[9px] w-[9px] rounded-full bg-amber-400" />
                  <span class="h-[9px] w-[9px] rounded-full bg-emerald-500" />
                </div>
                <p class="text-[11px] font-semibold text-slate-500">{{ t.hero.previewTitle }} · {{ t.hero.live }}</p>
              </div>

              <!-- Dashboard Content -->
              <div class="bg-[#eef6ff] p-[11px]">
                <div class="grid min-h-[351px] overflow-hidden rounded-md border border-blue-100 bg-white shadow-sm lg:grid-cols-[108px_minmax(0,1fr)_232px]">
                  <!-- Sidebar -->
                  <aside class="hidden min-w-[108px] border-r border-blue-100 bg-primary p-[9px] text-white lg:block">
                    <p class="whitespace-nowrap text-[11px] font-black">Aniforce</p>
                    <div class="mt-[22px] space-y-[5px] text-[10px]">
                      <div
                        v-for="(menu, idx) in sidebarMenus"
                        :key="menu"
                        :class="[
                          'whitespace-nowrap rounded-md px-[9px] py-[5px] text-blue-100',
                          idx === sidebarMenus.length - 1 ? 'bg-white/20 font-bold' : ''
                        ]"
                      >
                        {{ menu }}
                      </div>
                    </div>
                  </aside>

                  <!-- Center Content -->
                  <div class="bg-[#f8fbff] p-[14px]">
                    <!-- Stats Row -->
                    <div class="grid gap-[7px] sm:grid-cols-3">
                      <div
                        v-for="stat in dashboardStats"
                        :key="stat.label"
                        class="rounded-md border border-blue-100 bg-white p-[11px]"
                      >
                        <p class="text-[10px] font-semibold text-slate-500">{{ stat.label }}</p>
                        <p class="mt-[4px] whitespace-nowrap font-black text-slate-950 text-[11px]">{{ stat.value }}</p>
                        <p :class="['mt-[4px] text-[8px] font-bold', stat.hintColor]">{{ stat.hint }}</p>
                      </div>
                    </div>

                    <!-- Platform Performance Bars -->
                    <div class="mt-[14px] rounded-md border border-blue-100 bg-white p-[14px]">
                      <div class="flex items-center justify-between">
                        <p class="text-[11px] font-black text-slate-950">{{ t.dashboard.performanceTitle }}</p>
                        <p class="text-[10px] font-bold text-blue-600">{{ t.dashboard.period }}</p>
                      </div>
                      <div class="mt-[14px] space-y-[11px]">
                        <div
                          v-for="bar in platformBars"
                          :key="bar.name"
                          class="grid grid-cols-[52px_1fr_38px] items-center gap-[11px]"
                        >
                          <span class="text-[11px] font-bold text-slate-700">{{ bar.name }}</span>
                          <span class="h-[7px] rounded-full bg-blue-100">
                            <span
                              :class="['block h-[7px] rounded-full', bar.color]"
                              :style="{ width: bar.width }"
                            />
                          </span>
                          <span class="text-right text-[11px] font-bold text-slate-700">{{ bar.percent }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Bottom Metrics -->
                    <div class="mt-[14px] grid gap-[7px] sm:grid-cols-3">
                      <div
                        v-for="metric in bottomMetrics"
                        :key="metric.label"
                        class="rounded-md bg-primary p-[11px] text-white"
                      >
                        <p class="text-[10px] font-semibold text-slate-300">{{ metric.label }}</p>
                        <p class="mt-[4px] whitespace-nowrap text-[16px] font-black">{{ metric.value }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Right: Agent Chat -->
                  <aside class="border-t border-blue-100 bg-white p-[11px] lg:border-l lg:border-t-0">
                    <div class="flex h-full flex-col rounded-md border border-blue-100 bg-[#f8fbff]">
                      <div class="border-b border-blue-100 p-[11px]">
                        <p class="text-[11px] font-black text-slate-950">{{ t.dashboard.agentTitle }}</p>
                        <p class="mt-[4px] text-[10px] text-slate-500">{{ t.dashboard.agentSubtitle }}</p>
                      </div>
                      <div class="flex-1 space-y-[11px] overflow-y-auto p-[11px]">
                        <div
                          v-for="(msg, idx) in agentMessages"
                          :key="idx"
                          class="rounded-md bg-white p-[9px] text-[10px] leading-[18px] text-slate-700 shadow-sm"
                        >
                          {{ msg.text }}
                        </div>
                        <!-- Insights -->
                        <div class="space-y-[5px] pt-[7px]">
                          <div
                            v-for="insight in agentInsights"
                            :key="insight"
                            class="flex items-center gap-[7px] text-[10px]"
                          >
                            <span class="h-[5px] w-[5px] rounded-full bg-emerald-500" />
                            <span class="text-slate-600">{{ insight }}</span>
                          </div>
                        </div>
                      </div>
                      <div class="border-t border-blue-100 p-[7px]">
                        <div class="flex items-center gap-[7px] rounded-md bg-white px-[9px] py-[7px] text-[10px] text-slate-400">
                          <span class="material-symbols-outlined text-[13px]">chat</span>
                          {{ t.dashboard.agentPlaceholder }}
                        </div>
                      </div>
                    </div>
                  </aside>
                </div>
              </div>
            </div>

            <!-- AI Float Card -->
            <div class="ai-float-card">
              <h3>
                <span class="material-symbols-outlined">psychology</span>
                {{ t.dashboard.aiOptimization }}
              </h3>
              <div class="space-y-[4px]">
                <div
                  v-for="suggestion in aiSuggestions"
                  :key="suggestion"
                  class="optimization-row"
                >
                  <span class="h-[5px] w-[5px] rounded-full bg-emerald-500 shrink-0" />
                  <span>{{ suggestion }}</span>
                </div>
              </div>
              <p class="mt-[11px] text-right text-[10px] font-bold text-primary">Ready</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Features Section -->
      <section id="features" class="border-b border-slate-200 bg-white px-[18px] py-[58px] sm:px-[22px] lg:px-[36px]">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <h2 class="text-[27px] font-bold leading-snug tracking-tight md:text-[32px]">{{ t.features.title }}</h2>
            <p class="mt-[14px] text-[14px] leading-[29px] text-slate-600">{{ t.features.subtitle }}</p>
          </div>

          <div class="mt-[43px] grid gap-[22px] sm:grid-cols-2 lg:grid-cols-4">
            <article
              v-for="feature in features"
              :key="feature.title"
              class="rounded-md border border-slate-200 bg-slate-50 p-[22px] transition-all hover:border-primary/40 hover:shadow-lg"
            >
              <span class="material-symbols-outlined text-[27px] text-primary">{{ feature.icon }}</span>
              <h3 class="mt-[14px] text-[14px] font-semibold">{{ feature.title }}</h3>
              <p class="mt-[11px] text-[13px] leading-[25px] text-slate-600">{{ feature.description }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- Automation Section -->
      <section id="automation" class="border-b border-slate-200 bg-background-light px-[18px] py-[58px] sm:px-[22px] lg:px-[36px]">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <p class="text-[13px] font-semibold uppercase text-primary">{{ t.automation.eyebrow }}</p>
            <h2 class="mt-[14px] text-[27px] font-bold leading-snug tracking-tight md:text-[32px]">
              <span v-for="(line, idx) in t.automation.title" :key="idx">{{ line }}<br v-if="idx < t.automation.title.length - 1"></span>
            </h2>
          </div>

          <div class="mt-[43px] grid gap-[22px] lg:grid-cols-3">
            <article
              v-for="card in automationCards"
              :key="card.title"
              class="rounded-md border border-slate-200 bg-white p-[22px] shadow-sm"
            >
              <h3 class="text-[18px] font-semibold leading-snug">{{ card.title }}</h3>
              <p class="mt-[11px] text-[13px] leading-[25px] text-slate-600">{{ card.description }}</p>
              <div class="mt-[18px] flex flex-wrap gap-[7px]">
                <span
                  v-for="tag in card.tags"
                  :key="tag"
                  class="rounded-md border border-blue-100 bg-blue-50 px-[11px] py-[5px] text-[11px] font-semibold text-primary"
                >
                  {{ tag }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- Performance / Workflow Section -->
      <section id="performance" class="bg-white px-[18px] py-[58px] sm:px-[22px] lg:px-[36px]">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <p class="text-[13px] font-semibold uppercase text-primary">{{ t.workflow.eyebrow }}</p>
            <h2 class="mt-[14px] text-[27px] font-bold leading-snug tracking-tight md:text-[32px]">{{ t.workflow.title }}</h2>
            <p class="mt-[18px] text-[14px] leading-[29px] text-slate-600">{{ t.workflow.subtitle }}</p>
          </div>

          <div class="mt-[36px] grid gap-[11px] lg:grid-cols-4">
            <article
              v-for="(step, index) in workflowSteps"
              :key="step.title"
              class="rounded-md border border-slate-200 bg-slate-50 p-[18px]"
            >
              <div class="flex items-center justify-between gap-[11px]">
                <p class="text-[11px] font-bold text-slate-400">0{{ index + 1 }}</p>
                <span class="h-[5px] w-[36px] rounded-full bg-primary" />
              </div>
              <h3 class="mt-[14px] text-[14px] font-semibold">{{ step.title }}</h3>
              <p class="mt-[11px] text-[13px] leading-[25px] text-slate-600">{{ step.description }}</p>
              <div v-if="step.platforms && step.platforms.length" class="mt-[14px] flex flex-wrap gap-[7px]">
                <span
                  v-for="platform in step.platforms"
                  :key="platform"
                  class="rounded-md bg-slate-100 px-[9px] py-[4px] text-[11px] font-bold text-slate-700"
                >
                  {{ platform }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- CTA / Contact Section -->
      <section id="contact" class="bg-slate-950 px-[18px] py-[72px] text-white sm:px-[22px] lg:px-[36px]">
        <div class="mx-auto grid max-w-7xl gap-[43px] lg:grid-cols-[minmax(0,0.95fr)_minmax(288px,0.75fr)]">
          <!-- Left: CTA Content -->
          <div>
            <p class="text-[13px] font-semibold uppercase text-blue-200">{{ t.contact.eyebrow }}</p>
            <h2 class="mt-[14px] max-w-3xl text-[27px] font-bold leading-snug md:text-[32px]">
              {{ t.contact.title }}
            </h2>
            <p class="mt-[18px] max-w-2xl text-[14px] leading-[29px] text-slate-300">
              {{ t.contact.description }}
            </p>
            <div class="mt-[29px] grid gap-[11px] sm:grid-cols-3">
              <div
                v-for="card in ctaCards"
                :key="card.value"
                class="rounded-md border border-white/15 bg-white/10 p-[14px]"
              >
                <strong class="block text-[22px]">{{ card.value }}</strong>
                <span class="mt-[7px] block text-[11px] text-slate-300">{{ card.label }}</span>
              </div>
            </div>
          </div>

          <!-- Right: Contact Form -->
          <form class="rounded-md border border-white/15 bg-white/10 p-[18px]" @submit.prevent="handleSubmitContact">
            <label class="mb-[14px] block">
              <span class="mb-[7px] block text-[13px] text-slate-300">{{ t.contact.form.name }}</span>
              <input
                v-model="contactForm.name"
                class="h-[40px] w-full rounded-md border border-white/15 bg-white/10 px-[11px] text-[13px] text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                :placeholder="t.contact.form.namePlaceholder"
              >
            </label>
            <label class="mb-[14px] block">
              <span class="mb-[7px] block text-[13px] text-slate-300">{{ t.contact.form.company }}</span>
              <input
                v-model="contactForm.company"
                class="h-[40px] w-full rounded-md border border-white/15 bg-white/10 px-[11px] text-[13px] text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                :placeholder="t.contact.form.companyPlaceholder"
              >
            </label>
            <label class="mb-[14px] block">
              <span class="mb-[7px] block text-[13px] text-slate-300">{{ t.contact.form.contact }}</span>
              <input
                v-model="contactForm.contact"
                class="h-[40px] w-full rounded-md border border-white/15 bg-white/10 px-[11px] text-[13px] text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                :placeholder="t.contact.form.contactPlaceholder"
              >
            </label>

            <!-- 成功消息 -->
            <div v-if="submitSuccess" class="mb-[14px] rounded-md bg-emerald-500/20 border border-emerald-500/30 px-[14px] py-[11px] text-[13px] text-emerald-300">
              {{ t.contact.form.success }}
            </div>

            <!-- 错误消息 -->
            <div v-if="submitError" class="mb-[14px] rounded-md bg-red-500/20 border border-red-500/30 px-[14px] py-[11px] text-[13px] text-red-300">
              {{ submitError }}
            </div>

            <button
              :disabled="submitting"
              class="w-full rounded-md bg-white px-[18px] py-[11px] text-[13px] font-semibold text-slate-950 shadow-[5px_5px_0_rgba(19,127,236,0.9)] transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
              type="submit"
            >
              {{ submitting ? t.contact.form.submitting : t.contact.form.submit }}
            </button>
          </form>
        </div>
      </section>
    </main>

  </div>
</template>

<style scoped>
/* === Navigation Link === */
.public-nav-link {
  position: relative;
  padding: 7px 0;
  border: 0;
  color: #475569;
  background: transparent;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
}

.public-nav-link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 2px;
  height: 2px;
  transform: scaleX(0);
  transform-origin: left;
  background: #137fec;
  transition: transform 0.18s ease;
}

.public-nav-link:hover {
  color: #137fec;
}

.public-nav-link:hover::after {
  transform: scaleX(1);
}

/* === Signal Field === */
.signal-field {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  background:
    linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px);
  background-size: 49px 49px;
  opacity: 0.9;
}

.signal-field::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background:
    linear-gradient(90deg, #fffffff5, #ffffffc2 44%, #ffffff57),
    linear-gradient(180deg, #ffffff14, #fff 94%);
}

.signal-field::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background:
    repeating-linear-gradient(12deg, transparent 0 76px, rgba(19, 127, 236, 0.12) 77px 78px, transparent 79px 154px),
    repeating-linear-gradient(-9deg, transparent 0 90px, rgba(16, 185, 129, 0.1) 91px 92px, transparent 93px 170px);
  animation: signalFlow 16s linear infinite;
}

/* === Signal Dots === */
.signal-dot {
  position: absolute;
  z-index: 1;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: #137fec;
  box-shadow: 0 0 0 9px rgba(19, 127, 236, 0.12);
  animation: signalBlink 2.4s ease-in-out infinite, signalDrift 10s linear infinite;
}

.signal-dot:nth-child(4n+1) {
  background: #10b981;
  box-shadow: 0 0 0 9px rgba(16, 185, 129, 0.13);
}

.signal-dot:nth-child(4n+2) {
  background: #f59e0b;
  box-shadow: 0 0 0 9px rgba(245, 158, 11, 0.13);
}

.signal-dot:nth-child(4n+3) {
  background: #466c78;
  box-shadow: 0 0 0 9px rgba(70, 108, 120, 0.13);
}

/* === AI Float Card === */
.ai-float-card {
  position: absolute;
  z-index: 20;
  right: -20px;
  bottom: 31px;
  width: min(234px, 48%);
  padding: 13px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 7px;
  background: #fffffff2;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.15);
  animation: hoverFloat 4.5s ease-in-out infinite;
}

.ai-float-card h3 {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 11px;
  font-size: 13px;
  font-weight: 800;
}

.ai-float-card .material-symbols-outlined {
  color: #137fec;
  font-size: 18px;
}

.optimization-row {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 23px;
  color: #475569;
  font-size: 11px;
  font-weight: 600;
}

/* === Keyframes === */
@keyframes signalFlow {
  0% { background-position: 0 0, 0 0; }
  100% { background-position: 200px 200px, -200px -200px; }
}

@keyframes signalBlink {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

@keyframes signalDrift {
  0% { transform: translate(0, 0); }
  25% { transform: translate(16px, -11px); }
  50% { transform: translate(-7px, 14px); }
  75% { transform: translate(11px, 7px); }
  100% { transform: translate(0, 0); }
}

@keyframes hoverFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-11px); }
}

/* === Responsive: AI Float Card on mobile === */
@media (max-width: 1024px) {
  .ai-float-card {
    position: relative;
    right: auto;
    bottom: auto;
    width: auto;
    margin-top: 11px;
  }
}
</style>
