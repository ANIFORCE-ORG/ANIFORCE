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
  <main class="login-page">
    <section class="login-card" aria-labelledby="login-title">
      <button class="login-close" type="button" aria-label="关闭登录" @click="router.push('/')">
        <span class="material-symbols-outlined" aria-hidden="true">close</span>
      </button>

      <header class="login-intro">
        <div class="login-mark" aria-hidden="true">
          <span class="material-symbols-outlined">rocket_launch</span>
        </div>
        <h1 id="login-title">{{ t.title }}</h1>
        <p>{{ t.subtitle }}</p>
      </header>

      <form class="login-form" @submit.prevent="handleLogin">
        <div v-if="error" class="login-error" role="alert">{{ error }}</div>

        <div class="login-field">
          <label for="login-email">{{ t.emailLabel }}</label>
          <input
            id="login-email"
            v-model="email"
            class="login-input"
            type="email"
            autocomplete="email"
            :placeholder="t.emailPlaceholder"
            :disabled="loading"
          />
        </div>

        <div class="login-field">
          <div class="login-password-label">
            <label for="login-password">{{ t.passwordLabel }}</label>
            <button class="login-forgot" type="button" @click="handleForgotPassword">
              {{ t.forgotPassword }}
            </button>
          </div>
          <input
            id="login-password"
            v-model="password"
            class="login-input"
            type="password"
            autocomplete="current-password"
            :placeholder="t.passwordPlaceholder"
            :disabled="loading"
          />
        </div>

        <button class="login-submit" type="submit" :disabled="loading">
          <span v-if="loading" class="login-spinner" aria-hidden="true"></span>
          <span>{{ loading ? t.loggingIn : t.loginButton }}</span>
        </button>
      </form>

      <p class="login-terms">
        {{ t.termsText }}
        <a href="#">{{ t.termsLink }}</a>
        {{ t.and }}
        <a href="#">{{ t.privacyLink }}</a>
      </p>

      <footer class="login-copyright">© 2026 ANIFORCE</footer>
    </section>
  </main>

  <ToastContainer />
</template>

<style scoped>
.login-page {
  --login-canvas: var(--workspace-canvas, #ffffff);
  --login-surface: var(--workspace-content-surface, #ffffff);
  --login-soft: var(--workspace-metric-surface, #f6f5f4);
  --login-line: var(--workspace-hairline, #e5e3df);
  --login-ink: var(--workspace-ink, #1a1a1a);
  --login-muted: var(--workspace-muted, #787671);
  --login-primary: var(--workspace-action-primary, #137fec);
  --login-primary-hover: var(--workspace-action-primary-hover, #0f6fcf);
  display: grid;
  flex: 1;
  place-items: center;
  width: 100%;
  padding: 40px 24px;
  background: var(--login-canvas);
  color: var(--login-ink);
  font-family: var(--workspace-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
}

.login-card {
  position: relative;
  width: min(100%, 420px);
  overflow: hidden;
  border: 1px solid var(--login-line);
  border-radius: 12px;
  background: var(--login-surface);
  box-shadow: rgba(15, 15, 15, 0.08) 0 12px 36px;
}

.login-close {
  position: absolute;
  z-index: 1;
  top: 12px;
  right: 12px;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--login-muted);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.login-close:hover {
  background: var(--login-soft);
  color: var(--login-ink);
}

.login-close:focus-visible,
.login-forgot:focus-visible,
.login-submit:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--login-primary) 45%, transparent);
  outline-offset: 2px;
}

.login-close .material-symbols-outlined {
  font-size: 18px;
}

.login-intro {
  padding: 42px 36px 24px;
  text-align: center;
}

.login-mark {
  display: grid;
  width: 44px;
  height: 44px;
  margin: 0 auto 16px;
  place-items: center;
  border: 1px solid var(--login-line);
  border-radius: 9px;
  background: var(--login-soft);
  color: var(--login-primary);
}

.login-mark .material-symbols-outlined {
  font-size: 24px;
}

.login-intro h1 {
  margin: 0;
  color: var(--login-ink);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.login-intro p {
  margin: 6px 0 0;
  color: var(--login-muted);
  font-size: 13px;
  line-height: 1.5;
}

.login-form {
  display: grid;
  gap: 16px;
  padding: 0 36px 24px;
}

.login-field {
  display: grid;
  gap: 7px;
}

.login-field label,
.login-password-label {
  color: #37352f;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

.login-password-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.login-forgot {
  border: 0;
  background: transparent;
  color: var(--login-muted);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.login-forgot:hover {
  color: var(--login-primary);
}

.login-input {
  width: 100%;
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid var(--login-line);
  border-radius: 6px;
  outline: none;
  background: var(--login-surface);
  color: var(--login-ink);
  font: inherit;
  font-size: 14px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.login-input::placeholder {
  color: #a4a097;
}

.login-input:hover:not(:disabled) {
  border-color: rgba(55, 53, 47, 0.28);
}

.login-input:focus {
  border-color: var(--login-primary);
  box-shadow: rgba(19, 127, 236, 0.14) 0 0 0 2px;
}

.login-input:disabled {
  background: var(--login-soft);
  cursor: not-allowed;
  opacity: 0.68;
}

.login-error {
  padding: 9px 10px;
  border: 1px solid #f1c5c0;
  border-radius: 6px;
  background: #fff5f3;
  color: #c93c37;
  font-size: 12px;
  line-height: 1.45;
}

.login-submit {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 2px;
  padding: 8px 14px;
  border: 1px solid var(--login-primary);
  border-radius: 6px;
  background: var(--login-primary);
  color: #ffffff;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.login-submit:hover:not(:disabled) {
  border-color: var(--login-primary-hover);
  background: var(--login-primary-hover);
}

.login-submit:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.login-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: login-spin 0.7s linear infinite;
}

.login-terms {
  margin: 0;
  padding: 0 36px 24px;
  color: var(--login-muted);
  font-size: 11px;
  line-height: 1.65;
  text-align: center;
}

.login-terms a {
  color: #37352f;
  text-decoration: none;
}

.login-terms a:hover {
  text-decoration: underline;
}

.login-copyright {
  padding: 12px 20px;
  border-top: 1px solid var(--login-line);
  background: #fbfbfa;
  color: #a4a097;
  font-size: 11px;
  line-height: 1.4;
  text-align: center;
}

@keyframes login-spin {
  to { transform: rotate(360deg); }
}

:global(.dark) .login-page {
  --login-canvas: #191919;
  --login-surface: #202020;
  --login-soft: #2a2a2a;
  --login-line: #373737;
  --login-ink: #f4f4f2;
  --login-muted: #a6a6a2;
}

:global(.dark) .login-field label,
:global(.dark) .login-password-label,
:global(.dark) .login-terms a {
  color: #e8e8e5;
}

:global(.dark) .login-copyright {
  background: #252525;
}

@media (max-width: 560px) {
  .login-page {
    align-items: start;
    padding: 20px 16px;
  }

  .login-intro {
    padding: 38px 24px 22px;
  }

  .login-form {
    padding: 0 24px 22px;
  }

  .login-terms {
    padding: 0 24px 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-close,
  .login-input,
  .login-submit {
    transition: none;
  }
}
</style>
