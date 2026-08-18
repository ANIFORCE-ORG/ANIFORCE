<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useAgentSession } from '@/composables/useAgentSession'
import AccountControls from '@/components/layout/AccountControls.vue'
import SessionRenameDialog from '@/components/layout/SessionRenameDialog.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
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
  sessionActions: true,
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
const openSessionMenuId = ref<string | null>(null)
const localRenameDialog = ref<Session | null>(null)
const localRenameValue = ref('')
const localDeleteDialog = ref<Session | null>(null)

const closeSessionMenu = () => {
  openSessionMenuId.value = null
}

const toggleSessionMenu = (sessionId: string) => {
  openSessionMenuId.value = openSessionMenuId.value === sessionId ? null : sessionId
}

const openSessionMenu = (sessionId: string) => {
  openSessionMenuId.value = sessionId
}

const handleRenameSession = (session: Session) => {
  closeSessionMenu()
  if (route.path === '/home') {
    emit('rename-session', session)
    return
  }
  localRenameDialog.value = session
  localRenameValue.value = session.name
  nextTick(() => document.querySelector<HTMLInputElement>('[data-sidebar-session-rename-input]')?.focus())
}

const handleDeleteSession = (session: Session) => {
  closeSessionMenu()
  if (route.path === '/home') {
    emit('delete-session', session)
    return
  }
  localDeleteDialog.value = session
}

const confirmLocalRename = async () => {
  const session = localRenameDialog.value
  const title = localRenameValue.value.trim()
  if (!session || !title) return
  await agent.renameSession(session.id, title)
  localRenameDialog.value = null
}

const confirmLocalDelete = async () => {
  const session = localDeleteDialog.value
  if (!session) return
  await agent.deleteSession(session.id)
  localDeleteDialog.value = null
}

const handleDocumentClick = () => {
  closeSessionMenu()
}

const SIDEBAR_COLLAPSED_KEY = 'animagus_sidebar_collapsed'
const isCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true')
const isNarrowViewport = ref(false)
const mobileExpanded = ref(false)
const isSidebarCollapsed = computed(() => isNarrowViewport.value ? !mobileExpanded.value : isCollapsed.value)
const sidebarWidth = computed(() => isSidebarCollapsed.value ? '52px' : '240px')
const layoutSidebarWidth = computed(() => isNarrowViewport.value ? '52px' : sidebarWidth.value)
let narrowViewportMedia: MediaQueryList | null = null

const syncSidebarWidth = () => {
  document.documentElement.style.setProperty('--workspace-sidebar-width', layoutSidebarWidth.value)
}

syncSidebarWidth()
watch(layoutSidebarWidth, syncSidebarWidth)

const handleNarrowViewportChange = (event: MediaQueryListEvent | MediaQueryList) => {
  isNarrowViewport.value = event.matches
  if (!event.matches) mobileExpanded.value = false
}

onBeforeUnmount(() => {
  document.documentElement.style.removeProperty('--workspace-sidebar-width')
  document.removeEventListener('click', handleDocumentClick)
  narrowViewportMedia?.removeEventListener('change', handleNarrowViewportChange)
})

const toggleCollapse = () => {
  if (isNarrowViewport.value) {
    mobileExpanded.value = !mobileExpanded.value
    return
  }
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
  mobileExpanded.value = false
  emit('switch-panel', item)
  if (item.path) {
    router.push(item.path)
  }
}

const handleLogoClick = () => {
  mobileExpanded.value = false
  router.push('/home')
}

const handleSessionClick = (session: Session) => {
  mobileExpanded.value = false
  closeSessionMenu()
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
  document.addEventListener('click', handleDocumentClick)
  narrowViewportMedia = window.matchMedia('(max-width: 767px)')
  handleNarrowViewportChange(narrowViewportMedia)
  narrowViewportMedia.addEventListener('change', handleNarrowViewportChange)
  void agent.refreshSessions()
})
</script>

