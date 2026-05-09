<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import {
  getKnowledgeArticles,
  getMediaAccounts,
  getMediaCustomers,
  getMediaOpsDashboard,
  getMediaOrders,
  getMediaProducts,
  getPaymentVouchers,
  getServiceTickets,
  type AccountOrder,
  type KnowledgeArticle,
  type MediaAccount,
  type MediaCustomer,
  type MediaOpsDashboard,
  type MediaProduct,
  type PaymentVoucher,
  type ServiceTicket,
} from '@/api/mediaOps'

const router = useRouter()

const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/reports' },
]

const tabs = [
  { id: 'workbench', label: '工作台', icon: 'dashboard' },
  { id: 'orders', label: '下户订单', icon: 'assignment' },
  { id: 'accounts', label: '账号交付', icon: 'account_balance_wallet' },
  { id: 'finance', label: '财务水单', icon: 'payments' },
  { id: 'tickets', label: '售后工单', icon: 'support' },
  { id: 'knowledge', label: '知识库', icon: 'menu_book' },
]

const activeTab = ref('workbench')
const loading = ref(false)
const error = ref('')
const dashboard = ref<MediaOpsDashboard | null>(null)
const customers = ref<MediaCustomer[]>([])
const products = ref<MediaProduct[]>([])
const orders = ref<AccountOrder[]>([])
const vouchers = ref<PaymentVoucher[]>([])
const accounts = ref<MediaAccount[]>([])
const tickets = ref<ServiceTicket[]>([])
const articles = ref<KnowledgeArticle[]>([])
const orderStatusFilter = ref('')
const accountStatusFilter = ref('')

const switchPanel = (item: any) => {
  router.push(item.path)
}

const loadData = async () => {
  loading.value = true
  error.value = ''
  try {
    const [
      dashboardData,
      customerRows,
      productRows,
      orderRows,
      voucherRows,
      accountRows,
      ticketRows,
      articleRows,
    ] = await Promise.all([
      getMediaOpsDashboard(),
      getMediaCustomers(),
      getMediaProducts(),
      getMediaOrders(),
      getPaymentVouchers(),
      getMediaAccounts(),
      getServiceTickets(),
      getKnowledgeArticles(),
    ])
    dashboard.value = dashboardData
    customers.value = customerRows
    products.value = productRows
    orders.value = orderRows
    vouchers.value = voucherRows
    accounts.value = accountRows
    tickets.value = ticketRows
    articles.value = articleRows
  } catch (err: any) {
    error.value = err.message || '加载广告账户数据失败'
  } finally {
    loading.value = false
  }
}

const metricCards = computed(() => {
  const metrics = dashboard.value?.metrics || {}
  return [
    { label: '今日下户', value: metrics.today_orders || 0, icon: 'assignment_add', tone: 'blue' },
    { label: '待处理订单', value: metrics.pending_orders || 0, icon: 'pending_actions', tone: 'amber' },
    { label: '水单待审', value: metrics.pending_payment_reviews || 0, icon: 'receipt_long', tone: 'purple' },
    { label: '待交付账号', value: metrics.accounts_to_deliver || 0, icon: 'outbox', tone: 'emerald' },
    { label: '未结工单', value: metrics.open_tickets || 0, icon: 'support_agent', tone: 'red' },
    { label: '今日应收', value: `$${Number(metrics.today_receivable_usd || 0).toLocaleString()}`, icon: 'paid', tone: 'slate' },
  ]
})

const filteredOrders = computed(() => {
  return orders.value.filter(order => !orderStatusFilter.value || order.status === orderStatusFilter.value)
})

const filteredAccounts = computed(() => {
  return accounts.value.filter(account => !accountStatusFilter.value || account.status === accountStatusFilter.value)
})

const orderStatusOptions = computed(() => {
  return Array.from(new Set(orders.value.map(order => order.status)))
})

const accountStatusOptions = computed(() => {
  return Array.from(new Set(accounts.value.map(account => account.status)))
})

const statusText = (status: string) => ({
  pending_payment: '待付款',
  payment_review: '水单审核',
  pending_opening: '待开户',
  opening: '开户中',
  binding_card: '绑卡设限额',
  pending_delivery: '待交付',
  delivered: '已交付',
  exception: '异常',
  active: '正常',
  verifying: '待验证',
  frozen: '冻结',
  banned: '封禁',
  recycled: '回收',
  open: '待处理',
  processing: '处理中',
  waiting_customer: '等客户',
  resolved: '已解决',
  pending_review: '待审核',
  approved: '已到账',
  amount_mismatch: '金额不符',
  rejected: '驳回',
}[status] || status)

