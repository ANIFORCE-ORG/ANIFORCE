<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import MetaConfigDialog from '@/components/settings/MetaConfigDialog.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const activePlatform = ref<'meta' | 'google' | 'tiktok'>('meta')
const showConfigDialog = ref(false)

const platforms = [
  {
    id: 'meta',
    label: 'Meta',
    title: 'Meta Business OAuth',
    description: '连接 Facebook / Instagram 广告账户，支持真实创建 Campaign',
    status: 'available',
    keywords: ['Facebook', 'Instagram', 'Meta Business', 'Campaign'],
  },
  {
    id: 'google',
    label: 'Google',
    title: 'Google Ads OAuth',
    description: '连接 Google Ads 账号，后续同步客户账号和投放计划',
    status: 'available',
    keywords: ['Google Ads', 'Google Marketing', 'AdWords', 'Campaign'],
  },
  {
    id: 'tiktok',
    label: 'TikTok',
    title: 'TikTok Ads OAuth',
    description: '连接 TikTok Ads 账号，后续同步广告账户和计划创建能力',
    status: 'available',
    keywords: ['TikTok Ads', 'TikTok Marketing', 'Douyin', 'Campaign'],
  },
] as const

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const openConfigDialog = () => {
  showConfigDialog.value = true
}

const closeConfigDialog = () => {
  showConfigDialog.value = false
}

const handleSaveConfig = (data: any) => {
  console.log('保存配置:', data)
}

const handleImportToken = (data: any) => {
  console.log('导入沙盒账户:', data)
}

onMounted(() => {
  console.log('平台连接页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="[]"
      active-panel="settings"
      @switch-panel="switchPanel"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">平台连接</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">配置 Meta、Google、TikTok 的平台授权和广告账户同步</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="space-y-6">
          <!-- 平台选择卡片 -->
          <div class="grid grid-cols-3 gap-3">
            <button
              v-for="platform in platforms"
              :key="platform.id"
              class="rounded-md border p-4 text-left transition-colors hover:border-primary/50"
              :class="activePlatform === platform.id 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700'"
              @click="activePlatform = platform.id"
            >
              <div class="flex items-center justify-between">
                <div class="font-semibold text-slate-900 dark:text-white">{{ platform.label }}</div>
                <span class="rounded px-2 py-1 text-xs font-medium bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                  待接入
                </span>
              </div>
              <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">{{ platform.description }}</p>
            </button>
          </div>

          <!-- 平台详细配置 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
            <div class="flex items-center gap-2 mb-4">
              <span class="material-symbols-outlined text-primary">hub</span>
              <h2 class="text-sm font-semibold text-slate-900 dark:text-white">
                {{ platforms.find(p => p.id === activePlatform)?.title }}
              </h2>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
              {{ platforms.find(p => p.id === activePlatform)?.description }}
            </p>

            <!-- 连接流程 -->
            <div class="grid gap-2 text-xs text-slate-600 dark:text-slate-400 md:grid-cols-4 mb-6">
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                1. 配置应用信息
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                2. 发起 OAuth 授权
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                3. 平台确认权限
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                4. 同步广告账户
              </div>
            </div>

            <!-- 开发中提示 -->
            <div class="p-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-4">
              <div class="flex items-start gap-3">
                <span class="material-symbols-outlined text-amber-600 dark:text-amber-400 text-xl">construction</span>
                <div>
                  <div class="text-sm font-medium text-amber-900 dark:text-amber-200 mb-1">
                    {{ platforms.find(p => p.id === activePlatform)?.label }} 平台连接功能开发中
                  </div>
                  <p class="text-xs text-amber-700 dark:text-amber-300">
                    当前版本正在完善平台连接功能，包括应用配置、OAuth 授权、账户同步、Campaign 创建等核心能力，敬请期待。
                  </p>
                </div>
              </div>
            </div>

            <!-- Meta 平台特殊功能 -->
            <div v-if="activePlatform === 'meta'" class="flex items-center justify-between">
              <p class="text-sm text-slate-600 dark:text-slate-400">配置 Meta 广告账户连接</p>
              <button
                class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                @click="openConfigDialog"
              >
                添加广告账户
              </button>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Meta 配置弹窗组件 -->
    <MetaConfigDialog
      :show="showConfigDialog"
      @close="closeConfigDialog"
      @save="handleSaveConfig"
      @import="handleImportToken"
    />
  </div>
</template>
