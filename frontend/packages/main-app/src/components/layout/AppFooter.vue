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
    v-if="!isWorkspaceShell"
    :class="[
      'app-footer mt-auto border-t border-slate-200 px-5 py-3 dark:border-slate-800 md:px-10',
      {
        'app-footer--workspace': isWorkspaceShell,
        'app-footer--home': isHomeWorkspace
      }
    ]"
  >
    <div class="app-footer-content">
      <span class="app-footer-item">{{ copy[language].copyright }}</span>
      <a class="app-footer-item hover:text-primary" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">粤ICP备2026067584号-1</a>
      <a class="app-footer-item hover:text-primary" href="https://beian.mps.gov.cn/#/query/webSearch?code=44010602016311" target="_blank" rel="noreferrer">粤公网安备44010602016311号</a>
      <RouterLink class="app-footer-item hover:text-primary" to="/privacy">{{ copy[language].privacy }}</RouterLink>
      <RouterLink class="app-footer-item hover:text-primary" to="/terms">{{ copy[language].terms }}</RouterLink>
      <RouterLink class="app-footer-item hover:text-primary" to="/contact">{{ copy[language].contact }}</RouterLink>
    </div>
  </footer>
</template>

<style scoped>
.app-footer-content {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: flex-end;
  gap: 32px;
}

.app-footer-item {
  flex: none;
  color: #64748b;
  font-size: 10px;
  text-align: right;
  white-space: nowrap;
}

.app-footer--workspace {
  box-sizing: border-box;
  height: 57px;
  min-height: 57px;
  display: flex;
  align-items: center;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  padding-left: calc(var(--workspace-sidebar-width, 240px) + 40px) !important;
  border-top: 1px solid rgba(55, 53, 47, 0.08) !important;
  background: #f7f7f5;
}

.app-footer--home:not(.app-footer--workspace) {
  border-top: 0 !important;
}

@media (max-width: 767px) {
  .app-footer-content {
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px 12px;
  }

  .app-footer-item {
    text-align: center;
    white-space: normal;
  }

  .app-footer--workspace {
    height: auto;
    min-height: 57px;
    padding-top: 12px !important;
    padding-bottom: 12px !important;
    padding-right: 12px !important;
    padding-left: calc(var(--workspace-sidebar-width, 240px) + 12px) !important;
  }

  .app-footer--workspace a {
    overflow-wrap: anywhere;
  }
}
</style>
