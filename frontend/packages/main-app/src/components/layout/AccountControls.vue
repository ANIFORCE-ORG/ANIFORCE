<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useLanguage } from '@/store/language'

interface Props {
  variant: 'header' | 'sidebar'
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: false,
})

const router = useRouter()
const auth = useAuthStore()
const { language, toggleLanguage } = useLanguage()
const showMenu = ref(false)
const rootElement = ref<HTMLElement | null>(null)

const copy = {
  cn: {
    account: '账户与偏好设置',
    notifications: '通知',
    language: '语言',
    getStartButton: '开始使用',
    logout: '退出登录',
  },
  en: {
    account: 'Account and preferences',
    notifications: 'Notifications',
    language: 'Language',
    getStartButton: 'Get Start',
    logout: 'Logout',
  },
}

const t = computed(() => copy[language.value])
const isSidebar = computed(() => props.variant === 'sidebar')

const handleTrigger = () => {
  if (!auth.isLoggedIn) {
    void router.push('/login')
    return
  }
  showMenu.value = !showMenu.value
}

const handleLogout = () => {
  auth.logout()
  showMenu.value = false
  void router.push('/login')
}

const handleWindowKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    showMenu.value = false
  }
}

const handleDocumentPointerDown = (event: PointerEvent) => {
  if (showMenu.value && !rootElement.value?.contains(event.target as Node)) {
    showMenu.value = false
  }
}

watch(() => props.collapsed, () => {
  showMenu.value = false
})

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})
</script>

<template>
  <div
    ref="rootElement"
    :class="[
      'account-controls',
      `account-controls--${variant}`,
      { 'is-collapsed': isSidebar && collapsed },
    ]"
  >
    <template v-if="!isSidebar">
      <template v-if="auth.isLoggedIn">
        <div class="account-user-wrap">
          <button
            class="account-trigger account-trigger--header"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="showMenu"
            @click="handleTrigger"
          >
            <span class="account-avatar">{{ auth.user?.name?.charAt(0) }}</span>
            <span class="account-identity">
              <strong>{{ auth.user?.name }}</strong>
              <span>{{ auth.user?.email }}</span>
            </span>
          </button>

          <Transition name="account-popover">
            <div v-if="showMenu" class="account-popover account-popover--header" role="menu">
              <div class="account-popover-summary">
                <strong>{{ auth.user?.name }}</strong>
                <span>{{ auth.user?.email }}</span>
              </div>
              <button class="account-menu-action account-menu-action--danger" type="button" role="menuitem" @click="handleLogout">
                <span class="material-symbols-outlined">logout</span>
                {{ t.logout }}
              </button>
            </div>
          </Transition>
        </div>

        <button class="account-icon-button" type="button" :aria-label="t.notifications">
          <span class="material-symbols-outlined">notifications</span>
        </button>
      </template>

      <button v-else class="account-start-button" type="button" @click="handleTrigger">
        {{ t.getStartButton }}
      </button>

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
    </template>

    <template v-else-if="auth.isLoggedIn">
      <button
        class="account-trigger account-trigger--sidebar"
        type="button"
        aria-label="账户与偏好设置"
        aria-haspopup="menu"
        :aria-expanded="showMenu"
        @click="handleTrigger"
      >
        <span class="account-avatar account-avatar--sidebar">{{ auth.user?.name?.charAt(0) }}</span>
        <span v-if="!collapsed" class="sidebar-account-name">{{ auth.user?.name }}</span>
        <span v-if="!collapsed" class="material-symbols-outlined sidebar-account-chevron">more_horiz</span>
      </button>

      <Transition name="account-popover">
        <div
          v-if="showMenu"
          :class="[
            'account-popover',
            { 'account-popover--sidebar': isSidebar },
          ]"
          role="menu"
        >
          <div class="account-popover-summary account-popover-summary--sidebar">
            <span class="account-avatar account-avatar--popover">{{ auth.user?.name?.charAt(0) }}</span>
            <span class="account-popover-identity">
              <strong>{{ auth.user?.name }}</strong>
              <span>{{ auth.user?.email }}</span>
            </span>
          </div>

          <button class="account-menu-action" type="button" role="menuitem">
            <span class="material-symbols-outlined">notifications</span>
            {{ t.notifications }}
          </button>

          <div class="account-language-row">
            <span class="account-language-label">
              <span class="material-symbols-outlined">language</span>
              {{ t.language }}
            </span>
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

          <button class="account-menu-action account-menu-action--danger" type="button" role="menuitem" @click="handleLogout">
            <span class="material-symbols-outlined">logout</span>
            {{ t.logout }}
          </button>
        </div>
      </Transition>
    </template>
  </div>
</template>

<style scoped>
.account-controls {
  color: #37352f;
  font: inherit;
}

.account-controls--header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
}

.account-user-wrap,
.account-controls--sidebar {
  position: relative;
}

.account-trigger,
.account-icon-button,
.account-start-button,
.account-menu-action,
.language-option {
  border: 0;
  font: inherit;
}

.account-trigger {
  display: flex;
  align-items: center;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}

.account-trigger--header {
  gap: 8px;
  padding: 4px 6px;
}

.account-trigger:hover,
.account-icon-button:hover {
  background: #f1f1ef;
}

.account-trigger:focus-visible,
.account-icon-button:focus-visible,
.account-start-button:focus-visible,
.account-menu-action:focus-visible,
.language-option:focus-visible {
  outline: 2px solid #a8a29e;
  outline-offset: 2px;
}

.account-avatar {
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

.account-identity,
.account-popover-identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
}

.account-identity strong {
  color: #37352f;
  font-size: 12px;
  font-weight: 600;
  line-height: 15px;
}

