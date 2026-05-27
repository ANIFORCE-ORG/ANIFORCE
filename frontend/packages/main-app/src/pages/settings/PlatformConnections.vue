<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import MetaConfigDialog from '@/components/settings/MetaConfigDialog.vue'
import GoogleConfigDialog from '@/components/settings/GoogleConfigDialog.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import { navItems } from '@/config/navigation'
import { platformApi, type PlatformConnectionResponse } from '@/api/platform'
import {
  getPlatformAccounts,
  getPlatformAccountReadiness,
  syncPlatformAccounts,
  type PlatformAccount,
  type PlatformAccountAssetStatus,
} from '@/api/platformAccounts'
import { useToast } from '@/composables/useToast'
import { useOrganizationContext } from '@/composables/useOrganizationContext'

const router = useRouter()
const { success, error: showError } = useToast()
const { currentOrganization } = useOrganizationContext()
const activePlatform = ref<'meta' | 'google' | 'tiktok'>('meta')
const showConfigDialog = ref(false)
const connections = ref<PlatformConnectionResponse[]>([])
const platformAccounts = ref<PlatformAccount[]>([])
const readinessChecks = ref<Record<string, PlatformAccountAssetStatus[]>>({})
const loading = ref(false)
const accountsLoading = ref(false)
const editingConnection = ref<PlatformConnectionResponse | null>(null)
const showDeleteConfirm = ref(false)
const deletingConnection = ref<PlatformConnectionResponse | null>(null)

const platforms = [
  {
    id: 'meta',
    label: 'Meta',
    title: 'Meta Business OAuth',
    description: '连接 Facebook / Instagram 广告账户，支持真实创建 Campaign',
    status: 'available',
    keywords: ['Facebook', 'Instagram', 'Meta Business', 'Campaign'],
  },
  {
    id: 'google',
    label: 'Google',
    title: 'Google Ads OAuth',
    description: '连接 Google Ads 账号，后续同步客户账号和投放计划',
    status: 'available',
    keywords: ['Google Ads', 'Google Marketing', 'AdWords', 'Campaign'],
  },
  {
    id: 'tiktok',
    label: 'TikTok',
    title: 'TikTok Ads OAuth',
    description: '连接 TikTok Ads 账号，后续同步广告账户和计划创建能力',
    status: 'available',
    keywords: ['TikTok Ads', 'TikTok Marketing', 'Douyin', 'Campaign'],
  },
] as const

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const openConfigDialog = () => {
  editingConnection.value = null
  showConfigDialog.value = true
}

const closeConfigDialog = () => {
  showConfigDialog.value = false
  editingConnection.value = null
}

const loadConnections = async () => {
  loading.value = true
  try {
    connections.value = await platformApi.getAllConnections()
  } catch (err: any) {
    console.error('加载连接失败:', err)
    connections.value = []
  } finally {
    loading.value = false
  }
}

const demoAccounts: PlatformAccount[] = [
  {
    id: 'pa-meta-candy',
    org_id: 'org-aniforce-growth',
    platform: 'meta',
    account_id: 'act_1029384756',
    external_account_id: '1029384756',
    account_name: 'Candy Blast Meta UA',
    business_name: 'FunGame Business Manager',
    auth_status: 'authorized',
    account_status: 'active',
    readiness_status: 'ready',
    currency: 'USD',
    timezone: 'America/Los_Angeles',
    last_sync_at: '2026-05-27T09:30:00Z',
  },
  {
    id: 'pa-meta-dtc',
    org_id: 'org-aniforce-growth',
    platform: 'meta',
    account_id: 'act_6677889900',
    external_account_id: '6677889900',
    account_name: 'DTC Meta Prospecting',
    business_name: 'DTC Growth BM',
    auth_status: 'authorized',
    account_status: 'active',
    readiness_status: 'warning',
    currency: 'USD',
    timezone: 'Asia/Singapore',
    last_sync_at: '2026-05-27T08:40:00Z',
  },
  {
    id: 'pa-google-drama',
    org_id: 'org-aniforce-growth',
    platform: 'google',
    account_id: 'gads_559210',
    external_account_id: '559210',
    account_name: 'DramaBox Google Ads',
    business_name: 'DramaBox MCC',
    auth_status: 'authorized',
    account_status: 'active',
    readiness_status: 'warning',
    currency: 'USD',
    timezone: 'Asia/Singapore',
    last_sync_at: '2026-05-26T22:15:00Z',
  },
]

