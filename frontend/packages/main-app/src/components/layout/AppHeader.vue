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
  <header class="app-header">
    <!-- Logo -->
    <div class="flex items-center gap-2 cursor-pointer shrink-0" @click="handleLogoClick">
      <img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />
    </div>

    <!-- Right Actions -->
    <div class="header-actions">
      <!-- 已登录状态 -->
      <template v-if="auth.isLoggedIn">
        <!-- User Info -->
        <div class="relative">
          <button
            class="header-user"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="showUserMenu"
            @click="handleUserClick"
          >
            <div class="header-avatar">
              <span>{{ auth.user?.name?.charAt(0) }}</span>
            </div>
            <div class="header-identity">
              <div class="header-user-name">{{ auth.user?.name }}</div>
              <div class="header-user-email">{{ auth.user?.email }}</div>
            </div>
          </button>

          <!-- User Dropdown Menu -->
          <Transition name="fade">
            <div v-if="showUserMenu" class="header-user-menu" role="menu">
              <div class="header-menu-summary">
                <p>{{ auth.user?.name }}</p>
                <span>{{ auth.user?.email }}</span>
              </div>
              <button class="header-menu-logout" type="button" role="menuitem" @click="handleLogout">
                <span class="material-symbols-outlined">logout</span>
                {{ t.logout }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="header-icon-button" type="button" aria-label="通知">
          <span class="material-symbols-outlined">notifications</span>
        </button>
      </template>

      <!-- 未登录状态 -->
      <template v-else>
        <button class="header-start-button" type="button" @click="handleUserClick">
          {{ t.getStartButton }}
        </button>
      </template>

      <!-- Language Segmented Control -->
      <div class="language-switcher" role="group" aria-label="Language">
        <button
          type="button"
          :class="['language-option', { 'is-active': language === 'cn' }]"
          :aria-pressed="language === 'cn'"
          @click="() => language === 'en' && toggleLanguage()"
        >
          中文
        </button>
        <button
          type="button"
          :class="['language-option', { 'is-active': language === 'en' }]"
          :aria-pressed="language === 'en'"
          @click="() => language === 'cn' && toggleLanguage()"
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
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  border-bottom: 1px solid #e9e9e7;
  background: #ffffff;
  color: #37352f;
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
}

.header-user,
.header-icon-button,
.header-start-button,
.language-option,
.header-menu-logout {
  font: inherit;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background-color 120ms ease;
}

.header-user:hover,
.header-icon-button:hover {
  background: #f1f1ef;
}

.header-user:focus-visible,
.header-icon-button:focus-visible,
.header-start-button:focus-visible,
.language-option:focus-visible,
.header-menu-logout:focus-visible {
  outline: 2px solid #a8a29e;
  outline-offset: 2px;
}

.header-avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex: none;
  place-items: center;
  border: 1px solid #d9d9d6;
  border-radius: 50%;
  background: #f7f7f5;
  color: #37352f;
  font-size: 11px;
  font-weight: 600;
}

.header-identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
}

.header-user-name {
  color: #37352f;
  font-size: 12px;
  font-weight: 600;
  line-height: 15px;
}

.header-user-email {
  max-width: 180px;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-icon-button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}

.header-icon-button .material-symbols-outlined {
  font-size: 18px;
}

.language-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 1px;
  padding-left: 7px;
  border-left: 1px solid #e9e9e7;
}

.language-option {
  height: 28px;
  padding: 0 8px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  font-size: 10px;
  font-weight: 600;
  transition: background-color 120ms ease, color 120ms ease;
}

.language-option:hover {
  color: #37352f;
}

.language-option.is-active {
  background: #f1f1ef;
  color: #37352f;
}

.header-user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 50;
  width: 176px;
  margin-top: 6px;
  padding: 4px;
  border: 1px solid #deddd9;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgb(15 15 15 / 12%);
  color: #37352f;
}

.header-menu-summary {
  padding: 7px 8px 8px;
  border-bottom: 1px solid #eeeeec;
}

.header-menu-summary p {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.header-menu-summary span {
  display: block;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-menu-logout {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 6px 8px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #eb5757;
  cursor: pointer;
  font-size: 11px;
  text-align: left;
  transition: background-color 120ms ease;
}

.header-menu-logout:hover {
  background: rgb(235 87 87 / 8%);
}

.header-menu-logout .material-symbols-outlined {
  font-size: 15px;
}

.header-start-button {
  padding: 6px 10px;
  border: 0;
  border-radius: 5px;
  background: #37352f;
  color: #ffffff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Keep the existing ANIFORCE Logo rendering unchanged. */
.logo-blue {
  filter: brightness(0) saturate(100%) invert(45%) sepia(98%) saturate(1845%) hue-rotate(205deg) brightness(102%) contrast(98%);
}

:global(.dark) .app-header {
  border-color: #2f2f2f;
  background: #191919;
  color: #e6e6e5;
}

:global(.dark) .header-user:hover,
:global(.dark) .header-icon-button:hover,
:global(.dark) .language-option.is-active {
  background: #252525;
}

:global(.dark) .header-avatar {
  border-color: #3a3a3a;
  background: #252525;
  color: #e6e6e5;
}

:global(.dark) .header-user-name,
:global(.dark) .language-option:hover,
:global(.dark) .language-option.is-active {
  color: #e6e6e5;
}

:global(.dark) .header-user-email,
:global(.dark) .header-icon-button,
:global(.dark) .language-option,
:global(.dark) .header-menu-summary span {
  color: #9b9a97;
}

:global(.dark) .language-switcher {
  border-color: #2f2f2f;
}

:global(.dark) .header-user-menu {
  border-color: #373737;
  background: #202020;
  color: #e6e6e5;
  box-shadow: 0 4px 14px rgb(0 0 0 / 35%);
}

:global(.dark) .header-menu-summary {
  border-color: #2f2f2f;
}

:global(.dark) .header-start-button {
  background: #e6e6e5;
  color: #191919;
}

@media (min-width: 768px) {
  .app-header {
    padding-right: 40px;
    padding-left: 40px;
  }
}

@media (max-width: 520px) {
  .header-actions {
    gap: 3px;
  }

  .header-user {
    gap: 6px;
    padding-right: 4px;
    padding-left: 4px;
  }

  .header-user-email {
    max-width: 112px;
  }

  .language-switcher {
    padding-left: 4px;
  }

  .language-option {
    padding-right: 6px;
    padding-left: 6px;
  }
}
</style>
