<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
</script>

<template>
  <div class="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 transition-colors duration-300">
    <AppHeader />
    <RouterView v-slot="{ Component }">
      <KeepAlive :include="['Home']">
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
    <AppFooter />
  </div>
</template>