const demoReadinessChecks: Record<string, PlatformAccountAssetStatus[]> = {
  'pa-meta-candy': [
    { label: 'Page', status: 'connected', detail: 'Candy Blast Official' },
    { label: 'Instagram', status: 'connected', detail: '@candyblast' },
    { label: 'Pixel / Dataset', status: 'connected', detail: 'Install dataset ready' },
    { label: '支付状态', status: 'connected', detail: 'Billing active' },
  ],
  'pa-meta-dtc': [
    { label: 'Page', status: 'connected', detail: 'DTC Store' },
    { label: 'Instagram', status: 'optional', detail: 'Optional for current placement' },
    { label: 'Pixel / Dataset', status: 'missing', detail: 'Need dataset before purchase campaign' },
    { label: '支付状态', status: 'connected', detail: 'Billing active' },
  ],
  'pa-google-drama': [
    { label: 'Manager Account', status: 'connected', detail: 'MCC linked' },
    { label: 'Conversion', status: 'missing', detail: 'Waiting backend Google MA sync' },
    { label: 'Billing', status: 'unknown', detail: 'Pending API check' },
  ],
}

const platformNameMap: Record<string, string> = {
  meta: 'Meta',
  google: 'Google',
  tiktok: 'TikTok',
}

const loadPlatformAccounts = async () => {
  accountsLoading.value = true
  try {
    platformAccounts.value = await getPlatformAccounts({
      platform: activePlatform.value,
      org_id: currentOrganization.value?.id,
    })
    if (platformAccounts.value.length === 0) {
      platformAccounts.value = demoAccounts.filter((account) => account.platform === activePlatform.value)
    }
  } catch {
    platformAccounts.value = demoAccounts.filter((account) => account.platform === activePlatform.value)
  } finally {
    accountsLoading.value = false
  }

  await loadReadinessChecks()
}

const loadReadinessChecks = async () => {
  const checks: Record<string, PlatformAccountAssetStatus[]> = {}
  await Promise.all(platformAccounts.value.map(async (account) => {
    try {
      const response = await getPlatformAccountReadiness(account.id)
      checks[account.id] = response.checks
    } catch {
      checks[account.id] = demoReadinessChecks[account.id] || [
        { label: '授权状态', status: account.auth_status === 'authorized' ? 'connected' : 'missing' },
        { label: '账户状态', status: account.account_status === 'active' ? 'connected' : 'unknown' },
      ]
    }
  }))
  readinessChecks.value = checks
}

const handleSyncAccounts = async () => {
  accountsLoading.value = true
  try {
    await syncPlatformAccounts(activePlatform.value)
    await loadPlatformAccounts()
    success('广告账户已同步')
  } catch {
    await loadPlatformAccounts()
    showError('账户同步接口未就绪，当前展示 Demo 账户')
  } finally {
    accountsLoading.value = false
  }
}

const handleSaveConfig = async (data: any) => {
  console.log('保存配置:', data)
  closeConfigDialog()
  await loadConnections()
  await loadPlatformAccounts()
  success('配置已保存')
}

const handleImportToken = (data: any) => {
  console.log('导入沙盒账户:', data)
}

const handleEdit = (connection: PlatformConnectionResponse) => {
  console.log('编辑连接:', connection)
  editingConnection.value = connection
  showConfigDialog.value = true
}

const handleAuthorize = async (connection: PlatformConnectionResponse) => {
  console.log('授权连接:', connection)
  try {
    let response
    // 根据平台类型调用不同的授权 URL API
    if (connection.platform === 'Meta') {
      response = await platformApi.getMetaAuthorizeUrl(connection.id)
    } else if (connection.platform === 'Google') {
      response = await platformApi.getGoogleAuthorizeUrl(connection.id)
    } else {
      showError(`${connection.platform} 平台授权功能暂未实现`)
      return
    }
    // 在新窗口中打开授权页面
    window.open(response.authorize_url, '_blank', 'width=600,height=700')
  } catch (err: any) {
    console.error('获取授权 URL 失败:', err)
    showError('获取授权 URL 失败，请重试')
  }
}

const handleDelete = (connection: PlatformConnectionResponse) => {
  deletingConnection.value = connection
  showDeleteConfirm.value = true
}

const confirmDelete = async () => {
  if (!deletingConnection.value) return
  
  const connection = deletingConnection.value
  try {
    await platformApi.deleteConnection(connection.id)
    success('连接已删除')
    await loadConnections()
  } catch (err: any) {
    console.error('删除连接失败:', err)
    showError('删除连接失败，请重试')
  } finally {
    deletingConnection.value = null
  }
}

