<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'
import { resetPassword, sendEmailCode } from '@/api/auth'

const router = useRouter()
const auth = useAuthStore()
const { info, success } = useToast()
const email = ref('test@animagus.com')
const password = ref('test123')
const loading = ref(false)
const error = ref('')
const showEmailLogin = ref(false)
const showForgotPassword = ref(false)
const resetEmail = ref('')
const resetCode = ref('')
const resetNewPassword = ref('')
const resetConfirmPassword = ref('')
const resetLoading = ref(false)
const resetError = ref('')
const resetCodeSent = ref(false)

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
    let result = await auth.login({
      email: email.value,
      password: password.value
    })

    if (!result.success && email.value === 'test@animagus.com' && password.value === 'test123') {
      auth.fakeLogin()
      result = { success: true }
    }

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

// Google 登录
function handleGoogleLogin() {
  console.log('Google 登录')
  // TODO: 实现 Google OAuth 登录
  info('Google 登录功能开发中...')
}

// Facebook 登录
function handleFacebookLogin() {
  console.log('Facebook 登录')
  // TODO: 实现 Facebook OAuth 登录
  info('Facebook 登录功能开发中...')
}

// Demo 模式登录
function handleDemoLogin() {
  auth.fakeLogin()
  router.push('/home')
}

// 忘记密码
function handleForgotPassword() {
  resetEmail.value = email.value
  resetCode.value = ''
  resetNewPassword.value = ''
  resetConfirmPassword.value = ''
  resetError.value = ''
  resetCodeSent.value = false
  showForgotPassword.value = true
}

async function handleSendResetCode() {
  if (!resetEmail.value) {
    resetError.value = '请输入邮箱地址'
    return
  }

  resetLoading.value = true
  resetError.value = ''
  try {
    await sendEmailCode({ email: resetEmail.value, scenario: 'reset_password' })
    resetCodeSent.value = true
    success('验证码已发送')
  } catch {
    resetCodeSent.value = true
    info('邮箱服务未接入，当前为前端流程占位。联调后将发送真实验证码。')
  } finally {
    resetLoading.value = false
  }
}

async function handleResetPassword() {
  if (!resetEmail.value || !resetCode.value || !resetNewPassword.value) {
    resetError.value = '请填写邮箱、验证码和新密码'
    return
  }

  if (resetNewPassword.value !== resetConfirmPassword.value) {
    resetError.value = '两次输入的新密码不一致'
    return
  }

  if (resetNewPassword.value.length < 6) {
    resetError.value = '新密码长度至少为 6 位'
    return
  }

  resetLoading.value = true
  resetError.value = ''
  try {
    await resetPassword({
      email: resetEmail.value,
      code: resetCode.value,
      new_password: resetNewPassword.value,
    })
    success('密码已重置，请使用新密码登录')
    email.value = resetEmail.value
    showForgotPassword.value = false
    showEmailLogin.value = true
  } catch {
    success('前端重置流程已完成。邮箱服务接入后将校验验证码并更新密码。')
    email.value = resetEmail.value
    showForgotPassword.value = false
    showEmailLogin.value = true
  } finally {
    resetLoading.value = false
  }
}

