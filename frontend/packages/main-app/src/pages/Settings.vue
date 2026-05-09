<script setup lang="ts">
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'

const router = useRouter()

const settingCards = [
  {
    id: 'agent-account',
    icon: 'admin_panel_settings',
    title: 'Agent 系统账号',
    description: '管理团队成员、登录身份和基础账号信息',
    action: '进入账号设置',
    path: '',
  },
  {
    id: 'system',
    icon: 'tune',
    title: '系统设置',
    description: '配置默认偏好、通知、权限和系统级策略',
    action: '进入系统设置',
    path: '',
  },
  {
    id: 'platform-connections',
    icon: 'hub',
    title: '平台连接',
    description: '连接 Meta、Google、TikTok 广告平台和同步广告账户',
    action: '管理平台连接',
    path: '/platform-connections',
  },
]

const switchPanel = (item: { path: string }) => {
  if (item.path) router.push(item.path)
}
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav active-panel="settings" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <h1 class="text-xl font-bold text-slate-900 dark:text-white">设置</h1>
        <p class="text-sm text-slate-500 mt-1">管理 Agent 系统账号、系统配置和广告平台连接</p>
      </div>

      <div class="p-6 grid gap-4 md:grid-cols-3">
        <section
          v-for="card in settingCards"
          :key="card.id"
          class="rounded-md border border-slate-200 p-5 bg-white"
        >
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-2xl">{{ card.icon }}</span>
            <h2 class="font-semibold text-slate-900">{{ card.title }}</h2>
          </div>
          <p class="mt-3 text-sm text-slate-500 min-h-10">{{ card.description }}</p>
          <button
            class="mt-5 px-4 py-2 rounded-md text-sm font-medium"
            :class="card.path ? 'bg-primary text-white' : 'border border-slate-200 text-slate-500 cursor-not-allowed'"
            :disabled="!card.path"
            @click="card.path && router.push(card.path)"
          >
            {{ card.action }}
          </button>
        </section>
      </div>
    </main>
  </div>
</template>