const cancelDelete = () => {
  deletingConnection.value = null
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 根据当前选中的平台过滤连接列表
const filteredConnections = computed(() => {
  const platformName = platformNameMap[activePlatform.value]
  return connections.value.filter(conn => conn.platform === platformName)
})

// 判断各平台是否已接入（至少有一个账号状态为 authorized）
const isPlatformConnected = (platformId: string) => {
  const platformName = platformNameMap[platformId]
  return connections.value.some(conn => conn.platform === platformName && conn.status === 'active')
    || platformAccounts.value.some(account => account.platform === platformId && account.auth_status === 'authorized')
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'active': '已激活',
    'unauthorized': '未授权',
    'expired': '已过期',
    'revoked': '已撤销'
  }
  return statusMap[status] || status
}

const getStatusClass = (status: string) => {
  const classMap: Record<string, string> = {
    'active': 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    'unauthorized': 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    'expired': 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    'revoked': 'bg-slate-50 dark:bg-slate-700 text-slate-700 dark:text-slate-400'
  }
  return classMap[status] || classMap['unauthorized']
}

const getReadinessText = (status?: string) => {
  const textMap: Record<string, string> = {
    ready: '可创建广告',
    warning: '需补充资产',
    blocked: '阻塞',
    unknown: '待同步',
  }
  return textMap[status || 'unknown']
}

const getReadinessClass = (status?: string) => {
  const classMap: Record<string, string> = {
    ready: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    blocked: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    unknown: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  }
  return classMap[status || 'unknown']
}

const getAssetStatusClass = (status: PlatformAccountAssetStatus['status']) => {
  const classMap: Record<PlatformAccountAssetStatus['status'], string> = {
    connected: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    missing: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    optional: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    unknown: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  }
  return classMap[status]
}

const handlePlatformChange = async (platformId: 'meta' | 'google' | 'tiktok') => {
  activePlatform.value = platformId
  await loadPlatformAccounts()
}

