<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useLanguage } from '@/store/language'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { language, setLanguage } = useLanguage()

const showUserMenu = ref(false)

const publicCopy = {
  cn: {
    home: '首页',
    start: '马上体验',
    login: '登录',
    workspace: '进入系统',
    account: '账户设置',
    logout: '退出登录',
  },
  en: {
    home: 'Home',
    start: 'Start now',
    login: 'Login',
    workspace: 'Workspace',
    account: 'Account',
    logout: 'Log out',
  },
}

const isPublicPage = () => route.path === '/' || route.path === '/contact' || route.path === '/login' || route.path === '/register'

const handleLogoClick = () => {
  if (auth.isLoggedIn) {
    router.push('/home')
  } else {
    router.push('/')
  }
}

const handleUserClick = () => {
  if (!auth.isLoggedIn) {
    router.push('/login')
  } else {
    showUserMenu.value = !showUserMenu.value
  }
}

const goWorkspace = () => {
  showUserMenu.value = false
  router.push('/home')
}

const goAccountSettings = () => {
  showUserMenu.value = false
  router.push('/account-config')
}

const handleLogout = () => {
  auth.logout()
  showUserMenu.value = false
  router.push('/')
}
</script>

<template>
  <header class="flex items-center justify-between px-6 py-3 md:px-12 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
    <!-- Logo -->
    <div class="flex items-center gap-3 cursor-pointer shrink-0" @click="handleLogoClick">
      <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white">
        <span class="material-symbols-outlined text-xl">rocket_launch</span>
      </div>
      <h2 class="text-lg font-bold tracking-tight">ANIFORCE</h2>
    </div>

    <!-- Navigation -->
    <nav v-if="isPublicPage()" class="hidden md:flex items-center gap-6">
      <RouterLink class="text-sm font-medium text-slate-600 hover:text-primary" to="/">{{ publicCopy[language].home }}</RouterLink>
      <RouterLink class="text-sm font-medium text-slate-600 hover:text-primary" to="/contact">{{ publicCopy[language].start }}</RouterLink>
    </nav>

    <!-- Right Actions -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- 已登录状态 -->
      <template v-if="auth.isLoggedIn">
        <!-- User Info -->
        <div class="relative">
          <button
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
            <span class="material-symbols-outlined text-base text-slate-500">expand_more</span>
          </button>

          <!-- User Dropdown Menu -->
          <Transition name="fade">
            <div
              v-if="showUserMenu"
              class="absolute right-0 top-full mt-2 w-48 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl py-2 z-50"
            >
              <div class="px-4 py-2 border-b border-slate-100 dark:border-slate-800">
                <p class="text-sm font-semibold">{{ auth.user?.name }}</p>
                <p class="text-xs text-slate-500">{{ auth.user?.email }}</p>
              </div>
              <button
                class="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800 transition-colors"
                @click="goWorkspace"
              >
                <span class="material-symbols-outlined text-[18px]">space_dashboard</span>
                {{ publicCopy[language].workspace }}
              </button>
              <button
                class="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800 transition-colors"
                @click="goAccountSettings"
              >
                <span class="material-symbols-outlined text-[18px]">manage_accounts</span>
                {{ publicCopy[language].account }}
              </button>
              <button
                class="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                @click="handleLogout"
              >
                <span class="material-symbols-outlined text-[18px]">logout</span>
                {{ publicCopy[language].logout }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="flex h-9 w-9 items-center justify-center rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <span class="material-symbols-outlined text-xl text-slate-600 dark:text-slate-400">notifications</span>
        </button>
      </template>

      <!-- 未登录状态 -->
      <template v-else>
        <button
          class="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:text-primary transition-colors font-medium"
          @click="handleUserClick"
        >
          {{ publicCopy[language].login }}
        </button>
      </template>

      <div
        v-if="isPublicPage()"
        class="inline-flex h-9 items-center rounded-md border border-slate-200 bg-white p-0.5 text-xs font-semibold text-slate-500"
        aria-label="切换语言"
      >
        <button
          class="h-8 rounded px-2.5"
          :class="language === 'cn' ? 'bg-slate-950 text-white' : 'hover:text-slate-900'"
          type="button"
          @click="setLanguage('cn')"
        >
          CN
        </button>
        <button
          class="h-8 rounded px-2.5"
          :class="language === 'en' ? 'bg-slate-950 text-white' : 'hover:text-slate-900'"
          type="button"
          @click="setLanguage('en')"
        >
          EN
        </button>
      </div>
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
