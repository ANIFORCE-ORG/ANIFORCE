<script setup lang="ts">
import { ref } from 'vue'
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

const settingCards = [
  {
    id: 'agent-account',
    title: '系统账号设置',
    description: '管理团队成员、登录身份和基础账号信息。',
    action: '进入账号设置',
    path: '/account-config',
    icon: 'account'
  },
  {
    id: 'platform-connections',
    title: '平台连接',
    description: '连接 Meta、Google、TikTok 广告平台和同步广告账户。',
    action: '管理平台连接',
    path: '/platform-connections',
    icon: 'platform'
  },
  {
    id: 'ai-usage',
    title: 'AI 使用量',
    description: '查看模型调用、Token 消耗、场景日志和预算限制。',
    action: '查看使用量',
    path: '/ai-usage-config',
    icon: 'usage'
  }
]

const switchPanel = (item: any) => {
  if (item.path) router.push(item.path)
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(item => {
    item.active = item.id === session.id
  })
}

const openSetting = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="settings-shell workspace-page-canvas">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      :active-panel="activePanel"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="settings-main">
      <header data-workspace-page-header class="settings-page-head workspace-page-header">
        <div class="settings-page-title-wrap workspace-page-heading">
          <span class="settings-page-icon workspace-page-heading-icon">
            <span class="material-symbols-outlined">settings</span>
          </span>
          <div class="settings-page-title workspace-page-heading-text">
            <h1>设置</h1>
          </div>
        </div>
      </header>

      <div class="settings-scroll-area">
        <div class="settings-content workspace-page-content">
          <div class="settings-grid">
            <button
              v-for="card in settingCards"
              :key="card.id"
              class="settings-card"
              type="button"
              @click="openSetting(card.path)"
            >
              <span class="settings-card-icon" aria-hidden="true">
                <svg v-if="card.icon === 'account'" class="settings-icon" viewBox="0 0 24 24">
                  <circle cx="9" cy="8" r="3" />
                  <path d="M4 19c0-3 2-5 5-5 1.2 0 2.3.3 3.1.9M17 12l4 1.7V17c0 2.2-1.3 3.8-4 5-2.7-1.2-4-2.8-4-5v-3.3z" />
                </svg>
                <svg v-else-if="card.icon === 'platform'" class="settings-icon" viewBox="0 0 24 24">
                  <circle cx="12" cy="5" r="2" />
                  <circle cx="5" cy="12" r="2" />
                  <circle cx="19" cy="12" r="2" />
                  <circle cx="12" cy="19" r="2" />
                  <path d="M10.5 6.5L6.5 10.5M13.5 6.5l4 4M6.5 13.5l4 4M17.5 13.5l-4 4" />
                </svg>
                <svg v-else class="settings-icon" viewBox="0 0 24 24">
                  <path d="M4 17l6-6 4 4 6-8M15 7h5v5" />
                </svg>
              </span>
              <h2>{{ card.title }}</h2>
              <p>{{ card.description }}</p>
              <span class="settings-card-link">
                {{ card.action }}
                <svg class="settings-arrow" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h14M14 7l5 5-5 5" />
                </svg>
              </span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.settings-shell {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: var(--workspace-canvas);
  color: #37352f;
}

.settings-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--workspace-canvas);
}

.settings-page-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 clamp(24px, 3vw, 48px);
  border-bottom: 1px solid #e5e3df;
  background: rgba(255, 255, 255, .88);
}

.settings-page-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-page-icon {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: #f6f5f4;
  color: #37352f;
}

.settings-page-icon .material-symbols-outlined {
  font-size: 16px;
}

.settings-page-title {
  min-width: 0;
}

.settings-page-title h1 {
  margin: 0;
  color: #1a1a1a;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.2px;
}

.settings-page-title p {
  margin: 2px 0 0;
  color: #787671;
  font-size: 10px;
  font-weight: 400;
  line-height: 1.2;
}

.settings-scroll-area {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.settings-content {
  width: min(100%, 1220px);
  margin: 0 auto;
  padding: 24px clamp(22px, 3vw, 38px) 72px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.settings-card {
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

.settings-card:hover {
  border-color: #c8c4be;
  background: #fafaf9;
}

.settings-card:focus-visible {
  outline: 2px solid #37352f;
  outline-offset: 2px;
}

.settings-card-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  margin-bottom: 16px;
  border-radius: 8px;
  background: #f6f5f4;
  color: #37352f;
}

.settings-icon,
.settings-arrow {
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.settings-icon {
  width: 18px;
  height: 18px;
}

.settings-card h2 {
  margin: 0;
  color: #1a1a1a;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
}

.settings-card p {
  margin: 8px 0 18px;
  color: #787671;
  font-size: 13px;
  line-height: 1.55;
}

.settings-card-link {
  margin-top: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #37352f;
  font-size: 12px;
  font-weight: 550;
  line-height: 1.2;
}

.settings-arrow {
  width: 14px;
  height: 14px;
}

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
