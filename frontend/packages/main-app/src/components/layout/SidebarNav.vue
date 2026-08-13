<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useAgentSession } from '@/composables/useAgentSession'
import AccountControls from '@/components/layout/AccountControls.vue'
import logoSvg from '@/assets/aniforce-logo-transparent.svg'

interface NavItem {
  id: string
  icon: string
  label: string
  path: string
}

interface Session {
  id: string
  name: string
  active: boolean
}

interface Props {
  navItems?: NavItem[]
  sessions?: Session[]
  activePanel?: string
  sessionActions?: boolean
  sessionCreate?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  navItems: () => [
    { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
    { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
    { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
    { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
    { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
  ],
  sessions: () => [],
  activePanel: '',
  sessionActions: false,
  sessionCreate: false
})

const emit = defineEmits<{
  'switch-panel': [item: NavItem]
  'switch-session': [session: Session]
  'rename-session': [session: Session]
  'delete-session': [session: Session]
  'create-session': []
}>()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const agent = useAgentSession()

const isAdmin = computed(() => auth.user?.system_role === 'ADMIN')

const agentSessions = computed(() =>
  agent.sessions.value.map(session => ({
    id: session.id,
    name: session.title || session.id,
    active: agent.activeSession.value?.id === session.id
  }))
)

const displaySessions = computed(() => agentSessions.value)

const SIDEBAR_COLLAPSED_KEY = 'animagus_sidebar_collapsed'
const isCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true')
const sidebarWidth = computed(() => isCollapsed.value ? '52px' : '205px')

const syncSidebarWidth = () => {
  document.documentElement.style.setProperty('--workspace-sidebar-width', sidebarWidth.value)
}

syncSidebarWidth()
watch(sidebarWidth, syncSidebarWidth)

onBeforeUnmount(() => {
  document.documentElement.style.removeProperty('--workspace-sidebar-width')
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed.value))
}

const isActivePanel = (itemId: string) => {
  if (props.activePanel) {
    return props.activePanel === itemId
  }
  const item = props.navItems.find(i => i.id === itemId)
  if (!item) return false
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

const handleNavClick = (item: NavItem) => {
  emit('switch-panel', item)
  if (item.path) {
    router.push(item.path)
  }
}

const handleLogoClick = () => {
  router.push('/home')
}

const handleSessionClick = (session: Session) => {
  if (route.path !== '/home') {
    router.push({ path: '/home', query: { session_id: session.id } })
    return
  }
  emit('switch-session', session)
}

const handleCreateSession = () => {
  if (route.path !== '/home') {
    router.push('/home')
    return
  }
  emit('create-session')
}

onMounted(() => {
  void agent.refreshSessions()
})
</script>

<template>
  <div
    class="sidebar-rail-spacer flex-none transition-all duration-300"
    :class="isCollapsed ? 'w-[52px]' : 'w-[205px]'"
    aria-hidden="true"
  />
  <aside
    class="sidebar-notion fixed bottom-0 left-0 top-0 z-50 flex flex-col transition-all duration-300"
    :class="isCollapsed ? 'w-[52px]' : 'w-[205px]'"
  >
    <div class="sidebar-brand-row" :class="{ 'is-collapsed': isCollapsed }">
      <button
        v-if="!isCollapsed"
        class="sidebar-brand-button"
        type="button"
        aria-label="返回首页"
        @click="handleLogoClick"
      >
        <img :src="logoSvg" alt="ANIFORCE" class="sidebar-brand-logo logo-blue" />
      </button>
      <button
        class="sidebar-collapse flex items-center justify-center transition-colors"
        type="button"
        :aria-label="isCollapsed ? '展开导航栏' : '收起导航栏'"
        @click="toggleCollapse"
      >
        <span class="material-symbols-outlined">
          {{ isCollapsed ? 'menu' : 'menu_open' }}
        </span>
      </button>
    </div>

    <nav class="sidebar-scroll flex-1 overflow-y-auto space-y-[20px] overflow-x-hidden">
      <div>
        <div class="sidebar-section-head mb-[6px]">
          <span v-if="!isCollapsed" class="sidebar-section-title text-[11px] font-semibold text-slate-500 dark:text-slate-400">功能导航</span>
        </div>
        <ul class="sidebar-nav-list space-y-[12px]">
          <li
            v-for="item in navItems"
            :key="item.id"
            class="sidebar-nav-item flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel(item.id)
                ? 'sidebar-item-active'
                : 'sidebar-item-idle'
            ]"
            @click="handleNavClick(item)"
          >
            <span class="material-symbols-outlined text-[15px]">{{ item.icon }}</span>
            <span v-if="!isCollapsed" class="text-[11px]">{{ item.label }}</span>

            <div
              v-if="isCollapsed"
              class="absolute left-full ml-[6px] px-[10px] py-[6px] bg-slate-900 dark:bg-slate-700 text-white text-[11px] rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity"
            >
              {{ item.label }}
            </div>
          </li>

          <li
            v-if="isAdmin"
            class="sidebar-nav-item flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel('system-admin')
                ? 'sidebar-item-active'
                : 'sidebar-item-idle'
            ]"
            @click="handleNavClick({ id: 'system-admin', icon: 'admin_panel_settings', label: '系统管理', path: '/system-admin' })"
          >
            <span class="material-symbols-outlined text-[15px]">admin_panel_settings</span>
            <span v-if="!isCollapsed" class="text-[11px]">系统管理</span>

            <div
              v-if="isCollapsed"
              class="absolute left-full ml-[6px] px-[10px] py-[6px] bg-slate-900 dark:bg-slate-700 text-white text-[11px] rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity"
            >
              系统管理
            </div>
          </li>
        </ul>
      </div>

      <div v-if="displaySessions.length > 0 && !isCollapsed" class="sidebar-session-group">
        <div class="sidebar-session-head mb-[6px] flex items-center justify-between px-[6px]">
          <span class="sidebar-section-title text-[10px] font-semibold text-slate-500 dark:text-slate-400">历史会话</span>
          <button
            v-if="sessionCreate"
            class="sidebar-create-session flex h-[22px] w-[22px] items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            title="新建对话"
            @click.stop="handleCreateSession"
          >
            <span class="material-symbols-outlined text-[14px]">add</span>
          </button>
        </div>
        <ul class="sidebar-session-list space-y-[4px]">
          <li
            v-for="session in displaySessions"
            :key="session.id"
            class="sidebar-session-item group flex items-center gap-[6px] px-[10px] py-[6px] rounded-lg cursor-pointer transition-all"
            :class="session.active
              ? 'sidebar-item-active'
              : 'sidebar-item-idle'"
            @click="handleSessionClick(session)"
          >
            <span class="material-symbols-outlined text-[11px]">chat</span>
            <span class="text-[11px] flex-1 truncate">{{ session.name }}</span>
            <div v-if="sessionActions" class="opacity-0 group-hover:opacity-100 flex items-center gap-[4px]">
              <button class="p-[4px] hover:bg-slate-200 dark:hover:bg-slate-700 rounded" title="重命名" @click.stop="emit('rename-session', session)">
                <span class="material-symbols-outlined text-[10px]">edit</span>
              </button>
              <button class="p-[4px] hover:bg-slate-200 dark:hover:bg-slate-700 rounded" title="删除" @click.stop="emit('delete-session', session)">
                <span class="material-symbols-outlined text-[10px]">delete</span>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <AccountControls variant="sidebar" :collapsed="isCollapsed" />
  </aside>
</template>

<style scoped>
.sidebar-notion {
  --sidebar-canvas: #f7f7f5;
  --sidebar-surface: #efefed;
  --sidebar-surface-hover: #e9e9e7;
  --sidebar-line: #e5e3df;
  --sidebar-ink: #1a1a1a;
  --sidebar-charcoal: #37352f;
  --sidebar-slate: #5d5b54;
  --sidebar-steel: #787671;
  border-right: 0 !important;
  background: var(--sidebar-canvas) !important;
  color: var(--sidebar-charcoal);
  font-family: "Notion Sans", "Avenir Next", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.sidebar-notion::after {
  position: absolute;
  z-index: 2;
  top: 0;
  right: 0;
  bottom: 0;
  width: 16px;
  background: linear-gradient(90deg, rgba(55, 53, 47, 0) 0, rgba(55, 53, 47, 0.012) 34%, rgba(55, 53, 47, 0.032) 66%, rgba(55, 53, 47, 0.068) 100%);
  content: '';
  pointer-events: none;
}

.sidebar-brand-row {
  position: relative;
  z-index: 3;
  display: flex;
  height: 57px;
  min-height: 57px;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 0 16px;
}

.sidebar-brand-row.is-collapsed {
  justify-content: center;
  padding: 0;
}

.sidebar-brand-button {
  display: flex;
  min-width: 0;
  align-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.sidebar-brand-logo {
  width: auto;
  height: 30px;
  max-width: 94px;
  object-fit: contain;
}

.logo-blue {
  filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);
}

.sidebar-scroll {
  position: relative;
  z-index: 1;
  padding: 4px 8px 12px !important;
}

.sidebar-section-head,
.sidebar-session-head {
  min-height: 28px;
  margin-bottom: 4px !important;
  padding: 0 6px !important;
}

.sidebar-section-title {
  color: var(--sidebar-steel) !important;
  font-size: 10px !important;
  font-weight: 600 !important;
  line-height: 1.4;
  letter-spacing: 0.01em;
}

.sidebar-collapse,
.sidebar-create-session {
  border: 0;
  border-radius: 6px !important;
  background: transparent;
  color: var(--sidebar-steel) !important;
}

.sidebar-collapse {
  width: 28px;
  height: 28px;
  padding: 0 !important;
}

.sidebar-collapse:hover,
.sidebar-create-session:hover {
  background: var(--sidebar-surface-hover) !important;
  color: var(--sidebar-ink) !important;
}

.sidebar-collapse .material-symbols-outlined {
  color: inherit !important;
  font-size: 16px !important;
}

.sidebar-nav-list,
.sidebar-session-list {
  display: grid;
  gap: 2px;
}

.sidebar-nav-item,
.sidebar-session-item {
  min-height: 34px;
  padding: 6px 8px !important;
  border-radius: 6px !important;
  font-weight: 400 !important;
  line-height: 1.35;
}

.sidebar-nav-item {
  gap: 9px !important;
}

.sidebar-nav-item > .material-symbols-outlined {
  width: 18px;
  flex: 0 0 18px;
  color: inherit;
  font-size: 17px !important;
  text-align: center;
}

.sidebar-nav-item > span:not(.material-symbols-outlined),
.sidebar-session-item > span:last-of-type {
  color: inherit;
  font-size: 11px !important;
  font-weight: inherit;
}

.sidebar-item-idle {
  color: var(--sidebar-slate) !important;
}

.sidebar-item-idle:hover {
  background: var(--sidebar-surface-hover) !important;
  color: var(--sidebar-charcoal) !important;
}

.sidebar-item-active {
  background: var(--sidebar-surface) !important;
  color: var(--sidebar-ink) !important;
  font-weight: 500 !important;
}

.sidebar-session-group {
  margin-top: 18px;
}

.sidebar-session-item {
  gap: 7px !important;
}

.sidebar-session-item > .material-symbols-outlined {
  width: 16px;
  flex: 0 0 16px;
  font-size: 15px !important;
}

.sidebar-session-item button {
  border-radius: 4px !important;
  color: var(--sidebar-steel) !important;
}

.sidebar-session-item button:hover {
  background: rgba(55, 53, 47, 0.08) !important;
  color: var(--sidebar-ink) !important;
}

nav::-webkit-scrollbar {
  width: 3px;
}
nav::-webkit-scrollbar-thumb {
  background-color: var(--sidebar-line);
  border-radius: 1px;
}
nav::-webkit-scrollbar-thumb:hover {
  background-color: #c8c4be;
}

:global(.dark) .sidebar-notion::after {
  background: linear-gradient(90deg, rgba(0, 0, 0, 0) 0, rgba(0, 0, 0, 0.05) 34%, rgba(0, 0, 0, 0.12) 66%, rgba(0, 0, 0, 0.2) 100%);
}
</style>
