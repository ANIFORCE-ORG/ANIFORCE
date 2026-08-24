<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import DataSyncDialog from '@/components/dashboard/DataSyncDialog.vue'
import { navItems } from '@/config/navigation'
import { getMetaDashboardOverview, type MetaAdSetSyncResponse, type MetaDashboardAccount, type MetaDashboardOverview } from '@/api/dashboard'
import { platformApi, type PlatformConnectionResponse, type SubAccountResponse } from '@/api/platform'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
const router = useRouter()
const activeSession = ref('sess-g001')
const period = ref('7')
const connectionId = ref('')
const accountId = ref('')
const connections = ref<PlatformConnectionResponse[]>([])
const accounts = ref<SubAccountResponse[]>([])
const overview = ref<MetaDashboardOverview | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const syncing = ref(false)
const syncDialogOpen = ref(false)
const errorMessage = ref('')
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimer: number | undefined

const sessions = ref([
  { id: 'sess-g001', name: 'Candy Blast 投放咨询', active: true },
  { id: 'sess-g002', name: '素材优化建议', active: false },
  { id: 'sess-g003', name: '东南亚市场测试', active: false },
  { id: 'sess-d001', name: 'DramaBox 新剧推广', active: false },
])

const accountRows = computed<MetaDashboardAccount[]>(() => [...(overview.value?.accounts ?? [])].sort((a, b) => (b.spend ?? -1) - (a.spend ?? -1)))

const windowForDays = (days: number) => {
  const until = new Date()
  const since = new Date(until)
  since.setDate(since.getDate() - days + 1)
  const iso = (value: Date) => value.toISOString().slice(0, 10)
  return { since: iso(since), until: iso(until) }
}
const dateWindow = computed(() => windowForDays(Number(period.value)))

const numberValue = (value: number | null | undefined) => value == null ? null : Number(value)
const formatNumber = (value: number | null | undefined, maximumFractionDigits = 0) => {
  const numeric = numberValue(value)
  return numeric == null ? '—' : new Intl.NumberFormat('zh-CN', { maximumFractionDigits }).format(numeric)
}
const formatMoney = (value: number | null | undefined) => {
  const numeric = numberValue(value)
  if (numeric == null || overview.value?.window.mixed_currency) return overview.value?.window.mixed_currency ? '多币种' : '—'
  const currency = overview.value?.window.currency
  if (!currency) return formatNumber(numeric, 2)
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(numeric)
}
const formatPercent = (value: number | null | undefined) => {
  const numeric = numberValue(value)
  return numeric == null ? '—' : `${(numeric * 100).toFixed(2)}%`
}
const formatDate = (value: string) => value.slice(5)

const previousKpis = computed(() => overview.value?.previous?.kpis ?? null)
type DeltaTone = 'good' | 'bad' | 'neutral' | 'none'
const deltaOf = (current: number | null, previous: number | null, mode: 'spend' | 'leads' | 'cpl'): { text: string; tone: DeltaTone } => {
  if (current == null) return { text: '', tone: 'none' }
  if (previous == null) return { text: '上周期无数据', tone: 'none' }
  if (previous === 0) return current === 0 ? { text: '持平', tone: 'neutral' } : { text: '新增', tone: mode === 'cpl' ? 'bad' : 'good' }
  const pct = (current - previous) / previous * 100
  const arrow = pct >= 0 ? '▲' : '▼'
  const text = `${arrow} ${Math.abs(pct).toFixed(1)}%`
  const up = pct >= 0
  if (mode === 'spend') return { text, tone: 'neutral' }
  if (mode === 'leads') return { text, tone: up ? 'good' : 'bad' }
  return { text, tone: up ? 'bad' : 'good' }
}

const heroStats = computed(() => {
  const k = overview.value?.kpis
  const p = previousKpis.value
  return [
    { label: '消耗', value: formatMoney(k?.spend), delta: deltaOf(numberValue(k?.spend), numberValue(p?.spend), 'spend') },
    { label: 'Leads', value: formatNumber(k?.conversions), delta: deltaOf(numberValue(k?.conversions), numberValue(p?.conversions), 'leads') },
    { label: 'CPL', value: formatMoney(k?.result_cost), delta: deltaOf(numberValue(k?.result_cost), numberValue(p?.result_cost), 'cpl') },
  ]
})
const secondaryMetrics = computed(() => {
  const k = overview.value?.kpis
  const spend = numberValue(k?.spend)
  const clicks = numberValue(k?.clicks)
  return [
    { label: '曝光', value: formatNumber(k?.impressions) },
    { label: '点击', value: formatNumber(k?.clicks) },
    { label: 'CTR', value: formatPercent(k?.ctr) },
    { label: 'CPC', value: clicks && spend != null ? formatMoney(spend / clicks) : '—' },
  ]
})

