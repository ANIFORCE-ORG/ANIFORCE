<script setup lang="ts">
import { useLanguage } from '@/store/language'

const { language } = useLanguage()

const copy = {
  cn: {
    home: '首页',
    features: '产品功能',
    help: '使用帮助',
    api: 'API文档',
    privacy: '隐私政策',
    terms: '服务条款',
    contact: '联系我们',
    copyright: '© 2026 ANIFORCE Ltd. 保留所有权利。'
  },
  en: {
    home: 'Home',
    features: 'Features',
    help: 'Help',
    api: 'API Docs',
    privacy: 'Privacy Policy',
    terms: 'Terms of Service',
    contact: 'Contact',
    copyright: '© 2026 ANIFORCE Ltd. All rights reserved.'
  },
}
</script>

<template>
  <footer class="mt-auto border-t border-slate-200 bg-white/70 px-6 py-4 dark:border-slate-800 dark:bg-background-dark/50 md:px-12">
    <div class="flex flex-row items-center justify-between gap-4">
      <!-- 左侧：版权信息、品牌归属、联系方式 -->
      <div class="flex items-center gap-6 text-left">
        <span class="text-xs text-slate-500">{{ copy[language].copyright }}</span>
        <a class="text-xs text-slate-500 hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
      </div>

      <!-- 右侧：网站链接 + 备案 + 导航链接 -->
      <div class="flex flex-col items-center gap-3 lg:items-end">
        <!-- 导航链接 -->
        <div class="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-end">
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/privacy">{{ copy[language].privacy }}</RouterLink>
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/terms">{{ copy[language].terms }}</RouterLink>
          <RouterLink class="text-xs text-slate-500 hover:text-primary" to="/contact">{{ copy[language].contact }}</RouterLink>
        </div>
      </div>
    </div>
  </footer>
</template>
