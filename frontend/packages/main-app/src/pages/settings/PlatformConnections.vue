<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import MetaConfigDialog from '@/components/settings/MetaConfigDialog.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { navItems } from '@/config/navigation'
import { platformApi, type PlatformConnectionResponse } from '@/api/platform'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { success, error: showError } = useToast()
const activePlatform = ref<'meta' | 'google' | 'tiktok'>('meta')
const showConfigDialog = ref(false)
const connections = ref<PlatformConnectionResponse[]>([])
const loading = ref(false)
const editingConnection = ref<PlatformConnectionResponse | null>(null)

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
    showError('加载平台连接失败')
  } finally {
    loading.value = false
  }
}

const handleSaveConfig = async (data: any) => {
  console.log('保存配置:', data)
  closeConfigDialog()
  await loadConnections()
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

const handleAuthorize = (connection: PlatformConnectionResponse) => {
  console.log('授权连接:', connection)
  // TODO: 发起 OAuth 授权流程
  showError('OAuth 授权功能开发中')
}

const handleDelete = async (connection: PlatformConnectionResponse) => {
  if (!confirm(`确定要删除「${connection.account_name || connection.account_id}」吗？`)) {
    return
  }
  
  try {
    await platformApi.deleteConnection(connection.id)
    success('连接已删除')
    await loadConnections()
  } catch (err: any) {
    console.error('删除失败:', err)
    showError('删除连接失败')
  }
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

onMounted(() => {
  loadConnections()
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
              @click="activePlatform = platform.id"
            >
              <div class="flex items-center justify-between">
                <div class="font-semibold text-slate-900 dark:text-white">{{ platform.label }}</div>
                <span class="rounded px-2 py-1 text-xs font-medium bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                  待接入
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

            <!-- 开发中提示 -->
            <div class="p-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-4">
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
            
            <div v-else-if="connections.length === 0" class="p-8 text-center text-slate-500 dark:text-slate-400">
              <span class="material-symbols-outlined text-5xl mb-2">cloud_off</span>
              <p class="text-sm">暂无平台连接</p>
              <p class="text-xs mt-1">点击上方「添加广告账户」按钮开始配置</p>
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
                  <tr v-for="connection in connections" :key="connection.id" class="hover:bg-slate-50 dark:hover:bg-slate-700/30">
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
        </div>
      </div>
    </main>

    <!-- Meta 配置弹窗组件 -->
    <MetaConfigDialog
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
    
    <!-- Toast 提示容器 -->
    <ToastContainer />
  </div>
</template>
