<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()
const email = ref('admin@animagus.ai')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!email.value || !password.value) {
    error.value = '请输入邮箱和密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const result = await auth.login({
      email: email.value,
      password: password.value
    })

    if (result.success) {
      // 登录成功,router守卫会自动处理跳转
      router.push('/home')
    } else {
      error.value = result.message || '登录失败,请检查账号密码'
    }
  } catch (err: any) {
    error.value = err.message || '登录失败,请稍后重试'
  } finally {
    loading.value = false
  }
}

// 开发模式下的快速登录
function handleDemoLogin() {
  auth.fakeLogin()
  router.push('/home')
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
        <p class="text-sm text-slate-500 mt-2">登录 ANIMAGUS</p>
      </div>
      <form class="space-y-4" @submit.prevent="handleLogin">
        <!-- 错误提示 -->
        <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">邮箱</label>
          <input
            v-model="email"
            type="email"
            class="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
            placeholder="demo@example.com"
            :disabled="loading"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">密码</label>
          <input
            v-model="password"
            type="password"
            class="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
            placeholder="••••••••"
            :disabled="loading"
          />
        </div>
        <button
          type="submit"
          class="w-full py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary/90 transition-all shadow-lg shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          :disabled="loading"
        >
          <span v-if="loading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          <span>{{ loading ? '登录中...' : '登录' }}</span>
        </button>

        <!-- Demo登录按钮 -->
        <button
          type="button"
          class="w-full py-3 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all"
          @click="handleDemoLogin"
          :disabled="loading"
        >
          Demo模式登录
        </button>
      </form>
    </div>
  </main>
</template>