<template>
  <div
    class="sidebar-rail-spacer flex-none transition-all duration-300"
    :class="isNarrowViewport ? 'w-[52px]' : (isSidebarCollapsed ? 'w-[52px]' : 'w-[240px]')"
    aria-hidden="true"
  />
  <button
    v-if="isNarrowViewport && mobileExpanded"
    class="sidebar-mobile-backdrop"
    type="button"
    aria-label="关闭导航栏"
    @click="mobileExpanded = false"
  />
  <aside
    id="workspace-sidebar-navigation"
    class="sidebar-notion fixed bottom-0 left-0 top-0 z-50 flex flex-col transition-all duration-300"
    :class="isSidebarCollapsed ? 'w-[52px]' : 'w-[240px]'"
  >
    <div class="sidebar-brand-row" :class="{ 'is-collapsed': isSidebarCollapsed }">
      <button
        v-if="!isSidebarCollapsed"
        class="sidebar-brand-button"
        type="button"
        aria-label="返回首页"
        @click="handleLogoClick"
      >
        <span class="sidebar-brand-lockup" aria-hidden="true">
          <span class="sidebar-brand-mark">
            <img :src="logoSvg" alt="" class="sidebar-brand-logo logo-blue" />
          </span>
          <span class="sidebar-brand-divider" aria-hidden="true" />
          <span class="sidebar-brand-name">Aniforce</span>
        </span>
      </button>
      <button
        class="sidebar-collapse flex items-center justify-center transition-colors"
        type="button"
        aria-controls="workspace-sidebar-navigation"
        :aria-expanded="!isSidebarCollapsed"
        :aria-label="isSidebarCollapsed ? '展开导航栏' : '收起导航栏'"
        @click="toggleCollapse"
      >
        <span class="material-symbols-outlined">
          {{ isSidebarCollapsed ? 'menu' : 'menu_open' }}
        </span>
      </button>
    </div>

    <nav class="sidebar-scroll flex-1 overflow-y-auto space-y-[20px] overflow-x-hidden">
      <div>
        <div class="sidebar-section-head mb-[6px]">
          <span v-if="!isSidebarCollapsed" class="sidebar-section-title text-[11px] font-semibold text-slate-500 dark:text-slate-400">功能导航</span>
        </div>
        <ul class="sidebar-nav-list space-y-[12px]">
          <li
            v-for="item in navItems"
            :key="item.id"
            class="sidebar-nav-item flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isSidebarCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel(item.id)
                ? 'sidebar-item-active'
                : 'sidebar-item-idle'
            ]"
            @click="handleNavClick(item)"
          >
            <span class="material-symbols-outlined text-[15px]">{{ item.icon }}</span>
            <span v-if="!isSidebarCollapsed" class="text-[11px]">{{ item.label }}</span>

            <div
              v-if="isSidebarCollapsed"
              class="absolute left-full ml-[6px] px-[10px] py-[6px] bg-slate-900 dark:bg-slate-700 text-white text-[11px] rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity"
            >
              {{ item.label }}
            </div>
          </li>

          <li
            v-if="isAdmin"
            class="sidebar-nav-item flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isSidebarCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel('system-admin')
                ? 'sidebar-item-active'
                : 'sidebar-item-idle'
            ]"
            @click="handleNavClick({ id: 'system-admin', icon: 'admin_panel_settings', label: '系统管理', path: '/system-admin' })"
          >
            <span class="material-symbols-outlined text-[15px]">admin_panel_settings</span>
            <span v-if="!isSidebarCollapsed" class="text-[11px]">系统管理</span>

            <div
              v-if="isSidebarCollapsed"
              class="absolute left-full ml-[6px] px-[10px] py-[6px] bg-slate-900 dark:bg-slate-700 text-white text-[11px] rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity"
            >
              系统管理
            </div>
          </li>
        </ul>
      </div>

      <div v-if="displaySessions.length > 0 && !isSidebarCollapsed" class="sidebar-session-group">
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
            :class="[
              session.active ? 'sidebar-item-active' : 'sidebar-item-idle',
              { 'is-menu-open': openSessionMenuId === session.id }
            ]"
            @click="handleSessionClick(session)"
            @contextmenu.prevent.stop="openSessionMenu(session.id)"
          >
            <span class="material-symbols-outlined text-[11px]">chat</span>
            <span class="sidebar-session-title min-w-0 flex-1" :title="session.name">{{ session.name }}</span>
            <div
              v-if="sessionActions"
              class="sidebar-session-actions flex items-center"
            >
              <button
                class="sidebar-session-action-button hover:bg-slate-200 dark:hover:bg-slate-700"
                type="button"
                title="会话操作"
                :aria-label="`${session.name}的会话操作`"
                :aria-expanded="openSessionMenuId === session.id"
                @click.stop="toggleSessionMenu(session.id)"
              >
                <span class="material-symbols-outlined">more_horiz</span>
              </button>
            </div>
            <div v-if="openSessionMenuId === session.id" class="session-action-menu" role="menu" @click.stop>
              <button type="button" role="menuitem" @click.stop="handleRenameSession(session)">
                <span class="material-symbols-outlined">edit</span>
                <span>重命名</span>
              </button>
              <button class="session-action-menu__danger" type="button" role="menuitem" @click.stop="handleDeleteSession(session)">
                <span class="material-symbols-outlined">delete</span>
                <span>删除</span>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <AccountControls variant="sidebar" :collapsed="isSidebarCollapsed" />
  </aside>

  <SessionRenameDialog
    v-model="localRenameValue"
    :show="Boolean(localRenameDialog)"
    @confirm="confirmLocalRename"
    @close="localRenameDialog = null"
  />

  <ConfirmDialog
    :show="Boolean(localDeleteDialog)"
    title="删除对话"
    :message="`确定删除对话「${localDeleteDialog?.name || ''}」吗？删除后将从历史会话中移除，且无法撤销。`"
    confirm-text="删除"
    tone="danger"
    variant="notion"
    @confirm="confirmLocalDelete"
    @close="localDeleteDialog = null"
  />
</template>

