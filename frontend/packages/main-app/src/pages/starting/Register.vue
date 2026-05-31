<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const name = ref('')
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  // 验证输入
  if (!name.value || !email.value || !password.value) {
    error.value = '请填写所有必填项'
    return
  }

  if (!isValidEmail(email.value)) {
    error.value = '请输入有效的邮箱地址'
    return
  }

  if (password.value.length < 6) {
    error.value = '密码长度至少为 6 位'
    return
  }

  loading.value = true
  error.value = ''

  try {
    // 调用真实的注册 API
    const result = await auth.register({
      name: name.value,
      email: email.value,
      password: password.value
    })

    if (result.success) {
      // 注册成功，自动登录并跳转到首页
      router.push('/home')
    } else {
      error.value = result.message || '注册失败，请稍后重试'
    }
  } catch (err: any) {
    error.value = err.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

function goToLogin() {
  router.push('/login')
}
</script>

<template>
  <main class="flex flex-1 items-center justify-center px-4 py-6 bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
    <!-- 浮窗容器 -->
    <div class="relative w-full max-w-2xl">
      <!-- 注册浮窗 -->
      <div class="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <!-- 关闭按钮 -->
        <button 
          class="absolute top-4 right-4 p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
          @click="router.push('/')"
        >
          <span class="material-symbols-outlined text-slate-400">close</span>
        </button>

        <!-- 顶部插图区域 -->
        <div class="px-8 pt-8 pb-4 text-center">
          <div class="flex justify-center mb-4">
            <div class="w-20 h-20 bg-gradient-to-br from-primary/10 to-primary/5 rounded-2xl flex items-center justify-center">
              <span class="material-symbols-outlined text-4xl text-primary">person_add</span>
            </div>
          </div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white mb-1">创建账号</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">加入 ANIFORCE 开启您的营销之旅</p>
        </div>

        <!-- 注册表单区域 -->
        <div class="px-8 pb-6">
          <form class="space-y-3" @submit.prevent="handleRegister">
            <!-- 错误提示 -->
            <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
              <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
            </div>

            <!-- 姓名 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                姓名 <span class="text-red-500">*</span>
              </label>
              <input
                v-model="name"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                placeholder="您的姓名"
                :disabled="loading"
                required
              />
            </div>

            <!-- 邮箱 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                邮箱 <span class="text-red-500">*</span>
              </label>
              <input
                v-model="email"
                type="email"
                class="w-full px-4 py-2.5 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                placeholder="your@email.com"
                :disabled="loading"
                required
              />
            </div>

            <!-- 密码 -->
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                密码 <span class="text-red-500">*</span>
              </label>
              <input
                v-model="password"
                type="password"
                class="w-full px-4 py-2.5 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                placeholder="至少 6 位密码"
                :disabled="loading"
                required
              />
            </div>

            <!-- 注册按钮 -->
            <button
              type="submit"
              class="w-full py-3 bg-gradient-to-r from-primary to-primary/80 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              :disabled="loading"
            >
              <span v-if="loading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>{{ loading ? '注册中...' : '注册' }}</span>
            </button>

            <!-- 返回登录 -->
            <div class="text-center">
              <span class="text-sm text-slate-600 dark:text-slate-400">已有账号？</span>
              <button
                type="button"
                @click="goToLogin"
                class="ml-1 text-sm text-primary hover:underline font-medium"
              >
                立即登录
              </button>
            </div>
          </form>

          <!-- 服务条款 -->
          <p class="mt-6 text-xs text-center text-slate-500 dark:text-slate-400">
            注册即表示您同意 ANIFORCE 的
            <a href="#" class="text-primary hover:underline">服务条款</a>
            和
            <a href="#" class="text-primary hover:underline">隐私政策</a>
          </p>
        </div>

        <!-- 底部版权 -->
        <div class="px-8 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
          <p class="text-xs text-center text-slate-400 dark:text-slate-500">© 2026 ANIFORCE</p>
        </div>
      </div>
    </div>
  </main>
</template>
