<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

const activePanel = ref('system-admin')
const activeSession = ref('sess_g001')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false }
])

const showSystemPanel = ref(false)
const showUserManagementPanel = ref(false)

const adminCards = [
  {
    id: 'system',
    icon: 'tune',
    title: '系统设置',
    description: '配置默认偏好、通知、权限和系统级策略',
    action: '进入系统设置',
    enabled: false,
    path: ''
  },
  {
    id: 'user-management',
    icon: 'group',
    title: '全局账号管理',
    description: '查看和管理系统中的所有用户、角色权限和账号状态',
    action: '管理用户账号',
    enabled: true,
    path: ''
  }
]

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleCardClick = (cardId: string) => {
  const card = adminCards.find(c => c.id === cardId)

  if (card?.path) {
    router.push(card.path)
    return
  }

  switch (cardId) {
    case 'system':
      showSystemPanel.value = true
      showUserManagementPanel.value = false
      break
    case 'user-management':
      showUserManagementPanel.value = true
      showSystemPanel.value = false
      break
  }
}

const backToCards = () => {
  showSystemPanel.value = false
  showUserManagementPanel.value = false
}

onMounted(() => {
  console.log('系统管理页面加载')
})
</script>

<template>
  <div class="workspace-page-canvas flex h-screen w-full overflow-hidden dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div data-workspace-page-header class="workspace-page-header flex shrink-0 items-center justify-between gap-[20px] border-b border-[#e5e3df] bg-white/90 px-[clamp(24px,3vw,48px)] dark:border-slate-800 dark:bg-slate-900">
        <div class="flex min-w-0 items-center gap-[8px]">
          <span class="grid h-[26px] w-[26px] place-items-center rounded-[6px] bg-[#f6f5f4] text-[#37352f] dark:bg-slate-800 dark:text-slate-300">
            <span class="material-symbols-outlined text-[16px]">admin_panel_settings</span>
          </span>
          <div class="min-w-0">
            <h1 class="m-0 text-[16px] font-semibold tracking-[-0.2px] text-[#1a1a1a] dark:text-white">系统管理</h1>
            <p class="mt-[2px] text-[10px] font-normal leading-[1.2] text-[#787671] dark:text-slate-400">管理系统配置和全局用户账号</p>
          </div>
        </div>
      </div>

      <div class="system-admin-scroll-area">
        <div class="system-admin-content">
        <!-- 卡片式管理入口 -->
        <div v-if="!showSystemPanel && !showUserManagementPanel" class="system-admin-grid">
          <button
            v-for="card in adminCards"
            :key="card.id"
            class="system-admin-card"
            :class="{ 'system-admin-card-disabled': !card.enabled }"
            type="button"
            :disabled="!card.enabled"
            @click="handleCardClick(card.id)"
          >
            <span class="system-admin-card-icon" aria-hidden="true">
              <span class="material-symbols-outlined">{{ card.icon }}</span>
            </span>
            <h2>{{ card.title }}</h2>
            <p>{{ card.description }}</p>
            <span class="system-admin-card-link">
              {{ card.action }}
              <svg class="system-admin-arrow" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12h14M14 7l5 5-5 5" />
              </svg>
            </span>
          </button>
        </div>

        <!-- 系统设置详细面板 -->
        <div v-if="showSystemPanel" class="max-w-[750px] mx-auto">
          <div class="flex items-center gap-[8px] mb-[19px]">
            <button
              class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="backToCards"
            >
              <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">arrow_back</span>
            </button>
            <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">系统设置</h2>
          </div>
          <div class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-[23px] text-center">
            <span class="material-symbols-outlined text-slate-400 text-[37px] mb-[8px]">construction</span>
            <p class="text-[13px] text-slate-500 dark:text-slate-400">系统设置功能开发中...</p>
          </div>
        </div>

        <!-- 全局账号管理详细面板 -->
        <div v-if="showUserManagementPanel" class="max-w-[1200px] mx-auto">
          <div class="flex items-center gap-[8px] mb-[19px]">
            <button
              class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="backToCards"
            >
              <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">arrow_back</span>
            </button>
            <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">全局账号管理</h2>
          </div>
          <div class="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-[23px] text-center">
            <span class="material-symbols-outlined text-slate-400 text-[37px] mb-[8px]">group</span>
            <p class="text-[13px] text-slate-500 dark:text-slate-400">用户管理功能开发中...</p>
            <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-[8px]">后续将在此处查看和管理系统中的所有用户</p>
          </div>
        </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.system-admin-scroll-area {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.system-admin-content {
  width: min(100%, 1220px);
  margin: 0 auto;
  padding: 24px clamp(22px, 3vw, 38px) 72px;
}

.system-admin-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.system-admin-card {
  min-height: 170px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 20px;
  border: 1px solid #e5e3df;
  border-radius: 12px;
  background: #ffffff;
  color: #37352f;
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms ease, background-color 140ms ease;
}

.system-admin-card:hover {
  border-color: #c8c4be;
  background: #fafaf9;
}

.system-admin-card:focus-visible {
  outline: 2px solid #37352f;
  outline-offset: 2px;
}

.system-admin-card-disabled {
  cursor: not-allowed;
  opacity: .62;
}

.system-admin-card-disabled:hover {
  border-color: #e5e3df;
  background: #ffffff;
}

.system-admin-card-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  margin-bottom: 16px;
  border-radius: 8px;
  background: #f6f5f4;
  color: #37352f;
}

.system-admin-card-icon .material-symbols-outlined {
  font-size: 18px;
}

.system-admin-card h2 {
  margin: 0;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
}

.system-admin-card p {
  margin: 8px 0 18px;
  color: #787671;
  font-size: 11px;
  line-height: 1.55;
}

.system-admin-card-link {
  margin-top: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #37352f;
  font-size: 10px;
  font-weight: 550;
  line-height: 1.2;
}

.system-admin-arrow {
  width: 14px;
  height: 14px;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

@media (max-width: 900px) {
  .system-admin-grid {
    grid-template-columns: 1fr;
  }
}
</style>