const totalSpend = computed(() => numberValue(overview.value?.kpis.spend) ?? 0)
const overallCpl = computed(() => numberValue(overview.value?.kpis.result_cost))
const rankingRows = computed(() => {
  const total = totalSpend.value
  return accountRows.value.map(row => {
    const spend = numberValue(row.spend) ?? 0
    const leads = numberValue(row.conversions)
    const cpl = numberValue(row.result_cost)
    let status: { label: string; tone: 'warn' | 'bad' | 'ok' | 'muted' } = { label: '', tone: 'muted' }
    if (spend > 0) {
      if (leads == null || leads === 0) status = { label: '无转化', tone: 'warn' }
      else if (cpl != null && overallCpl.value != null && cpl > overallCpl.value * 1.5) status = { label: 'CPL 偏高', tone: 'bad' }
      else status = { label: '', tone: 'ok' }
    }
    return { ...row, spendShare: total ? spend / total : null, status }
  })
})

const selectedAdsetAccountId = ref('')
const selectedAdsetAccountName = computed(() => accountRows.value.find(row => row.account_id === selectedAdsetAccountId.value)?.account_name ?? selectedAdsetAccountId.value)
const adsetRows = computed(() => {
  const id = selectedAdsetAccountId.value
  if (!id) return []
  return (overview.value?.adsets ?? [])
    .filter(a => a.account_id === id)
    .map(a => ({ ...a }))
    .sort((a, b) => (numberValue(b.spend) ?? -1) - (numberValue(a.spend) ?? -1))
})
const selectAdsetAccount = (id: string) => { selectedAdsetAccountId.value = selectedAdsetAccountId.value === id ? '' : id }

