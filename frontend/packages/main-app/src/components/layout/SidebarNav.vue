<script setup lang="ts">
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
}

const props = withDefaults(defineProps<Props>(), {
  navItems: () => [
    { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
    { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
    { id: 'campaigns', icon: 'campaign', label: '广告投放', path: '/campaign' },
    { id: 'materials', icon: 'auto_awesome', label: '创意素材', path: '/material' },
    { id: 'reports', icon: 'analytics', label: '数据报表', path: '/monitor' },
  ],
  sessions: () => [],
  activePanel: ''
})

const emit = defineEmits<{
  'switch-panel': [item: NavItem]
  'switch-session': [session: Session]
}>()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isActivePanel = (itemId: string) => {
  if (props.activePanel) {
    return props.activePanel === itemId
  }
  // 根据当前路由判断
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
            v-for="item in navItems"
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
