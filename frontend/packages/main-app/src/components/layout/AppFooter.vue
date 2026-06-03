<script setup lang="ts">
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    home: '首页',
    product: '产品功能',
    automation: '自动化工作流',
    performance: '广告效果',
    privacy: '隐私政策',
    terms: '服务条款',
    contact: '联系我们',
    copyright: '© 2026 aniforce. 保留所有权利。',
    ownership: 'ANIFORCE 是由 aniforce 拥有并运营的产品和品牌。',
  },
  en: {
    home: 'Home',
    product: 'Product',
    automation: 'Automation',
    performance: 'Performance',
    privacy: 'Privacy Policy',
    terms: 'Terms of Service',
    contact: 'Contact',
    copyright: '© 2026 aniforce. All rights reserved.',
    ownership: 'ANIFORCE is a product and brand owned and operated by aniforce.',
  },
}
</script>

<template>
  <footer class="mt-auto border-t border-slate-200 bg-white/70 px-6 py-4 dark:border-slate-800 dark:bg-background-dark/50 md:px-12">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex flex-col items-center gap-2 text-center lg:items-start lg:text-left">
        <span class="text-xs text-slate-500">{{ copy[language].copyright }}</span>
        <span class="text-xs text-slate-500">{{ copy[language].ownership }}</span>
        <span class="text-xs text-slate-500">Contact: <a class="font-medium text-primary hover:underline" href="mailto:support@aniforce.cc">support@aniforce.cc</a></span>
      </div>

      <div class="flex flex-col items-center gap-3 lg:items-end">
        <div class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-end">
        <a class="text-xs text-slate-500 hover:text-primary" href="https://aniforce.cc">aniforce.cc</a>
        <a class="text-xs text-slate-500 hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
      </div>
        <div class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-end">
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/">{{ copy[language].home }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#features">{{ copy[language].product }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#automation">{{ copy[language].automation }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#performance">{{ copy[language].performance }}</RouterLink>
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/privacy">{{ copy[language].privacy }}</RouterLink>
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/terms">{{ copy[language].terms }}</RouterLink>
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/contact">{{ copy[language].contact }}</RouterLink>
        </div>
      </div>
    </div>
  </footer>
</template>
