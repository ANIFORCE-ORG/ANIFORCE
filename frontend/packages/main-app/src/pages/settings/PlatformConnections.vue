<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import { navItems } from '@/config/navigation'
import { platformApi, type PlatformConnectionResponse } from '@/api/platform'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { success, error: showError } = useToast()
const activePlatform = ref<'meta' | 'google' | 'tiktok'>('meta')
const connections = ref<PlatformConnectionResponse[]>([])
const loading = ref(false)
const showDeleteConfirm = ref(false)
const deletingConnection = ref<PlatformConnectionResponse | null>(null)

// 子账号管理
const expandedAccounts = ref<Set<string>>(new Set())
const subAccounts = ref<Record<string, any[]>>({})
const loadingSubAccounts = ref<Set<string>>(new Set())
const showAddSubAccountDialog = ref(false)
const currentParentConnectionId = ref<string | null>(null)
const newSubAccountName = ref('')
const newSubAccountCustomerId = ref('')

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

const loadConnections = async () => {
  loading.value = true
  try {
    connections.value = await platformApi.getAllConnections()
  } catch (err: any) {
    console.error('加载连接失败:', err)
    showError('加载平台连接失败')
  } finally {
    loading.value = false
  }
}

const handleAddMetaAccount = async () => {
  try {
    // 调用新接口：自动创建 connection 并获取授权 URL
    const response = await platformApi.startMetaOAuth()
    // 在新窗口中打开授权页面
    window.open(response.authorize_url, '_blank', 'width=600,height=700')
    // 刷新连接列表
    await loadConnections()
  } catch (err: any) {
    console.error('启动 Meta OAuth 失败:', err)
    showError('启动授权失败，请重试')
  }
}

const handleAddGoogleAccount = async () => {
  try {
    // 调用新接口：自动创建 connection 并获取授权 URL
    const response = await platformApi.startGoogleOAuth()
    // 在新窗口中打开授权页面
    window.open(response.authorize_url, '_blank', 'width=600,height=700')
    // 刷新连接列表
    await loadConnections()
  } catch (err: any) {
    console.error('启动 Google OAuth 失败:', err)
    showError('启动授权失败，请重试')
  }
}

const handleSyncAdAccounts = async (connection: PlatformConnectionResponse) => {
  console.log('同步广告账户:', connection)
  try {
    // 根据平台类型调用不同的同步接口
    if (connection.platform === 'Meta') {
      await platformApi.syncMetaAdAccounts(connection.id)
      success('Meta 广告账户同步成功')
    } else if (connection.platform === 'Google') {
      await platformApi.syncGoogleAdAccounts(connection.id)
      success('Google 广告账户同步成功')
    } else {
      showError('该平台暂不支持同步功能')
      return
    }
    // 刷新连接列表
    await loadConnections()
    // 如果当前账户已展开，重新加载子账号
    if (isExpanded(connection.id)) {
      await loadSubAccounts(connection.id)
    }
  } catch (err: any) {
    console.error('同步广告账户失败:', err)
    showError('同步广告账户失败，请重试')
  }
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
  const platformMap: Record<string, string> = {
    'meta': 'Meta',
    'google': 'Google',
    'tiktok': 'TikTok'
  }
  const platformName = platformMap[activePlatform.value]
  return connections.value.filter(conn => conn.platform === platformName)
})

// 判断各平台是否已接入（至少有一个账号状态为 authorized）
const isPlatformConnected = (platformId: string) => {
  const platformMap: Record<string, string> = {
    'meta': 'Meta',
    'google': 'Google',
    'tiktok': 'TikTok'
  }
  const platformName = platformMap[platformId]
  return connections.value.some(conn => conn.platform === platformName && conn.status === 'active')
}

// 判断 token 是否已过期
const isTokenExpired = (connection: PlatformConnectionResponse) => {
  if (!connection.token_expires_at) return false
  return new Date(connection.token_expires_at + 'Z') < new Date()
}

// 获取连接的有效状态（考虑 token 过期）
const getEffectiveStatus = (connection: PlatformConnectionResponse) => {
  if (connection.status === 'active' && isTokenExpired(connection)) {
    return 'token_expired'
  }
  return connection.status
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'active': '已激活',
    'unauthorized': '未授权',
    'expired': '已过期',
    'token_expired': '授权过期',
    'revoked': '已撤销'
  }
  return statusMap[status] || status
}

const getStatusClass = (status: string) => {
  const classMap: Record<string, string> = {
    'active': 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    'unauthorized': 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    'expired': 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    'token_expired': 'bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
    'revoked': 'bg-slate-50 dark:bg-slate-700 text-slate-700 dark:text-slate-400'
  }
  return classMap[status] || classMap['unauthorized']
}

