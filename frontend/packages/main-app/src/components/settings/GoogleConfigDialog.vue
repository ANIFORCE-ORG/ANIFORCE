<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'
import { platformApi, type GoogleConfigRequest } from '@/api/platform'

interface Props {
  show: boolean
  connectionId?: string | null
  initialData?: {
    account_name: string
    client_id: string
    scopes: string[]
  } | null
}

interface Emits {
  (e: 'close'): void
  (e: 'save', data: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { success, error: showError } = useToast()
const saving = ref(false)
const copied = ref(false)
const showSecret = ref(false)
const isEditingSecret = ref(false)
const isEditMode = ref(false)

const REDIRECT_URI = 'https://8.148.151.36:8010/api/v1/platform-auth/google/auth_callback'

const form = ref({
  account_name: '',
  client_id: '',
  client_secret: '',
  redirect_uri: REDIRECT_URI,
  scopes: [] as string[],
})

// 监听 initialData 变化，填充表单数据
watch(() => props.initialData, (data) => {
  if (data) {
    isEditMode.value = true
    form.value.account_name = data.account_name || ''
    form.value.client_id = data.client_id || ''
    form.value.scopes = data.scopes || [
      'https://www.googleapis.com/auth/adwords',
      'https://www.googleapis.com/auth/userinfo.email'
    ]
    // 编辑模式：显示32个加密字符，实际值为空
    form.value.client_secret = '********************************'
    isEditingSecret.value = false
  } else {
    // 重置表单（新建模式）
    isEditMode.value = false
    form.value.account_name = ''
    form.value.client_id = ''
    form.value.client_secret = ''
    form.value.scopes = [
      'https://www.googleapis.com/auth/adwords',
      'https://www.googleapis.com/auth/userinfo.email'
    ]
    isEditingSecret.value = false
  }
}, { immediate: true })

// 点击笔图标，允许编辑 Client Secret
const startEditingSecret = () => {
  isEditingSecret.value = true
  form.value.client_secret = ''
  showSecret.value = false
}

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

// 可用的授权权限选项（使用简化关键词，后端会添加前缀）
const availableScopes = [
  { 
    value: 'adwords', 
    label: 'Google Ads API', 
    description: '管理 Google Ads 广告系列和数据' 
  },
  { 
    value: 'userinfo.email', 
    label: 'User Email', 
    description: '获取用户邮箱信息' 
  },
  { 
    value: 'userinfo.profile', 
    label: 'User Profile', 
    description: '获取用户基本资料' 
  },
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
  if (!form.value.client_id.trim()) {
    return 'Client ID 不能为空'
  }
  // 仅在新建模式或编辑模式下选择修改 Client Secret 时校验
  if (!isEditMode.value || isEditingSecret.value) {
    if (!form.value.client_secret.trim() || form.value.client_secret === '********************************') {
      return 'Client Secret 不能为空'
    }
  }
  if (form.value.scopes.length === 0) {
    return '请至少选择一个授权权限'
  }
  return null
}

// 计算表单是否有效
const isFormValid = computed(() => {
  const baseValid = form.value.account_name.trim() !== '' &&
                    form.value.client_id.trim() !== '' &&
                    form.value.scopes.length > 0
  
  // 新建模式：必须填写 Client Secret
  if (!isEditMode.value) {
    return baseValid && form.value.client_secret.trim() !== ''
  }
  
  // 编辑模式：如果选择修改 Client Secret，则必须填写
  if (isEditingSecret.value) {
    return baseValid && form.value.client_secret.trim() !== '' && form.value.client_secret !== '********************************'
  }
  
  // 编辑模式且不修改 Client Secret：只需基础字段有效
  return baseValid
})

const handleSaveConfig = async () => {
  const validationError = validateForm()
  if (validationError) {
    showError(validationError)
    return
  }
  
  saving.value = true
  try {
    const payload: GoogleConfigRequest = {
      account_name: form.value.account_name,
      client_id: form.value.client_id,
      scopes: form.value.scopes
    }
    
    // 仅在新建模式或编辑模式下选择修改 Client Secret 时发送
    if (!isEditMode.value || isEditingSecret.value) {
      payload.client_secret = form.value.client_secret
    }
    
    // 编辑模式：传递 connection_id 用于更新
    if (props.connectionId) {
      payload.connection_id = props.connectionId
    }
    
    const response = await platformApi.saveGoogleConfig(payload)
    
    emit('save', response)
    success('Google 配置已保存')
  } catch (err: any) {
    console.error('保存配置失败:', err)
    const errorDetail = err.response?.data?.detail || '保存配置失败，请重试'
    showError(errorDetail)
  } finally {
    saving.value = false
  }
}

const handleGoogleAuthorize = async () => {
  if (!props.connectionId) {
    showError('请先保存配置后再进行授权')
    return
  }
  
  try {
    const response = await platformApi.getGoogleAuthorizeUrl(props.connectionId)
    window.location.href = response.authorize_url
  } catch (err: any) {
    console.error('获取授权 URL 失败:', err)
    const errorDetail = err.response?.data?.detail || '获取授权 URL 失败，请重试'
    showError(errorDetail)
  }
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
        <h2 class="text-lg font-bold text-slate-900 dark:text-white">Google OAuth 配置</h2>
        <button
          class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          @click="handleClose"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
        </button>
      </div>

      <!-- 弹窗内容 -->
      <div class="p-6 space-y-6">
        <!-- Google OAuth 配置部分 -->
        <section>
          <div class="space-y-4">
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">Account Name</span>
              <input
                v-model="form.account_name"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Google Account Name"
              />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">Client ID</span>
              <input
                v-model="form.client_id"
                class="mt-1 w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Google OAuth Client ID"
              />
            </label>
            <label class="block">
              <span class="text-xs font-medium text-slate-600 dark:text-slate-400">Client Secret</span>
              <div class="relative mt-1">
                <input
                  v-model="form.client_secret"
                  :type="showSecret ? 'text' : 'password'"
                  :readonly="isEditMode && !isEditingSecret"
                  :class="[
                    'w-full px-3 py-2 pr-10 rounded-md border text-sm focus:outline-none focus:ring-2 focus:ring-primary',
                    isEditMode && !isEditingSecret
                      ? 'border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 cursor-default'
                      : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white'
                  ]"
                  :placeholder="isEditMode && !isEditingSecret ? '' : '保存后不会在前端回显'"
                />
                <!-- 编辑模式且未开始修改：显示笔图标 -->
                <button
                  v-if="isEditMode && !isEditingSecret"
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                  @click="startEditingSecret"
                  title="点击修改 Client Secret"
                >
                  <span class="material-symbols-outlined text-lg text-slate-600 dark:text-slate-400">
                    edit
                  </span>
                </button>
                <!-- 新建模式或正在编辑：显示眼睛图标 -->
                <button
                  v-else
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                  @click="showSecret = !showSecret"
                  :title="showSecret ? '隐藏密码' : '显示密码'"
                >
                  <span class="material-symbols-outlined text-lg text-slate-600 dark:text-slate-400">
                    {{ showSecret ? 'visibility_off' : 'visibility' }}
                  </span>
                </button>
              </div>
              <span v-if="isEditMode && !isEditingSecret" class="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                已加密保存，点击笔图标可修改
              </span>
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
                需要在 Google Cloud Console 的 OAuth 2.0 客户端配置中添加此重定向 URI。
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
              class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!connectionId"
              @click="handleGoogleAuthorize"
            >
              Google OAuth 授权
            </button>
          </div>
        </section>
      </div>
    </div>
    <!-- Toast 提示容器 -->
    <ToastContainer />
  </div>
</template>
