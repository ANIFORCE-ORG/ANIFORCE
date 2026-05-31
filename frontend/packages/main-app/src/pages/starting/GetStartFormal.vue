<script setup lang="ts">
import { ref } from 'vue'

// --- Hero Section ---
const heroTags = ['实时素材创作', '7x24盯盘', 'AI复盘归因', '可持续优化']

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
const dashboardStats = [
  { label: '消耗', value: '$28.4K', hint: '节奏正常', hintColor: 'text-emerald-600' },
  { label: 'CPA', value: '-18%', hint: '持续改善', hintColor: 'text-emerald-600' },
  { label: '素材', value: '2 条预警', hint: '需要复盘', hintColor: 'text-amber-600' }
]

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

const sidebarMenus = ['新任务', '项目管理', '广告投放', '创意素材', '数据概览']

const agentMessages = [
  { role: 'agent', text: 'Meta 两条素材出现疲劳，建议替换前三秒 Hook。' },
  { role: 'agent', text: '是否生成 3 个新素材方向，并同步到测试计划？' }
]

const agentInsights = ['预算消耗正常', '2 条素材疲劳预警', '转化成本下降 18%']

const aiSuggestions = ['转移预算至高转化素材', '降低冷启动计划出价', '新增相似用户包']

// --- Features Section ---
const features = [
  {
    icon: 'auto_awesome',
    title: 'AI智能优化',
    description: '自动分析投放数据，实时优化广告策略，帮助团队提升预算使用效率和整体 ROI。'
  },
  {
    icon: 'trending_up',
    title: '数据驱动增长',
    description: '深度洞察市场趋势，精准定位目标用户，加速业务增长并降低试错成本。'
  },
  {
    icon: 'psychology',
    title: '创意生成',
    description: 'AI辅助创意素材生成，快速产出高质量广告内容，并根据表现进行持续迭代。'
  },
  {
    icon: 'speed',
    title: '自动化投放',
    description: '一键启动广告投放，自动调整预算和出价策略，让执行链路更轻、更稳。'
  }
]

// --- Automation Section ---
const automationCards = [
  {
    title: 'Real-time Creative',
    description: '实时生成、拆解和迭代广告素材，让创意测试跟上投放节奏。',
    tags: ['视频拆解', '脚本生成', '多语言适配']
  },
  {
    title: 'Campaign Intelligence',
    description: '统一项目、账户、素材、计划和报表上下文，辅助判断预算、素材疲劳和转化异常。',
    tags: ['账户上下文', '素材疲劳', '转化异常']
  },
  {
    title: 'Performance Loop',
    description: '把每一次投放结果沉淀为可复用的素材特征、渠道经验和复盘结论。',
    tags: ['指标回流', '复盘结论', '经验沉淀']
  }
]

// --- Workflow Section ---
const workflowSteps = [
  {
    step: '01',
    title: 'Campaign Brief',
    description: '明确产品目标、受众、预算和区域。',
    platforms: [] as string[]
  },
  {
    step: '02',
    title: 'Creative Production',
    description: '实时自动生成创意、管理和复用广告素材。',
    platforms: [] as string[]
  },
  {
    step: '03',
    title: 'Media Execution',
    description: '统一管理跨平台账户，组织计划、素材、预算和状态。',
    platforms: ['Meta', 'Google', 'TikTok']
  },
  {
    step: '04',
    title: 'Monitor & Performance Review',
    description: '聚合监控各项广告指标，提出下一步优化动作，并完成工作复盘。',
    platforms: [] as string[]
  }
]

// --- CTA Section ---
const ctaCards = [
  { value: '30 min', label: '快速梳理投放流程' },
  { value: 'API', label: '确认渠道字段与权限' },
  { value: 'Demo', label: '按团队角色演示闭环' }
]

const contactForm = ref({
  name: '',
  company: '',
  contact: ''
})

const handleSubmitContact = () => {
  // TODO: Implement form submission
  console.log('Contact form submitted:', contactForm.value)
}
</script>

