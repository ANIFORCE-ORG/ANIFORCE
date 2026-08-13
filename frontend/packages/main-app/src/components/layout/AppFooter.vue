<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLanguage } from '@/store/language'

const route = useRoute()
const { language } = useLanguage()
const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)
const isHomeWorkspace = computed(() => route.name === 'home')

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
  <footer
    :class="[
      'app-footer mt-auto border-t border-slate-200 px-5 py-3 dark:border-slate-800 md:px-10',
      {
        'app-footer--workspace': isWorkspaceShell,
        'app-footer--home': isHomeWorkspace
      }
    ]"
  >
    <div class="flex flex-row items-center justify-between gap-2">
      <!-- 左侧：版权信息、品牌归属、联系方式 -->
      <div class="flex items-center gap-5 text-left">
        <span class="text-[10px] text-slate-500">{{ copy[language].copyright }}</span>
        <a class="text-[10px] text-slate-500 hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
        <a class="text-[10px] text-slate-500 hover:text-primary" href="https://beian.mps.gov.cn/#/query/webSearch?code=44010602016311"" target="_blank" rel="noreferrer">粤公网安备44010602016311号</a>
      </div>

      <!-- 右侧：网站链接 + 备案 + 导航链接 -->
      <div class="flex flex-col items-center gap-2 lg:items-end">
        <!-- 导航链接 -->
        <div class="flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 lg:justify-end">
          <RouterLink class="text-[10px] text-slate-500 hover:text-primary" to="/privacy">{{ copy[language].privacy }}</RouterLink>
          <RouterLink class="text-[10px] text-slate-500 hover:text-primary" to="/terms">{{ copy[language].terms }}</RouterLink>
          <RouterLink class="text-[10px] text-slate-500 hover:text-primary" to="/contact">{{ copy[language].contact }}</RouterLink>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer--workspace {
  padding-left: calc(var(--workspace-sidebar-width, 205px) + 40px) !important;
}

.app-footer--home {
  border-top: 0 !important;
}

@media (max-width: 767px) {
  .app-footer--workspace {
    padding-right: 12px !important;
    padding-left: calc(var(--workspace-sidebar-width, 205px) + 12px) !important;
  }

  .app-footer--workspace > div,
  .app-footer--workspace > div > div:first-child {
    min-width: 0;
    flex-wrap: wrap;
  }

  .app-footer--workspace a {
    overflow-wrap: anywhere;
  }
}
</style>
