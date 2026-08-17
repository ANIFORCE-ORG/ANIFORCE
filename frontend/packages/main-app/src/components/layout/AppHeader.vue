<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import AccountControls from '@/components/layout/AccountControls.vue'
import logoSvg from '@/assets/aniforce-logo-transparent.svg'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)

const handleLogoClick = () => {
  if (auth.isLoggedIn) {
    void router.push('/home')
  } else {
    void router.push('/')
  }
}
</script>

<template>
  <header :class="['app-header', { 'app-header--workspace': isWorkspaceShell }]">
    <!-- Keep the existing public ANIFORCE Logo rendering unchanged. -->
    <div v-if="!isWorkspaceShell" class="flex items-center gap-2 cursor-pointer shrink-0" @click="handleLogoClick">
      <img :src="logoSvg" alt="ANIFORCE" class="h-10 w-auto max-w-[176px] object-contain logo-blue" />
    </div>

    <AccountControls v-if="!isWorkspaceShell" variant="header" />
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
  padding: 8px 20px;
  border-bottom: 1px solid #e9e9e7;
  background: #ffffff;
  color: #37352f;
}

.app-header--workspace {
  min-height: 57px;
  justify-content: flex-end;
  border-bottom: 0.5px solid rgba(55, 53, 47, 0.16);
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

:global(.dark) .app-header.app-header--workspace {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

@media (min-width: 768px) {
  .app-header {
    padding-right: 40px;
    padding-left: 40px;
  }
}

@media (max-width: 520px) {
  .app-header {
    gap: 8px;
    padding: 6px 10px;
  }

  .app-header img {
    width: auto;
    height: 32px;
    max-width: 110px;
  }
}
</style>