const statusClass = (status: string) => ({
  delivered: 'bg-emerald-50 text-emerald-700',
  active: 'bg-emerald-50 text-emerald-700',
  approved: 'bg-emerald-50 text-emerald-700',
  payment_review: 'bg-purple-50 text-purple-700',
  pending_review: 'bg-purple-50 text-purple-700',
  binding_card: 'bg-blue-50 text-blue-700',
  pending_delivery: 'bg-blue-50 text-blue-700',
  frozen: 'bg-red-50 text-red-700',
  banned: 'bg-red-50 text-red-700',
  exception: 'bg-red-50 text-red-700',
  processing: 'bg-amber-50 text-amber-700',
  open: 'bg-amber-50 text-amber-700',
}[status] || 'bg-slate-100 text-slate-700')

const priorityClass = (priority: string) => ({
  urgent: 'bg-red-600 text-white',
  high: 'bg-orange-100 text-orange-700',
  normal: 'bg-blue-50 text-blue-700',
  low: 'bg-slate-100 text-slate-600',
}[priority] || 'bg-slate-100 text-slate-600')

const formatDate = (value?: string) => {
  if (!value) return '-'
  return value.slice(0, 16).replace('T', ' ')
}

onMounted(loadData)
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav :nav-items="navItems" active-panel="accounts" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white">广告账户</h1>
          <p class="text-sm text-slate-500 mt-1">统一查看账户开户、收款、交付、充值、售后和风险处理</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-slate-200 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            @click="router.push('/platform-accounts/manage')"
          >
            <span class="material-symbols-outlined text-[18px]">list_alt</span>
            账户操作
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white text-sm font-semibold hover:bg-primary/90 transition-colors"
            @click="loadData"
          >
            <span class="material-symbols-outlined text-[18px]">refresh</span>
            刷新
          </button>
        </div>
      </div>

      <div class="p-6 space-y-6">
        <div v-if="error" class="p-3 rounded-md bg-red-50 text-red-700 text-sm">{{ error }}</div>
        <div v-if="loading" class="text-sm text-slate-500">加载广告账户数据...</div>

        <div class="grid grid-cols-2 lg:grid-cols-6 gap-3">
          <div
            v-for="card in metricCards"
            :key="card.label"
            class="rounded-md border border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900"
          >
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-500">{{ card.label }}</span>
              <span class="material-symbols-outlined text-primary text-[20px]">{{ card.icon }}</span>
            </div>
            <div class="mt-3 text-2xl font-bold text-slate-900 dark:text-white">{{ card.value }}</div>
          </div>
        </div>

        <div class="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="inline-flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors"
            :class="activeTab === tab.id
              ? 'border-primary text-primary'
              : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white'"
            @click="activeTab = tab.id"
          >
            <span class="material-symbols-outlined text-[18px]">{{ tab.icon }}</span>
            {{ tab.label }}
          </button>
        </div>

        <section v-if="activeTab === 'workbench'" class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div class="xl:col-span-2 space-y-6">
            <div class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 font-semibold text-slate-900 dark:text-white">
                下户订单状态漏斗
              </div>
              <div class="p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div
                  v-for="item in dashboard?.status_funnel || []"
                  :key="item.status"
                  class="p-3 rounded-md border border-slate-200 dark:border-slate-800"
                >
                  <div class="text-xs text-slate-500">{{ item.label }}</div>
                  <div class="mt-2 text-xl font-bold text-slate-900 dark:text-white">{{ item.count }}</div>
                </div>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 font-semibold text-slate-900 dark:text-white">
                账户产品 / 户类型
              </div>
              <div class="divide-y divide-slate-100 dark:divide-slate-800">
                <div v-for="product in products" :key="product.id" class="p-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="font-semibold text-slate-900 dark:text-white">{{ product.name }}</div>
                      <div class="text-xs text-slate-500 mt-1">
                        {{ product.platform }} · {{ product.account_type }} · {{ product.account_property }} · 最低充值 ${{ product.min_recharge_usd }}
                      </div>
                    </div>
                    <span class="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700">SLA {{ product.delivery_sla_minutes }} 分钟</span>
                  </div>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="point in product.selling_points"
                      :key="point"
                      class="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                    >
                      {{ point }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <div class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 font-semibold text-slate-900 dark:text-white">
                今日待办
              </div>
              <div class="divide-y divide-slate-100 dark:divide-slate-800">
                <div v-for="task in dashboard?.pending_tasks || []" :key="task.title" class="p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ task.title }}</div>
                    <span class="text-xs px-2 py-1 rounded" :class="priorityClass(task.priority)">{{ task.priority }}</span>
                  </div>
                  <div class="mt-2 text-xs text-slate-500">负责人：{{ task.owner }}</div>
                </div>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 font-semibold text-slate-900 dark:text-white">
                风险提醒
              </div>
              <div class="p-4 space-y-3">
                <div
                  v-for="alert in dashboard?.alerts || []"
                  :key="alert.message"
                  class="p-3 rounded-md bg-amber-50 text-amber-800 text-sm"
                >
                  {{ alert.message }}
                </div>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 font-semibold text-slate-900 dark:text-white">
                重点客户
              </div>
              <div class="divide-y divide-slate-100 dark:divide-slate-800">
                <div v-for="customer in customers" :key="customer.id" class="p-4">
                  <div class="flex items-center justify-between">
                    <div class="font-semibold text-slate-900 dark:text-white">{{ customer.name }}</div>
                    <span class="text-xs px-2 py-1 rounded bg-primary/10 text-primary">{{ customer.level }}</span>
                  </div>
                  <div class="mt-2 text-xs text-slate-500">
                    {{ customer.industry }} · {{ customer.payment_preference }} · {{ customer.owner }}
                  </div>
                  <div v-if="customer.risk_note" class="mt-2 text-xs text-amber-700 bg-amber-50 rounded p-2">
                    {{ customer.risk_note }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'orders'" class="space-y-4">
          <div class="flex items-center gap-3">
            <select v-model="orderStatusFilter" class="px-3 py-2 rounded-md border text-sm">
              <option value="">全部状态</option>
              <option v-for="status in orderStatusOptions" :key="status" :value="status">{{ statusText(status) }}</option>
            </select>
          </div>
          <div class="overflow-hidden rounded-md border border-slate-200 dark:border-slate-800">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 dark:bg-slate-800/50 text-slate-500">
                <tr>
                  <th class="text-left p-3">订单</th>
                  <th class="text-left p-3">客户</th>
                  <th class="text-left p-3">户类型</th>
                  <th class="text-left p-3">开户信息</th>
                  <th class="text-right p-3">应收</th>
                  <th class="text-left p-3">状态</th>
                  <th class="text-left p-3">下一步</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in filteredOrders" :key="order.id" class="border-t border-slate-100 dark:border-slate-800">
                  <td class="p-3 font-semibold text-slate-900 dark:text-white">{{ order.id }}</td>
                  <td class="p-3">{{ order.customer_name }}</td>
                  <td class="p-3">{{ order.product_name }}</td>
                  <td class="p-3 text-xs text-slate-500">
                    {{ order.timezone }} · {{ order.email }} · {{ order.quantity }} 个 · {{ order.ad_industry }}
                  </td>
                  <td class="p-3 text-right font-semibold">${{ order.receivable_amount.toLocaleString() }} {{ order.payment_method }}</td>
                  <td class="p-3"><span class="px-2 py-1 rounded text-xs font-medium" :class="statusClass(order.status)">{{ statusText(order.status) }}</span></td>
                  <td class="p-3 text-xs text-slate-500 max-w-[260px]">{{ order.next_action }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'accounts'" class="space-y-4">
          <div class="flex items-center gap-3">
            <select v-model="accountStatusFilter" class="px-3 py-2 rounded-md border text-sm">
              <option value="">全部状态</option>
              <option v-for="status in accountStatusOptions" :key="status" :value="status">{{ statusText(status) }}</option>
            </select>
          </div>
          <div class="overflow-hidden rounded-md border border-slate-200 dark:border-slate-800">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 dark:bg-slate-800/50 text-slate-500">
                <tr>
                  <th class="text-left p-3">账户</th>
                  <th class="text-left p-3">客户</th>
                  <th class="text-left p-3">状态</th>
                  <th class="text-left p-3">BMID / 时区</th>
                  <th class="text-right p-3">消耗</th>
                  <th class="text-right p-3">余额</th>
                  <th class="text-left p-3">待办标记</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="account in filteredAccounts" :key="account.id" class="border-t border-slate-100 dark:border-slate-800">
                  <td class="p-3">
                    <div class="font-semibold text-slate-900 dark:text-white">{{ account.account_name }}</div>
                    <div class="text-xs text-slate-500">{{ account.account_id }} · {{ account.email }}</div>
                  </td>
                  <td class="p-3">{{ account.customer_name }}</td>
                  <td class="p-3"><span class="px-2 py-1 rounded text-xs font-medium" :class="statusClass(account.status)">{{ statusText(account.status) }}</span></td>
                  <td class="p-3 text-xs text-slate-500">{{ account.business_manager_id || '-' }} · {{ account.timezone }}</td>
                  <td class="p-3 text-right font-semibold">${{ account.spend.toLocaleString() }}</td>
                  <td class="p-3 text-right font-semibold">${{ account.balance.toLocaleString() }}</td>
                  <td class="p-3">
                    <div class="flex flex-wrap gap-1">
                      <span v-for="flag in account.operation_flags" :key="flag" class="px-2 py-1 rounded bg-slate-100 text-xs text-slate-600">{{ flag }}</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'finance'" class="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div class="xl:col-span-2 overflow-hidden rounded-md border border-slate-200 dark:border-slate-800">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 dark:bg-slate-800/50 text-slate-500">
                <tr>
                  <th class="text-left p-3">水单</th>
                  <th class="text-left p-3">客户</th>
                  <th class="text-right p-3">金额</th>
                  <th class="text-left p-3">状态</th>
                  <th class="text-left p-3">交易信息</th>
                  <th class="text-left p-3">提交时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="voucher in vouchers" :key="voucher.id" class="border-t border-slate-100 dark:border-slate-800">
                  <td class="p-3 font-semibold">{{ voucher.id }}</td>
                  <td class="p-3">{{ voucher.customer_name }}</td>
                  <td class="p-3 text-right font-semibold">{{ voucher.amount.toLocaleString() }} {{ voucher.currency }}</td>
                  <td class="p-3"><span class="px-2 py-1 rounded text-xs font-medium" :class="statusClass(voucher.status)">{{ statusText(voucher.status) }}</span></td>
                  <td class="p-3 text-xs text-slate-500">{{ voucher.transaction_hash || voucher.screenshot_url || '-' }}</td>
                  <td class="p-3 text-xs text-slate-500">{{ formatDate(voucher.submitted_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="rounded-md border border-slate-200 dark:border-slate-800 p-4">
            <h3 class="font-semibold text-slate-900 dark:text-white">财务规则</h3>
            <div class="mt-3 space-y-3 text-sm text-slate-600 dark:text-slate-300">
              <p>充值对接时间：10:00 - 24:00。</p>
              <p>单次单户最低充值：1000 美金。</p>
              <p>客户上传水单后财务审核，目标 10 分钟内到账。</p>
              <p>金额不符、链路异常、截图不清晰时进入异常状态。</p>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'tickets'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div
            v-for="ticket in tickets"
            :key="ticket.id"
            class="rounded-md border border-slate-200 dark:border-slate-800 p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="font-semibold text-slate-900 dark:text-white">{{ ticket.summary }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ ticket.id }} · {{ ticket.customer_name }} · {{ ticket.account_id || '-' }}</div>
              </div>
              <span class="px-2 py-1 rounded text-xs font-medium" :class="priorityClass(ticket.priority)">{{ ticket.priority }}</span>
            </div>
            <div class="mt-4 flex items-center justify-between text-xs text-slate-500">
              <span>负责人：{{ ticket.owner }}</span>
              <span>SLA：{{ formatDate(ticket.sla_due_at) }}</span>
            </div>
            <div class="mt-3"><span class="px-2 py-1 rounded text-xs font-medium" :class="statusClass(ticket.status)">{{ statusText(ticket.status) }}</span></div>
          </div>
        </section>

        <section v-else-if="activeTab === 'knowledge'" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div
            v-for="article in articles"
            :key="article.id"
            class="rounded-md border border-slate-200 dark:border-slate-800 p-4"
          >
            <div class="text-xs font-semibold text-primary">{{ article.category }}</div>
            <h3 class="mt-2 font-semibold text-slate-900 dark:text-white">{{ article.title }}</h3>
            <p class="mt-3 text-sm text-slate-600 dark:text-slate-300 leading-6">{{ article.answer }}</p>
            <div class="mt-4 flex flex-wrap gap-1">
              <span v-for="keyword in article.trigger_keywords" :key="keyword" class="px-2 py-1 rounded bg-slate-100 text-xs text-slate-600">{{ keyword }}</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