onMounted(() => {
  loadConnections()
  loadPlatformAccounts()
  
  // 检查 URL 参数，显示授权结果
  const urlParams = new URLSearchParams(window.location.search)
  const successParam = urlParams.get('success')
  const errorParam = urlParams.get('error')
  
  if (successParam === 'authorized') {
    success('授权成功！')
    // 清除 URL 参数
    window.history.replaceState({}, '', window.location.pathname)
  } else if (errorParam) {
    const errorMessages: Record<string, string> = {
      'connection_not_found': '连接不存在',
      'token_exchange_failed': '获取访问令牌失败',
      'callback_failed': '授权回调失败'
    }
    showError(errorMessages[errorParam] || '授权失败')
    // 清除 URL 参数
    window.history.replaceState({}, '', window.location.pathname)
  }
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav 
      :nav-items="navItems"
      :sessions="[]"
      active-panel="settings"
      @switch-panel="switchPanel"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">平台连接</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">配置 Meta、Google、TikTok 的平台授权和广告账户同步</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div class="space-y-6">
          <!-- 平台选择卡片 -->
          <div class="grid grid-cols-3 gap-3">
            <button
              v-for="platform in platforms"
              :key="platform.id"
              class="rounded-md border p-4 text-left transition-colors hover:border-primary/50"
              :class="activePlatform === platform.id 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700'"
              @click="handlePlatformChange(platform.id)"
            >
              <div class="flex items-center justify-between">
                <div class="font-semibold text-slate-900 dark:text-white">{{ platform.label }}</div>
                <span 
                  class="rounded px-2 py-1 text-xs font-medium"
                  :class="isPlatformConnected(platform.id)
                    ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'"
                >
                  {{ isPlatformConnected(platform.id) ? '已接入' : '待接入' }}
                </span>
              </div>
              <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">{{ platform.description }}</p>
            </button>
          </div>

          <!-- 平台详细配置 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
            <div class="flex items-center gap-2 mb-4">
              <span class="material-symbols-outlined text-primary">hub</span>
              <h2 class="text-sm font-semibold text-slate-900 dark:text-white">
                {{ platforms.find(p => p.id === activePlatform)?.title }}
              </h2>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
              {{ platforms.find(p => p.id === activePlatform)?.description }}
            </p>

            <!-- 连接流程 -->
            <div class="grid gap-2 text-xs text-slate-600 dark:text-slate-400 md:grid-cols-4 mb-6">
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                1. 配置应用信息
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                2. 发起 OAuth 授权
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                3. 平台确认权限
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-3 border border-slate-200 dark:border-slate-600">
                4. 同步广告账户
              </div>
            </div>

            <!-- 开发中提示（仅 Google 和 TikTok 显示）-->
            <div v-if="activePlatform !== 'meta'" class="p-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-4">
              <div class="flex items-start gap-3">
                <span class="material-symbols-outlined text-amber-600 dark:text-amber-400 text-xl">construction</span>
                <div>
                  <div class="text-sm font-medium text-amber-900 dark:text-amber-200 mb-1">
                    {{ platforms.find(p => p.id === activePlatform)?.label }} 平台连接功能开发中
                  </div>
                  <p class="text-xs text-amber-700 dark:text-amber-300">
                    当前版本正在完善平台连接功能，包括应用配置、OAuth 授权、账户同步、Campaign 创建等核心能力，敬请期待。
                  </p>
                </div>
              </div>
            </div>

            <!-- Meta 平台特殊功能 -->
            <div v-if="activePlatform === 'meta'" class="flex items-center justify-between">
              <p class="text-sm text-slate-600 dark:text-slate-400">配置 Meta 广告账户连接</p>
              <button
                class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                @click="openConfigDialog"
              >
                添加广告账户
              </button>
            </div>
            
            <!-- Google 平台特殊功能 -->
            <div v-if="activePlatform === 'google'" class="flex items-center justify-between">
              <p class="text-sm text-slate-600 dark:text-slate-400">配置 Google 广告账户连接</p>
              <button
                class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                @click="openConfigDialog"
              >
                添加广告账户
              </button>
            </div>
          </section>

          <!-- 平台连接列表 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
            <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700">
              <h2 class="text-sm font-semibold text-slate-900 dark:text-white">已连接的平台账户</h2>
            </div>
            
            <div v-if="loading" class="p-8 text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined animate-spin text-3xl">progress_activity</span>
              <p class="mt-2 text-sm">加载中...</p>
            </div>
            
            <div v-else-if="filteredConnections.length === 0" class="p-8 text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined text-5xl mb-2">cloud_off</span>
              <p class="text-sm">暂无 {{ platforms.find(p => p.id === activePlatform)?.label }} 平台连接</p>
              <p v-if="activePlatform === 'meta'" class="text-xs mt-1">点击上方「添加广告账户」按钮开始配置</p>
            </div>
            
            <div v-else class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-slate-50 dark:bg-slate-700/50">
                  <tr>
                    <th class="px-5 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400">账户名称</th>
                    <th class="px-5 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400">APP ID</th>
                    <th class="px-5 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400">授权范围</th>
                    <th class="px-5 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400">状态</th>
                    <th class="px-5 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400">更新时间</th>
                    <th class="px-5 py-3 text-right text-xs font-medium text-slate-600 dark:text-slate-400">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
                  <tr v-for="connection in filteredConnections" :key="connection.id" class="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td class="px-5 py-4 text-sm text-slate-900 dark:text-white">
                      {{ connection.account_name || '-' }}
                    </td>
                    <td class="px-5 py-4 text-sm text-slate-600 dark:text-slate-400 font-mono">
                      {{ connection.account_id }}
                    </td>
                    <td class="px-5 py-4 text-xs">
                      <div class="flex flex-wrap gap-1">
                        <span
                          v-for="scope in connection.scopes"
                          :key="scope"
                          class="px-2 py-1 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                        >
                          {{ scope }}
                        </span>
                        <span v-if="!connection.scopes || connection.scopes.length === 0" class="text-slate-400">-</span>
                      </div>
                    </td>
                    <td class="px-5 py-4 text-xs">
                      <span class="px-2 py-1 rounded font-medium" :class="getStatusClass(connection.status)">
                        {{ getStatusText(connection.status) }}
                      </span>
                    </td>
                    <td class="px-5 py-4 text-xs text-slate-600 dark:text-slate-400">
                      {{ formatDate(connection.updated_at) }}
                    </td>
                    <td class="px-5 py-4 text-right">
                      <div class="flex items-center justify-end gap-2">
                        <button
                          class="px-3 py-1.5 rounded text-xs font-medium border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                          @click="handleEdit(connection)"
                        >
                          编辑
                        </button>
                        <button
                          class="px-3 py-1.5 rounded text-xs font-medium border transition-colors"
                          :class="connection.status === 'active' 
                            ? 'border-slate-200 dark:border-slate-600 text-slate-400 dark:text-slate-500 cursor-not-allowed opacity-50'
                            : 'border-primary text-primary hover:bg-primary/5'"
                          :disabled="connection.status === 'active'"
                          @click="handleAuthorize(connection)"
                        >
                          授权
                        </button>
                        <button
                          class="px-3 py-1.5 rounded text-xs font-medium border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                          @click="handleDelete(connection)"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- 可投放广告账户 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
            <div class="flex items-center justify-between gap-4 px-5 py-4 border-b border-slate-200 dark:border-slate-700">
              <div>
                <h2 class="text-sm font-semibold text-slate-900 dark:text-white">可投放广告账户</h2>
                <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  当前组织：{{ currentOrganization?.name || '未选择组织' }}，创建广告前需要选择一个满足前置条件的账户
                </p>
              </div>
              <button
                class="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700 whitespace-nowrap"
                :disabled="accountsLoading"
                @click="handleSyncAccounts"
              >
                <span class="material-symbols-outlined text-base" :class="accountsLoading ? 'animate-spin' : ''">sync</span>
                同步账户
              </button>
            </div>

            <div v-if="accountsLoading" class="p-8 text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined animate-spin text-3xl">progress_activity</span>
              <p class="mt-2 text-sm">加载广告账户中...</p>
            </div>

            <div v-else-if="platformAccounts.length === 0" class="p-8 text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined text-5xl mb-2">account_balance_wallet</span>
              <p class="text-sm">暂无 {{ platforms.find(p => p.id === activePlatform)?.label }} 广告账户</p>
              <p class="text-xs mt-1">完成平台授权后点击「同步账户」获取可投放账户</p>
            </div>

            <div v-else class="divide-y divide-slate-200 dark:divide-slate-700">
              <article
                v-for="account in platformAccounts"
                :key="account.id"
                class="p-5"
              >
                <div class="flex flex-wrap items-start justify-between gap-4">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="text-sm font-semibold text-slate-900 dark:text-white">{{ account.account_name }}</h3>
                      <span class="rounded px-2 py-1 text-xs font-medium" :class="getReadinessClass(account.readiness_status)">
                        {{ getReadinessText(account.readiness_status) }}
                      </span>
                    </div>
                    <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      <span>{{ account.business_name || '未同步 Business' }}</span>
                      <span class="font-mono">{{ account.account_id }}</span>
                      <span>{{ account.currency || '-' }} · {{ account.timezone || '-' }}</span>
                      <span>最近同步 {{ account.last_sync_at ? formatDate(account.last_sync_at) : '待同步' }}</span>
                    </div>
                  </div>
                  <button
                    class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90 whitespace-nowrap"
                    @click="router.push({ path: '/campaigns/create', query: { platform: activePlatform, platformAccountId: account.id } })"
                  >
                    创建广告
                  </button>
                </div>

                <div class="mt-4 grid gap-2 md:grid-cols-4">
                  <div
                    v-for="check in readinessChecks[account.id] || []"
                    :key="`${account.id}-${check.label}`"
                    class="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900"
                  >
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-xs font-medium text-slate-700 dark:text-slate-200">{{ check.label }}</span>
                      <span class="rounded px-1.5 py-0.5 text-[11px] font-medium" :class="getAssetStatusClass(check.status)">
                        {{ check.status }}
                      </span>
                    </div>
                    <p class="mt-2 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">{{ check.detail || '待平台同步确认' }}</p>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Meta 配置弹窗组件 -->
    <MetaConfigDialog
      v-if="activePlatform === 'meta'"
      :show="showConfigDialog"
      :connection-id="editingConnection?.id || null"
      :initial-data="editingConnection ? {
        account_name: editingConnection.account_name || '',
        app_id: editingConnection.account_id,
        scopes: editingConnection.scopes || []
      } : null"
      @close="closeConfigDialog"
      @save="handleSaveConfig"
      @import="handleImportToken"
    />
    
    <!-- Google 配置弹窗组件 -->
    <GoogleConfigDialog
      v-if="activePlatform === 'google'"
      :show="showConfigDialog"
      :connection-id="editingConnection?.id || null"
      :initial-data="editingConnection ? {
        account_name: editingConnection.account_name || '',
        client_id: editingConnection.account_id,
        scopes: editingConnection.scopes || []
      } : null"
      @close="closeConfigDialog"
      @save="handleSaveConfig"
    />
    
    <!-- 删除确认弹窗 -->
    <ConfirmDialog
      :show="showDeleteConfirm"
      title="确认删除"
      :message="`确定要删除「${deletingConnection?.account_name || deletingConnection?.account_id}」吗？`"
      confirm-text="确定"
      cancel-text="取消"
      confirm-button-class="bg-blue-500 hover:bg-blue-600"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
      @close="showDeleteConfirm = false"
    />
    
    <!-- Toast 提示容器 -->
    <ToastContainer />
  </div>
</template>
