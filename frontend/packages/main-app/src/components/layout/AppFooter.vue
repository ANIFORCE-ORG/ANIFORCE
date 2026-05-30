<script setup lang="ts">
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    home: '首页',
    product: '产品功能',
    automation: '自动化工作流',
    performance: '广告效果',
  },
  en: {
    home: 'Home',
    product: 'Product',
    automation: 'Automation',
    performance: 'Performance',
  },
}
</script>

<template>
  <footer class="mt-auto py-2 border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-background-dark/50 px-6 md:px-12">
    <div class="flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 md:justify-start">
        <span class="text-xs text-slate-400">&copy; 2026 aniforce Ltd.</span>
        <a class="text-xs text-slate-500 hover:text-primary" href="https://aniforce.cc">aniforce.cc</a>
        <a class="text-xs text-slate-500 hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
      </div>
      <div class="flex items-center gap-6">
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/">{{ copy[language].home }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#features">{{ copy[language].product }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#automation">{{ copy[language].automation }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#performance">{{ copy[language].performance }}</RouterLink>
      </div>
    </div>
  </footer>
</template>