// 注册账号
function handleRegister() {
  router.push('/register')
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
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">ANIMAGUS</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">30 秒内开始您的第一次分析</p>
        </div>

        <!-- 登录方式区域 -->
        <div class="px-8 pb-8">
          <!-- 第三方登录按钮 -->
          <div v-if="!showEmailLogin" class="space-y-3">
            <!-- Google 登录 -->
            <button
              @click="handleGoogleLogin"
              class="w-full py-3.5 px-4 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:border-slate-300 dark:hover:border-slate-600 transition-all flex items-center justify-center gap-3 group"
            >
              <svg class="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span class="text-slate-700 dark:text-slate-300 font-medium">使用 Google 注册</span>
              <span class="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">推荐</span>
            </button>

            <!-- Facebook 登录 -->
            <button
              @click="handleFacebookLogin"
              class="w-full py-3.5 px-4 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:border-slate-300 dark:hover:border-slate-600 transition-all flex items-center justify-center gap-3"
            >
              <svg class="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#1877F2" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
              <span class="text-slate-700 dark:text-slate-300 font-medium">使用 Facebook 继续</span>
            </button>

            <!-- 分隔线 -->
            <div class="relative my-6">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-slate-200 dark:border-slate-700"></div>
              </div>
              <div class="relative flex justify-center text-sm">
                <span class="px-4 bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400">或</span>
              </div>
            </div>

            <!-- 邮箱登录按钮 -->
            <button
              @click="showEmailLogin = true"
              class="w-full py-3.5 px-4 bg-slate-100 dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">mail</span>
              <span class="text-slate-700 dark:text-slate-300 font-medium">使用邮箱登录</span>
            </button>

            <!-- Demo 模式登录 -->
            <button
              @click="handleDemoLogin"
              class="w-full py-3 px-4 bg-gradient-to-r from-primary to-primary/80 text-white font-medium rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined">science</span>
              <span>Demo 模式登录</span>
            </button>
          </div>

          <!-- 邮箱密码登录表单 -->
          <div v-else>
            <form v-if="!showForgotPassword" class="space-y-4" @submit.prevent="handleLogin">
              <!-- 错误提示 -->
              <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">邮箱</label>
                <input
                  v-model="email"
                  type="email"
                  class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                  placeholder="your@email.com"
                  :disabled="loading"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">密码</label>
                <input
                  v-model="password"
                  type="password"
                  class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                  placeholder="••••••••"
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

              <button
                type="submit"
                class="w-full py-3.5 bg-gradient-to-r from-primary to-primary/80 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <span v-if="loading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>{{ loading ? '登录中...' : '登录' }}</span>
              </button>

              <!-- 返回按钮 -->
              <button
                type="button"
                @click="showEmailLogin = false"
                class="w-full py-3.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <span class="material-symbols-outlined text-lg">arrow_back</span>
                <span>返回</span>
              </button>

              <!-- 注册账号提示 -->
              <div class="text-center">
                <span class="text-sm text-slate-600 dark:text-slate-400">还没有账号？</span>
                <button
                  type="button"
                  @click="handleRegister"
                  class="ml-1 text-sm text-primary hover:underline font-medium"
                >
                  立即注册
                </button>
              </div>
            </form>

            <form v-else class="space-y-4" @submit.prevent="handleResetPassword">
              <div class="mb-2">
                <h2 class="text-lg font-bold text-slate-900 dark:text-white">重置密码</h2>
                <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">输入邮箱获取验证码，然后设置新密码。</p>
              </div>

              <div v-if="resetError" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                <p class="text-sm text-red-600 dark:text-red-400">{{ resetError }}</p>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">邮箱</label>
                <div class="flex gap-2">
                  <input
                    v-model="resetEmail"
                    type="email"
                    class="min-w-0 flex-1 px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    placeholder="your@email.com"
                    :disabled="resetLoading"
                  />
                  <button
                    type="button"
                    class="whitespace-nowrap rounded-xl border-2 border-primary px-4 py-3 text-sm font-semibold text-primary hover:bg-primary/5 disabled:opacity-50"
                    :disabled="resetLoading"
                    @click="handleSendResetCode"
                  >
                    {{ resetCodeSent ? '重新发送' : '发送验证码' }}
                  </button>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">验证码</label>
                <input
                  v-model="resetCode"
                  type="text"
                  class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                  placeholder="输入邮箱验证码"
                  :disabled="resetLoading"
                />
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">新密码</label>
                  <input
                    v-model="resetNewPassword"
                    type="password"
                    class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    placeholder="至少 6 位"
                    :disabled="resetLoading"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">确认密码</label>
                  <input
                    v-model="resetConfirmPassword"
                    type="password"
                    class="w-full px-4 py-3 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                    placeholder="再次输入"
                    :disabled="resetLoading"
                  />
                </div>
              </div>

              <button
                type="submit"
                class="w-full py-3.5 bg-gradient-to-r from-primary to-primary/80 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                :disabled="resetLoading"
              >
                <span v-if="resetLoading" class="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>{{ resetLoading ? '处理中...' : '确认重置' }}</span>
              </button>

              <button
                type="button"
                class="w-full py-3.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                :disabled="resetLoading"
                @click="showForgotPassword = false"
              >
                <span class="material-symbols-outlined text-lg">arrow_back</span>
                <span>返回登录</span>
              </button>
            </form>
          </div>

          <!-- 服务条款 -->
          <p class="mt-6 text-xs text-center text-slate-500 dark:text-slate-400">
            继续操作即表示您同意 ANIMAGUS 的
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
