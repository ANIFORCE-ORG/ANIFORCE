<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'

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
  activeId?: string
}

const props = withDefaults(defineProps<Props>(), {
  navItems: () => [
    { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
    { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
    { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
    { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
    { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
    { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/reports' },
  ],
  sessions: () => [],
  activePanel: '',
  activeId: ''
})

const emit = defineEmits<{
  'switch-panel': [item: NavItem]
  'switch-session': [session: Session]
}>()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const requiredNavItems: NavItem[] = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/reports' },
]

const settingsNavItems: NavItem[] = [
  { id: 'settings', icon: 'settings', label: '设置', path: '/settings' },
]

const normalizedNavItems = computed(() => {
  const byId = new Map<string, NavItem>()
  props.navItems.forEach(item => byId.set(item.id, item))
  requiredNavItems.forEach(item => {
    const existing = byId.get(item.id)
    byId.set(item.id, existing ? { ...existing, path: item.path } : item)
  })
  return requiredNavItems.map(item => byId.get(item.id) || item)
})

const isActivePanel = (itemId: string) => {
  const active = props.activePanel || props.activeId
  if (active) {
    return active === itemId
  }
  // 根据当前路由判断
  const item = normalizedNavItems.value.find(i => i.id === itemId)
  if (!item) return false
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

const isActiveSettings = (item: NavItem) => {
  const active = props.activePanel || props.activeId
  if (active) return active === item.id
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

const handleNavClick = (item: NavItem) => {
  emit('switch-panel', item)
  if (item.path) {
    router.push(item.path)
  }
}

const handleSessionClick = (session: Session) => {
  emit('switch-session', session)
}
</script>

<template>
  <aside class="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col">
    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto p-4 space-y-6 pt-6">
      <!-- 功能导航 -->
      <div>
        <div class="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 px-2">功能导航</div>
        <ul class="space-y-1">
          <li
            v-for="item in normalizedNavItems"
            :key="item.id"
            class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all"
            :class="isActivePanel(item.id)
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="handleNavClick(item)"
          >
            <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
            <span class="text-sm">{{ item.label }}</span>
          </li>
        </ul>
      </div>

      <!-- 历史会话 -->
      <div v-if="sessions.length > 0">
        <div class="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 px-2">历史会话</div>
        <ul class="space-y-1">
          <li
            v-for="session in sessions"
            :key="session.id"
            class="group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all"
            :class="session.active
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="handleSessionClick(session)"
          >
            <span class="material-symbols-outlined text-sm">chat</span>
            <span class="text-sm flex-1 truncate">{{ session.name }}</span>
            <div class="opacity-0 group-hover:opacity-100 flex items-center gap-1">
              <button class="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded" @click.stop>
                <span class="material-symbols-outlined text-xs">edit</span>
              </button>
              <button class="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded" @click.stop>
                <span class="material-symbols-outlined text-xs">delete</span>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <div class="border-t border-slate-200 dark:border-slate-800 p-4">
      <div class="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 px-2">系统</div>
      <ul class="space-y-1">
        <li
          v-for="item in settingsNavItems"
          :key="item.id"
          class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all"
          :class="isActiveSettings(item)
            ? 'bg-primary/10 text-primary font-semibold'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
          @click="handleNavClick(item)"
        >
          <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
          <span class="text-sm">{{ item.label }}</span>
        </li>
      </ul>
    </div>
  </aside>
</template>

<style scoped>
/* 自定义滚动条 */
nav::-webkit-scrollbar {
  width: 4px;
}
nav::-webkit-scrollbar-thumb {
  background-color: rgb(203 213 225);
  border-radius: 2px;
}
nav::-webkit-scrollbar-thumb:hover {
  background-color: rgb(148 163 184);
}
</style>
