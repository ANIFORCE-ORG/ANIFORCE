<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()

// 检查登录状态,已登录则跳转到/home
onMounted(() => {
  if (auth.isLoggedIn) {
    router.push('/home')
  }
})

const handleGetStarted = () => {
  router.push('/login')
}

const features = [
  {
    icon: 'auto_awesome',
    title: 'AI智能优化',
    description: '自动分析投放数据，实时优化广告策略，提升ROI'
  },
  {
    icon: 'trending_up',
    title: '数据驱动增长',
    description: '深度洞察市场趋势，精准定位目标用户，加速业务增长'
  },
  {
    icon: 'psychology',
    title: '创意生成',
    description: 'AI辅助创意素材生成，快速产出高质量广告内容'
  },
  {
    icon: 'speed',
    title: '自动化投放',
    description: '一键启动广告投放，自动调整预算和出价策略'
  }
]

const workflows = [
  {
    title: '智能分析',
    status: 'running',
    tasks: [
      { name: '市场趋势分析', time: '2h ago' },
      { name: '竞品监控', time: '5h ago' },
      { name: '用户画像更新', time: '1d ago' }
    ]
  },
  {
    title: '投放优化',
    status: 'running',
    tasks: [
      { name: '预算分配优化', time: 'Running' },
      { name: '出价策略调整', time: 'Next: 1h' },
      { name: '素材效果评估', time: 'Next: 3h' }
    ]
  }
]
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
    <!-- Hero Section -->
    <section class="pt-20 pb-20 px-6">
      <div class="max-w-7xl mx-auto">
        <div class="grid lg:grid-cols-2 gap-12 items-center">
          <!-- Left Content -->
          <div>
            <h1 class="text-5xl lg:text-6xl font-bold text-slate-900 dark:text-white mb-6 leading-tight">
              智能营销,自动增长
            </h1>
            <p class="text-lg text-slate-600 dark:text-slate-400 mb-8 leading-relaxed">
              ANIFORCE 利用 AI 技术自动规划、执行和优化您的广告投放策略。从策略制定到创意生成，从预算分配到效果监控，让增长变得简单高效。
            </p>
            <button
              class="px-8 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl hover:bg-slate-800 dark:hover:bg-slate-100 transition-all font-medium text-lg shadow-lg hover:shadow-xl"
              @click="handleGetStarted"
            >
              免费开始
            </button>
          </div>

          <!-- Right Illustration -->
          <div class="relative">
            <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-200 dark:border-slate-700">
              <!-- Illustration placeholder -->
              <div class="flex items-center justify-center h-96">
                <div class="text-center">
                  <span class="material-symbols-outlined text-9xl text-primary mb-4">rocket_launch</span>
                  <div class="flex items-center justify-center gap-2 text-slate-400">
                    <span class="material-symbols-outlined">auto_awesome</span>
                    <span class="material-symbols-outlined">trending_up</span>
                    <span class="material-symbols-outlined">psychology</span>
                    <span class="material-symbols-outlined">speed</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="py-20 px-6 bg-white dark:bg-slate-900">
      <div class="max-w-7xl mx-auto">
        <div class="text-center mb-16">
          <h2 class="text-4xl font-bold text-slate-900 dark:text-white mb-4">强大的功能特性</h2>
          <p class="text-lg text-slate-600 dark:text-slate-400">AI驱动的全流程营销自动化</p>
        </div>

        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="p-6 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-primary dark:hover:border-primary transition-all hover:shadow-lg"
          >
            <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <span class="material-symbols-outlined text-primary text-2xl">{{ feature.icon }}</span>
            </div>
            <h3 class="text-lg font-bold text-slate-900 dark:text-white mb-2">{{ feature.title }}</h3>
            <p class="text-sm text-slate-600 dark:text-slate-400">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Workflow Section -->
    <section id="workflow" class="py-20 px-6">
      <div class="max-w-7xl mx-auto">
        <div class="text-center mb-16">
          <h2 class="text-4xl font-bold text-slate-900 dark:text-white mb-4">自动化工作流</h2>
          <p class="text-lg text-slate-600 dark:text-slate-400">AI助手7x24小时为您工作</p>
        </div>

        <div class="grid lg:grid-cols-2 gap-8">
          <div
            v-for="workflow in workflows"
            :key="workflow.title"
            class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
          >
            <div class="p-6 border-b border-slate-200 dark:border-slate-700">
              <div class="flex items-center justify-between">
                <h3 class="text-xl font-bold text-slate-900 dark:text-white">{{ workflow.title }}</h3>
                <span class="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                  <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  {{ workflow.status === 'running' ? '运行中' : '已完成' }}
                </span>
              </div>
            </div>
            <div class="p-6">
              <div class="space-y-4">
                <div
                  v-for="(task, index) in workflow.tasks"
                  :key="index"
                  class="flex items-center gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50"
                >
                  <span class="material-symbols-outlined text-slate-400">check_circle</span>
                  <div class="flex-1">
                    <p class="text-sm font-medium text-slate-900 dark:text-white">{{ task.name }}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">{{ task.time }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 px-6 bg-gradient-to-r from-primary/10 to-purple-500/10 dark:from-primary/20 dark:to-purple-500/20">
      <div class="max-w-4xl mx-auto text-center">
        <h2 class="text-4xl font-bold text-slate-900 dark:text-white mb-4">准备好开始了吗？</h2>
        <p class="text-lg text-slate-600 dark:text-slate-400 mb-8">
          立即体验AI驱动的智能营销，让增长变得简单高效
        </p>
        <button
          class="px-8 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl hover:bg-slate-800 dark:hover:bg-slate-100 transition-all font-medium text-lg shadow-lg hover:shadow-xl"
          @click="handleGetStarted"
        >
          免费开始使用
        </button>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-12 px-6 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
      <div class="max-w-7xl mx-auto">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-2xl">rocket_launch</span>
            <span class="text-lg font-bold text-slate-900 dark:text-white">ANIFORCE</span>
          </div>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            © 2024 ANIFORCE. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>
