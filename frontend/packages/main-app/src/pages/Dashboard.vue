<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'
import { getMetaDashboardOverview, type MetaDashboardOverview } from '@/api/dashboard'
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

const selectedAccount = computed(() => accounts.value.find(item => item.sub_account_id.replace(/^act_/, '') === accountId.value))
const metricStatus = computed(() => overview.value?.data_quality.status ?? 'accessible_with_no_rows')
const statusLabel = computed(() => ({
  accessible_with_rows: '数据正常',
  accessible_with_no_rows: '当前窗口无数据',
  accessible_with_zero_delivery: '当前窗口零投放',
  partial_error: '部分数据异常',
}[metricStatus.value]))

const dateWindow = computed(() => {
  const until = new Date()
  const since = new Date(until)
  since.setDate(since.getDate() - Number(period.value) + 1)
  const iso = (value: Date) => value.toISOString().slice(0, 10)
  return { since: iso(since), until: iso(until) }
})

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

const kpis = computed(() => {
  const metrics = overview.value?.kpis
  return [
    { label: '总消耗', value: formatMoney(metrics?.spend), note: overview.value?.window.currency ?? '金额', icon: 'account_balance_wallet' },
    { label: 'Leads', value: formatNumber(metrics?.conversions), note: 'Canonical lead', icon: 'target' },
    { label: 'CPL', value: formatMoney(metrics?.result_cost), note: '单个 Lead 成本', icon: 'attach_money' },
    { label: 'Link CTR', value: formatPercent(metrics?.ctr), note: '链接点击 / 曝光', icon: 'ads_click' },
    { label: 'Link Clicks', value: formatNumber(metrics?.clicks), note: '链接点击', icon: 'touch_app' },
    { label: 'Impressions', value: formatNumber(metrics?.impressions), note: `${overview.value?.trend.length ?? 0} 个数据日`, icon: 'visibility' },
  ]
})

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
  const costValues = rows.map(row => numberValue(row.result_cost))
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
      x,
      spendY: scaleY(numberValue(row.spend), spendValues),
      costY: scaleY(numberValue(row.result_cost), costValues),
      barY: 155 - barHeight,
      barHeight,
      tooltipLeft: rows.length <= 1 ? 50 : 5 + index * (90 / (rows.length - 1)),
      hitWidth: Math.min(128, 768 / Math.max(rows.length, 1)),
    }
  })
})
const linePath = (field: 'spendY' | 'costY') => trendPoints.value
  .filter(point => point[field] != null)
  .map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point[field]}`)
  .join('')
const spendPath = computed(() => linePath('spendY'))
const costPath = computed(() => linePath('costY'))
const hoveredTrendIndex = ref<number | null>(null)
const selectedTrendIndex = ref<number | null>(null)
const activeTrendIndex = computed(() => hoveredTrendIndex.value ?? selectedTrendIndex.value)
const activeTrendPoint = computed(() => activeTrendIndex.value == null ? null : trendPoints.value[activeTrendIndex.value] ?? null)
const toggleTrendSelection = (index: number) => { selectedTrendIndex.value = selectedTrendIndex.value === index ? null : index }

const funnel = computed(() => {
  const metrics = overview.value?.kpis
  const impressions = numberValue(metrics?.impressions)
  const clicks = numberValue(metrics?.clicks)
  const leads = numberValue(metrics?.conversions)
  const width = (value: number | null) => !impressions || value == null ? 0 : Math.min(100, Math.max(value > 0 ? 6 : 0, value / impressions * 100))
  const rate = (value: number | null, base: number | null) => !base || value == null ? '—' : `${(value / base * 100).toFixed(2)}%`
  return [
    { label: '曝光', value: formatNumber(impressions), rate: impressions == null ? '—' : '100%', width: impressions == null ? 0 : 100 },
    { label: '链接点击', value: formatNumber(clicks), rate: rate(clicks, impressions), width: width(clicks) },
    { label: 'Lead', value: formatNumber(leads), rate: rate(leads, clicks), width: width(leads) },
  ]
})

const dailyRows = computed(() => trendPoints.value.map(point => ({ date: point.label, spend: point.spendText, leads: point.leadsText, cost: point.costText })))

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
  accountId.value = items[0]?.sub_account_id.replace(/^act_/, '') ?? ''
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
              <option v-if="!accounts.length" value="">暂无活跃账号</option>
              <option v-for="item in accounts" :key="item.id" :value="item.sub_account_id.replace(/^act_/, '')">{{ item.name }}</option>
            </select>
          </label>
          <button class="refresh-button" :class="{ refreshing }" type="button" aria-label="刷新本地数据视图" :disabled="loading || !connectionId" @click="handleRefresh">
            <span class="icon material-symbols-outlined" aria-hidden="true">refresh</span><span class="refresh-label">刷新视图</span>
          </button>
        </div>
      </header>

      <div class="content replay-content workspace-page-content">
        <div v-if="errorMessage" class="dashboard-feedback error" role="alert">{{ errorMessage }} · 已保留最近一次成功数据</div>
        <div v-else-if="loading" class="dashboard-feedback" role="status">正在读取本地 Meta 数据…</div>
        <div v-else-if="metricStatus !== 'accessible_with_rows'" class="dashboard-feedback" role="status">{{ statusLabel }}，所选窗口不会用 0 替代缺失数据。</div>

        <section class="replay-kpis" aria-label="核心指标" :aria-busy="loading">
          <article v-for="kpi in kpis" :key="kpi.label" class="replay-kpi">
            <div class="kpi-head"><span>{{ kpi.label }}</span><span class="icon material-symbols-outlined" aria-hidden="true">{{ kpi.icon }}</span></div>
            <div class="kpi-value">{{ kpi.value }}</div>
            <span class="kpi-delta">{{ kpi.note }}</span>
          </article>
        </section>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>趋势监控</h2><p>消耗、Lead 与 CPL 随时间变化</p></div><span class="soft-chip">近 {{ period }} 天 · {{ overview?.trend.length ?? 0 }} 个数据日</span></div>
          <div class="trend-grid">
            <div class="chart-panel">
              <div class="chart-legend"><span class="legend-item"><i class="legend-dot spend"></i>消耗</span><span class="legend-item"><i class="legend-dot conversions"></i>Lead</span><span class="legend-item"><i class="legend-dot roas"></i>CPL</span></div>
              <div v-if="!trendPoints.length" class="chart-empty">所选窗口暂无日级投放数据</div>
              <svg v-else viewBox="60 24 830 138" preserveAspectRatio="xMidYMid meet" role="img" :aria-label="`近 ${period} 天消耗、Lead 和 CPL 趋势图`">
                <g stroke="#ecebea" stroke-width="1"><path d="M52 32H892M52 73H892M52 114H892M52 155H892" /></g>
                <g fill="#20a464" opacity=".8"><rect v-for="point in trendPoints" :key="`bar-${point.date}`" :x="point.x - 11" :y="point.barY" width="22" :height="point.barHeight" rx="3" /></g>
                <path v-if="spendPath" :d="spendPath" fill="none" stroke="#4f8fe8" stroke-width="1.4" />
                <path v-if="costPath" :d="costPath" fill="none" stroke="#dd7d00" stroke-width="1.35" />
                <g fill="#4f8fe8" stroke="#fff" stroke-width="1"><circle v-for="point in trendPoints" v-show="point.spendY != null" :key="`spend-${point.date}`" :cx="point.x" :cy="point.spendY ?? 0" r="2.1" /></g>
                <g fill="#dd7d00" stroke="#fff" stroke-width="1"><circle v-for="point in trendPoints" v-show="point.costY != null" :key="`cost-${point.date}`" :cx="point.x" :cy="point.costY ?? 0" r="2.1" /></g>
                <g v-if="activeTrendPoint" class="chart-active-markers" aria-hidden="true">
                  <line :x1="activeTrendPoint.x" :x2="activeTrendPoint.x" y1="24" y2="155" />
                  <rect :x="activeTrendPoint.x - 10" :y="activeTrendPoint.barY" width="20" :height="activeTrendPoint.barHeight" rx="3" />
                  <circle v-if="activeTrendPoint.spendY != null" class="spend" :cx="activeTrendPoint.x" :cy="activeTrendPoint.spendY" r="3.5" />
                  <circle v-if="activeTrendPoint.costY != null" class="roas" :cx="activeTrendPoint.x" :cy="activeTrendPoint.costY" r="3.5" />
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
                <div><span><i class="legend-dot roas"></i>CPL</span><b>{{ activeTrendPoint.costText }}</b></div>
              </div>
              <div v-if="trendPoints.length" class="chart-axis-labels" aria-hidden="true">
                <button v-for="(point, index) in trendPoints" :key="point.date" type="button" :class="{ active: activeTrendIndex === index, selected: selectedTrendIndex === index }" @mouseenter="hoveredTrendIndex = index" @mouseleave="hoveredTrendIndex = null" @focus="hoveredTrendIndex = index" @blur="hoveredTrendIndex = null" @click="toggleTrendSelection(index)">{{ point.label }}</button>
              </div>
            </div>
            <aside class="chart-summary">
              <div class="summary-box"><span>筛选消耗</span><strong>{{ formatMoney(overview?.kpis.spend) }}</strong><small>{{ selectedAccount?.name || '当前账号' }}</small></div>
              <div class="summary-box"><span>Lead</span><strong>{{ formatNumber(overview?.kpis.conversions) }}</strong><small>Canonical lead，不叠加派生事件</small></div>
              <div class="summary-box"><span>CPL</span><strong>{{ formatMoney(overview?.kpis.result_cost) }}</strong><small>总消耗 / Lead</small></div>
            </aside>
          </div>
        </section>

        <div class="replay-split">
          <section class="replay-card">
            <div class="replay-card-head"><div><h2>归因转化路径</h2><p>Meta 归因事件计数，不代表跨阶段用户去重</p></div><span class="soft-chip">Lead</span></div>
            <div class="compact-body funnel-list">
              <div v-for="item in funnel" :key="item.label" class="funnel-row"><strong>{{ item.label }}</strong><span class="funnel-track"><i :style="{ width: `${item.width}%` }"></i></span><strong>{{ item.value }}</strong><small>{{ item.rate }}</small></div>
            </div>
          </section>
          <section class="replay-card">
            <div class="replay-card-head"><div><h2>分群表现</h2><p>国家 / 设备 / 版位效率对比</p></div><span class="soft-chip">待采集</span></div>
            <div class="compact-body segment-empty">
              <span class="material-symbols-outlined" aria-hidden="true">data_info_alert</span>
              <div><strong>尚未采集 Breakdown</strong><small>当前基础事实不包含国家、设备和版位，页面不会使用模拟分群数据。</small></div>
            </div>
          </section>
        </div>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>平台表现</h2><p>当前 Meta 广告账号的真实日级表现</p></div><span class="soft-chip">Meta Account</span></div>
          <div class="platform-grid single">
            <article class="platform-card">
              <div class="platform-top">
                <div class="platform-heading"><div><h3>Meta</h3><p>{{ selectedAccount?.name || '未选择广告账号' }}</p></div><span class="soft-chip" :class="{ 'status-warning': metricStatus !== 'accessible_with_rows' }">{{ statusLabel }}</span></div>
                <div class="platform-status"><span class="material-symbols-outlined" aria-hidden="true">{{ metricStatus === 'accessible_with_rows' ? 'check_circle' : 'info' }}</span><div><strong>{{ statusLabel }}</strong><small>刷新视图只读取本地事实，不会请求 Meta 官方接口。</small></div></div>
                <div class="platform-metrics">
                  <div class="platform-metric"><span>Spend</span><strong>{{ formatMoney(overview?.kpis.spend) }}</strong></div><div class="platform-metric"><span>Lead</span><strong>{{ formatNumber(overview?.kpis.conversions) }}</strong></div><div class="platform-metric"><span>CPL</span><strong>{{ formatMoney(overview?.kpis.result_cost) }}</strong></div><div class="platform-metric"><span>Link CTR</span><strong>{{ formatPercent(overview?.kpis.ctr) }}</strong></div>
                </div>
              </div>
              <div class="daily-table" role="table" aria-label="Meta 账号分天表现">
                <div class="daily-table-head" role="row"><span>日期</span><span>消耗</span><span>Lead</span><span>CPL</span></div>
                <div v-if="!dailyRows.length" class="daily-empty">所选窗口暂无日级数据</div>
                <div v-for="row in dailyRows" :key="row.date" class="daily-table-row workspace-data-row" role="row"><span>{{ row.date }}</span><strong>{{ row.spend }}</strong><span>{{ row.leads }}</span><span class="daily-roas">{{ row.cost }}</span></div>
              </div>
            </article>
          </div>
        </section>
      </div>
    </main>

    <div class="toast" :class="{ show: toastVisible }" role="status" aria-live="polite">{{ toastMessage }}</div>
  </div>
</template>

<style scoped>
.dashboard-shell {
  height: 100vh;
  width: 100%;
  display: flex;
  overflow: hidden;
  background: #fff;
}

.dashboard-shell.embedded {
  height: 100%;
  min-height: 0;
}

.dashboard-shell.embedded .replay-page {
  min-width: 0;
}

.dashboard-shell.embedded .replay-bar {
  align-items: flex-start;
  flex-direction: column;
  padding-top: 10px;
  padding-bottom: 10px;
}

.dashboard-shell.embedded .replay-actions {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  overflow: visible;
  padding-bottom: 2px;
}

.dashboard-shell.embedded .filter-field .period-select,
.dashboard-shell.embedded .refresh-button {
  width: 100%;
  min-width: 0;
}

.dashboard-shell.embedded .replay-content {
  padding: 12px 12px 52px;
}

.dashboard-shell.embedded .replay-kpis {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-shell.embedded .replay-kpi {
  border-bottom: 1px solid #f3f2f0;
}

.dashboard-shell.embedded .replay-kpi:nth-child(2n)::after {
  display: none;
}

.dashboard-shell.embedded .replay-kpi:nth-last-child(-n + 2) {
  border-bottom: 0;
}

.dashboard-shell.embedded .trend-grid,
.dashboard-shell.embedded .replay-split {
  grid-template-columns: 1fr;
}

.dashboard-shell.embedded .chart-summary {
  width: 100%;
  height: auto;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-template-rows: 1fr;
}

.dashboard-shell.embedded .summary-box {
  border-right: 1px solid var(--hairline-soft);
  border-bottom: 0;
}

.dashboard-shell.embedded .summary-box:last-child {
  border-right: 0;
}

.dashboard-shell.embedded .segment-grid,
.dashboard-shell.embedded .platform-grid {
  grid-template-columns: 1fr;
}

.dashboard-shell.embedded .platform-card {
  display: block;
}

.dashboard-shell.embedded .platform-card .platform-top {
  border-right: 0;
}

.replay-page {
  --canvas: var(--workspace-canvas);
  --surface: #f6f5f4;
  --surface-soft: #fafaf9;
  --hairline: #e5e3df;
  --hairline-soft: #ede9e4;
  --hairline-strong: #c8c4be;
  --ink: #1a1a1a;
  --charcoal: #37352f;
  --slate: #5d5b54;
  --steel: #787671;
  --stone: #a4a097;
  --green-soft: #d9f3e1;
  min-width: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--hairline-strong) transparent;
  scrollbar-width: thin;
  background: var(--canvas);
  color: var(--charcoal);
}

.page-bar { min-height: 54px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 clamp(24px,3vw,48px); border-bottom: 1px solid var(--hairline); background: rgba(255,255,255,.86); }
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
.refresh-button { height: 34px; min-width: 116px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px; border: 1px solid var(--workspace-action-primary,#137fec); border-radius: 8px; background: var(--workspace-action-primary,#137fec); color: #fff; font-size: 13px; font-weight: 600; cursor: pointer; transition: background-color .16s ease,border-color .16s ease; }
.refresh-button:hover { border-color: var(--workspace-action-primary-hover,#0f6fcf); background: var(--workspace-action-primary-hover,#0f6fcf); }
.refresh-button:disabled { border-color: var(--hairline); background: var(--hairline); color: var(--stone); cursor: not-allowed; }
.refresh-button .icon { font-size: 15px; }
.refreshing .icon { animation: spin .65s ease; }
@keyframes spin { to { transform: rotate(360deg); } }

.replay-content { width: 100%; max-width: none; margin: 0; padding-top: 24px; padding-bottom: 64px; }
.dashboard-feedback { margin-bottom: 10px; padding: 9px 12px; border: 1px solid var(--hairline); border-radius: 8px; background: var(--surface-soft); color: var(--slate); font-size: 12px; }
.dashboard-feedback.error { border-color: #f0c9c9; background: #fff5f5; color: #a33a3a; }
.quiet-badge { display: inline-flex; align-items: center; min-height: 28px; padding: 4px 10px; border: 1px solid var(--hairline); border-radius: 999px; background: #fff; color: var(--steel); font-size: 11px; font-weight: 600; white-space: nowrap; }
button.quiet-badge { cursor: pointer; font-family: inherit; }

.replay-kpis { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 0; margin-top: 0; border: 1px solid var(--hairline); border-radius: 12px; overflow: hidden; background: #fff; }
.replay-kpi { position: relative; min-width: 0; padding: 18px 20px; border: 0; border-radius: 0; background: #fff; }
.replay-kpi:not(:last-child)::after { content: ""; position: absolute; top: 20%; right: 0; bottom: 20%; width: 1px; background: #f0efed; }
.kpi-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--steel); font-size: 13px; font-weight: 600; }
.kpi-head .icon { color: var(--steel); font-size: 18px; font-weight: 400; }
.kpi-value { margin-top: 9px; color: var(--ink); font-size: 26px; line-height: 1.1; font-weight: 650; letter-spacing: -.45px; }
.kpi-delta { width: fit-content; display: inline-flex; align-items: center; margin-top: 9px; padding: 3px 7px; border-radius: 4px; background: #edf8f0; color: #16804a; font-size: 11px; font-weight: 600; }
.kpi-delta.warn { background: #fff6e4; color: #9a6700; }

.replay-card { margin-top: 16px; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; overflow: hidden; }
.replay-card-head { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--hairline-soft); }
.replay-card-head h2 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.replay-card-head p { margin: 3px 0 0; color: var(--steel); font-size: 12px; }
.soft-chip { display: inline-flex; align-items: center; min-height: 26px; padding: 3px 9px; border-radius: 6px; background: var(--surface); color: var(--slate); font-size: 11px; font-weight: 600; }

.trend-grid { display: grid; grid-template-columns: minmax(0,1fr) 180px; align-items: start; gap: 8px; padding: 8px; }
.chart-panel { position: relative; min-width: 0; height: 252px; min-height: 0; padding: 7px 2px 0; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fcfcfb; }
.chart-empty { height: 208px; display: grid; place-items: center; color: var(--stone); font-size: 12px; }
.chart-legend { display: flex; align-items: center; gap: 14px; padding-left: 8px; color: var(--steel); font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 5px; height: 5px; border-radius: 50%; }
.legend-dot.spend { background: #4f8fe8; }.legend-dot.conversions { background: #20a464; }.legend-dot.roas { background: #dd7d00; }
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
.chart-active-markers circle.roas { stroke: #dd7d00; }
.chart-tooltip { position: absolute; z-index: 4; top: 28px; width: 146px; padding: 8px 9px; border: 1px solid var(--hairline); border-radius: 7px; background: rgb(255 255 255 / 96%); box-shadow: rgba(15,15,15,.12) 0 8px 24px; color: var(--charcoal); pointer-events: none; transform: translateX(-50%); }
.chart-tooltip > strong { display: block; margin-bottom: 5px; color: var(--ink); font-size: 12px; }
.chart-tooltip > div { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 19px; color: var(--steel); font-size: 11px; }
.chart-tooltip span { display: inline-flex; align-items: center; gap: 4px; }
.chart-tooltip b { color: var(--charcoal); font-size: 12px; font-weight: 600; }
.chart-summary { height: 252px; display: grid; grid-template-rows: repeat(3,1fr); gap: 0; border: 1px solid var(--hairline); border-radius: 8px; overflow: hidden; background: var(--surface); }
.summary-box { min-height: 0; display: flex; flex-direction: column; justify-content: center; padding: 10px 12px; border-bottom: 1px solid #f0efed; }
.summary-box:last-child { border-bottom: 0; }
.summary-box span { color: var(--steel); font-size: 12px; }
.summary-box strong { display: block; margin: 5px 0 2px; color: var(--ink); font-size: 20px; line-height: 1.1; }
.summary-box small { color: var(--steel); font-size: 11px; }

.replay-split { display: grid; grid-template-columns: .86fr 1.14fr; align-items: stretch; gap: 12px; }
.replay-split > .replay-card { align-self: stretch; }
.compact-body { padding: 10px 12px 12px; }
.funnel-list { display: grid; gap: 11px; }
.funnel-row { display: grid; grid-template-columns: 52px minmax(0,1fr) 72px 46px; align-items: center; gap: 10px; font-size: 12px; }
.funnel-track { height: 6px; border-radius: 999px; background: #efefed; overflow: hidden; }
.funnel-track i { display: block; height: 100%; border-radius: inherit; background: #4f8fe8; }
.funnel-row strong { font-size: 12px; }.funnel-row small { color: var(--steel); font-size: 11px; }
.segment-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 7px; }
.segment-row { min-height: 58px; display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fff; }
.segment-row strong { display: block; color: var(--ink); font-size: 13px; }.segment-row small { display: block; margin-top: 3px; color: var(--steel); font-size: 12px; }
.segment-empty { min-height: 126px; display: flex; align-items: center; justify-content: center; gap: 12px; color: var(--stone); text-align: left; }
.segment-empty > .material-symbols-outlined { font-size: 24px; }.segment-empty strong { display: block; color: var(--slate); font-size: 13px; }.segment-empty small { display: block; max-width: 340px; margin-top: 4px; color: var(--steel); font-size: 12px; line-height: 1.45; }

.platform-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: stretch; gap: 8px; padding: 10px; }
.platform-grid.single { grid-template-columns: minmax(0,1fr); }
.platform-card { --accent: #4f8fe8; min-width: 0; align-self: stretch; border: 1px solid var(--hairline); border-radius: 9px; overflow: hidden; background: #fff; }
.platform-card.google { --accent: #dd7d00; }.platform-card.tiktok { --accent: #16a05d; }
.platform-top { padding: 10px; }
.platform-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.platform-heading h3 { margin: 0; color: var(--ink); font-size: 14px; }.platform-heading p { margin: 3px 0 0; color: var(--steel); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.platform-status { display: flex; align-items: center; gap: 9px; margin-top: 9px; padding: 9px 10px; border-radius: 7px; background: var(--surface-soft); color: var(--steel); }
.platform-status > .material-symbols-outlined { color: #16804a; font-size: 20px; }.platform-status strong { display: block; color: var(--charcoal); font-size: 12px; }.platform-status small { display: block; margin-top: 2px; font-size: 11px; }.soft-chip.status-warning { background: #fff6e4; color: #9a6700; }
.platform-health { display: grid; grid-template-columns: 50px 1fr; align-items: center; gap: 9px; margin-top: 9px; }
.gauge { width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; background: conic-gradient(var(--accent) calc(var(--score)*1%),var(--hairline) 0); position: relative; }
.gauge::after { content: ""; position: absolute; inset: 6px; border-radius: 50%; background: #fff; }.gauge strong { position: relative; z-index: 1; font-size: 12px; }
.health-copy { min-width: 0; color: var(--steel); font-size: 11px; }.health-bar { height: 5px; margin-top: 6px; border-radius: 999px; background: var(--hairline-soft); overflow: hidden; }.health-bar i { display: block; width: calc(var(--score)*1%); height: 100%; border-radius: inherit; background: var(--accent); }
.platform-metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 0; margin-top: 9px; border: 1px solid var(--hairline-soft); border-radius: 6px; overflow: hidden; background: var(--surface-soft); }
.platform-metric { position: relative; padding: 7px 8px; }.platform-metric:not(:last-child)::after { content: ""; position: absolute; top: 22%; right: 0; bottom: 22%; width: 1px; background: #f0efed; }
.platform-metric span { display: block; color: var(--steel); font-size: 11px; }.platform-metric strong { display: block; margin-top: 3px; color: var(--ink); font-size: 13px; }
.daily-table { margin: 0 8px 8px; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 7px; background: #fff; }
.daily-table-head,.daily-table-row { display: grid; grid-template-columns: .8fr 1.15fr .9fr .8fr; align-items: center; gap: 8px; min-height: 30px; padding: 0 10px; }
.daily-table-head { min-height: 34px; background: var(--surface-soft); color: var(--steel); font-size: 11px; font-weight: 600; }.daily-table-row { min-height: 38px; border-top: 1px solid #f1f0ee; background: #fff; color: var(--slate); font-size: 12px; }.daily-table-row:hover { background: #fafaf9; }.daily-table-row strong { color: var(--ink); font-size: 12px; font-weight: 600; }
.daily-empty { min-height: 72px; display: grid; place-items: center; border-top: 1px solid var(--hairline-soft); color: var(--stone); font-size: 12px; }
.daily-roas { display: inline-flex; align-items: center; gap: 5px; color: var(--ink); font-weight: 600; }.daily-roas::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--accent); }

.toast { position: fixed; z-index: 90; left: 50%; bottom: 52px; max-width: calc(100vw - 32px); padding: 10px 13px; border: 1px solid var(--hairline,#e5e3df); border-radius: 8px; background: #fff; color: #37352f; font-size: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 44px -10px; opacity: 0; pointer-events: none; transform: translate(-50%,8px); transition: opacity .16s ease,transform .16s ease; }
.toast.show { opacity: 1; transform: translate(-50%,0); }

@media (max-width: 1220px) {
  .replay-kpis { grid-template-columns: repeat(3,1fr); }.replay-kpi:nth-child(3)::after,.replay-kpi:nth-child(6)::after { display: none; }.replay-kpi:nth-child(-n+3) { border-bottom: 1px solid #f3f2f0; }
  .platform-grid { grid-template-columns: 1fr; }.platform-card { display: grid; grid-template-columns: 310px minmax(0,1fr); align-items: start; }.platform-card .platform-top { border-right: 1px solid var(--hairline-soft); }.platform-card .daily-table { margin: 8px; }
}
@media (max-width: 900px) {
  .dashboard-shell:not(.embedded) .replay-title { flex: 0 0 auto; }.dashboard-shell:not(.embedded) .replay-title p { display: none; }.dashboard-shell:not(.embedded) .replay-actions { min-width: 0; overflow-x: auto; }.dashboard-shell:not(.embedded) .filter-field,.dashboard-shell:not(.embedded) .refresh-button { flex: 0 0 auto; }
  .trend-grid,.replay-split { grid-template-columns: 1fr; }.chart-summary { width: 100%; height: auto; grid-template-columns: repeat(3,1fr); grid-template-rows: 1fr; }.summary-box { border-right: 1px solid var(--hairline-soft); border-bottom: 0; }.summary-box:last-child { border-right: 0; }
  .platform-card { display: block; }.platform-card .platform-top { border-right: 0; }
}
@media (max-width: 620px) {
  .replay-content { padding: 12px 12px 52px; }.replay-kpis { grid-template-columns: repeat(2,1fr); }.replay-kpi { border-bottom: 1px solid #f3f2f0; }.replay-kpi:nth-child(3)::after { display: block; }.replay-kpi:nth-child(2n)::after { display: none; }.replay-kpi:nth-last-child(-n+2) { border-bottom: 0; }
  .dashboard-shell:not(.embedded) .replay-title h1 { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }.dashboard-shell:not(.embedded) .refresh-button { width: 31px; min-width: 31px; padding: 0; }.dashboard-shell:not(.embedded) .refresh-label { display: none; }
  .segment-grid { grid-template-columns: 1fr; }.chart-summary { grid-template-columns: 1fr; }.summary-box { border-right: 0; border-bottom: 1px solid var(--hairline-soft); }.summary-box:last-child { border-bottom: 0; }.funnel-row { grid-template-columns: 36px minmax(0,1fr) 48px; }.funnel-row small { display: none; }
}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
