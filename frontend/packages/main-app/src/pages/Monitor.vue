<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

const activeSession = ref('sess_m001')
const sessions = ref([
  { id: 'sess_m001', name: '数据分析咨询', active: true },
  { id: 'sess_m002', name: '优化建议', active: false },
  { id: 'sess_m003', name: '效果监控', active: false },
])

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧功能导航 -->
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间核心工作区 -->
    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <!-- Header -->
      <div class="h-[50px] border-b border-slate-200 dark:border-slate-800 flex items-center px-[19px]">
        <div class="flex items-center gap-[9px]">
          <span class="material-symbols-outlined text-primary text-[19px]">analytics</span>
          <h1 class="text-[17px] font-bold text-slate-900 dark:text-white">投放数据分析</h1>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-[19px]">
        <div class="max-w-5xl mx-auto">
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-[37px] text-center">
            <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-600 mb-[12px]">construction</span>
            <p class="text-[15px] text-slate-500 dark:text-slate-400">投放数据分析功能开发中...</p>
            <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-[6px]">实时监控投放效果与 AI 优化建议</p>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>
