<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const { info } = useToast()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
if (!email.value && !password.value) {
  error.value = '请输入邮箱和密码'
  return
}

  if (!email.value) {
    error.value = '请输入正确邮箱地址'
    return
  }

  if (!password.value) {
    error.value = '请输入密码'
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

// 忘记密码
function handleForgotPassword() {
  console.log('忘记密码')
  // TODO: 实现忘记密码功能
  info('忘记密码功能开发中，请联系管理员重置密码')
}

</script>

<template>
  <main class="flex flex-1 items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
    <!-- 浮窗容器 -->
    <div class="relative w-full max-w-2xl">
      <!-- 主登录浮窗 -->
      <div class="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <!-- 关闭按钮 -->
        <button 
          class="absolute top-4 right-4 p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          @click="router.push('/')"
        >
          <span class="material-symbols-outlined text-slate-400">close</span>
        </button>

        <!-- 顶部插图区域 -->
        <div class="px-8 pt-12 pb-6 text-center">
          <div class="flex justify-center mb-6">
            <div class="w-24 h-24 bg-gradient-to-br from-primary/10 to-primary/5 rounded-2xl flex items-center justify-center">
              <span class="material-symbols-outlined text-5xl text-primary">rocket_launch</span>
            </div>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">ANIFORCE</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">30 秒内开始您的第一次分析</p>
        </div>

        <!-- 登录方式区域 -->
        <div class="px-8 pb-8">
          <!-- 邮箱密码登录表单 -->
          <div>
            <form class="space-y-5" @submit.prevent="handleLogin">
              <!-- 错误提示 -->
              <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
              </div>

              <!-- 邮箱输入 -->
              <div class="flex items-start gap-4">
                <label class="text-base font-bold text-slate-700 dark:text-slate-300 flex-shrink-0 pt-3">邮箱</label>
                <input
                  v-model="email"
                  type="email"
                  class="flex-1 px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                  placeholder="Your@email.com"
                  :disabled="loading"
                />
              </div>

              <!-- 密码输入 -->
              <div class="flex items-start gap-4">
                <label class="text-base font-bold text-slate-700 dark:text-slate-300 flex-shrink-0 pt-3">密码</label>
                <div class="flex-1">
                  <input
                    v-model="password"
                    type="password"
                    class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    placeholder="Enter your password"
                    :disabled="loading"
                  />
                  <!-- 忘记密码链接 -->
                  <div class="mt-2 text-right">
                    <button
                      type="button"
                      @click="handleForgotPassword"
                      class="text-sm text-primary hover:underline"
                    >
                      忘记密码？
                    </button>
                  </div>
                </div>
              </div>

              <!-- 登录按钮 -->
              <button
                type="submit"
                class="w-full py-3.5 bg-gradient-to-r from-primary to-primary/80 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <span v-if="loading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>{{ loading ? '登录中...' : '登录' }}</span>
              </button>
            </form>
          </div>

          <!-- 服务条款 -->
          <p class="mt-6 text-xs text-center text-slate-500 dark:text-slate-400">
            继续操作即表示您同意 ANIFORCE 的
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

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
