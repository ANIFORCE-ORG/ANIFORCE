<script setup lang="ts">
import { ref, computed } from 'vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'

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

const { success } = useToast()
const saving = ref(false)
const copied = ref(false)

const REDIRECT_URI = 'https://8.148.151.36:8010/meta/callback'

const form = ref({
  account_name: '',
  app_id: '',
  app_secret: '',
  redirect_uri: REDIRECT_URI,
  scopes: ['ads_management', 'ads_read', 'business_management'] as string[],
})

// 复制 Redirect URI 到剪贴板
const copyRedirectUri = async () => {
  try {
    await navigator.clipboard.writeText(REDIRECT_URI)
    copied.value = true
    success('已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('复制失败:', err)
  }
}

const tokenForm = ref({
  access_token: '',
  account_id: '',
  account_name: 'Meta Sandbox Ad Account',
})

// 可用的授权权限选项
const availableScopes = [
  { value: 'ads_management', label: 'ads_management', description: '管理广告系列、广告组和广告' },
  { value: 'ads_read', label: 'ads_read', description: '读取广告数据和统计信息' },
  { value: 'business_management', label: 'business_management', description: '管理商务管理平台资源' },
]

// 切换权限选择
const toggleScope = (scope: string) => {
  const index = form.value.scopes.indexOf(scope)
  if (index > -1) {
    form.value.scopes.splice(index, 1)
  } else {
    form.value.scopes.push(scope)
  }
}

const handleClose = () => {
  emit('close')
}

// 表单校验
const validateForm = () => {
  if (!form.value.account_name.trim()) {
    return 'Account Name 不能为空'
  }
  if (!form.value.app_id.trim()) {
    return 'App ID 不能为空'
  }
  if (!form.value.app_secret.trim()) {
    return 'App Secret 不能为空'
  }
  if (form.value.scopes.length === 0) {
    return '请至少选择一个授权权限'
  }
  return null
}

// 计算表单是否有效
const isFormValid = computed(() => {
  return form.value.account_name.trim() !== '' &&
         form.value.app_id.trim() !== '' &&
         form.value.app_secret.trim() !== '' &&
         form.value.scopes.length > 0
})

const handleSaveConfig = () => {
  const error = validateForm()
  if (error) {
    alert(error)
    return
  }
  
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
    <div class="bg-white dark:bg-slate-800 rounded-md shadow-lg max-w-4xl w-full">
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
                v-model="form.account_name"
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
              <div class="relative mt-1">
                <input
                  :value="REDIRECT_URI"
                  readonly
                  class="w-full px-3 py-2 pr-10 rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 text-sm cursor-default"
                />
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                  @click="copyRedirectUri"
                  :title="copied ? '已复制' : '复制到剪贴板'"
                >
                  <span 
                    class="material-symbols-outlined text-lg"
                    :class="copied ? 'text-green-600 dark:text-green-400' : 'text-slate-600 dark:text-slate-400'"
                  >
                    {{ copied ? 'check' : 'content_copy' }}
                  </span>
                </button>
              </div>
              <span class="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                需要在 Meta App 后台 Valid OAuth Redirect URIs 填入同一个地址。
              </span>
            </label>
            <div>
              <div class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-3">授权权限</div>
              <div class="grid grid-cols-3 gap-3">
                <label
                  v-for="scope in availableScopes"
                  :key="scope.value"
                  class="flex flex-col gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                >
                  <div class="flex items-center gap-2">
                    <input
                      type="checkbox"
                      :value="scope.value"
                      :checked="form.scopes.includes(scope.value)"
                      class="w-4 h-4 text-primary border-slate-300 dark:border-slate-600 rounded focus:ring-2 focus:ring-primary cursor-pointer flex-shrink-0"
                      @change="toggleScope(scope.value)"
                    />
                    <span class="text-sm font-medium text-slate-900 dark:text-white">{{ scope.label }}</span>
                  </div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 pl-2">{{ scope.description }}</div>
                </label>
              </div>
              <div class="mt-2 text-xs text-slate-500 dark:text-slate-400">
                已选择 {{ form.scopes.length }} 个权限
              </div>
            </div>
          </div>

          <div class="mt-5 flex items-center gap-2">
            <button
              class="px-4 py-2 rounded-md bg-primary text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
              :disabled="saving || !isFormValid"
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
        <!--
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
        -->
      </div>
    </div>
    <!-- Toast 提示容器 -->
    <ToastContainer />
  </div>
</template>