const scaleY = (value: number | null, values: Array<number | null>, top = 48, bottom = 138) => {
  if (value == null) return null
  const present = values.filter((item): item is number => item != null)
  const max = Math.max(...present, 0)
  return max === 0 ? bottom : bottom - (value / max) * (bottom - top)
}
const trendPoints = computed(() => {
  const rows = overview.value?.trend ?? []
  const spendValues = rows.map(row => numberValue(row.spend))
  const leadValues = rows.map(row => numberValue(row.conversions))
  return rows.map((row, index) => {
    const x = rows.length <= 1 ? 475 : 91 + index * (768 / (rows.length - 1))
    const leads = numberValue(row.conversions)
    const leadMax = Math.max(...leadValues.filter((item): item is number => item != null), 0)
    const barHeight = leads == null || leadMax === 0 ? 0 : Math.max(2, (leads / leadMax) * 105)
    return {
      ...row,
      label: formatDate(row.date),
      spendText: formatMoney(row.spend),
      leadsText: formatNumber(row.conversions),
      costText: formatMoney(row.result_cost),
      impressionsText: formatNumber(row.impressions),
      clicksText: formatNumber(row.clicks),
      ctrText: formatPercent(row.ctr),
      x,
      spendY: scaleY(numberValue(row.spend), spendValues),
      barY: 155 - barHeight,
      barHeight,
      tooltipLeft: rows.length <= 1 ? 50 : 5 + index * (90 / (rows.length - 1)),
      hitWidth: Math.min(128, 768 / Math.max(rows.length, 1)),
    }
  })
})
const linePath = (field: 'spendY') => trendPoints.value
  .filter(point => point[field] != null)
  .map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point[field]}`)
  .join('')
const spendPath = computed(() => linePath('spendY'))
const hoveredTrendIndex = ref<number | null>(null)
const selectedTrendIndex = ref<number | null>(null)
const activeTrendIndex = computed(() => hoveredTrendIndex.value ?? selectedTrendIndex.value)
const activeTrendPoint = computed(() => activeTrendIndex.value == null ? null : trendPoints.value[activeTrendIndex.value] ?? null)
const toggleTrendSelection = (index: number) => { selectedTrendIndex.value = selectedTrendIndex.value === index ? null : index }

const dailyDetailRows = computed(() => trendPoints.value.map(point => ({
  date: point.label,
  spend: point.spendText,
  impressions: point.impressionsText,
  clicks: point.clicksText,
  ctr: point.ctrText,
  leads: point.leadsText,
  cpl: point.costText,
})))

const showToast = (message: string) => {
  window.clearTimeout(toastTimer)
  toastMessage.value = message
  toastVisible.value = true
  toastTimer = window.setTimeout(() => { toastVisible.value = false }, 2000)
}
const switchPanel = (item: any) => item.path && router.push(item.path)
const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(item => { item.active = item.id === session.id })
}

const loadOverview = async (isRefresh = false) => {
  if (!connectionId.value) return
  if (isRefresh) refreshing.value = true
  else loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await getMetaDashboardOverview({
      connectionId: connectionId.value,
      accountId: accountId.value || undefined,
      since: dateWindow.value.since,
      until: dateWindow.value.until,
      resultActionType: 'lead',
      clickType: 'inline_link_clicks',
    })
    selectedTrendIndex.value = null
    selectedAdsetAccountId.value = ''
    if (isRefresh) showToast('已刷新本地数据视图')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据加载失败'
    showToast(errorMessage.value)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const loadAccounts = async () => {
  accounts.value = []
  accountId.value = ''
  if (!connectionId.value) return
  const response = await platformApi.getSubAccounts(connectionId.value, { page: 1, page_size: 200, status: 'active' })
  const items = Array.isArray(response) ? response : response.items
  accounts.value = items
  accountId.value = ''
}

const initialize = async () => {
  loading.value = true
  try {
    connections.value = (await platformApi.getAllConnections()).filter(item => item.platform === 'Meta' && item.status === 'active')
    for (const connection of connections.value) {
      connectionId.value = connection.id
      await loadAccounts()
      if (accounts.value.length) break
    }
    await loadOverview()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据加载失败'
  } finally {
    loading.value = false
  }
}
const changePeriod = () => loadOverview()
const changeConnection = async () => { await loadAccounts(); await loadOverview() }
const changeAccount = () => loadOverview()
const handleRefresh = () => loadOverview(true)
const handleSync = () => {
  if (!connectionId.value || syncing.value) return
  syncDialogOpen.value = true
}
const handleSyncCompleted = async (result: MetaAdSetSyncResponse) => {
  const failed = result.accounts.filter(item => item.status === 'failed').length
  const rows = result.accounts.reduce((sum, item) => sum + item.rows_written, 0)
  showToast(failed ? `${result.accounts.length - failed} 个账号成功，${failed} 个失败` : `数据同步完成，写入 ${rows} 条 AdSet 日级事实`)
  await loadOverview()
}

onMounted(initialize)
onBeforeUnmount(() => window.clearTimeout(toastTimer))
</script>

<template>
  <div class="dashboard-shell workspace-page-canvas" :class="{ embedded: props.embedded }">
    <SidebarNav
      v-if="!props.embedded"
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="workspace replay-page">
      <header class="page-bar replay-bar" data-workspace-page-header :class="{ 'workspace-page-header': !props.embedded }">
        <div class="page-title replay-title workspace-page-heading">
          <span class="page-icon workspace-page-heading-icon" aria-hidden="true">
            <span class="material-symbols-outlined">bar_chart</span>
          </span>
          <div class="workspace-page-heading-text">
            <h1>数据概览</h1>
          </div>
        </div>
        <div class="page-actions replay-actions">
          <label class="filter-field">
            <select v-model="period" class="period-select" aria-label="时间范围" @change="changePeriod">
              <option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="90">最近 90 天</option>
            </select>
          </label>
          <label class="filter-field">
            <select v-model="connectionId" class="period-select" aria-label="Meta 连接" @change="changeConnection">
              <option v-if="!connections.length" value="">暂无 Meta 连接</option>
              <option v-for="item in connections" :key="item.id" :value="item.id">{{ item.account_name || 'Meta 连接' }}</option>
            </select>
          </label>
          <label class="filter-field">
            <select v-model="accountId" class="period-select" aria-label="广告账号" @change="changeAccount">
              <option value="">全部 active 账号</option><option v-if="!accounts.length" value="">暂无活跃账号</option>
              <option v-for="item in accounts" :key="item.id" :value="item.sub_account_id.replace(/^act_/, '')">{{ item.name }}</option>
            </select>
          </label>
          <button class="sync-button" :class="{ syncing }" type="button" aria-label="配置数据同步" :disabled="loading || syncing || !connectionId || !accounts.length" @click="handleSync">
            <span class="icon material-symbols-outlined" aria-hidden="true">{{ syncing ? 'progress_activity' : 'cloud_sync' }}</span><span class="sync-label">{{ syncing ? '同步中' : '数据同步' }}</span>
          </button>
          <button class="refresh-button" :class="{ refreshing }" type="button" aria-label="刷新本地数据视图" :disabled="loading || syncing || !connectionId" @click="handleRefresh">
            <span class="icon material-symbols-outlined" aria-hidden="true">refresh</span><span class="refresh-label">刷新视图</span>
          </button>
        </div>
      </header>

      <div class="content replay-content workspace-page-content">
        <div v-if="errorMessage" class="dashboard-feedback error" role="alert">{{ errorMessage }} · 已保留最近一次成功数据</div>
        <div v-else-if="loading" class="dashboard-feedback" role="status">正在读取本地 Meta 数据…</div>
        <div v-else class="dashboard-feedback" :class="{ warning: (overview?.data_quality.accounts_with_rows ?? 0) < (overview?.data_quality.accounts_expected ?? 0) }" role="status"><strong>{{ (overview?.data_quality.accounts_with_rows ?? 0) < (overview?.data_quality.accounts_expected ?? 0) ? '部分数据' : '数据完整' }}</strong><span>{{ overview?.window.since }} 至 {{ overview?.window.until }}</span><span v-if="overview?.data_quality.status === 'accessible_with_no_rows'">当前窗口无投放事实</span><span v-else-if="overview?.window.mixed_currency">多币种金额未合计</span></div>

        <section class="replay-card hero" aria-label="结果总览">
          <div class="hero-stats">
            <article v-for="stat in heroStats" :key="stat.label" class="hero-stat">
              <span class="hero-label">{{ stat.label }}</span>
              <div class="hero-value">{{ stat.value }}</div>
              <span class="hero-delta" :class="stat.delta.tone">{{ stat.delta.text || '—' }}</span>
            </article>
          </div>
          <div class="hero-secondary">
            <span v-for="metric in secondaryMetrics" :key="metric.label" class="hero-secondary-item"><small>{{ metric.label }}</small><b>{{ metric.value }}</b></span>
          </div>
        </section>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>每日趋势</h2><p>Spend / Lead / CPL</p></div><span class="soft-chip">近 {{ period }} 天</span></div>
          <div class="trend-grid">
            <div class="chart-panel">
              <div class="chart-legend"><span class="legend-item"><i class="legend-dot spend"></i>Spend</span><span class="legend-item"><i class="legend-dot conversions"></i>Lead</span></div>
              <div v-if="!trendPoints.length" class="chart-empty">所选窗口暂无日级投放数据</div>
              <svg v-else viewBox="60 24 830 138" preserveAspectRatio="xMidYMid meet" role="img" :aria-label="`近 ${period} 天 Spend 与 Lead 趋势图，CPL 在右侧汇总`">
                <g stroke="#ecebea" stroke-width="1"><path d="M52 32H892M52 73H892M52 114H892M52 155H892" /></g>
                <g fill="#20a464" opacity=".8"><rect v-for="point in trendPoints" :key="`bar-${point.date}`" :x="point.x - 11" :y="point.barY" width="22" :height="point.barHeight" rx="3" /></g>
                <path v-if="spendPath" :d="spendPath" fill="none" stroke="#4f8fe8" stroke-width="1.4" />
                                <g fill="#4f8fe8" stroke="#fff" stroke-width="1"><circle v-for="point in trendPoints" v-show="point.spendY != null" :key="`spend-${point.date}`" :cx="point.x" :cy="point.spendY ?? 0" r="2.1" /></g>
                                <g v-if="activeTrendPoint" class="chart-active-markers" aria-hidden="true">
                  <line :x1="activeTrendPoint.x" :x2="activeTrendPoint.x" y1="24" y2="155" />
                  <rect :x="activeTrendPoint.x - 10" :y="activeTrendPoint.barY" width="20" :height="activeTrendPoint.barHeight" rx="3" />
                  <circle v-if="activeTrendPoint.spendY != null" class="spend" :cx="activeTrendPoint.x" :cy="activeTrendPoint.spendY" r="3.5" />
                </g>
                <rect
                  v-for="(point, index) in trendPoints"
                  :key="`hit-${point.date}`"
                  class="chart-hit-area"
                  :class="{ selected: selectedTrendIndex === index }"
                  :x="point.x - point.hitWidth / 2"
                  y="24"
                  :width="point.hitWidth"
                  height="138"
                  role="button"
                  tabindex="0"
                  :aria-label="`${point.date}，消耗 ${point.spendText}，Lead ${point.leadsText}，CPL ${point.costText}`"
                  @mouseenter="hoveredTrendIndex = index"
                  @mouseleave="hoveredTrendIndex = null"
                  @focus="hoveredTrendIndex = index"
                  @blur="hoveredTrendIndex = null"
                  @click="toggleTrendSelection(index)"
                  @keydown.enter.prevent="toggleTrendSelection(index)"
                  @keydown.space.prevent="toggleTrendSelection(index)"
                />
              </svg>
              <div v-if="activeTrendPoint" class="chart-tooltip" :style="{ left: `${activeTrendPoint.tooltipLeft}%` }" role="status" aria-live="polite">
                <strong>{{ activeTrendPoint.date }}</strong>
                <div><span><i class="legend-dot spend"></i>消耗</span><b>{{ activeTrendPoint.spendText }}</b></div>
                <div><span><i class="legend-dot conversions"></i>Lead</span><b>{{ activeTrendPoint.leadsText }}</b></div>
                <div><span>CPL</span><b>{{ activeTrendPoint.costText }}</b></div>
              </div>
              <div v-if="trendPoints.length" class="chart-axis-labels" aria-hidden="true">
                <button v-for="(point, index) in trendPoints" :key="point.date" type="button" :class="{ active: activeTrendIndex === index, selected: selectedTrendIndex === index }" @mouseenter="hoveredTrendIndex = index" @mouseleave="hoveredTrendIndex = null" @focus="hoveredTrendIndex = index" @blur="hoveredTrendIndex = null" @click="toggleTrendSelection(index)">{{ point.label }}</button>
              </div>
            </div>
          </div>
        </section>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>日明细</h2><p>逐日定位消耗与 Lead 的变化</p></div><span class="soft-chip">{{ dailyDetailRows.length }} 天</span></div>
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>日期</th><th>消耗</th><th>曝光</th><th>点击</th><th>CTR</th><th>Lead</th><th>CPL</th></tr></thead>
              <tbody>
                <tr v-if="!dailyDetailRows.length"><td colspan="7" class="data-empty">所选窗口暂无日级投放数据</td></tr>
                <tr v-for="row in dailyDetailRows" :key="row.date" :class="{ active: selectedTrendIndex === dailyDetailRows.indexOf(row) }">
                  <td>{{ row.date }}</td><td>{{ row.spend }}</td><td>{{ row.impressions }}</td><td>{{ row.clicks }}</td><td>{{ row.ctr }}</td><td>{{ row.leads }}</td><td>{{ row.cpl }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>账号排行</h2><p>按消耗排序，标记无转化或 CPL 偏高的账号</p></div><span class="soft-chip">{{ rankingRows.length }} 个账号</span></div>
          <div class="table-wrap">
            <table class="data-table ranking-table">
              <thead><tr><th>账号</th><th>消耗</th><th>占比</th><th>Lead</th><th>CPL</th><th>点击</th><th>CTR</th><th>状态</th></tr></thead>
              <tbody>
                <tr v-if="!rankingRows.length"><td colspan="8" class="data-empty">当前窗口没有可展示的账号</td></tr>
                <tr v-for="row in rankingRows" :key="row.account_id" :class="{ selected: selectedAdsetAccountId === row.account_id }" @click="selectAdsetAccount(row.account_id)">
                  <td><strong>{{ row.account_name }}</strong><small>{{ row.account_id }}</small></td>
                  <td>{{ formatMoney(row.spend) }}</td>
                  <td><span class="share-track"><i :style="{ width: `${(row.spendShare ?? 0) * 100}%` }"></i></span><small>{{ row.spendShare != null ? formatPercent(row.spendShare) : '—' }}</small></td>
                  <td>{{ formatNumber(row.conversions) }}</td>
                  <td>{{ formatMoney(row.result_cost) }}</td>
                  <td>{{ formatNumber(row.clicks) }}</td>
                  <td>{{ formatPercent(row.ctr) }}</td>
                  <td><span v-if="row.status.label" class="quiet-badge" :class="row.status.tone">{{ row.status.label }}</span><span v-else class="row-dot" :class="row.status.tone"></span></td>
                </tr>
              </tbody>
              <tfoot><tr><td>合计</td><td>{{ formatMoney(overview?.kpis.spend) }}</td><td>100%</td><td>{{ formatNumber(overview?.kpis.conversions) }}</td><td>{{ formatMoney(overview?.kpis.result_cost) }}</td><td>{{ formatNumber(overview?.kpis.clicks) }}</td><td>{{ formatPercent(overview?.kpis.ctr) }}</td><td></td></tr></tfoot>
            </table>
          </div>
        </section>

        <section v-if="selectedAdsetAccountId" class="replay-card">
          <div class="replay-card-head"><div><h2>AdSet 明细</h2><p>{{ selectedAdsetAccountName }} · 当前窗口</p></div><button type="button" class="back-button" @click="selectedAdsetAccountId = ''"><span class="material-symbols-outlined">arrow_back</span>返回全部账号</button></div>
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>AdSet</th><th>Campaign</th><th>消耗</th><th>Lead</th><th>CPL</th><th>点击</th><th>CTR</th></tr></thead>
              <tbody>
                <tr v-if="!adsetRows.length"><td colspan="7" class="data-empty">该账号在当前窗口没有 AdSet 事实</td></tr>
                <tr v-for="row in adsetRows" :key="row.adset_id">
                  <td><strong>{{ row.adset_name }}</strong><small>{{ row.adset_id }}</small></td>
                  <td>{{ row.campaign_name || '—' }}</td>
                  <td>{{ formatMoney(row.spend) }}</td>
                  <td>{{ formatNumber(row.conversions) }}</td>
                  <td>{{ formatMoney(row.result_cost) }}</td>
                  <td>{{ formatNumber(row.clicks) }}</td>
                  <td>{{ formatPercent(row.ctr) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </main>

    <DataSyncDialog :show="syncDialogOpen" :connection-id="connectionId" :accounts="accounts" :current-account-id="accountId || undefined" @close="syncDialogOpen = false" @completed="handleSyncCompleted" />
    <div class="toast" :class="{ show: toastVisible }" role="status" aria-live="polite">{{ toastMessage }}</div>
  </div>
</template>

<style scoped>
.dashboard-shell { height: 100vh; width: 100%; display: flex; overflow: hidden; background: #fff; }
.dashboard-shell.embedded { height: 100%; min-height: 0; }
.dashboard-shell.embedded .replay-page { min-width: 0; }
.dashboard-shell.embedded .replay-bar { align-items: flex-start; flex-direction: column; padding-top: 10px; padding-bottom: 10px; }
.dashboard-shell.embedded .replay-actions { display: grid; width: 100%; grid-template-columns: repeat(2, minmax(0, 1fr)); overflow: visible; padding-bottom: 2px; }
.dashboard-shell.embedded .filter-field .period-select,
.dashboard-shell.embedded .sync-button,
.dashboard-shell.embedded .refresh-button { width: 100%; min-width: 0; }
.dashboard-shell.embedded .replay-content { padding: 12px 12px 52px; }
.dashboard-shell.embedded .hero-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.dashboard-shell.embedded .trend-grid { grid-template-columns: 1fr; }

.replay-page {
  --canvas: var(--workspace-canvas);
  --surface: #f6f5f4; --surface-soft: #fafaf9; --hairline: #e5e3df; --hairline-soft: #ede9e4; --hairline-strong: #c8c4be;
  --ink: #1a1a1a; --charcoal: #37352f; --slate: #5d5b54; --steel: #787671; --stone: #a4a097;
  min-width: 0; flex: 1; overflow-y: auto; overscroll-behavior: contain; scrollbar-color: var(--hairline-strong) transparent; scrollbar-width: thin; background: var(--canvas); color: var(--charcoal);
}

.page-bar { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 clamp(24px,3vw,48px); border-bottom: 1px solid var(--hairline); background: rgba(255,255,255,.86); }
.page-title { display: flex; align-items: center; gap: 12px; }
.page-title .page-icon { width: 26px; height: 26px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 6px; }
.page-title .page-icon .material-symbols-outlined { display: block; width: 16px; height: 16px; font-size: 16px; line-height: 16px; }
.page-title h1 { margin: 0; color: var(--ink); font-size: 16px; font-weight: 600; letter-spacing: -.2px; }
.page-actions { display: flex; align-items: center; gap: 7px; }
.period-select { height: 34px; min-width: 112px; padding: 0 29px 0 10px; border: 1px solid var(--hairline-strong); border-radius: 8px; outline: none; background: #fff; color: var(--slate); font-size: 13px; cursor: pointer; }
.content { width: min(100%,1220px); margin: 0 auto; padding: 30px clamp(24px,3vw,48px) 74px; }

.replay-bar { align-items: center; }
.replay-title { align-items: center; }
.replay-title .page-icon { background: #f6f5f4; color: #37352f; }
.replay-title h1 { font-size: 16px; }
.replay-actions { gap: 8px; }
.filter-field { display: flex; align-items: center; min-width: 0; white-space: nowrap; }
.filter-field .period-select { min-width: 92px; }
.sync-button,.refresh-button { height: 34px; min-width: 116px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background-color .16s ease,border-color .16s ease; }
.sync-button { border: 1px solid var(--hairline-strong); background: #fff; color: var(--charcoal); }
.sync-button:hover { border-color: var(--workspace-action-primary,#137fec); color: var(--workspace-action-primary,#137fec); background: #f7fbff; }
.refresh-button { border: 1px solid var(--workspace-action-primary,#137fec); background: var(--workspace-action-primary,#137fec); color: #fff; }
.refresh-button:hover { border-color: var(--workspace-action-primary-hover,#0f6fcf); background: var(--workspace-action-primary-hover,#0f6fcf); }
.sync-button:disabled,.refresh-button:disabled { border-color: var(--hairline); background: var(--hairline); color: var(--stone); cursor: not-allowed; }
.sync-button .icon,.refresh-button .icon { font-size: 15px; }
.sync-button.syncing .icon,.refreshing .icon { animation: spin .65s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.replay-content { width: 100%; max-width: none; margin: 0; padding-top: 24px; padding-bottom: 64px; }
.dashboard-feedback { display:flex; flex-wrap:wrap; gap:6px 12px; margin-bottom: 10px; padding: 9px 12px; border: 1px solid var(--hairline); border-radius: 8px; background: var(--surface-soft); color: var(--slate); font-size: 12px; }
.dashboard-feedback strong{color:var(--charcoal)}
.dashboard-feedback.warning{border-color:#f0d8a8;background:#fffaf0}
.dashboard-feedback.warning strong{color:#946200}
.dashboard-feedback.error { border-color: #f0c9c9; background: #fff5f5; color: #a33a3a; }
.quiet-badge { display: inline-flex; align-items: center; min-height: 24px; padding: 2px 8px; border: 1px solid var(--hairline); border-radius: 999px; background: #fff; color: var(--steel); font-size: 11px; font-weight: 600; white-space: nowrap; }
button.quiet-badge { cursor: pointer; font-family: inherit; }

.replay-card { margin-top: 16px; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; overflow: hidden; }
.replay-card-head { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--hairline-soft); }
.replay-card-head h2 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.replay-card-head p { margin: 3px 0 0; color: var(--steel); font-size: 12px; }
.soft-chip { display: inline-flex; align-items: center; min-height: 26px; padding: 3px 9px; border-radius: 6px; background: var(--surface); color: var(--slate); font-size: 11px; font-weight: 600; }

.hero { padding: 0; }
.hero-stats { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0; }
.hero-stat { position: relative; padding: 22px 24px; }
.hero-stat:not(:last-child)::after { content: ""; position: absolute; top: 20%; right: 0; bottom: 20%; width: 1px; background: #f0efed; }
.hero-label { color: var(--steel); font-size: 13px; font-weight: 600; }
.hero-value { margin-top: 8px; color: var(--ink); font-size: 30px; line-height: 1.1; font-weight: 650; letter-spacing: -.5px; }
.hero-delta { display: inline-flex; align-items: center; margin-top: 10px; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.hero-delta.good { background: #edf8f0; color: #16804a; }
.hero-delta.bad { background: #fdecec; color: #b4402e; }
.hero-delta.neutral { background: #f0efed; color: var(--slate); }
.hero-delta.none { background: transparent; color: var(--stone); padding-left: 0; }
.hero-secondary { display: flex; flex-wrap: wrap; gap: 0; padding: 12px 24px; border-top: 1px solid var(--hairline-soft); background: var(--surface-soft); }
.hero-secondary-item { display: inline-flex; align-items: baseline; gap: 6px; padding-right: 18px; }
.hero-secondary-item:not(:last-child) { border-right: 1px solid var(--hairline-soft); margin-right: 18px; padding-right: 18px; }
.hero-secondary-item small { color: var(--steel); font-size: 11px; }
.hero-secondary-item b { color: var(--charcoal); font-size: 13px; font-weight: 600; }

.trend-grid { display: grid; grid-template-columns: minmax(0,1fr); gap: 8px; padding: 8px; }
.chart-panel { position: relative; min-width: 0; height: 252px; min-height: 0; padding: 7px 2px 0; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fcfcfb; }
.chart-empty { height: 208px; display: grid; place-items: center; color: var(--stone); font-size: 12px; }
.chart-legend { display: flex; align-items: center; gap: 14px; padding-left: 8px; color: var(--steel); font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 5px; height: 5px; border-radius: 50%; }
.legend-dot.spend { background: #4f8fe8; }.legend-dot.conversions { background: #20a464; }
.chart-panel svg { display: block; width: 100%; height: 202px; margin-top: -2px; overflow: visible; }
.chart-axis-labels { display: flex; align-items: center; justify-content: space-between; height: 24px; padding: 0 3.7%; color: var(--stone); font-size: 11px; line-height: 1; }
.chart-axis-labels button { padding: 3px 2px; border: 0; background: transparent; color: inherit; cursor: pointer; font: inherit; line-height: inherit; }
.chart-axis-labels button.active { color: var(--charcoal); font-weight: 600; }
.chart-axis-labels button.selected { color: #3276cc; }
.chart-hit-area { fill: transparent; cursor: pointer; outline: none; }
.chart-hit-area:focus { fill: rgb(79 143 232 / 4%); }
.chart-active-markers { pointer-events: none; }
.chart-active-markers line { stroke: rgb(100 116 139 / 28%); stroke-width: .75; stroke-dasharray: 3 3; }
.chart-active-markers rect { fill: none; stroke: #20a464; stroke-width: 1.2; }
.chart-active-markers circle { fill: #ffffff; stroke-width: 1.5; }
.chart-active-markers circle.spend { stroke: #4f8fe8; }
.chart-tooltip { position: absolute; z-index: 4; top: 28px; width: 146px; padding: 8px 9px; border: 1px solid var(--hairline); border-radius: 7px; background: rgb(255 255 255 / 96%); box-shadow: rgba(15,15,15,.12) 0 8px 24px; color: var(--charcoal); pointer-events: none; transform: translateX(-50%); }
.chart-tooltip > strong { display: block; margin-bottom: 5px; color: var(--ink); font-size: 12px; }
.chart-tooltip > div { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 19px; color: var(--steel); font-size: 11px; }
.chart-tooltip span { display: inline-flex; align-items: center; gap: 4px; }
.chart-tooltip b { color: var(--charcoal); font-size: 12px; font-weight: 600; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; min-width: 720px; border-collapse: collapse; font-size: 12px; }
.data-table th,.data-table td { height: 42px; padding: 0 12px; border-bottom: 1px solid var(--hairline-soft); text-align: right; white-space: nowrap; }
.data-table th:first-child,.data-table td:first-child { text-align: left; }
.data-table th { height: 36px; color: var(--steel); font-size: 11px; font-weight: 600; background: var(--surface-soft); }
.data-table tbody tr { transition: background-color .12s ease; }
.data-table tbody tr:hover { background: #fafaf9; }
.data-table tbody tr.active { background: #f7fbff; }
.data-table td strong { display: block; color: var(--ink); font-size: 12px; }
.data-table td small { display: block; margin-top: 2px; color: var(--stone); font-size: 10px; }
.data-table tfoot td { height: 42px; border-top: 1px solid var(--hairline-strong); border-bottom: 0; color: var(--ink); font-weight: 600; }
.data-empty { text-align: center!important; color: var(--stone); }

.ranking-table tbody tr { cursor: pointer; }
.ranking-table tbody tr:hover,.ranking-table tbody tr.selected { background: #f7fbff; }
.share-track { display: inline-block; width: 56px; height: 5px; border-radius: 999px; background: var(--hairline-soft); overflow: hidden; vertical-align: middle; margin-right: 6px; }
.share-track i { display: block; height: 100%; border-radius: inherit; background: #4f8fe8; }
.row-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--stone); }
.row-dot.ok { background: #16804a; }
.row-dot.muted { background: var(--stone); }
.quiet-badge.warn { background: #fff6e4; color: #9a6700; border-color: #f0d8a8; }
.quiet-badge.bad { background: #fdecec; color: #b4402e; border-color: #f0c9c9; }

.back-button { display: inline-flex; align-items: center; gap: 4px; height: 30px; padding: 0 10px; border: 1px solid var(--hairline-strong); border-radius: 6px; background: #fff; color: var(--charcoal); font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; }
.back-button:hover { border-color: #8db8ed; background: #f7fbff; }
.back-button .material-symbols-outlined { font-size: 14px; }

.platform-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: stretch; gap: 8px; padding: 10px; }
.platform-card { --accent: #4f8fe8; min-width: 0; align-self: stretch; border: 1px solid var(--hairline); border-radius: 9px; overflow: hidden; background: #fff; }

.toast { position: fixed; z-index: 90; left: 50%; bottom: 52px; max-width: calc(100vw - 32px); padding: 10px 13px; border: 1px solid var(--hairline,#e5e3df); border-radius: 8px; background: #fff; color: #37352f; font-size: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 44px -10px; opacity: 0; pointer-events: none; transform: translate(-50%,8px); transition: opacity .16s ease,transform .16s ease; }
.toast.show { opacity: 1; transform: translate(-50%,0); }

@media (max-width: 1220px) {
  .hero-stats { grid-template-columns: repeat(3,1fr); }
  .platform-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .dashboard-shell:not(.embedded) .replay-title { flex: 0 0 auto; }.dashboard-shell:not(.embedded) .replay-title p { display: none; }.dashboard-shell:not(.embedded) .replay-actions { min-width: 0; overflow-x: auto; }.dashboard-shell:not(.embedded) .filter-field,.dashboard-shell:not(.embedded) .sync-button,.dashboard-shell:not(.embedded) .refresh-button { flex: 0 0 auto; }
  .trend-grid { grid-template-columns: 1fr; }
  .hero-stats { grid-template-columns: repeat(3,1fr); }
}
@media (max-width: 620px) {
  .replay-content { padding: 12px 12px 52px; }
  .dashboard-shell:not(.embedded) .replay-title h1 { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
  .dashboard-shell:not(.embedded) .sync-button,.dashboard-shell:not(.embedded) .refresh-button { width: 34px; min-width: 34px; padding: 0; }
  .dashboard-shell:not(.embedded) .sync-label,.dashboard-shell:not(.embedded) .refresh-label { display: none; }
  .hero-stats { grid-template-columns: repeat(3,1fr); }
  .hero-stat { padding: 14px 12px; }
  .hero-value { font-size: 22px; }
  .hero-secondary { padding: 10px 12px; }
}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
