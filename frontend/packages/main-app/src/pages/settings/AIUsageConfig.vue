<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'
import '@/styles/settings-notion.css'

const router = useRouter()
const activePanel = ref('settings')
const activeSession = ref('sess_g001')
const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false }
])

const switchPanel = (item: any) => {
  if (item.path) router.push(item.path)
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(item => {
    item.active = item.id === session.id
  })
}
</script>

<template>
  <div class="settings-notion workspace-page-canvas">
    <SidebarNav :nav-items="navItems" :sessions="sessions" :active-panel="activePanel" @switch-panel="switchPanel" @switch-session="switchSession" />
    <main class="sn-main">
      <header data-workspace-page-header class="sn-page-head workspace-page-header">
        <button class="sn-back" type="button" aria-label="返回设置" @click="router.push('/settings')"><svg class="sn-icon" viewBox="0 0 24 24"><path d="M19 12H5M10 7l-5 5 5 5" /></svg></button>
        <div class="sn-page-title"><h1>AI 使用量</h1><p>查看模型调用、Token 消耗、场景日志和预算限制</p></div>
      </header>
      <div class="sn-scroll">
        <div class="sn-content">
          <section class="sn-empty-state">
            <span class="sn-empty-icon"><svg class="sn-icon" style="width:25px;height:25px" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M7 17v-4M12 17V8M17 17v-7" /></svg></span>
            <h2>AI 使用量统计功能开发中</h2>
            <p>后续将在这里集中展示模型调用次数、Token 消耗趋势、任务场景日志和预算预警。</p>
            <span class="sn-development">预计后续版本开放</span>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>
