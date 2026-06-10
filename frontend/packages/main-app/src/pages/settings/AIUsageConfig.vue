<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

const activePanel = ref('settings')
const activeSession = ref('sess_g001')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false }
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

onMounted(() => {
  console.log('AI 使用量配置页面加载')
})
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-[19px] py-[12px]">
        <div class="flex items-center gap-[12px]">
          <button
            class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">arrow_back</span>
          </button>
          <div>
            <h1 class="text-[15px] font-bold text-slate-900 dark:text-white">AI 使用量</h1>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">查看模型调用、Token 消耗、场景日志和预算限制</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-[19px]">
        <div class="space-y-[19px]">
          <!-- 开发中提示 -->
          <div class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md p-[25px] text-center">
            <span class="material-symbols-outlined text-slate-400 text-[39px] mb-[9px]">analytics</span>
            <p class="text-[13px] text-slate-500 dark:text-slate-400">AI 使用量统计功能开发中...</p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
