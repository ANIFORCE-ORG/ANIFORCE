<script setup lang="ts">
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    home: '首页',
    start: '马上体验',
  },
  en: {
    home: 'Home',
    start: 'Start now',
  },
}
</script>

<template>
  <footer class="mt-auto py-2 border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-background-dark/50 px-6 md:px-12">
    <div class="flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-6">
        <span class="text-xs text-slate-400">&copy; 2026 aniforce Ltd.</span>
      </div>
      <div class="flex items-center gap-6">
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/">{{ copy[language].home }}</RouterLink>
        <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/contact">{{ copy[language].start }}</RouterLink>
      </div>
    </div>
  </footer>
</template>
