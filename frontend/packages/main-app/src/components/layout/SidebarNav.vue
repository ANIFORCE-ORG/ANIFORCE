<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useAgentSession } from '@/composables/useAgentSession'

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
  activePanel: ''
})

const emit = defineEmits<{
  'switch-panel': [item: NavItem]
  'switch-session': [session: Session]
  'rename-session': [session: Session]
  'delete-session': [session: Session]
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

const handleSessionClick = (session: Session) => {
  if (route.path !== '/') {
    router.push('/')
  }
  emit('switch-session', session)
}

onMounted(() => {
  void agent.refreshSessions()
})
</script>

<template>
  <aside
    class="bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-all duration-300"
    :class="isCollapsed ? 'w-[52px]' : 'w-[205px]'"
  >
    <nav class="flex-1 overflow-y-auto pb-0 p-[12px] pt-[20px] space-y-[20px] overflow-x-hidden">
      <div>
        <div
          class="mb-[6px]"
          :class="isCollapsed ? '' : 'flex items-center justify-between px-[6px]'"
        >
          <span v-if="!isCollapsed" class="text-[11px] font-semibold text-slate-500 dark:text-slate-400">功能导航</span>
          <button
            class="rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center justify-center"
            :class="isCollapsed ? 'w-full py-[10px]' : 'p-[6px]'"
            @click="toggleCollapse"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[15px]">
              {{ isCollapsed ? 'menu' : 'menu_open' }}
            </span>
          </button>
        </div>
        <ul class="space-y-[12px]">
          <li
            v-for="item in navItems"
            :key="item.id"
            class="flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel(item.id)
                ? 'bg-primary/10 text-primary font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
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
            class="flex items-center rounded-lg cursor-pointer transition-all relative group"
            :class="[
              isCollapsed ? 'justify-center px-[6px] py-[10px]' : 'gap-[10px] px-[10px] py-[6px]',
              isActivePanel('system-admin')
                ? 'bg-primary/10 text-primary font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
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

      <div v-if="displaySessions.length > 0 && !isCollapsed">
        <div class="text-[10px] font-semibold text-slate-500 dark:text-slate-400 mb-[6px] px-[6px]">历史会话</div>
        <ul class="space-y-[4px]">
          <li
            v-for="session in displaySessions"
            :key="session.id"
            class="group flex items-center gap-[6px] px-[10px] py-[6px] rounded-lg cursor-pointer transition-all"
            :class="session.active
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="handleSessionClick(session)"
          >
            <span class="material-symbols-outlined text-[11px]">chat</span>
            <span class="text-[11px] flex-1 truncate">{{ session.name }}</span>
            <div class="opacity-0 group-hover:opacity-100 flex items-center gap-[4px]">
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
  </aside>
</template>

<style scoped>
nav::-webkit-scrollbar {
  width: 3px;
}
nav::-webkit-scrollbar-thumb {
  background-color: rgb(203 213 225);
  border-radius: 1px;
}
nav::-webkit-scrollbar-thumb:hover {
  background-color: rgb(148 163 184);
}
</style>
