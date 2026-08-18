<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import NewUserGuide from '@/components/onboarding/NewUserGuide.vue'

const route = useRoute()
const isWorkspaceShell = computed(() => route.meta.workspaceShell === true)
</script>

<template>
  <div
    :class="[
      'relative flex min-h-screen w-full flex-col overflow-x-hidden font-display text-slate-900 dark:bg-background-dark dark:text-slate-100 transition-colors duration-300',
      isWorkspaceShell ? 'workspace-app-shell bg-white' : 'bg-background-light'
    ]"
  >
    <AppHeader v-if="!isWorkspaceShell" />
    <RouterView v-slot="{ Component }">
      <KeepAlive :include="['Home']">
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
    <AppFooter />
    <NewUserGuide v-if="isWorkspaceShell" />
  </div>
</template>
