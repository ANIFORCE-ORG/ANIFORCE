<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useLanguage } from '@/store/language'
import logoSvg from '@/assets/aniforce-logo-transparent.svg'

const router = useRouter()
const auth = useAuthStore()
const { language, toggleLanguage } = useLanguage()

const showUserMenu = ref(false)

// Bilingual copy
const copy = {
  cn: {
    getStartButton: '开始使用',
    logout: '退出登录'
  },
  en: {
    getStartButton: 'Get Start',
    logout: 'Logout'
  }
}

const t = computed(() => copy[language.value])

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
  <header class="flex items-center justify-between px-5 py-2 md:px-10 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
    <!-- Logo -->
    <div class="flex items-center gap-2 cursor-pointer shrink-0" @click="handleLogoClick">
        <img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />
      </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-2 shrink-0">
      <!-- 已登录状态 -->
      <template v-if="auth.isLoggedIn">
        <!-- User Info -->
        <div class="relative">
          <button
            class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
            @click="handleUserClick"
          >
            <div class="h-7 w-7 rounded-full bg-primary/10 border-2 border-primary/30 flex items-center justify-center">
              <span class="text-[10px] font-bold text-primary">{{ auth.user?.name?.charAt(0) }}</span>
            </div>
            <div class="flex flex-col items-start">
              <div class="text-xs font-semibold text-slate-900 dark:text-white">{{ auth.user?.name }}</div>
              <div class="text-[10px] text-slate-500 dark:text-slate-400">{{ auth.user?.email }}</div>
            </div>
          </button>

          <!-- User Dropdown Menu -->
          <Transition name="fade">
            <div
              v-if="showUserMenu"
              class="absolute right-0 top-full mt-1.5 w-40 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl py-1.5 z-50"
            >
              <div class="px-3 py-1.5 border-b border-slate-100 dark:border-slate-800">
                <p class="text-xs font-semibold">{{ auth.user?.name }}</p>
                <p class="text-[10px] text-slate-500">{{ auth.user?.email }}</p>
              </div>
              <button
                class="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                @click="handleLogout"
              >
                <span class="material-symbols-outlined text-[14px]">logout</span>
                {{ t.logout }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="flex h-7 w-7 items-center justify-center rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <span class="material-symbols-outlined text-base text-slate-600 dark:text-slate-400">notifications</span>
        </button>
      </template>

      <!-- 未登录状态 -->
      <template v-else>
        <button
          class="px-3 py-1.5 text-xs bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors font-medium"
          @click="handleUserClick"
        >
          {{ t.getStartButton }}
        </button>
      </template>

      <!-- Language Segmented Control -->
      <div class="flex items-center gap-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 p-0.5">
        <button
          @click="() => language === 'en' && toggleLanguage()"
          :class="[
            'px-2 py-1 text-[10px] font-semibold rounded-md transition-all',
            language === 'cn'
              ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          ]"
        >
          中文
        </button>
        <button
          @click="() => language === 'cn' && toggleLanguage()"
          :class="[
            'px-2 py-1 text-[10px] font-semibold rounded-md transition-all',
            language === 'en'
              ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          ]"
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
/* === Logo Blue Color === */
.logo-blue {
  /* 使用 filter 将 SVG 调整为蓝色 #3B82F6 */
  filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);
}
</style>
