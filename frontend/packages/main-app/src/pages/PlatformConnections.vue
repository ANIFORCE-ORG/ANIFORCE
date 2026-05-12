<script setup lang="ts">
// @ts-nocheck
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import {
  connectPlatformToken,
  getPlatformConnectUrl,
  getPlatformConnectionConfig,
  savePlatformConnectionConfig,
  type PlatformConnectionConfig,
} from '@/api/platformAccounts'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const connecting = ref(false)
const fbSdkReady = ref(false)
const error = ref('')
const success = ref('')
const config = ref<PlatformConnectionConfig | null>(null)
const activePlatform = ref<'meta' | 'google' | 'tiktok'>('meta')

const platforms = [
  {
    id: 'meta',
    label: 'Meta',
    title: 'Meta Business OAuth',
    description: '连接 Facebook / Instagram 广告账户，支持真实创建 Campaign',
    status: 'available',
  },
  {
    id: 'google',
    label: 'Google',
    title: 'Google Ads OAuth',
    description: '连接 Google Ads 账号，后续同步客户账号和投放计划',
    status: 'planned',
  },
  {
    id: 'tiktok',
    label: 'TikTok',
    title: 'TikTok Ads OAuth',
    description: '连接 TikTok Ads 账号，后续同步广告账户和计划创建能力',
    status: 'planned',
  },
] as const

const activePlatformConfig = computed(() => platforms.find(platform => platform.id === activePlatform.value) || platforms[0])

const form = ref({
  app_id: '',
  app_secret: '',
  redirect_uri: '',
})

const tokenForm = ref({
  access_token: '',
  account_id: '',
  account_name: 'Meta Sandbox Ad Account',
})

const scopes = ['ads_management', 'ads_read', 'business_management']

declare global {
  interface Window {
    FB?: any
    fbAsyncInit?: () => void
  }
}

const switchPanel = (item: { path: string }) => {
  if (item.path) router.push(item.path)
}

const loadConfig = async () => {
  loading.value = true
  error.value = ''
  try {
    config.value = await getPlatformConnectionConfig('meta')
    form.value.app_id = config.value.app_id || ''
    form.value.redirect_uri = config.value.redirect_uri || ''
  } catch (err: any) {
    error.value = err.message || '加载平台连接配置失败'
  } finally {
    loading.value = false
  }
}

const loadFacebookSdk = () => {
  if (window.FB) {
    fbSdkReady.value = true
    return
  }
  window.fbAsyncInit = () => {
    fbSdkReady.value = true
    if (form.value.app_id) {
      window.FB.init({
        appId: form.value.app_id,
        cookie: true,
        xfbml: true,
        version: 'v19.0',
      })
      window.FB.AppEvents?.logPageView?.()
    }
  }
  if (document.getElementById('facebook-jssdk')) return
  const firstScript = document.getElementsByTagName('script')[0]
  const sdkScript = document.createElement('script')
  sdkScript.id = 'facebook-jssdk'
  sdkScript.src = 'https://connect.facebook.net/en_US/sdk.js'
  firstScript.parentNode?.insertBefore(sdkScript, firstScript)
}

const initFacebookSdk = () => {
  if (!window.FB || !form.value.app_id) return
  window.FB.init({
    appId: form.value.app_id,
    cookie: true,
    xfbml: true,
    version: 'v19.0',
  })
}

const saveConfig = async () => {
  if (!form.value.app_id.trim()) {
    error.value = '请填写 Meta App ID'
    return
  }
  if (!config.value?.has_app_secret && !form.value.app_secret.trim()) {
    error.value = '首次配置请填写 Meta App Secret'
    return
  }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    config.value = await savePlatformConnectionConfig('meta', {
      app_id: form.value.app_id.trim(),
      app_secret: form.value.app_secret.trim() || undefined,
      redirect_uri: form.value.redirect_uri.trim() || undefined,
      scopes,
    })
    form.value.app_secret = ''
    initFacebookSdk()
    success.value = 'Meta 连接配置已保存'
  } catch (err: any) {
    error.value = err.message || '保存 Meta 连接配置失败'
  } finally {
    saving.value = false
  }
}

const connectMeta = async () => {
  connecting.value = true
  error.value = ''
  success.value = ''
  try {
    const result = await getPlatformConnectUrl('meta')
    window.location.href = result.auth_url
  } catch (err: any) {
    error.value = err.message || '无法发起 Meta 授权'
  } finally {
    connecting.value = false
  }
}