// 切换子账号展开/收起
const toggleSubAccounts = async (connectionId: string) => {
  if (expandedAccounts.value.has(connectionId)) {
    expandedAccounts.value.delete(connectionId)
  } else {
    expandedAccounts.value.add(connectionId)
    // 如果还没有加载子账号，则加载
    if (!subAccounts.value[connectionId]) {
      await loadSubAccounts(connectionId)
    }
  }
}

// 加载子账号列表
const loadSubAccounts = async (connectionId: string) => {
  loadingSubAccounts.value.add(connectionId)
  try {
    const accounts = await platformApi.getSubAccounts(connectionId)
    subAccounts.value[connectionId] = accounts
  } catch (err: any) {
    console.error('加载子账号失败:', err)
    showError('加载子账号失败')
  } finally {
    loadingSubAccounts.value.delete(connectionId)
  }
}

// 检查账号是否展开
const isExpanded = (connectionId: string) => {
  return expandedAccounts.value.has(connectionId)
}

// 打开添加子账号弹窗
const openAddSubAccountDialog = (connectionId: string) => {
  currentParentConnectionId.value = connectionId
  newSubAccountName.value = ''
  newSubAccountCustomerId.value = ''
  showAddSubAccountDialog.value = true
}

// 关闭添加子账号弹窗
const closeAddSubAccountDialog = () => {
  showAddSubAccountDialog.value = false
  currentParentConnectionId.value = null
  newSubAccountName.value = ''
  newSubAccountCustomerId.value = ''
}

// 添加子账号
const handleAddSubAccount = async () => {
  if (!currentParentConnectionId.value || !newSubAccountName.value || !newSubAccountCustomerId.value) {
    showError('请填写完整的子账号信息')
    return
  }

  try {
    const newSubAccount = await platformApi.addSubAccount(currentParentConnectionId.value, {
      name: newSubAccountName.value,
      sub_account_id: newSubAccountCustomerId.value
    })

    // 更新本地数据
    if (!subAccounts.value[currentParentConnectionId.value]) {
      subAccounts.value[currentParentConnectionId.value] = []
    }
    subAccounts.value[currentParentConnectionId.value].push(newSubAccount)

    success('子账号添加成功')
    closeAddSubAccountDialog()
  } catch (err: any) {
    console.error('添加子账号失败:', err)
    showError('添加子账号失败')
  }
}

// 删除子账号
const handleDeleteSubAccount = async (connectionId: string, subAccountId: string) => {
  try {
    await platformApi.deleteSubAccount(connectionId, subAccountId)

    // 更新本地数据
    if (subAccounts.value[connectionId]) {
      subAccounts.value[connectionId] = subAccounts.value[connectionId].filter(
        (account) => account.id !== subAccountId
      )
    }

    success('子账号已删除')
  } catch (err: any) {
    console.error('删除子账号失败:', err)
    showError('删除子账号失败')
  }
}

