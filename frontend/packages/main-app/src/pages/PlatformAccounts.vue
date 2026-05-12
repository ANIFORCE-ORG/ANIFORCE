<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import {
  createPlatformAccountOperation,
  disconnectPlatformAccount,
  getPlatformAccountOperations,
  getPlatformAccounts,
  type PlatformAccount,
  type PlatformAccountOperation,
} from '@/api/platformAccounts'

const router = useRouter()

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/reports' },
]

const accounts = ref<PlatformAccount[]>([])
const loading = ref(false)
const error = ref('')
const platformFilter = ref('meta')
const statusFilter = ref('')
const searchQuery = ref('')
const showOperationPanel = ref(false)
const showHistoryPanel = ref(false)
const selectedAccount = ref<PlatformAccount | null>(null)
const accountOperations = ref<PlatformAccountOperation[]>([])
const oauthResult = ref('')

const operationForm = ref({
  operation_type: 'recharge' as 'open' | 'recharge' | 'clear' | 'bind' | 'recycle',
  amount: 100,
  currency: 'USD',
  target_id: '',
  note: '',
})

const statusCards = computed(() => {
  const rows = platformFilter.value ? accounts.value.filter(a => a.platform === platformFilter.value) : accounts.value
  const count = (status: string) => rows.filter(a => a.status === status).length
  return [
    { id: '', label: '全部', value: rows.length, icon: 'apps' },
    { id: 'active', label: '正常', value: count('active'), icon: 'check_circle' },
    { id: 'clearing', label: '清零中', value: count('clearing'), icon: 'hourglass_top' },
    { id: 'banned', label: '封禁', value: count('banned'), icon: 'block' },
    { id: 'cleared', label: '已清零', value: count('cleared'), icon: 'cleaning_services' },
    { id: 'recycled', label: '已回收', value: count('recycled'), icon: 'assignment_return' },
  ]
})

const spendBands = computed(() => {
  const bands = [
    { label: '$0-10', min: 0, max: 10 },
    { label: '$10-100', min: 10, max: 100 },
    { label: '$100-500', min: 100, max: 500 },
    { label: '$500-1000', min: 500, max: 1000 },
    { label: '$1000-2000', min: 1000, max: 2000 },
    { label: '$2000+', min: 2000, max: Number.POSITIVE_INFINITY },
  ]
  const rows = accounts.value.filter(a => !platformFilter.value || a.platform === platformFilter.value)
  return bands.map(band => ({
    ...band,
    total: rows.filter(a => a.amount_spent >= band.min && a.amount_spent < band.max).length,
    normal: rows.filter(a => a.status === 'active' && a.amount_spent >= band.min && a.amount_spent < band.max).length,
    banned: rows.filter(a => a.status === 'banned' && a.amount_spent >= band.min && a.amount_spent < band.max).length,
  }))
})

const filteredAccounts = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return accounts.value.filter(account => {
    if (platformFilter.value && account.platform !== platformFilter.value) return false
    if (statusFilter.value && account.status !== statusFilter.value) return false
    if (!query) return true
    return [
      account.account_id,
      account.account_name,
      account.business_manager_id,
      account.remark,
    ].some(value => (value || '').toLowerCase().includes(query))
  })
})

const loadAccounts = async () => {
  loading.value = true
  error.value = ''
  try {
    accounts.value = await getPlatformAccounts()
  } catch (err: any) {
    error.value = err.message || '加载平台账户失败'
  } finally {
    loading.value = false
  }
}

const switchPanel = (item: any) => {
  router.push(item.path)
}

const openOperation = (account: PlatformAccount, type: typeof operationForm.value.operation_type) => {
  selectedAccount.value = account
  operationForm.value.operation_type = type
  operationForm.value.amount = type === 'recharge' ? 100 : 0
  operationForm.value.target_id = type === 'bind' ? (account.business_manager_id || '') : ''
  operationForm.value.note = ''
  showOperationPanel.value = true
}

const submitOperation = async () => {
  if (!selectedAccount.value) return
  await createPlatformAccountOperation(selectedAccount.value.id, {
    operation_type: operationForm.value.operation_type,
    amount: operationForm.value.operation_type === 'recharge' ? Number(operationForm.value.amount || 0) : undefined,
    currency: operationForm.value.currency,
    target_id: operationForm.value.target_id || undefined,
    note: operationForm.value.note || undefined,
  })
  showOperationPanel.value = false
  await loadAccounts()
}

const disconnect = async (account: PlatformAccount) => {
  await disconnectPlatformAccount(account.id)
  await loadAccounts()
}

