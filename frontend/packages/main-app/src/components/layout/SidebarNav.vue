<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

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
}>()

const router = useRouter()
const route = useRoute()

// 折叠状态 - 从localStorage读取初始值
const SIDEBAR_COLLAPSED_KEY = 'animagus_sidebar_collapsed'
const isCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true')

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  // 保存到localStorage
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed.value))
}

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
  <aside 
    class="bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-all duration-300"
    :class="isCollapsed ? 'w-[52px]' : 'w-[205px]'"
  >
    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto pb-0 p-[12px] pt-[20px] space-y-[20px] overflow-x-hidden">
      <!-- 功能导航 -->
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
            
            <!-- Tooltip for collapsed state -->
            <div
              v-if="isCollapsed"
              class="absolute left-full ml-[6px] px-[10px] py-[6px] bg-slate-900 dark:bg-slate-700 text-white text-[11px] rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity"
            >
              {{ item.label }}
            </div>
          </li>
        </ul>
      </div>

      <!-- 历史会话 -->
      <div v-if="sessions.length > 0 && !isCollapsed">
        <div class="text-[10px] font-semibold text-slate-500 dark:text-slate-400 mb-[6px] px-[6px]">历史会话</div>
        <ul class="space-y-[4px]">
          <li
            v-for="session in sessions"
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
              <button class="p-[4px] hover:bg-slate-200 dark:hover:bg-slate-700 rounded" @click.stop>
                <span class="material-symbols-outlined text-[10px]">edit</span>
              </button>
              <button class="p-[4px] hover:bg-slate-200 dark:hover:bg-slate-700 rounded" @click.stop>
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
/* 自定义滚动条 */
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
