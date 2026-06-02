<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import logoSvg from '@/assets/aniforce-logo-transparent.svg'

const router = useRouter()
const auth = useAuthStore()

const showUserMenu = ref(false)

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

const handleLogout = () => {
  auth.logout()
  showUserMenu.value = false
  router.push('/')
}
</script>

<template>
  <header class="flex items-center justify-between px-6 py-3 md:px-12 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
    <!-- Logo -->
    <div class="flex items-center gap-3 cursor-pointer shrink-0">
        <img :src="logoSvg" alt="ANIFORCE" class="h-12 w-auto max-w-[220px] object-contain logo-blue" />
      </div>

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
              <div class="text-xs text-slate-500 dark:text-slate-400">{{ auth.user?.email }}</div>
            </div>
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
      </template>

      <!-- 未登录状态 -->
      <template v-else>
        <!--
        <button
          class="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:text-primary transition-colors font-medium"
          @click="handleUserClick"
        >
          登录
        </button>
        -->
        <button
          class="px-4 py-2 text-sm bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors font-medium"
          @click="handleUserClick"
        >
          开始使用
        </button>
      </template>
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
/* === Logo Blue Color === */
.logo-blue {
  /* 使用 filter 将 SVG 调整为蓝色 #3B82F6 */
  filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);
}
</style>
