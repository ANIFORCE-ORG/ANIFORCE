<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useLanguage } from '@/store/language'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const { language } = useLanguage()
const { info } = useToast()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const demoMode = import.meta.env.VITE_DEMO_MODE === 'true'

// Bilingual copy
const copy = {
  cn: {
    title: 'ANIFORCE',
    subtitle: '30 秒内开始您的第一次分析',
    emailLabel: '邮箱',
    emailPlaceholder: 'Your@email.com',
    passwordLabel: '密码',
    passwordPlaceholder: 'Enter your password',
    forgotPassword: '忘记密码？',
    loginButton: '登录',
    loggingIn: '登录中...',
    termsText: '继续操作即表示您同意 ANIFORCE 的',
    termsLink: '服务条款',
    and: '和',
    privacyLink: '隐私政策',
    errors: {
      emailAndPassword: '请输入邮箱和密码',
      invalidEmail: '请输入正确邮箱地址',
      passwordRequired: '请输入密码',
      loginFailed: '登录失败,请检查账号密码',
      loginError: '登录失败,请稍后重试'
    },
    forgotPasswordMessage: '忘记密码功能开发中，请联系管理员重置密码'
  },
  en: {
    title: 'ANIFORCE',
    subtitle: 'Start your first analysis in 30 seconds',
    emailLabel: 'Email',
    emailPlaceholder: 'Your@email.com',
    passwordLabel: 'Password',
    passwordPlaceholder: 'Enter your password',
    forgotPassword: 'Forgot password?',
    loginButton: 'Login',
    loggingIn: 'Logging in...',
    termsText: 'By continuing, you agree to ANIFORCE\'s',
    termsLink: 'Terms of Service',
    and: 'and',
    privacyLink: 'Privacy Policy',
    errors: {
      emailAndPassword: 'Please enter email and password',
      invalidEmail: 'Please enter a valid email address',
      passwordRequired: 'Please enter password',
      loginFailed: 'Login failed, please check your credentials',
      loginError: 'Login failed, please try again later'
    },
    forgotPasswordMessage: 'Forgot password feature is under development, please contact admin to reset password'
  }
}

const t = computed(() => copy[language.value])

async function handleLogin() {
  if (demoMode) {
    auth.fakeLogin()
    router.push('/home')
    return
  }

  if (!email.value && !password.value) {
    error.value = t.value.errors.emailAndPassword
    return
  }

  if (!email.value) {
    error.value = t.value.errors.invalidEmail
    return
  }

  if (!password.value) {
    error.value = t.value.errors.passwordRequired
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
      error.value = result.message || t.value.errors.loginFailed
    }
  } catch (err: any) {
    error.value = err.message || t.value.errors.loginError
  } finally {
    loading.value = false
  }
}

// 忘记密码
function handleForgotPassword() {
  console.log('忘记密码')
  // TODO: 实现忘记密码功能
  info(t.value.forgotPasswordMessage)
}

</script>

<template>
  <main class="flex flex-1 items-center justify-center px-3 py-10 bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
    <!-- 浮窗容器 -->
    <div class="relative w-full max-w-xl">
      <!-- 主登录浮窗 -->
      <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <!-- 关闭按钮 -->
        <button 
          class="absolute top-3 right-3 p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          @click="router.push('/')"
        >
          <span class="material-symbols-outlined text-lg text-slate-400">close</span>
        </button>

        <!-- 顶部插图区域 -->
        <div class="px-6 pt-10 pb-5 text-center">
          <div class="flex justify-center mb-5">
            <div class="w-20 h-20 bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl flex items-center justify-center">
              <span class="material-symbols-outlined text-4xl text-primary">rocket_launch</span>
            </div>
          </div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white mb-1.5">{{ t.title }}</h1>
          <p class="text-xs text-slate-500 dark:text-slate-400">{{ t.subtitle }}</p>
        </div>

        <!-- 登录方式区域 -->
        <div class="px-6 pb-6">
          <!-- 邮箱密码登录表单 -->
          <div>
            <form class="space-y-4" @submit.prevent="handleLogin">
              <!-- 错误提示 -->
              <div v-if="error" class="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p class="text-xs text-red-600 dark:text-red-400">{{ error }}</p>
              </div>

              <!-- 邮箱输入 -->
              <div class="flex items-start gap-3">
                <label class="w-20 text-sm font-bold text-slate-700 dark:text-slate-300 flex-shrink-0 pt-2">{{ t.emailLabel }}</label>
                <input
                  v-model="email"
                  type="email"
                  class="flex-1 px-3 py-2 rounded-lg border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-sm"
                  :placeholder="t.emailPlaceholder"
                  :disabled="loading"
                />
              </div>

              <!-- 密码输入 -->
              <div class="flex items-start gap-3">
                <label class="w-20 text-sm font-bold text-slate-700 dark:text-slate-300 flex-shrink-0 pt-2">{{ t.passwordLabel }}</label>
                <div class="flex-1">
                  <input
                    v-model="password"
                    type="password"
                    class="w-full px-3 py-2 rounded-lg border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all text-sm"
                    :placeholder="t.passwordPlaceholder"
                    :disabled="loading"
                  />
                  <!-- 忘记密码链接 -->
                  <div class="mt-1.5 text-right">
                    <button
                      type="button"
                      @click="handleForgotPassword"
                      class="text-xs text-primary hover:underline"
                    >
                      {{ t.forgotPassword }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- 登录按钮 -->
              <button
                type="submit"
                class="w-full py-2.5 bg-gradient-to-r from-primary to-primary/80 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
                :disabled="loading"
              >
                <span v-if="loading" class="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>{{ loading ? t.loggingIn : t.loginButton }}</span>
              </button>
            </form>
          </div>

          <!-- 服务条款 -->
          <p class="mt-5 text-[10px] text-center text-slate-500 dark:text-slate-400">
            {{ t.termsText }}
            <a href="#" class="text-primary hover:underline">{{ t.termsLink }}</a>
            {{ t.and }}
            <a href="#" class="text-primary hover:underline">{{ t.privacyLink }}</a>
          </p>
        </div>

        <!-- 底部版权 -->
        <div class="px-6 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
          <p class="text-[10px] text-center text-slate-400 dark:text-slate-500">© 2026 ANIFORCE</p>
        </div>
      </div>
    </div>
  </main>

  <!-- Toast 提示容器 -->
  <ToastContainer />
</template>