const openHistory = async (account: PlatformAccount) => {
  selectedAccount.value = account
  accountOperations.value = await getPlatformAccountOperations(account.id)
  showHistoryPanel.value = true
}

const statusLabel = (status: string) => ({
  active: '正常',
  clearing: '清零中',
  banned: '封禁',
  cleared: '已清零',
  recycled: '已回收',
  disconnected: '已断开',
}[status] || status)

const statusClass = (status: string) => ({
  active: 'bg-emerald-50 text-emerald-700',
  clearing: 'bg-amber-50 text-amber-700',
  banned: 'bg-red-50 text-red-700',
  cleared: 'bg-blue-50 text-blue-700',
  recycled: 'bg-slate-100 text-slate-700',
  disconnected: 'bg-slate-100 text-slate-500',
}[status] || 'bg-slate-100 text-slate-700')

const operationLabel = (type: string) => ({
  open: '开户',
  recharge: '充值',
  clear: '清零',
  bind: '绑定',
  recycle: '回收',
}[type] || type)

const formatDate = (value?: string) => value ? value.slice(0, 16).replace('T', ' ') : '-'

onMounted(async () => {
  const status = router.currentRoute.value.query.status
  const count = router.currentRoute.value.query.count
  const message = router.currentRoute.value.query.message
  if (status === 'success') {
    oauthResult.value = `Meta Business 已连接，已同步 ${count || 0} 个广告账户。`
  } else if (status === 'error') {
    error.value = String(message || 'Meta 授权失败，请重新连接。')
  }

  await loadAccounts()
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav :nav-items="navItems" active-panel="accounts" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white">账户操作</h1>
          <p class="text-sm text-slate-500 mt-1">管理已绑定平台广告账户、充值、清零、绑定和回收</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="px-4 py-2 rounded-md border text-sm font-medium"
            @click="router.push('/platform-accounts')"
          >
            返回首页
          </button>
        </div>
      </div>

      <div class="p-6 space-y-6">
        <div v-if="oauthResult" class="p-3 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
          {{ oauthResult }}
        </div>

        <div class="flex items-center gap-3">
          <select v-model="platformFilter" class="px-3 py-2 rounded-md border text-sm">
            <option value="meta">Meta</option>
          </select>
          <span class="text-xs text-slate-500">Google/TikTok 待接入，v0.1 仅展示 Meta 账户</span>
          <input
            v-model="searchQuery"
            class="flex-1 px-3 py-2 rounded-md border text-sm"
            placeholder="搜索账户 ID、名称、BMID、备注"
          />
        </div>

        <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
          <button
            v-for="card in statusCards"
            :key="card.label"
            class="p-4 rounded-md border text-left transition-colors"
            :class="statusFilter === card.id ? 'border-primary bg-primary/5' : 'border-slate-200 hover:border-primary/50'"
            @click="statusFilter = card.id"
          >
            <span class="material-symbols-outlined text-lg text-primary">{{ card.icon }}</span>
            <div class="text-2xl font-bold text-slate-900 mt-2">{{ card.value }}</div>
            <div class="text-xs text-slate-500">{{ card.label }}</div>
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div v-for="band in spendBands" :key="band.label" class="p-3 rounded-md border border-slate-200">
            <div class="text-sm font-semibold text-slate-900">{{ band.label }}</div>
            <div class="text-xs text-slate-500 mt-1">总 {{ band.total }} · 正常 {{ band.normal }} · 封禁 {{ band.banned }}</div>
          </div>
        </div>

        <div v-if="error" class="p-3 rounded-md bg-red-50 text-red-700 text-sm">{{ error }}</div>

        <div class="overflow-hidden rounded-md border border-slate-200">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-slate-500">
              <tr>
                <th class="text-left p-3">账户</th>
                <th class="text-left p-3">状态</th>
                <th class="text-left p-3">BMID</th>
                <th class="text-left p-3">时区</th>
                <th class="text-right p-3">累计消耗</th>
                <th class="text-right p-3">余额</th>
                <th class="text-left p-3">授权</th>
                <th class="text-left p-3">同步状态</th>
                <th class="text-right p-3">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="account in filteredAccounts" :key="account.id" class="border-t border-slate-100">
                <td class="p-3">
                  <div class="font-semibold text-slate-900">{{ account.account_name }}</div>
                  <div class="text-xs text-slate-500">{{ account.account_id }}</div>
                </td>
                <td class="p-3">
                  <span class="px-2 py-1 rounded text-xs font-medium" :class="statusClass(account.status)">
                    {{ statusLabel(account.status) }}
                  </span>
                </td>
                <td class="p-3 text-slate-600">{{ account.business_manager_id || '-' }}</td>
                <td class="p-3 text-slate-600">{{ account.timezone || '-' }}</td>
                <td class="p-3 text-right font-medium">${{ Math.round(account.amount_spent || 0).toLocaleString() }}</td>
                <td class="p-3 text-right font-medium">${{ Math.round(account.available_balance || account.balance || 0).toLocaleString() }}</td>
                <td class="p-3">
                  <span :class="account.has_token ? 'text-emerald-600' : 'text-slate-400'" class="text-xs font-medium">
                    {{ account.has_token ? '已保存' : '未连接' }}
                  </span>
                </td>
                <td class="p-3 text-xs text-slate-500">
                  <div>{{ account.last_sync_at ? formatDate(account.last_sync_at) : '未同步' }}</div>
                  <div>{{ account.source_type || '-' }}</div>
                </td>
                <td class="p-3">
                  <div class="flex items-center justify-end gap-1">
                    <button class="px-2 py-1 rounded border text-xs" @click="openOperation(account, 'recharge')">充值</button>
                    <button class="px-2 py-1 rounded border text-xs" @click="openOperation(account, 'clear')">清零</button>
                    <button class="px-2 py-1 rounded border text-xs" @click="openOperation(account, 'bind')">绑定</button>
                    <button class="px-2 py-1 rounded border text-xs" @click="openOperation(account, 'recycle')">回收</button>
                    <button class="px-2 py-1 rounded border text-xs" @click="openHistory(account)">历史</button>
                    <button class="px-2 py-1 rounded border text-xs" @click="disconnect(account)">断开</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loading && filteredAccounts.length === 0" class="py-16 text-center text-sm text-slate-500">
            暂无广告账户
          </div>
        </div>
      </div>
    </main>

    <div v-if="showOperationPanel" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center" @click.self="showOperationPanel = false">
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 class="text-lg font-bold text-slate-900">{{ selectedAccount?.account_name }}</h3>
        <div class="mt-4 space-y-3">
          <select v-model="operationForm.operation_type" class="w-full px-3 py-2 rounded-md border text-sm">
            <option value="open">开户</option>
            <option value="recharge">充值</option>
            <option value="clear">清零</option>
            <option value="bind">绑定</option>
            <option value="recycle">回收</option>
          </select>
          <input v-if="operationForm.operation_type === 'recharge'" v-model.number="operationForm.amount" type="number" class="w-full px-3 py-2 rounded-md border text-sm" placeholder="金额" />
          <input v-if="operationForm.operation_type === 'bind'" v-model="operationForm.target_id" class="w-full px-3 py-2 rounded-md border text-sm" placeholder="BMID / 资产 ID" />
          <textarea v-model="operationForm.note" class="w-full h-20 px-3 py-2 rounded-md border text-sm" placeholder="操作备注"></textarea>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button class="px-4 py-2 rounded-md border text-sm" @click="showOperationPanel = false">取消</button>
          <button class="px-4 py-2 rounded-md bg-primary text-white text-sm" @click="submitOperation">确认</button>
        </div>
      </div>
    </div>

    <div v-if="showHistoryPanel" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center" @click.self="showHistoryPanel = false">
      <div class="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h3 class="text-lg font-bold text-slate-900">操作历史</h3>
            <p class="text-sm text-slate-500">{{ selectedAccount?.account_name }}</p>
          </div>
          <button class="p-2 rounded-md hover:bg-slate-100" @click="showHistoryPanel = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div v-if="accountOperations.length === 0" class="py-10 text-center text-sm text-slate-500">
          暂无操作历史
        </div>
        <div v-else class="overflow-hidden rounded-md border border-slate-200">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-slate-500">
              <tr>
                <th class="p-3 text-left">操作</th>
                <th class="p-3 text-left">状态</th>
                <th class="p-3 text-right">金额</th>
                <th class="p-3 text-left">目标</th>
                <th class="p-3 text-left">备注</th>
                <th class="p-3 text-left">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="operation in accountOperations" :key="operation.id" class="border-t border-slate-100">
                <td class="p-3 font-medium">{{ operationLabel(operation.operation_type) }}</td>
                <td class="p-3">{{ operation.status }}</td>
                <td class="p-3 text-right">{{ operation.amount ? `$${operation.amount}` : '-' }}</td>
                <td class="p-3">{{ operation.target_id || '-' }}</td>
                <td class="p-3">{{ operation.note || '-' }}</td>
                <td class="p-3">{{ formatDate(operation.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
