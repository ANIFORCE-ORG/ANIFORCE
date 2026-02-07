<script setup lang="ts">
import { ref } from 'vue'

const navItems = [
  { label: 'Dashboard', href: '/', active: true },
  { label: 'Assets', href: '/material' },
  { label: 'Analytics', href: '/monitor' },
  { label: 'Settings', href: '/settings' },
]

const currentNav = ref('Dashboard')
</script>

<template>
  <header class="flex items-center justify-between px-6 py-4 md:px-12 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-50">
    <!-- Logo -->
    <div class="flex items-center gap-3">
      <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white">
        <span class="material-symbols-outlined">rocket_launch</span>
      </div>
      <h2 class="text-lg font-bold tracking-tight">Game Marketing Pro</h2>
    </div>

    <!-- Navigation -->
    <nav class="hidden md:flex items-center gap-8">
      <a
        v-for="item in navItems"
        :key="item.label"
        :href="item.href"
        class="text-sm font-medium transition-colors"
        :class="currentNav === item.label
          ? 'font-semibold text-primary'
          : 'text-slate-600 dark:text-slate-400 hover:text-primary'"
        @click.prevent="currentNav = item.label"
      >
        {{ item.label }}
      </a>
    </nav>

    <!-- Right Actions -->
    <div class="flex items-center gap-4">
      <button class="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
        <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">notifications</span>
      </button>
      <div class="h-10 w-10 rounded-full bg-slate-200 dark:bg-slate-700 border-2 border-white dark:border-slate-800 overflow-hidden shadow-sm flex items-center justify-center">
        <span class="material-symbols-outlined text-slate-500">person</span>
      </div>
    </div>
  </header>
</template>