const connectWithFacebookSdk = async () => {
  if (!form.value.app_id.trim()) {
    error.value = '请先保存 Meta App ID'
    return
  }
  if (!window.FB) {
    error.value = 'Facebook SDK 还未加载完成，请稍后再试'
    return
  }
  connecting.value = true
  error.value = ''
  success.value = ''
  initFacebookSdk()
  window.FB.login(async (response: any) => {
    try {
      if (!response?.authResponse?.accessToken) {
        throw new Error('Facebook 授权未完成')
      }
      const result = await connectPlatformToken({
        platform: 'meta',
        access_token: response.authResponse.accessToken,
        source_type: 'facebook-js-sdk',
        remark: 'Connected with Facebook JavaScript SDK',
      })
      success.value = `Facebook 授权成功，已同步 ${result.accounts.length} 个广告账户`
      router.push('/platform-accounts/manage')
    } catch (err: any) {
      error.value = err.message || 'Facebook SDK 授权失败'
    } finally {
      connecting.value = false
    }
  }, {
    scope: scopes.join(','),
    return_scopes: true,
    auth_type: 'rerequest',
  })
}

const importSandboxToken = async () => {
  if (!tokenForm.value.access_token.trim() || !tokenForm.value.account_id.trim()) {
    error.value = '请填写沙盒 Access Token 和广告账户编号'
    return
  }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const result = await connectPlatformToken({
      platform: 'meta',
      access_token: tokenForm.value.access_token.trim(),
      account_id: tokenForm.value.account_id.trim().startsWith('act_')
        ? tokenForm.value.account_id.trim()
        : `act_${tokenForm.value.account_id.trim()}`,
      account_name: tokenForm.value.account_name.trim() || 'Meta Sandbox Ad Account',
      source_type: 'sandbox-token-import',
      remark: 'Imported from Meta sample code sandbox token',
    })
    tokenForm.value.access_token = ''
    success.value = `已导入 ${result.accounts.length} 个 Meta 广告账户`
  } catch (err: any) {
    error.value = err.message || '导入 Meta 沙盒账户失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadConfig()
  loadFacebookSdk()
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav active-panel="platform-connections" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white">平台连接</h1>
          <p class="text-sm text-slate-500 mt-1">配置 Meta、Google、TikTok 的平台授权和广告账户同步</p>
        </div>
      </div>

      <div class="p-6 space-y-6 max-w-5xl">
        <div class="grid grid-cols-3 gap-3">
          <button
            v-for="platform in platforms"
            :key="platform.id"
            class="rounded-md border p-4 text-left transition-colors"
            :class="[
              activePlatform === platform.id ? 'border-primary bg-primary/5' : 'border-slate-200',
              platform.status === 'available' ? 'hover:border-primary/50' : 'cursor-not-allowed opacity-70 bg-slate-50'
            ]"
            @click="platform.status === 'available' && (activePlatform = platform.id)"
          >
            <div class="flex items-center justify-between">
              <div class="font-semibold text-slate-900">{{ platform.label }}</div>
              <span
                class="rounded px-2 py-1 text-xs font-medium"
                :class="platform.status === 'available' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'"
              >
                {{ platform.status === 'available' ? '可连接' : '待接入' }}
              </span>
            </div>
            <p class="mt-2 text-xs text-slate-500">{{ platform.description }}</p>
          </button>
        </div>

        <section v-if="activePlatform !== 'meta'" class="rounded-md border border-slate-200 p-6 bg-white">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-slate-500">construction</span>
            <h2 class="text-sm font-semibold text-slate-900">{{ activePlatformConfig.title }}</h2>
          </div>
          <p class="mt-3 text-sm text-slate-500">
            当前版本先完成 Meta 生产链路。{{ activePlatformConfig.label }} 会按同一套连接模型扩展：应用配置、OAuth 授权、账户同步、Campaign 创建和回调状态页。
          </p>
        </section>

        <template v-if="activePlatform === 'meta'">
        <section class="rounded-md border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">hub</span>
                <h2 class="text-sm font-semibold text-slate-900">Meta Business OAuth</h2>
              </div>
              <div class="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-4">
                <div class="rounded bg-white p-3 border border-slate-200">1. 配置 Meta App</div>
                <div class="rounded bg-white p-3 border border-slate-200">2. 从系统发起授权</div>
                <div class="rounded bg-white p-3 border border-slate-200">3. Meta 确认权限</div>
                <div class="rounded bg-white p-3 border border-slate-200">4. 回到系统同步账户</div>
              </div>
            </div>
            <div
              class="inline-flex items-center rounded px-2 py-1 text-xs font-medium"
              :class="config?.status === 'connected' ? 'bg-emerald-50 text-emerald-700' : config?.status === 'configured' ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-700'"
            >
              {{ config?.status === 'connected' ? '已连接' : config?.status === 'configured' ? '已配置' : '未配置' }}
            </div>
          </div>
        </section>

        <div v-if="error" class="p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm">{{ error }}</div>
        <div v-if="success" class="p-3 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">{{ success }}</div>

        <section class="rounded-md border border-slate-200 p-5">
          <h3 class="text-sm font-semibold text-slate-900">Meta App 配置</h3>
          <div class="mt-4 grid gap-4">
            <label class="block">
              <span class="text-xs font-medium text-slate-600">App ID</span>
              <input v-model="form.app_id" class="mt-1 w-full px-3 py-2 rounded-md border text-sm" placeholder="Meta App ID" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600">App Secret</span>
              <input v-model="form.app_secret" type="password" class="mt-1 w-full px-3 py-2 rounded-md border text-sm" placeholder="保存后不会在前端回显" />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600">OAuth Redirect URI</span>
              <input v-model="form.redirect_uri" class="mt-1 w-full px-3 py-2 rounded-md border text-sm" />
              <span class="mt-1 block text-xs text-slate-500">需要在 Meta App 后台 Valid OAuth Redirect URIs 填入同一个地址。</span>
            </label>
            <div>
              <div class="text-xs font-medium text-slate-600">授权权限</div>
              <div class="mt-2 flex flex-wrap gap-2">
                <span v-for="scope in scopes" :key="scope" class="px-2 py-1 rounded bg-slate-100 text-xs text-slate-700">{{ scope }}</span>
              </div>
            </div>
          </div>

          <div class="mt-5 flex items-center gap-2">
            <button class="px-4 py-2 rounded-md bg-primary text-white text-sm disabled:opacity-50" :disabled="saving" @click="saveConfig">
              {{ saving ? '保存中...' : '保存配置' }}
            </button>
            <button class="px-4 py-2 rounded-md border text-sm disabled:opacity-50" :disabled="connecting || !config?.has_app_secret" @click="connectMeta">
              {{ connecting ? '正在跳转 Meta...' : '连接 Meta Business' }}
            </button>
            <button class="px-4 py-2 rounded-md border text-sm disabled:opacity-50" :disabled="connecting || !fbSdkReady || !form.app_id" @click="connectWithFacebookSdk">
              Facebook SDK 授权
            </button>
          </div>
        </section>

        <section class="rounded-md border border-slate-200 p-5">
          <h3 class="text-sm font-semibold text-slate-900">开发 / 沙盒 Token 导入</h3>
          <p class="mt-1 text-xs text-slate-500">用于 Meta 示例代码、沙盒广告账户和内部联调。生产用户仍应使用上方 OAuth 授权。</p>
          <div class="mt-4 grid gap-4">
            <label class="block">
              <span class="text-xs font-medium text-slate-600">Access Token</span>
              <textarea v-model="tokenForm.access_token" class="mt-1 w-full h-24 px-3 py-2 rounded-md border text-sm" placeholder="Meta Marketing API Access Token"></textarea>
            </label>
            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="text-xs font-medium text-slate-600">沙盒广告账户编号</span>
                <input v-model="tokenForm.account_id" class="mt-1 w-full px-3 py-2 rounded-md border text-sm" placeholder="1943996592887453" />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-slate-600">账户名称</span>
                <input v-model="tokenForm.account_name" class="mt-1 w-full px-3 py-2 rounded-md border text-sm" />
              </label>
            </div>
          </div>
          <div class="mt-5">
            <button class="px-4 py-2 rounded-md border text-sm disabled:opacity-50" :disabled="saving" @click="importSandboxToken">
              导入沙盒广告账户
            </button>
          </div>
        </section>
        </template>
      </div>
    </main>
  </div>
</template>
