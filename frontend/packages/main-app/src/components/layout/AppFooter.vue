<script setup lang="ts">
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    privacy: '隐私政策',
    terms: '服务条款',
    contact: '联系我们',
    copyright: '© 2026 aniforce. 保留所有权利。',
  },
  en: {
    privacy: 'Privacy Policy',
    terms: 'Terms of Service',
    contact: 'Contact',
    copyright: '© 2026 aniforce. All rights reserved.',
  },
}
</script>

<template>
  <footer class="mt-auto border-t border-slate-200 bg-white/70 px-6 py-3 dark:border-slate-800 dark:bg-background-dark/50 md:px-12">
    <div class="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-center lg:justify-between lg:text-left">
      <span class="text-xs text-slate-500">{{ copy[language].copyright }}</span>
      <div class="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 lg:justify-end">
        <a class="text-xs text-slate-500 hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/privacy">{{ copy[language].privacy }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/terms">{{ copy[language].terms }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/#contact">{{ copy[language].contact }}</RouterLink>
      </div>
    </div>
  </footer>
</template>
