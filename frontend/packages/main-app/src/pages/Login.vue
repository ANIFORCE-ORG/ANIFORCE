<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref('')
const password = ref('')

function handleLogin() {
  // Demo 模式直接跳转首页
  router.push('/')
}
</script>

<template>
  <main class="flex flex-1 items-center justify-center px-4 py-12">
    <div class="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl p-8">
      <div class="text-center mb-8">
        <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-white mx-auto mb-4">
          <span class="material-symbols-outlined text-3xl">rocket_launch</span>
        </div>
        <h1 class="text-2xl font-bold">欢迎回来</h1>
        <p class="text-sm text-slate-500 mt-2">登录 Game Marketing Pro</p>
      </div>
      <form class="space-y-4" @submit.prevent="handleLogin">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">邮箱</label>
          <input
            v-model="email"
            type="email"
            class="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
            placeholder="demo@example.com"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">密码</label>
          <input
            v-model="password"
            type="password"
            class="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
            placeholder="••••••••"
          />
        </div>
        <button
          type="submit"
          class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary/90 transition-all shadow-lg shadow-primary/30"
        >
          登录
        </button>
      </form>
    </div>
  </main>
</template>