onMounted(() => {
  loadConnections()

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
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="[]"
      active-panel="settings"
      @switch-panel="switchPanel"
    />

    <main class="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden">
      <div class="border-b border-slate-200 dark:border-slate-800 px-[19px] py-[12px]">
        <div class="flex items-center gap-[12px]">
          <button
            class="p-[6px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            @click="router.back()"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400 text-[17px]">arrow_back</span>
          </button>
          <div>
            <h1 class="text-[15px] font-bold text-slate-900 dark:text-white">平台连接</h1>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1">配置 Meta、Google、TikTok 的平台授权和广告账户同步</p>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-[19px]">
        <div class="space-y-[19px]">
          <!-- 平台选择卡片 -->
          <div class="grid grid-cols-3 gap-[12px]">
            <button
              v-for="platform in platforms"
              :key="platform.id"
              class="rounded-md border p-[12px] text-left transition-colors hover:border-primary/50"
              :class="activePlatform === platform.id
                ? 'border-primary bg-primary/5'
                : 'border-slate-200 dark:border-slate-700'"
              @click="activePlatform = platform.id"
            >
              <div class="flex items-center justify-between">
                <div class="font-semibold text-[13px] text-slate-900 dark:text-white">{{ platform.label }}</div>
                <span
                  class="rounded px-[6px] py-[4px] text-[10px] font-medium"
                  :class="isPlatformConnected(platform.id)
                    ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'"
                >
                  {{ isPlatformConnected(platform.id) ? '已接入' : '待接入' }}
                </span>
              </div>
              <p class="mt-[6px] text-[10px] text-slate-500 dark:text-slate-400">{{ platform.description }}</p>
            </button>
          </div>

          <!-- 平台详细配置 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-[16px]">
            <div class="flex items-center gap-[6px] mb-[12px]">
              <span class="material-symbols-outlined text-primary text-[17px]">hub</span>
              <h2 class="text-[11px] font-semibold text-slate-900 dark:text-white">
                {{ platforms.find(p => p.id === activePlatform)?.title }}
              </h2>
            </div>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-[12px]">
              {{ platforms.find(p => p.id === activePlatform)?.description }}
            </p>

            <!-- 连接流程 -->
            <div class="grid gap-[6px] text-[10px] text-slate-600 dark:text-slate-400 md:grid-cols-4 mb-[19px]">
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-[9px] border border-slate-200 dark:border-slate-600">
                1. 配置应用信息
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-[9px] border border-slate-200 dark:border-slate-600">
                2. 发起 OAuth 授权
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-[9px] border border-slate-200 dark:border-slate-600">
                3. 平台确认权限
              </div>
              <div class="rounded bg-slate-50 dark:bg-slate-700 p-[9px] border border-slate-200 dark:border-slate-600">
                4. 同步广告账户
              </div>
            </div>

            <!-- 开发中提示（仅 Google 和 TikTok 显示）-->
            <div v-if="activePlatform == 'tiktok'" class="p-[12px] rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-[12px]">
              <div class="flex items-start gap-[9px]">
                <span class="material-symbols-outlined text-amber-600 dark:text-amber-400 text-[17px]">construction</span>
                <div>
                  <div class="text-[11px] font-medium text-amber-900 dark:text-amber-200 mb-[4px]">
                    {{ platforms.find(p => p.id === activePlatform)?.label }} 平台连接功能开发中
                  </div>
                  <p class="text-[10px] text-amber-700 dark:text-amber-300">
                    当前版本正在完善平台连接功能，包括应用配置、OAuth 授权、账户同步、Campaign 创建等核心能力，敬请期待。
                  </p>
                </div>
              </div>
            </div>

            <!-- Meta 平台特殊功能 -->
            <div v-if="activePlatform === 'meta'" class="flex items-center justify-between">
              <p class="text-[11px] text-slate-600 dark:text-slate-400">点击添加账户后将直接跳转到 Meta OAuth 授权页面</p>
              <button
                class="px-[12px] py-[6px] rounded-md bg-primary text-white text-[11px] font-medium hover:bg-primary/90 transition-colors"
                @click="handleAddMetaAccount"
              >
                添加广告账户
              </button>
            </div>

            <!-- Google 平台特殊功能 -->
            <div v-if="activePlatform === 'google'" class="flex items-center justify-between">
              <p class="text-[11px] text-slate-600 dark:text-slate-400">点击添加账户后将直接跳转到 Google OAuth 授权页面</p>
              <button
                class="px-[12px] py-[6px] rounded-md bg-primary text-white text-[11px] font-medium hover:bg-primary/90 transition-colors"
                @click="handleAddGoogleAccount"
              >
                添加广告账户
              </button>
            </div>
          </section>

          <!-- 平台连接列表 -->
          <section class="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
            <div class="px-[16px] py-[12px] border-b border-slate-200 dark:border-slate-700">
              <h2 class="text-[11px] font-semibold text-slate-900 dark:text-white">已连接的平台账户</h2>
            </div>

            <div v-if="loading" class="p-[25px] text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined animate-spin text-[23px]">progress_activity</span>
              <p class="mt-[6px] text-[11px]">加载中...</p>
            </div>

            <div v-else-if="filteredConnections.length === 0" class="p-[25px] text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined text-[39px] mb-[6px]">cloud_off</span>
              <p class="text-[11px]">暂无 {{ platforms.find(p => p.id === activePlatform)?.label }} 平台连接</p>
              <p v-if="activePlatform === 'meta'" class="text-[10px] mt-[4px]">点击上方「添加广告账户」按钮开始配置</p>
            </div>

            <div v-else class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-slate-50 dark:bg-slate-700/50">
                  <tr>
                    <th v-if="activePlatform === 'meta' || activePlatform === 'google'" class="px-[9px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400 w-[37px]"></th>
                    <th class="px-[16px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400">账户名称</th>
                    <th v-if="activePlatform !== 'meta'" class="px-[16px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400">APP ID</th>
                    <th class="px-[16px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400">授权范围</th>
                    <th class="px-[16px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400">状态</th>
                    <th class="px-[16px] py-[9px] text-left text-[10px] font-medium text-slate-600 dark:text-slate-400">更新时间</th>
                    <th class="px-[16px] py-[9px] text-right text-[10px] font-medium text-slate-600 dark:text-slate-400">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
                  <template v-for="connection in filteredConnections" :key="connection.id">
                    <!-- 主账号行 -->
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                      <!-- Meta 和 Google 平台展开按钮 -->
                      <td v-if="activePlatform === 'meta' || activePlatform === 'google'" class="px-[9px] py-[12px] text-center">
                        <button
                          @click="toggleSubAccounts(connection.id)"
                          class="p-[4px] rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                          :class="{ 'text-primary': isExpanded(connection.id) }"
                        >
                          <span class="material-symbols-outlined text-[15px] transition-transform" :class="{ 'rotate-90': isExpanded(connection.id) }">
                            chevron_right
                          </span>
                        </button>
                      </td>
                      <td class="px-[16px] py-[12px] text-[11px] text-slate-900 dark:text-white">
                        {{ connection.account_name || '-' }}
                      </td>
                    <td v-if="activePlatform !== 'meta'" class="px-[16px] py-[12px] text-[11px] text-slate-600 dark:text-slate-400 font-mono">
                      {{ connection.account_id }}
                    </td>
                    <td class="px-[16px] py-[12px] text-[10px]">
                      <div class="flex flex-wrap gap-[4px]">
                        <span
                          v-for="scope in connection.scopes"
                          :key="scope"
                          class="px-[6px] py-[4px] rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                        >
                          {{ scope }}
                        </span>
                        <span v-if="!connection.scopes || connection.scopes.length === 0" class="text-slate-400">-</span>
                      </div>
                    </td>
                    <td class="px-[16px] py-[12px] text-[10px]">
                      <span class="px-[6px] py-[4px] rounded font-medium" :class="getStatusClass(getEffectiveStatus(connection))">
                        {{ getStatusText(getEffectiveStatus(connection)) }}
                      </span>
                    </td>
                    <td class="px-[16px] py-[12px] text-[10px] text-slate-600 dark:text-slate-400">
                      {{ formatDate(connection.updated_at) }}
                    </td>
                    <td class="px-[16px] py-[12px] text-right">
                      <div class="flex items-center justify-end gap-[6px]">
                        <!-- Meta 和 Google 平台显示同步按钮 -->
                        <button
                          v-if="(activePlatform === 'meta' || activePlatform === 'google')"
                          class="px-[9px] py-[6px] rounded text-[10px] font-medium border transition-colors"
                          :class="getEffectiveStatus(connection) === 'active'
                            ? 'border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                            : 'border-slate-200 dark:border-slate-600 text-slate-400 dark:text-slate-500 cursor-not-allowed opacity-50'"
                          :disabled="getEffectiveStatus(connection) !== 'active'"
                          @click="handleSyncAdAccounts(connection)"
                        >
                          同步广告子账号
                        </button>
                        <button
                          class="px-[9px] py-[6px] rounded text-[10px] font-medium border transition-colors"
                          :class="getEffectiveStatus(connection) === 'active'
                            ? 'border-slate-200 dark:border-slate-600 text-slate-400 dark:text-slate-500 cursor-not-allowed opacity-50'
                            : 'border-primary text-primary hover:bg-primary/5'"
                          :disabled="getEffectiveStatus(connection) === 'active'"
                          @click="handleAuthorize(connection)"
                        >
                          授权
                        </button>
                        <button
                          class="px-[9px] py-[6px] rounded text-[10px] font-medium border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                          @click="handleDelete(connection)"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                    </tr>

                    <!-- 子账号展开行（Meta 和 Google 平台） -->
                    <tr v-if="(activePlatform === 'meta' || activePlatform === 'google') && isExpanded(connection.id)" class="bg-slate-50/50 dark:bg-slate-700/20">
                      <td :colspan="activePlatform === 'meta' ? 6 : 7" class="px-0 py-0">
                        <div class="px-[25px] py-[12px]">
                          <!-- 加载中 -->
                          <div v-if="loadingSubAccounts.has(connection.id)" class="text-center py-[12px]">
                            <span class="material-symbols-outlined animate-spin text-[19px] text-slate-400">progress_activity</span>
                            <p class="text-[10px] text-slate-500 dark:text-slate-400 mt-[6px]">加载子账号中...</p>
                          </div>

                          <!-- 子账号列表 -->
                          <div v-else-if="subAccounts[connection.id] && subAccounts[connection.id].length > 0">
                            <div class="flex items-center justify-between mb-[9px]">
                              <h4 class="text-[10px] font-semibold text-slate-700 dark:text-slate-300">子账号列表</h4>
                              <div class="flex items-center gap-[9px]">
                                <span class="text-[10px] text-slate-500 dark:text-slate-400">共 {{ subAccounts[connection.id].length }} 个子账号</span>
                                <!-- Google 平台显示手动添加按钮 -->
                                <button
                                  v-if="activePlatform === 'google'"
                                  @click="openAddSubAccountDialog(connection.id)"
                                  class="px-[9px] py-[6px] rounded text-[10px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                                >
                                  添加子账号
                                </button>
                              </div>
                            </div>
                            <div class="space-y-[6px]">
                              <div
                                v-for="subAccount in subAccounts[connection.id]"
                                :key="subAccount.id"
                                class="flex items-center justify-between p-[9px] rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600"
                              >
                                <div class="flex-1">
                                  <div class="flex items-center gap-[6px]">
                                    <span class="text-[11px] font-medium text-slate-900 dark:text-white">{{ subAccount.name }}</span>
                                    <span class="px-[6px] py-[2px] rounded text-[10px] font-medium" :class="getStatusClass(subAccount.status)">
                                      {{ getStatusText(subAccount.status) }}
                                    </span>
                                  </div>
                                  <div class="flex items-center gap-[12px] mt-[4px]">
                                    <span class="text-[10px] text-slate-600 dark:text-slate-400">
                                      <span class="font-medium">Sub Account ID:</span> {{ subAccount.sub_account_id }}
                                    </span>
                                    <span class="text-[10px] text-slate-500 dark:text-slate-400">
                                      更新时间: {{ formatDate(subAccount.updated_at) }}
                                    </span>
                                  </div>
                                </div>
                                <div class="flex items-center gap-[6px]">
                                  <button
                                    @click="handleDeleteSubAccount(connection.id, subAccount.id)"
                                    class="px-[9px] py-[6px] rounded text-[10px] font-medium border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                  >
                                    删除
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>

                          <!-- 无子账号 -->
                          <div v-else class="text-center py-[12px]">
                            <span class="material-symbols-outlined text-[23px] text-slate-300 dark:text-slate-600">folder_open</span>
                            <p class="text-[10px] text-slate-500 dark:text-slate-400 mt-[6px] mb-[9px]">
                              {{ activePlatform === 'meta' ? '暂无子账号，请点击上方「同步广告子账号」按钮获取' : '暂无子账号' }}
                            </p>
                            <!-- Google 平台显示添加按钮 -->
                            <button
                              v-if="activePlatform === 'google'"
                              @click="openAddSubAccountDialog(connection.id)"
                              class="px-[12px] py-[6px] rounded text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
                            >
                              + 添加子账号
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- 添加子账号弹窗 -->
    <div v-if="showAddSubAccountDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white dark:bg-slate-800 rounded-md shadow-xl w-full max-w-[344px] mx-4">
        <div class="px-[19px] py-[12px] border-b border-slate-200 dark:border-slate-700">
          <h3 class="text-[15px] font-semibold text-slate-900 dark:text-white">添加子账号</h3>
        </div>

        <div class="px-[19px] py-[12px] space-y-[12px]">
          <div>
            <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[6px]">
              子账号名称 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newSubAccountName"
              type="text"
              placeholder="请输入子账号名称"
              class="w-full px-[9px] py-[6px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-[11px]"
            />
          </div>

          <div>
            <label class="block text-[11px] font-medium text-slate-700 dark:text-slate-300 mb-[6px]">
              Customer ID <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newSubAccountCustomerId"
              type="text"
              placeholder="请输入 Google Customer ID"
              class="w-full px-[9px] py-[6px] border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-[11px]"
            />
            <p class="mt-[4px] text-[10px] text-slate-500 dark:text-slate-400">
              格式：123-456-7890
            </p>
          </div>
        </div>

        <div class="px-[19px] py-[12px] border-t border-slate-200 dark:border-slate-700 flex items-center justify-end gap-[9px]">
          <button
            @click="closeAddSubAccountDialog"
            class="px-[12px] py-[6px] rounded-md text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            取消
          </button>
          <button
            @click="handleAddSubAccount"
            class="px-[12px] py-[6px] rounded-md text-[11px] font-medium bg-primary text-white hover:bg-primary/90 transition-colors"
            :disabled="!newSubAccountName || !newSubAccountCustomerId"
            :class="{ 'opacity-50 cursor-not-allowed': !newSubAccountName || !newSubAccountCustomerId }"
          >
            确定添加
          </button>
        </div>
      </div>
    </div>

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
