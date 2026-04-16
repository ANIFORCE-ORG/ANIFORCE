<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const showUserMenu = ref(false)

const navItems = [
  //{ label: '首页', path: '/', icon: 'home' },
  //{ label: '数据概览', path: '/dashboard', icon: 'pie_chart' },
  //{ label: '市场分析', path: '/market-analysis', icon: 'trending_up' },
  //{ label: '素材生产', path: '/material', icon: 'auto_awesome' },
  //{ label: '投放计划', path: '/campaign', icon: 'campaign' },
  //{ label: '投放数据分析', path: '/monitor', icon: 'analytics' },
]

const isActive = (path: string) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const navigateTo = (path: string) => {
  router.push(path)
}

const handleUserClick = () => {
  if (!auth.isLoggedIn) {
    router.push('/login')
  } else {
    showUserMenu.value = !showUserMenu.value
  }
}

const handleLogout = () => {
  auth.logout()
  showUserMenu.value = false
}
</script>

<template>
  <header class="flex items-center justify-between px-6 py-3 md:px-12 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
    <!-- Logo -->
    <div class="flex items-center gap-3 cursor-pointer shrink-0" @click="navigateTo('/')">
      <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white">
        <span class="material-symbols-outlined text-xl">rocket_launch</span>
      </div>
      <h2 class="text-lg font-bold tracking-tight">ANIFORCE</h2>
    </div>

    <!-- Navigation -->
    <nav class="hidden md:flex items-center gap-1">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
        :class="isActive(item.path)
          ? 'bg-primary/10 text-primary font-semibold shadow-sm'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-primary'"
        @click="navigateTo(item.path)"
      >
        <span class="material-symbols-outlined text-[18px]">{{ item.icon }}</span>
        {{ item.label }}
      </button>
    </nav>

    <!-- Right Actions -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- User Info / Login -->
      <div class="relative">
        <button
          v-if="auth.isLoggedIn"
          class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
          @click="handleUserClick"
        >
          <div class="h-9 w-9 rounded-full bg-primary/10 border-2 border-primary/30 flex items-center justify-center">
            <span class="text-xs font-bold text-primary">{{ auth.user?.name?.charAt(0) }}</span>
          </div>
          <div class="flex flex-col items-start">
            <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ auth.user?.name }}</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">投放经理 · FunGame Studio</div>
          </div>
        </button>
        <button
          v-else
          class="flex h-9 w-9 items-center justify-center rounded-full border-2 bg-slate-200 dark:bg-slate-700 border-white dark:border-slate-800 hover:border-primary transition-all duration-200 cursor-pointer"
          @click="handleUserClick"
        >
          <span class="material-symbols-outlined text-lg text-slate-500">person</span>
        </button>

        <!-- User Dropdown Menu -->
        <Transition name="fade">
          <div
            v-if="showUserMenu && auth.isLoggedIn"
            class="absolute right-0 top-full mt-2 w-48 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl py-2 z-50"
          >
            <div class="px-4 py-2 border-b border-slate-100 dark:border-slate-800">
              <p class="text-sm font-semibold">{{ auth.user?.name }}</p>
              <p class="text-xs text-slate-500">{{ auth.user?.email }}</p>
            </div>
            <button
              class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              @click="handleLogout"
            >
              <span class="material-symbols-outlined text-[18px]">logout</span>
              退出登录
            </button>
          </div>
        </Transition>
      </div>

      <button class="flex h-9 w-9 items-center justify-center rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
        <span class="material-symbols-outlined text-xl text-slate-600 dark:text-slate-400">notifications</span>
      </button>
    </div>
  </header>

  <!-- Click outside to close menu -->
  <div v-if="showUserMenu" class="fixed inset-0 z-40" @click="showUserMenu = false" />
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
