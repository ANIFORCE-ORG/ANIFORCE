<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'save', data: any): void
  (e: 'import', data: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const saving = ref(false)

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

const handleClose = () => {
  emit('close')
}

const handleSaveConfig = () => {
  saving.value = true
  setTimeout(() => {
    emit('save', form.value)
    saving.value = false
    alert('Meta App 配置已保存（模拟）')
  }, 1000)
}

const handleImportToken = () => {
  saving.value = true
  setTimeout(() => {
    emit('import', tokenForm.value)
    saving.value = false
    alert('沙盒广告账户已导入（模拟）')
    handleClose()
  }, 1000)
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    @click.self="handleClose"
  >
    <div class="bg-white dark:bg-slate-800 rounded-md shadow-lg max-w-2xl w-full">
      <!-- 弹窗头部 -->
      <div class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between rounded-t-xl">
        <h2 class="text-lg font-bold text-slate-900 dark:text-white">Meta App 配置</h2>
        <button
          class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          @click="handleClose"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
        </button>
      </div>

      <!-- 弹窗内容 -->
      <div class="p-6 space-y-6">
        <!-- Meta App 配置部分 -->
        <section>
          <div class="space-y-4">
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">Account Name</span>
              <input
                v-model="form.app_id"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Meta Account Name"
              />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">App ID</span>
              <input
                v-model="form.app_id"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Meta App ID"
              />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">App Secret</span>
              <input
                v-model="form.app_secret"
                type="password"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="保存后不会在前端回显"
              />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">OAuth Redirect URI</span>
              <input
                v-model="form.redirect_uri"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span class="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                需要在 Meta App 后台 Valid OAuth Redirect URIs 填入同一个地址。
              </span>
            </label>
            <div>
              <div class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">授权权限</div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="scope in scopes"
                  :key="scope"
                  class="px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-xs text-slate-700 dark:text-slate-300"
                >
                  {{ scope }}
                </span>
              </div>
            </div>
          </div>

          <div class="mt-5 flex items-center gap-2">
            <button
              class="px-4 py-2 rounded-md bg-primary text-white text-sm disabled:opacity-50 hover:bg-primary/90 transition-colors"
              :disabled="saving"
              @click="handleSaveConfig"
            >
              {{ saving ? '保存中...' : '保存配置' }}
            </button>
            <button
              class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm opacity-50 cursor-not-allowed"
              disabled
            >
              连接 Meta Business
            </button>
            <button
              class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm opacity-50 cursor-not-allowed"
              disabled
            >
              Facebook SDK 授权
            </button>
          </div>
        </section>

        <!-- 分隔线 -->
        <div class="border-t border-slate-200 dark:border-slate-700"></div>

        <!-- 开发/沙盒 Token 导入部分 -->
        <section>
          <h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-2">开发 / 沙盒 Token 导入</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">
            用于 Meta 示例代码、沙盒广告账户和内部联调。生产用户仍应使用上方 OAuth 授权。
          </p>
          <div class="space-y-4">
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">Access Token</span>
              <textarea
                v-model="tokenForm.access_token"
                class="mt-1 w-full h-24 px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                placeholder="Meta Marketing API Access Token"
              ></textarea>
            </label>
            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="text-xs font-medium text-slate-600 dark:text-slate-400">沙盒广告账户编号</span>
                <input
                  v-model="tokenForm.account_id"
                  class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="1943996592887453"
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-slate-600 dark:text-slate-400">账户名称</span>
                <input
                  v-model="tokenForm.account_name"
                  class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </label>
            </div>
          </div>
          <div class="mt-5">
            <button
              class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              :disabled="saving"
              @click="handleImportToken"
            >
              导入沙盒广告账户
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