<template>
  <div class="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light font-display text-slate-900 transition-colors duration-300">
    <!-- Main Content -->
    <main class="bg-background-light text-slate-950">
      <!-- Hero Section -->
      <section
        id="top"
        class="relative isolate overflow-hidden border-b border-slate-200 bg-white px-5 pb-14 pt-12 sm:px-6 lg:px-10 lg:pb-18 lg:pt-16"
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

        <div class="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <!-- Left Content -->
          <div>
            <p class="inline-flex rounded-md bg-primary/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-primary">
              新一代 RTC 广告 AI 引擎
            </p>
            <h1 class="mt-5 max-w-3xl text-4xl font-bold leading-tight tracking-tight md:text-5xl lg:text-[56px]">
              智能营销，自动增长
            </h1>
            <p class="mt-5 max-w-2xl text-base leading-8 text-slate-600">
              ANIFORCE 利用 AI 技术自动规划、执行和优化广告投放策略。从策略制定到创意生成，从预算分配到效果监控，让增长变得简单高效。
            </p>

            <!-- Hero Tags -->
            <div class="mt-6 flex max-w-3xl flex-wrap gap-2.5">
              <span
                v-for="tag in heroTags"
                :key="tag"
                class="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-semibold text-slate-700"
              >
                <span class="h-2 w-2 rounded-full bg-primary" />
                {{ tag }}
              </span>
            </div>

            <!-- CTA Buttons -->
            <div class="mt-8 flex flex-wrap gap-3">
              <a
                href="#contact"
                class="inline-flex items-center justify-center rounded-md bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-slate-800"
              >
                免费体验
              </a>
              <a
                href="#features"
                class="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-800 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-primary"
              >
                查看功能
              </a>
            </div>
          </div>

          <!-- Right: Dashboard Mockup -->
          <div class="relative">
            <div class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl shadow-blue-100/80">
              <!-- Window Chrome -->
              <div class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
                <div class="flex items-center gap-2">
                  <span class="h-2.5 w-2.5 rounded-full bg-red-400" />
                  <span class="h-2.5 w-2.5 rounded-full bg-amber-400" />
                  <span class="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                </div>
                <p class="text-xs font-semibold text-slate-500">广告工作台 · 实时运行</p>
              </div>

              <!-- Dashboard Content -->
              <div class="bg-[#eef6ff] p-3">
                <div class="grid min-h-[390px] overflow-hidden rounded-md border border-blue-100 bg-white shadow-sm lg:grid-cols-[156px_minmax(0,1fr)_258px]">
                  <!-- Sidebar -->
                  <aside class="hidden min-w-[156px] border-r border-blue-100 bg-primary p-3 text-white lg:block">
                    <p class="whitespace-nowrap text-sm font-black">aniforce</p>
                    <div class="mt-7 space-y-2 text-xs">
                      <div
                        v-for="(menu, idx) in sidebarMenus"
                        :key="menu"
                        :class="[
                          'whitespace-nowrap rounded-md px-3 py-2 text-blue-100',
                          idx === sidebarMenus.length - 1 ? 'bg-white/20 font-bold' : ''
                        ]"
                      >
                        {{ menu }}
                      </div>
                    </div>
                  </aside>

                  <!-- Center Content -->
                  <div class="bg-[#f8fbff] p-4">
                    <!-- Stats Row -->
                    <div class="grid gap-2 sm:grid-cols-3">
                      <div
                        v-for="stat in dashboardStats"
                        :key="stat.label"
                        class="rounded-md border border-blue-100 bg-white p-3"
                      >
                        <p class="text-[11px] font-semibold text-slate-500">{{ stat.label }}</p>
                        <p class="mt-1 whitespace-nowrap font-black text-slate-950 text-lg">{{ stat.value }}</p>
                        <p :class="['mt-1 text-[11px] font-bold', stat.hintColor]">{{ stat.hint }}</p>
                      </div>
                    </div>

                    <!-- Platform Performance Bars -->
                    <div class="mt-4 rounded-md border border-blue-100 bg-white p-4">
                      <div class="flex items-center justify-between">
                        <p class="text-xs font-black text-slate-950">跨平台投放表现</p>
                        <p class="text-[11px] font-bold text-blue-600">近 7 天</p>
                      </div>
                      <div class="mt-4 space-y-3">
                        <div
                          v-for="bar in platformBars"
                          :key="bar.name"
                          class="grid grid-cols-[58px_1fr_42px] items-center gap-3"
                        >
                          <span class="text-xs font-bold text-slate-700">{{ bar.name }}</span>
                          <span class="h-2 rounded-full bg-blue-100">
                            <span
                              :class="['block h-2 rounded-full', bar.color]"
                              :style="{ width: bar.width }"
                            />
                          </span>
                          <span class="text-right text-xs font-bold text-slate-700">{{ bar.percent }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Bottom Metrics -->
                    <div class="mt-4 grid gap-2 sm:grid-cols-3">
                      <div
                        v-for="metric in bottomMetrics"
                        :key="metric.label"
                        class="rounded-md bg-primary p-3 text-white"
                      >
                        <p class="text-[11px] font-semibold text-slate-300">{{ metric.label }}</p>
                        <p class="mt-1 whitespace-nowrap text-lg font-black">{{ metric.value }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Right: Agent Chat -->
                  <aside class="border-t border-blue-100 bg-white p-3 lg:border-l lg:border-t-0">
                    <div class="flex h-full flex-col rounded-md border border-blue-100 bg-[#f8fbff]">
                      <div class="border-b border-blue-100 p-3">
                        <p class="text-xs font-black text-slate-950">ANIFORCE Agent</p>
                        <p class="mt-1 text-[11px] text-slate-500">7x24 盯盘</p>
                      </div>
                      <div class="flex-1 space-y-3 overflow-y-auto p-3">
                        <div
                          v-for="(msg, idx) in agentMessages"
                          :key="idx"
                          class="rounded-md bg-white p-2.5 text-[11px] leading-5 text-slate-700 shadow-sm"
                        >
                          {{ msg.text }}
                        </div>
                        <!-- Insights -->
                        <div class="space-y-1.5 pt-2">
                          <div
                            v-for="insight in agentInsights"
                            :key="insight"
                            class="flex items-center gap-2 text-[11px]"
                          >
                            <span class="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                            <span class="text-slate-600">{{ insight }}</span>
                          </div>
                        </div>
                      </div>
                      <div class="border-t border-blue-100 p-2">
                        <div class="flex items-center gap-2 rounded-md bg-white px-2.5 py-2 text-[11px] text-slate-400">
                          <span class="material-symbols-outlined text-sm">chat</span>
                          询问 agent...
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
                AI 优化建议
              </h3>
              <div class="space-y-1">
                <div
                  v-for="suggestion in aiSuggestions"
                  :key="suggestion"
                  class="optimization-row"
                >
                  <span class="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                  <span>{{ suggestion }}</span>
                </div>
              </div>
              <p class="mt-3 text-right text-[11px] font-bold text-primary">Ready</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Features Section -->
      <section id="features" class="border-b border-slate-200 bg-white px-5 py-16 sm:px-6 lg:px-10">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <h2 class="text-3xl font-bold leading-snug tracking-tight md:text-4xl">强大的功能特性</h2>
            <p class="mt-4 text-base leading-8 text-slate-600">AI驱动的全流程营销自动化，覆盖分析、投放与监控复盘</p>
          </div>

          <div class="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <article
              v-for="feature in features"
              :key="feature.title"
              class="rounded-md border border-slate-200 bg-slate-50 p-6 transition-all hover:border-primary/40 hover:shadow-lg"
            >
              <span class="material-symbols-outlined text-3xl text-primary">{{ feature.icon }}</span>
              <h3 class="mt-4 text-base font-semibold">{{ feature.title }}</h3>
              <p class="mt-3 text-sm leading-7 text-slate-600">{{ feature.description }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- Automation Section -->
      <section id="automation" class="border-b border-slate-200 bg-background-light px-5 py-16 sm:px-6 lg:px-10">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <p class="text-sm font-semibold uppercase text-primary">为什么需要新的广告 AI 引擎</p>
            <h2 class="mt-4 text-3xl font-bold leading-snug tracking-tight md:text-4xl">
              从搭建一个增长团队，<br>到一套可持续优化的工作流
            </h2>
          </div>

          <div class="mt-12 grid gap-6 lg:grid-cols-3">
            <article
              v-for="card in automationCards"
              :key="card.title"
              class="rounded-md border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h3 class="text-xl font-semibold leading-snug">{{ card.title }}</h3>
              <p class="mt-3 text-sm leading-7 text-slate-600">{{ card.description }}</p>
              <div class="mt-5 flex flex-wrap gap-2">
                <span
                  v-for="tag in card.tags"
                  :key="tag"
                  class="rounded-md border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-primary"
                >
                  {{ tag }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- Performance / Workflow Section -->
      <section id="performance" class="bg-white px-5 py-16 sm:px-6 lg:px-10">
        <div class="mx-auto max-w-7xl">
          <div class="max-w-4xl">
            <p class="text-sm font-semibold uppercase text-primary">跨平台广告引擎</p>
            <h2 class="mt-4 text-3xl font-bold leading-snug tracking-tight md:text-4xl">智能投放策略保障广告生意效果</h2>
            <p class="mt-5 text-base leading-8 text-slate-600">你把生意做好，其他事情交给aniforce</p>
          </div>

          <div class="mt-10 grid gap-3 lg:grid-cols-4">
            <article
              v-for="step in workflowSteps"
              :key="step.step"
              class="rounded-md border border-slate-200 bg-slate-50 p-5"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="text-xs font-bold text-slate-400">{{ step.step }}</p>
                <span class="h-1.5 w-10 rounded-full bg-primary" />
              </div>
              <h3 class="mt-4 text-base font-semibold">{{ step.title }}</h3>
              <p class="mt-3 text-sm leading-7 text-slate-600">{{ step.description }}</p>
              <div v-if="step.platforms.length" class="mt-4 flex flex-wrap gap-2">
                <span
                  v-for="platform in step.platforms"
                  :key="platform"
                  class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700"
                >
                  {{ platform }}
                </span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- CTA / Contact Section -->
      <section id="contact" class="bg-slate-950 px-5 py-20 text-white sm:px-6 lg:px-10">
        <div class="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.75fr)]">
          <!-- Left: CTA Content -->
          <div>
            <p class="text-sm font-semibold uppercase text-blue-200">免费体验</p>
            <h2 class="mt-4 max-w-3xl text-3xl font-bold leading-snug md:text-4xl">
              让你的投放团队先少开 5 个后台。
            </h2>
            <p class="mt-5 max-w-2xl text-base leading-8 text-slate-300">
              留下联系方式，ANIFORCE将为你升级现有的广告投放流程。
            </p>
            <div class="mt-8 grid gap-3 sm:grid-cols-3">
              <div
                v-for="card in ctaCards"
                :key="card.value"
                class="rounded-md border border-white/15 bg-white/10 p-4"
              >
                <strong class="block text-2xl">{{ card.value }}</strong>
                <span class="mt-2 block text-xs text-slate-300">{{ card.label }}</span>
              </div>
            </div>
          </div>

          <!-- Right: Contact Form -->
          <form class="rounded-md border border-white/15 bg-white/10 p-5" @submit.prevent="handleSubmitContact">
            <label class="mb-4 block">
              <span class="mb-2 block text-sm text-slate-300">姓名</span>
              <input
                v-model="contactForm.name"
                class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                placeholder="你的姓名"
              >
            </label>
            <label class="mb-4 block">
              <span class="mb-2 block text-sm text-slate-300">公司 / 团队</span>
              <input
                v-model="contactForm.company"
                class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                placeholder="公司或团队名称"
              >
            </label>
            <label class="mb-4 block">
              <span class="mb-2 block text-sm text-slate-300">联系方式</span>
              <input
                v-model="contactForm.contact"
                class="h-11 w-full rounded-md border border-white/15 bg-white/10 px-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-blue-300"
                placeholder="手机号或微信"
              >
            </label>
            <button
              class="w-full rounded-md bg-white px-5 py-3 text-sm font-semibold text-slate-950 shadow-[6px_6px_0_rgba(19,127,236,0.9)] transition-all hover:-translate-y-0.5"
              type="submit"
            >
              提交体验需求
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
  padding: 8px 0;
  border: 0;
  color: #475569;
  background: transparent;
  font-size: 20px;
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
  z-index: -1;
  overflow: hidden;
  background:
    linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px);
  background-size: 54px 54px;
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
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: #137fec;
  box-shadow: 0 0 0 10px rgba(19, 127, 236, 0.12);
  animation: signalBlink 2.4s ease-in-out infinite, signalDrift 10s linear infinite;
}

.signal-dot:nth-child(4n+1) {
  background: #10b981;
  box-shadow: 0 0 0 10px rgba(16, 185, 129, 0.13);
}

.signal-dot:nth-child(4n+2) {
  background: #f59e0b;
  box-shadow: 0 0 0 10px rgba(245, 158, 11, 0.13);
}

.signal-dot:nth-child(4n+3) {
  background: #466c78;
  box-shadow: 0 0 0 10px rgba(70, 108, 120, 0.13);
}

/* === AI Float Card === */
.ai-float-card {
  position: absolute;
  right: -22px;
  bottom: 34px;
  width: min(260px, 48%);
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 8px;
  background: #fffffff2;
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
  gap: 10px;
  min-height: 26px;
  color: #475569;
  font-size: 12px;
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
  25% { transform: translate(18px, -12px); }
  50% { transform: translate(-8px, 16px); }
  75% { transform: translate(12px, 8px); }
  100% { transform: translate(0, 0); }
}

@keyframes hoverFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* === Responsive: AI Float Card on mobile === */
@media (max-width: 1024px) {
  .ai-float-card {
    position: relative;
    right: auto;
    bottom: auto;
    width: auto;
    margin-top: 12px;
  }
}
</style>