<style scoped>
.sidebar-mobile-backdrop {
  position: fixed;
  z-index: 49;
  inset: 0;
  border: 0;
  background: rgba(15, 15, 15, 0.2);
  cursor: default;
}

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
  z-index: 5;
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
  border-bottom: 1px solid rgba(55, 53, 47, 0.08);
  background: rgba(247, 247, 245, 0.94);
  backdrop-filter: blur(8px);
}

.sidebar-brand-row.is-collapsed {
  justify-content: center;
  padding: 0;
}

.sidebar-brand-button {
  display: flex;
  min-height: 36px;
  min-width: 0;
  align-items: center;
  margin-left: -6px;
  padding: 3px 6px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.sidebar-brand-button:hover {
  background: rgba(55, 53, 47, 0.06);
}

.sidebar-brand-button:focus-visible,
.sidebar-collapse:focus-visible {
  outline: 2px solid rgba(35, 131, 226, 0.4);
  outline-offset: 1px;
}

.sidebar-brand-lockup {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.sidebar-brand-mark {
  width: 36px;
  height: 30px;
  display: block;
  flex: 0 0 36px;
  overflow: hidden;
}

.sidebar-brand-logo {
  width: 110px;
  height: 30px;
  max-width: none;
  object-fit: contain;
  object-position: left center;
}

.sidebar-brand-divider {
  width: 1px;
  height: 20px;
  flex: 0 0 1px;
  background: rgba(55, 53, 47, 0.14);
}

.sidebar-brand-name {
  overflow: hidden;
  color: var(--sidebar-charcoal);
  font-family: "Notion Sans", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.45px;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  font-size: 12px !important;
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
  width: 30px;
  height: 30px;
  padding: 0 !important;
  border-radius: 8px !important;
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

.sidebar-session-list {
  width: 100%;
  min-width: 0;
}

.sidebar-nav-item,
.sidebar-session-item {
  min-height: 36px;
  padding: 7px 9px !important;
  border-radius: 6px !important;
  font-weight: 400 !important;
  line-height: 1.35;
}

.sidebar-nav-item {
  gap: 11px !important;
}

.sidebar-nav-item > .material-symbols-outlined {
  width: 20px;
  flex: 0 0 20px;
  color: inherit;
  font-size: 19px !important;
  text-align: center;
}

.sidebar-nav-item > span:not(.material-symbols-outlined),
.sidebar-session-item > span:last-of-type {
  color: inherit;
  font-size: 13px !important;
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
  position: relative;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  gap: 9px !important;
}

.sidebar-session-title {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-session-actions {
  width: 24px;
  min-width: 24px;
  flex: 0 0 24px;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease;
}

.sidebar-session-item:hover .sidebar-session-actions,
.sidebar-session-item:focus-within .sidebar-session-actions,
.sidebar-session-item.sidebar-item-active .sidebar-session-actions,
.sidebar-session-item.is-menu-open .sidebar-session-actions {
  opacity: 1;
  pointer-events: auto;
}

.sidebar-session-list:has(.sidebar-session-item:hover)
  .sidebar-session-item.sidebar-item-active:not(:hover):not(:focus-within):not(.is-menu-open)
  .sidebar-session-actions {
  opacity: 0;
  pointer-events: none;
}

.sidebar-session-action-button {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  padding: 0 !important;
  border: 0;
  background: transparent;
}

.sidebar-session-action-button .material-symbols-outlined {
  font-size: 14px !important;
}

.sidebar-session-item.is-menu-open {
  z-index: 8;
}

.session-action-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 5px);
  right: 5px;
  width: 150px;
  padding: 5px;
  border: 1px solid #deddd9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgb(15 15 15 / 14%), 0 1px 3px rgb(15 15 15 / 8%);
}

.session-action-menu > button {
  display: flex;
  width: 100%;
  min-height: 34px;
  align-items: center;
  gap: 9px;
  padding: 6px 9px;
  border: 0;
  border-radius: 5px !important;
  background: transparent;
  color: var(--sidebar-charcoal) !important;
  cursor: pointer;
  font-size: 11px;
  text-align: left;
}

.session-action-menu > button:hover {
  background: #f1f1ef !important;
}

.session-action-menu .material-symbols-outlined {
  width: 16px;
  flex: 0 0 16px;
  font-size: 16px !important;
}

.session-action-menu > .session-action-menu__danger {
  color: #d14343 !important;
}

.session-action-menu > .session-action-menu__danger:hover {
  background: rgb(209 67 67 / 8%) !important;
}

:global(.dark) .session-action-menu {
  border-color: #373737;
  background: #202020;
  box-shadow: 0 8px 28px rgb(0 0 0 / 38%);
}

:global(.dark) .session-action-menu > button {
  color: #e6e6e5 !important;
}

:global(.dark) .session-action-menu > button:hover {
  background: #2a2a2a !important;
}

.sidebar-session-item > .material-symbols-outlined {
  width: 16px;
  flex: 0 0 16px;
  font-size: 17px !important;
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
