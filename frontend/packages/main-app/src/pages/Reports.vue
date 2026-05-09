<script setup lang="ts">
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ReportsContent from '@/components/home/workspace/ReportsContent.vue'

const router = useRouter()

const switchPanel = (item: { path: string }) => {
  if (item.path) router.push(item.path)
}
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav active-panel="reports" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white">数据报表</h1>
          <p class="text-sm text-slate-500 mt-1">汇总计划消耗、安装、ROI、平台对比、素材排行和策略洞察</p>
        </div>
      </div>

      <div class="p-6">
        <ReportsContent />
      </div>
    </main>
  </div>
</template>