.account-identity > span {
  max-width: 180px;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-icon-button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 6px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}

.account-icon-button .material-symbols-outlined {
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

.account-start-button {
  padding: 6px 10px;
  border-radius: 5px;
  background: var(--workspace-action-primary, #137fec);
  color: #ffffff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
}

.account-popover {
  z-index: 70;
  width: 224px;
  padding: 5px;
  border: 1px solid #deddd9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 26px rgb(15 15 15 / 14%), 0 1px 3px rgb(15 15 15 / 8%);
  color: #37352f;
}

.account-popover--header {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 176px;
}

.account-popover--sidebar {
  position: absolute;
  bottom: 8px;
  left: calc(100% + 8px);
}

.account-popover-summary {
  padding: 7px 8px 8px;
  border-bottom: 1px solid #eeeeec;
}

.account-popover-summary strong {
  display: block;
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
}

.account-popover-summary > span,
.account-popover-identity > span {
  display: block;
  overflow: hidden;
  color: #787774;
  font-size: 10px;
  line-height: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-popover-summary--sidebar {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 8px 10px;
}

.account-avatar--popover {
  width: 30px;
  height: 30px;
}

.account-popover-identity {
  flex: 1;
}

.account-popover-identity strong {
  max-width: 156px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-menu-action,
.account-language-row {
  display: flex;
  width: 100%;
  min-height: 32px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 5px;
  background: transparent;
  color: #5d5b54;
  font-size: 11px;
}

.account-menu-action {
  cursor: pointer;
  text-align: left;
}

.account-menu-action:hover {
  background: #f1f1ef;
  color: #37352f;
}

.account-menu-action .material-symbols-outlined,
.account-language-label .material-symbols-outlined {
  width: 18px;
  font-size: 17px;
  text-align: center;
}

.account-menu-action--danger {
  margin-top: 3px;
  color: #c9433b;
}

.account-menu-action--danger:hover {
  background: rgb(201 67 59 / 8%);
  color: #b5332c;
}

.account-language-row {
  justify-content: space-between;
}

.account-language-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-language-row .language-switcher {
  margin: 0;
  padding: 0;
  border: 0;
}

.account-language-row .language-option {
  height: 24px;
  padding: 0 6px;
}

.account-controls--sidebar {
  z-index: 4;
  box-sizing: border-box;
  width: 100%;
  height: 57px;
  min-height: 57px;
  flex: none;
  display: flex;
  align-items: center;
  padding: 8px 10px 10px 8px;
  border-top: 1px solid #e5e3df;
  background: #f7f7f5;
}

.account-controls--sidebar.is-collapsed {
  padding-right: 6px;
  padding-left: 6px;
}

.account-trigger--sidebar {
  width: 100%;
  min-height: 38px;
  gap: 9px;
  justify-content: flex-start;
  padding: 5px 7px;
}

.is-collapsed .account-trigger--sidebar {
  justify-content: center;
  padding-right: 0;
  padding-left: 0;
}

.account-avatar--sidebar {
  width: 26px;
  height: 26px;
  border-color: #d4d2ce;
  background: #efefed;
  font-size: 10px;
}

.sidebar-account-name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: #37352f;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-account-chevron {
  color: #9b9a97;
  font-size: 16px;
}

.account-popover-enter-active,
.account-popover-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}

.account-popover-enter-from,
.account-popover-leave-to {
  opacity: 0;
  transform: translateX(-3px) translateY(2px);
}

:global(.dark) .account-controls {
  color: #e6e6e5;
}

:global(.dark) .account-controls--sidebar {
  border-top-color: rgba(255, 255, 255, 0.08);
  background: #191919;
}

:global(.dark) .account-trigger:hover,
:global(.dark) .account-icon-button:hover,
:global(.dark) .language-option.is-active,
:global(.dark) .account-menu-action:hover {
  background: #252525;
}

:global(.dark) .account-avatar {
  border-color: #3a3a3a;
  background: #252525;
  color: #e6e6e5;
}

:global(.dark) .account-identity strong,
:global(.dark) .sidebar-account-name,
:global(.dark) .language-option:hover,
:global(.dark) .language-option.is-active {
  color: #e6e6e5;
}

:global(.dark) .account-identity > span,
:global(.dark) .account-icon-button,
:global(.dark) .language-option,
:global(.dark) .account-popover-summary > span,
:global(.dark) .account-popover-identity > span,
:global(.dark) .account-menu-action,
:global(.dark) .account-language-row {
  color: #9b9a97;
}

:global(.dark) .language-switcher,
:global(.dark) .account-popover-summary {
  border-color: #2f2f2f;
}

:global(.dark) .account-popover {
  border-color: #373737;
  background: #202020;
  color: #e6e6e5;
  box-shadow: 0 8px 28px rgb(0 0 0 / 38%);
}

:global(.dark) .account-start-button {
  background: var(--workspace-action-primary, #137fec);
  color: #ffffff;
}

@media (max-width: 767px) {
  .account-popover--sidebar {
    position: fixed;
    right: 10px;
    bottom: max(10px, env(safe-area-inset-bottom));
    left: 62px;
    width: auto;
    max-width: 280px;
  }
}

@media (max-width: 520px) {
  .account-controls--header {
    gap: 3px;
  }

  .account-trigger--header {
    gap: 4px;
    padding-right: 4px;
    padding-left: 4px;
  }

  .account-controls--header .account-identity {
    display: none;
  }

  .account-controls--header .language-switcher {
    padding-left: 4px;
  }

  .account-controls--header .language-option {
    padding-right: 4px;
    padding-left: 4px;
  }
}
</style>
