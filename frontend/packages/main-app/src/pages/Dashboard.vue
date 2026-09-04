<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import DataSyncDialog from '@/components/dashboard/DataSyncDialog.vue'
import AnalysisMetricTable, { type AnalysisTableRow } from '@/components/dashboard/AnalysisMetricTable.vue'
import MetricSelector from '@/components/dashboard/MetricSelector.vue'
import { formatTrendMetricValue, trendMetricOptions, type TrendMetric } from '@/data/trendMetrics'
import { navItems } from '@/config/navigation'
import { getMetaDashboardOverview, type DashboardMetrics, type MetaAdSetSyncResponse, type MetaDashboardOverview } from '@/api/dashboard'
import { platformApi, type PlatformConnectionResponse, type SubAccountResponse } from '@/api/platform'

const props = withDefaults(defineProps<{ embedded?: boolean; workspaceOverview?: MetaDashboardOverview | null }>(), { embedded: false, workspaceOverview: null })
const router = useRouter()
const activeSession = ref('sess-g001')
const period = ref('7')
const dateInput = (date: Date) => date.toISOString().slice(0, 10)
const initialUntil = new Date()
const initialSince = new Date(initialUntil)
initialSince.setDate(initialUntil.getDate() - 6)
const dateStart = ref(dateInput(initialSince))
const dateEnd = ref(dateInput(initialUntil))
const dateStartInput = ref<HTMLInputElement | null>(null)
const dateEndInput = ref<HTMLInputElement | null>(null)
const connectionId = ref('')
const accountId = ref('')
const objective = ref('')
const connections = ref<PlatformConnectionResponse[]>([])
const accounts = ref<SubAccountResponse[]>([])
const overview = ref<MetaDashboardOverview | null>(props.workspaceOverview)
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

const OBJECTIVE_SALES = 'OUTCOME_SALES'
const OBJECTIVE_LEADS = 'OUTCOME_LEADS'

const numberValue = (value: number | null | undefined) => value == null ? null : Number(value)
const formatNumber = (value: number | null | undefined, maximumFractionDigits = 0) => {
  const numeric = numberValue(value)
  return numeric == null ? '—' : new Intl.NumberFormat('zh-CN', { maximumFractionDigits }).format(numeric)
}
const formatMoney = (value: number | null | undefined) => {
  const numeric = numberValue(value)
  if (overview.value?.window?.mixed_currency) return '多币种'
  if (numeric == null) return '—'
  const currency = overview.value?.window?.currency
  if (!currency) return formatNumber(numeric, 2)
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(numeric)
}
const formatPercent = (value: number | null | undefined, digits = 2) => {
  const numeric = numberValue(value)
  return numeric == null ? '—' : `${(numeric * 100).toFixed(digits)}%`
}
const formatRoas = (value: number | null | undefined) => {
  const numeric = numberValue(value)
  return numeric == null ? '—' : `${numeric.toFixed(2)}x`
}
const formatDate = (value: string) => value.slice(5)
const formatDateLabel = (value: string) => value.split('-').join('/')

const openDatePicker = (input: HTMLInputElement | null) => {
  if (!input) return
  input.focus()
  try {
    input.showPicker?.()
  } catch {
    // Native input activation remains available when showPicker is unsupported.
  }
}

const windowForDays = (days: number) => {
  const until = new Date()
  const since = new Date(until)
  since.setDate(since.getDate() - days + 1)
  return { since: dateInput(since), until: dateInput(until) }
}
const dateWindow = computed(() => ({ since: dateStart.value, until: dateEnd.value }))
const dateRangeDays = computed(() => {
  const since = Date.parse(`${dateStart.value}T00:00:00Z`)
  const until = Date.parse(`${dateEnd.value}T00:00:00Z`)
  return Number.isFinite(since) && Number.isFinite(until) ? Math.max(1, Math.round((until - since) / 86400000) + 1) : 1
})

const objectives = computed(() => overview.value?.objectives ?? [])
const scope = computed(() => overview.value?.scope ?? null)
const isSales = computed(() => objective.value === OBJECTIVE_SALES)
const isLeads = computed(() => objective.value === OBJECTIVE_LEADS)
const supportedObjective = computed(() => isSales.value || isLeads.value)

// Ratio metrics are recomputed from range totals, never averaged across accounts.
const derive = (metrics: DashboardMetrics | null | undefined) => {
  const spend = numberValue(metrics?.spend)
  const revenue = numberValue(metrics?.conversion_value)
  const results = numberValue(metrics?.conversions)
  const clicks = numberValue(metrics?.clicks)
  const impressions = numberValue(metrics?.impressions)
  return {
    spend,
    revenue,
    results,
    clicks,
    impressions,
    roas: numberValue(metrics?.roas) ?? (spend && revenue != null ? revenue / spend : null),
    cost: numberValue(metrics?.result_cost) ?? (results && spend != null ? spend / results : null),
    aov: results && revenue != null ? revenue / results : null,
    ctr: numberValue(metrics?.ctr),
    cpc: clicks && spend != null ? spend / clicks : null,
    cpm: impressions && spend != null ? spend / impressions * 1000 : null,
  }
}
const current = computed(() => derive(overview.value?.kpis))
const previous = computed(() => derive(overview.value?.previous?.kpis))

type DeltaTone = 'good' | 'bad' | 'neutral' | 'none'
type DeltaDirection = 'higher_is_better' | 'lower_is_better' | 'neutral'
const deltaOf = (currentValue: number | null, previousValue: number | null, direction: DeltaDirection): { text: string; tone: DeltaTone } => {
  if (currentValue == null) return { text: '', tone: 'none' }
  if (previousValue == null) return { text: '上周期无数据', tone: 'none' }
  if (previousValue === 0) return currentValue === 0 ? { text: '持平', tone: 'neutral' } : { text: '新增', tone: direction === 'lower_is_better' ? 'bad' : 'good' }
  const pct = (currentValue - previousValue) / previousValue * 100
  const text = `${pct >= 0 ? '▲' : '▼'} ${Math.abs(pct).toFixed(1)}%`
  if (direction === 'neutral') return { text, tone: 'neutral' }
  const improving = direction === 'higher_is_better' ? pct >= 0 : pct < 0
  return { text, tone: improving ? 'good' : 'bad' }
}

// Each objective declares its own success metrics. Sales spend is never divided
// by leads, and lead spend is never reported as revenue.
const resultStats = computed(() => {
  const now = current.value
  const before = previous.value
  if (isSales.value) {
    return [
      { label: '花费', value: formatMoney(now.spend), delta: deltaOf(now.spend, before.spend, 'neutral'), primary: false },
      { label: '收入', value: formatMoney(now.revenue), delta: deltaOf(now.revenue, before.revenue, 'higher_is_better'), primary: true },
      { label: 'ROAS', value: formatRoas(now.roas), delta: deltaOf(now.roas, before.roas, 'higher_is_better'), primary: true },
      { label: '订单', value: formatNumber(now.results), delta: deltaOf(now.results, before.results, 'higher_is_better'), primary: false },
      { label: '客单价', value: formatMoney(now.aov), delta: deltaOf(now.aov, before.aov, 'higher_is_better'), primary: false },
      { label: '每单成本', value: formatMoney(now.cost), delta: deltaOf(now.cost, before.cost, 'lower_is_better'), primary: false }
    ]
  }
  return [
    { label: '花费', value: formatMoney(now.spend), delta: deltaOf(now.spend, before.spend, 'neutral'), primary: false },
    { label: 'Leads', value: formatNumber(now.results), delta: deltaOf(now.results, before.results, 'higher_is_better'), primary: true },
    { label: 'CPL', value: formatMoney(now.cost), delta: deltaOf(now.cost, before.cost, 'lower_is_better'), primary: true },
    { label: '链接点击', value: formatNumber(now.clicks), delta: deltaOf(now.clicks, before.clicks, 'neutral'), primary: false },
    { label: '点击到 Lead', value: formatPercent(now.clicks && now.results != null ? now.results / now.clicks : null), delta: { text: '', tone: 'none' }, primary: false },
    { label: 'CPC', value: formatMoney(now.cpc), delta: deltaOf(now.cpc, before.cpc, 'lower_is_better'), primary: false },
  ]
})
const trafficMetrics = computed(() => {
  const now = current.value
  return [
    { label: '曝光', value: formatNumber(now.impressions) },
    { label: '链接点击', value: formatNumber(now.clicks) },
    { label: 'CTR', value: formatPercent(now.ctr) },
    { label: 'CPM', value: formatMoney(now.cpm) },
    { label: 'CPC', value: formatMoney(now.cpc) },
  ]
})

const funnelSteps = computed(() => {
  const steps = overview.value?.funnel ?? []
  const top = numberValue(steps[0]?.value) ?? 0
  return steps.map(step => ({
    ...step,
    valueText: formatNumber(step.value),
    fromPreviousText: step.rate_from_previous == null ? null : formatPercent(step.rate_from_previous, 1),
    width: top > 0 ? Math.max((numberValue(step.value) ?? 0) / top * 100, 1.5) : 0,
  }))
})
const biggestDropStep = computed(() => {
  const candidates = funnelSteps.value.filter(step => step.rate_from_previous != null)
  if (!candidates.length) return null
  return candidates.reduce((worst, step) => (numberValue(step.rate_from_previous) ?? 1) < (numberValue(worst.rate_from_previous) ?? 1) ? step : worst)
})

const scaleY = (value: number | null, values: Array<number | null>, top = 48, bottom = 138) => {
  if (value == null) return null
  const present = values.filter((item): item is number => item != null)
  const max = Math.max(...present, 0)
  return max === 0 ? bottom : bottom - (value / max) * (bottom - top)
}
const TREND_X_START = 91
const TREND_X_SPAN = 768
const DAY_MS = 86400000
const trendWindowRange = computed(() => {
  const since = overview.value?.window?.since ?? dateStart.value
  const until = overview.value?.window?.until ?? dateEnd.value
  const sinceTime = Date.parse(`${since}T00:00:00Z`)
  const untilTime = Date.parse(`${until}T00:00:00Z`)
  const valid = Number.isFinite(sinceTime) && Number.isFinite(untilTime) && untilTime >= sinceTime
  return {
    sinceTime,
    untilTime,
    valid,
    dayCount: valid ? Math.round((untilTime - sinceTime) / DAY_MS) + 1 : 1,
  }
})
const trendXForDate = (date: string, fallbackIndex: number, rowCount: number) => {
  const range = trendWindowRange.value
  const pointTime = Date.parse(`${date}T00:00:00Z`)
  if (range.valid && range.untilTime > range.sinceTime && Number.isFinite(pointTime)) {
    const progress = Math.min(1, Math.max(0, (pointTime - range.sinceTime) / (range.untilTime - range.sinceTime)))
    return TREND_X_START + progress * TREND_X_SPAN
  }
  return rowCount <= 1 ? TREND_X_START + TREND_X_SPAN / 2 : TREND_X_START + fallbackIndex * (TREND_X_SPAN / (rowCount - 1))
}
const trendPoints = computed(() => {
  const rows = overview.value?.trend ?? []
  const chartMetrics = selectedTrendChartMetrics.value
  const barMetrics = chartMetrics.filter(metric => metric !== 'spend')
  const spendValues = rows.map(row => numberValue(row.spend))
  const barMaxByMetric = new Map<TrendMetric, number>(barMetrics.map(metric => {
    const values = rows.map(row => metricValueOf(row, metric))
    return [metric, Math.max(...values.filter((item): item is number => item != null), 0)]
  }))
  const barGap = 2
  const barWidth = barMetrics.length ? Math.max(3, Math.min(14, (42 - barGap * (barMetrics.length - 1)) / barMetrics.length)) : 0
  const barGroupWidth = barMetrics.length * barWidth + Math.max(0, barMetrics.length - 1) * barGap

  return rows.map((row, index) => {
    const x = trendXForDate(row.date, index, rows.length)
    const metricValues = chartMetrics.map(metric => {
      const option = trendMetricOptions.find(item => item.key === metric)!
      const value = metricValueOf(row, metric)
      return {
        metric,
        label: option.label,
        color: option.color,
        text: formatTrendMetricValue(metric, value, overview.value?.window?.currency, overview.value?.window?.mixed_currency),
      }
    })
    const bars = barMetrics.map((metric, seriesIndex) => {
      const value = metricValueOf(row, metric)
      const max = barMaxByMetric.get(metric) ?? 0
      const height = value == null || max === 0 ? 0 : Math.max(2, (value / max) * 105)
      return {
        metric,
        color: trendMetricOptions.find(item => item.key === metric)?.color ?? '#20a464',
        x: x - barGroupWidth / 2 + seriesIndex * (barWidth + barGap),
        y: 155 - height,
        width: barWidth,
        height,
      }
    })
    return {
      ...row,
      label: formatDate(row.date),
      metricValues,
      bars,
      ariaLabel: [row.date, ...metricValues.map(metric => `${metric.label} ${metric.text}`)].join('，'),
      x,
      spendY: chartMetrics.includes('spend') ? scaleY(numberValue(row.spend), spendValues) : null,
      tooltipLeft: 5 + ((x - TREND_X_START) / TREND_X_SPAN) * 90,
      hitWidth: Math.min(128, TREND_X_SPAN / Math.max(trendWindowRange.value.dayCount, 1)),
    }
  })
})
const trendBars = computed(() => trendPoints.value.flatMap(point => point.bars.map(bar => ({ ...bar, date: point.date }))))
const linePath = (field: 'spendY') => trendPoints.value
  .filter(point => point[field] != null)
  .map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point[field]}`)
  .join('')
const spendPath = computed(() => linePath('spendY'))
const hoveredTrendIndex = ref<number | null>(null)
const selectedTrendIndex = ref<number | null>(null)
const chartPanelRef = ref<HTMLElement | null>(null)
const chartPanelWidth = ref(0)
const selectedTrendChartMetrics = ref<TrendMetric[]>(['spend', 'conversions'])
const availableTrendMetrics = computed(() => trendMetricOptions.filter(option => {
  if (option.key === 'conversion_value' || option.key === 'roas') return isSales.value
  if (option.key === 'result_cost') return isLeads.value
  return true
}))
const defaultAnalysisMetrics = (sales: boolean): TrendMetric[] => sales
  ? ['spend', 'conversion_value', 'conversions', 'roas', 'clicks', 'ctr']
  : ['spend', 'conversions', 'result_cost', 'clicks', 'ctr']
const selectedTrendMetrics = ref<TrendMetric[]>(defaultAnalysisMetrics(false))
const selectedHierarchyMetrics = ref<TrendMetric[]>(defaultAnalysisMetrics(false))
const selectedDailyMetrics = ref<TrendMetric[]>(defaultAnalysisMetrics(false))
const availableAnalysisMetrics = (metrics: TrendMetric[]) => {
  const available = new Set(availableTrendMetrics.value.map(option => option.key))
  const selected = metrics.filter(metric => available.has(metric))
  return selected.length ? selected : defaultAnalysisMetrics(isSales.value).filter(metric => available.has(metric))
}
const trendMetricColumns = computed<TrendMetric[]>(() => availableAnalysisMetrics(selectedTrendMetrics.value))
const hierarchyMetricColumns = computed<TrendMetric[]>(() => availableAnalysisMetrics(selectedHierarchyMetrics.value))
const dailyMetricColumns = computed<TrendMetric[]>(() => availableAnalysisMetrics(selectedDailyMetrics.value))
const updateTrendMetrics = (metrics: TrendMetric[]) => {
  selectedTrendMetrics.value = metrics
  const retained = selectedTrendChartMetrics.value.filter(metric => metrics.includes(metric))
  selectedTrendChartMetrics.value = retained.length ? retained : [metrics[0]!]
}
const toggleTrendMetric = (metric: TrendMetric) => {
  const selected = new Set(selectedTrendChartMetrics.value)
  if (selected.has(metric)) {
    if (selected.size === 1) return
    selected.delete(metric)
  } else {
    selected.add(metric)
  }
  selectedTrendChartMetrics.value = trendMetricColumns.value.filter(item => selected.has(item))
}
const updateHierarchyMetrics = (metrics: TrendMetric[]) => { selectedHierarchyMetrics.value = metrics }
const updateDailyMetrics = (metrics: TrendMetric[]) => { selectedDailyMetrics.value = metrics }
const metricValueFromDerived = (metrics: ReturnType<typeof derive>, metric: TrendMetric) => ({
  spend: metrics.spend,
  impressions: metrics.impressions,
  clicks: metrics.clicks,
  conversions: metrics.results,
  conversion_value: metrics.revenue,
  ctr: metrics.ctr,
  result_cost: metrics.cost,
  roas: metrics.roas,
}[metric])
const formatAnalysisMetric = (metrics: ReturnType<typeof derive>, metric: TrendMetric) => formatTrendMetricValue(
  metric,
  metricValueFromDerived(metrics, metric),
  overview.value?.window?.currency,
  overview.value?.window?.mixed_currency,
)
const hierarchyGridStyle = computed(() => ({
  gridTemplateColumns: `minmax(280px, 2fr) minmax(90px, .65fr) repeat(${hierarchyMetricColumns.value.length}, minmax(86px, .72fr))`,
  minWidth: `${430 + hierarchyMetricColumns.value.length * 100}px`,
}))
const metricValueOf = (point: DashboardMetrics, metric: TrendMetric): number | null => {
  const metrics = derive(point)
  if (metric === 'conversion_value') return metrics.revenue
  if (metric === 'roas') return metrics.roas
  if (metric === 'result_cost') return metrics.cost
  return numberValue(point[metric])
}
watch(isSales, sales => {
  const defaults = defaultAnalysisMetrics(sales)
  selectedTrendMetrics.value = [...defaults]
  selectedHierarchyMetrics.value = [...defaults]
  selectedDailyMetrics.value = [...defaults]
  selectedTrendChartMetrics.value = sales ? ['spend', 'conversion_value'] : ['spend', 'conversions']
})
const activeTrendIndex = computed(() => hoveredTrendIndex.value ?? selectedTrendIndex.value)
const activeTrendPoint = computed(() => activeTrendIndex.value == null ? null : trendPoints.value[activeTrendIndex.value] ?? null)
const toggleTrendSelection = (index: number) => { selectedTrendIndex.value = selectedTrendIndex.value === index ? null : index }
const visibleTrendAxisPoints = computed(() => {
  const range = trendWindowRange.value
  if (!range.valid || !trendPoints.value.length) return []
  const availableWidth = chartPanelWidth.value || 960
  const maximumLabels = Math.min(12, Math.max(4, Math.floor(availableWidth / 92)))
  const labelCount = Math.min(range.dayCount, maximumLabels)
  return Array.from({ length: labelCount }, (_, position) => {
    const progress = labelCount <= 1 ? 0.5 : position / (labelCount - 1)
    const dayOffset = labelCount <= 1 ? 0 : Math.round(progress * (range.dayCount - 1))
    const date = new Date(range.sinceTime + dayOffset * DAY_MS).toISOString().slice(0, 10)
    return {
      date,
      label: formatDate(date),
      x: TREND_X_START + progress * TREND_X_SPAN,
    }
  })
})
const trendAxisFontSize = computed(() => {
  const availableWidth = chartPanelWidth.value || 960
  const svgScale = Math.min(availableWidth / 830, 246 / 161)
  const screenFontSize = availableWidth < 640 ? 9 : 10
  return Math.min(24, Math.max(6, screenFontSize / Math.max(svgScale, 0.25)))
})

const dailyAnalysisRows = computed<AnalysisTableRow[]>(() => (overview.value?.trend ?? []).map((point, index) => {
  const metrics = derive(point)
  const previousPoint = index > 0 ? derive(overview.value?.trend?.[index - 1]) : null
  const currentEfficiency = isSales.value ? metrics.roas : metrics.cost
  const previousEfficiency = previousPoint ? (isSales.value ? previousPoint.roas : previousPoint.cost) : null
  const delta = currentEfficiency != null && previousEfficiency != null && previousEfficiency !== 0
    ? (currentEfficiency - previousEfficiency) / Math.abs(previousEfficiency) * 100
    : null
  return {
    id: point.date,
    name: point.date,
    detail: `${point.accounts_with_facts ?? '—'} / ${point.accounts_expected ?? '—'} 个账号有事实数据`,
    metrics: {
      spend: metrics.spend,
      conversion_value: metrics.revenue,
      conversions: metrics.results,
      roas: metrics.roas,
      clicks: metrics.clicks,
      ctr: metrics.ctr,
      impressions: metrics.impressions,
      result_cost: metrics.cost,
    },
    delta,
    status: point.accounts_with_facts != null && point.accounts_expected != null && point.accounts_with_facts < point.accounts_expected ? '部分数据' : '',
    statusTone: point.accounts_with_facts != null && point.accounts_expected != null && point.accounts_with_facts < point.accounts_expected ? 'warning' : 'normal',
  }
}))
type Level = 'account' | 'campaign' | 'adset'
const level = ref<Level>('account')
const selectedAccountId = ref('')
const selectedCampaignId = ref('')
const showAllRows = ref(false)
const search = ref('')

const rowsOf = (target: Level) => {
  if (target === 'account') return (overview.value?.accounts ?? []).filter(row => (numberValue(row.spend) ?? 0) > 0 || (numberValue(row.conversions) ?? 0) > 0)
  if (target === 'campaign') return overview.value?.campaigns ?? []
  return overview.value?.adsets ?? []
}
const entityRows = computed(() => {
  const rows = rowsOf(level.value).map(row => {
    const metrics = derive(row as DashboardMetrics)
    const before = derive((row as { previous?: DashboardMetrics | null }).previous)
    const anyRow = row as Record<string, any>
    const name = level.value === 'account' ? anyRow.account_name : level.value === 'campaign' ? anyRow.campaign_name : anyRow.adset_name
    const id = level.value === 'account' ? anyRow.account_id : level.value === 'campaign' ? anyRow.campaign_id : anyRow.adset_id
    const efficiency = isSales.value ? metrics.roas : metrics.cost
    const previousEfficiency = isSales.value ? before.roas : before.cost
    const flags: Array<{ label: string; tone: 'warn' | 'bad' }> = []
    if ((metrics.spend ?? 0) > 0 && !metrics.results) {
      flags.push({ label: isSales.value ? '0 订单' : '0 Lead', tone: 'warn' })
    } else if (isSales.value && metrics.roas != null && metrics.roas < 1) {
      flags.push({ label: 'ROAS < 1', tone: 'bad' })
    } else if (efficiency != null && previousEfficiency != null && previousEfficiency > 0) {
      const change = (efficiency - previousEfficiency) / previousEfficiency
      if (isSales.value && change <= -0.3) flags.push({ label: 'ROAS 跌超 30%', tone: 'bad' })
      if (isLeads.value && change >= 0.3) flags.push({ label: 'CPL 涨超 30%', tone: 'bad' })
    }
    return {
      id: String(id ?? ''),
      name: String(name ?? id ?? ''),
      subtitle: level.value === 'adset' ? anyRow.campaign_name : level.value === 'campaign' ? anyRow.account_name : anyRow.account_id,
      accountId: anyRow.account_id as string,
      campaignId: (anyRow.campaign_id ?? null) as string | null,
      metrics,
      efficiency,
      efficiencyDelta: deltaOf(efficiency, previousEfficiency, isSales.value ? 'higher_is_better' : 'lower_is_better'),
      flags,
    }
  })
  const scoped = rows.filter(row => {
    if (level.value === 'campaign' && selectedAccountId.value) return row.accountId === selectedAccountId.value
    if (level.value === 'adset') {
      if (selectedCampaignId.value) return row.campaignId === selectedCampaignId.value
      if (selectedAccountId.value) return row.accountId === selectedAccountId.value
    }
    return true
  })
  const keyword = search.value.trim().toLowerCase()
  const filtered = keyword
    ? scoped.filter(row => row.name.toLowerCase().includes(keyword) || row.id.toLowerCase().includes(keyword))
    : scoped
  return filtered.sort((a, b) => (b.metrics.spend ?? -1) - (a.metrics.spend ?? -1))
})
const attentionRows = computed(() => entityRows.value.filter(row => row.flags.length))
const visibleRows = computed(() => {
  if (showAllRows.value || !attentionRows.value.length) return entityRows.value
  return attentionRows.value
})
const attentionSpend = computed(() => attentionRows.value.reduce((sum, row) => sum + (row.metrics.spend ?? 0), 0))
const levelLabels: Record<Level, string> = { account: '账号', campaign: 'Campaign', adset: 'AdSet' }
const breadcrumb = computed(() => {
  const items: Array<{ label: string; level: Level }> = [{ label: '全部账号', level: 'account' }]
  if (selectedAccountId.value) {
    const account = (overview.value?.accounts ?? []).find(row => row.account_id === selectedAccountId.value)
    items.push({ label: account?.account_name ?? selectedAccountId.value, level: 'campaign' })
  }
  if (selectedCampaignId.value) {
    const campaign = (overview.value?.campaigns ?? []).find(row => row.campaign_id === selectedCampaignId.value)
    items.push({ label: campaign?.campaign_name ?? selectedCampaignId.value, level: 'adset' })
  }
  return items
})
const drillInto = (row: { id: string; accountId: string }) => {
  if (level.value === 'account') {
    selectedAccountId.value = row.id
    selectedCampaignId.value = ''
    level.value = 'campaign'
  } else if (level.value === 'campaign') {
    selectedCampaignId.value = row.id
    level.value = 'adset'
  }
  showAllRows.value = false
}
const goToLevel = (target: Level) => {
  if (target === 'account') { selectedAccountId.value = ''; selectedCampaignId.value = '' }
  if (target === 'campaign') selectedCampaignId.value = ''
  level.value = target
  showAllRows.value = false
}

type HierarchyRow = {
  key: string
  id: string
  name: string
  detail: string
  kind: Level
  depth: number
  parentKey: string | null
  hasChildren: boolean
  metrics: ReturnType<typeof derive>
  status: string
}
const expandedHierarchy = ref<Set<string>>(new Set())
const hierarchyQuery = ref('')
const HIERARCHY_PAGE_SIZE = 10
const hierarchyPage = ref(1)
const hierarchyMetricComparator = (left: DashboardMetrics, right: DashboardMetrics) => {
  const values = (metrics: DashboardMetrics) => [metrics.spend, metrics.conversion_value, metrics.conversions, metrics.clicks, metrics.impressions]
  const leftValues = values(left).map(value => value ?? 0)
  const rightValues = values(right).map(value => value ?? 0)
  const activityDifference = Number(rightValues.some(value => value > 0)) - Number(leftValues.some(value => value > 0))
  if (activityDifference) return activityDifference
  for (let index = 0; index < leftValues.length; index += 1) {
    const difference = rightValues[index]! - leftValues[index]!
    if (difference) return difference
  }
  return 0
}
const hierarchySource = computed<HierarchyRow[]>(() => {
  const accountsById = new Map((overview.value?.accounts ?? []).map(item => [item.account_id, item]))
  const campaignsByAccount = new Map<string, NonNullable<MetaDashboardOverview['campaigns']>>()
  for (const campaign of overview.value?.campaigns ?? []) {
    const rows = campaignsByAccount.get(campaign.account_id) ?? []
    rows.push(campaign)
    campaignsByAccount.set(campaign.account_id, rows)
  }
  const adsetsByCampaign = new Map<string, NonNullable<MetaDashboardOverview['adsets']>>()
  for (const adset of overview.value?.adsets ?? []) {
    if (!adset.campaign_id) continue
    const rows = adsetsByCampaign.get(adset.campaign_id) ?? []
    rows.push(adset)
    adsetsByCampaign.set(adset.campaign_id, rows)
  }
  const result: HierarchyRow[] = []
  const sortedAccounts = [...accountsById.values()].sort(hierarchyMetricComparator)
  for (const account of sortedAccounts) {
    const accountKey = `account:${account.account_id}`
    const campaigns = (campaignsByAccount.get(account.account_id) ?? []).sort(hierarchyMetricComparator)
    result.push({ key: accountKey, id: account.account_id, name: account.account_name, detail: `${campaigns.length} 个 Campaign`, kind: 'account', depth: 0, parentKey: null, hasChildren: Boolean(campaigns.length), metrics: derive(account), status: account.sync_status === 'failed' ? '同步失败' : account.data_status === 'no_delivery' ? '无投放' : '已连接' })
    for (const campaign of campaigns) {
      const campaignKey = `campaign:${campaign.campaign_id}`
      const adsets = (adsetsByCampaign.get(campaign.campaign_id) ?? []).sort(hierarchyMetricComparator)
      result.push({ key: campaignKey, id: campaign.campaign_id, name: campaign.campaign_name, detail: `${account.account_name} · ${adsets.length} 个 AdSet`, kind: 'campaign', depth: 1, parentKey: accountKey, hasChildren: Boolean(adsets.length), metrics: derive(campaign), status: (campaign.spend ?? 0) > 0 ? '投放中' : '无投放' })
      for (const adset of adsets) result.push({ key: `adset:${adset.adset_id}`, id: adset.adset_id, name: adset.adset_name, detail: `${campaign.campaign_name} · ${adset.optimization_goal ?? 'AdSet'}`, kind: 'adset', depth: 2, parentKey: campaignKey, hasChildren: false, metrics: derive(adset), status: (adset.spend ?? 0) > 0 ? '投放中' : '无投放' })
    }
  }
  return result
})
const hierarchyGroups = computed(() => {
  const groups: Array<{ root: HierarchyRow; rows: HierarchyRow[] }> = []
  for (const row of hierarchySource.value) {
    if (!row.parentKey) groups.push({ root: row, rows: [row] })
    else groups[groups.length - 1]?.rows.push(row)
  }
  return groups
})
const hierarchyFilteredGroups = computed(() => {
  const keyword = hierarchyQuery.value.trim().toLowerCase()
  if (!keyword) return hierarchyGroups.value
  return hierarchyGroups.value.filter(group => group.rows.some(row => `${row.name} ${row.id} ${row.detail}`.toLowerCase().includes(keyword)))
})
const hierarchyPageCount = computed(() => Math.max(1, Math.ceil(hierarchyFilteredGroups.value.length / HIERARCHY_PAGE_SIZE)))
const hierarchyPageStart = computed(() => hierarchyFilteredGroups.value.length ? (hierarchyPage.value - 1) * HIERARCHY_PAGE_SIZE + 1 : 0)
const hierarchyPageEnd = computed(() => Math.min(hierarchyPage.value * HIERARCHY_PAGE_SIZE, hierarchyFilteredGroups.value.length))
const paginatedHierarchyGroups = computed(() => {
  const start = (hierarchyPage.value - 1) * HIERARCHY_PAGE_SIZE
  return hierarchyFilteredGroups.value.slice(start, start + HIERARCHY_PAGE_SIZE)
})
const hierarchyRows = computed(() => {
  const keyword = hierarchyQuery.value.trim().toLowerCase()
  return paginatedHierarchyGroups.value.flatMap(group => {
    if (keyword) {
      const rowsByKey = new Map(group.rows.map(row => [row.key, row]))
      const visibleKeys = new Set<string>()
      for (const row of group.rows) {
        if (!`${row.name} ${row.id} ${row.detail}`.toLowerCase().includes(keyword)) continue
        let current: HierarchyRow | undefined = row
        while (current) {
          visibleKeys.add(current.key)
          current = current.parentKey ? rowsByKey.get(current.parentKey) : undefined
        }
      }
      return group.rows.filter(row => visibleKeys.has(row.key))
    }
    const rowsByKey = new Map(group.rows.map(row => [row.key, row]))
    return group.rows.filter(row => {
      if (!row.parentKey) return true
      if (!expandedHierarchy.value.has(row.parentKey)) return false
      const parent = rowsByKey.get(row.parentKey)
      return !parent?.parentKey || expandedHierarchy.value.has(parent.parentKey)
    })
  })
})
const goToHierarchyPage = (page: number) => {
  hierarchyPage.value = Math.min(Math.max(page, 1), hierarchyPageCount.value)
}
const toggleHierarchy = (key: string) => {
  const next = new Set(expandedHierarchy.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedHierarchy.value = next
}
const expandAllHierarchy = () => { expandedHierarchy.value = new Set(hierarchySource.value.filter(row => row.hasChildren).map(row => row.key)) }
const collapseHierarchy = () => { expandedHierarchy.value = new Set() }

watch(hierarchyQuery, () => { hierarchyPage.value = 1 })
watch(hierarchyPageCount, pageCount => {
  if (hierarchyPage.value > pageCount) hierarchyPage.value = pageCount
})

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
    const response = await getMetaDashboardOverview({
      connectionId: connectionId.value,
      accountId: accountId.value || undefined,
      since: dateWindow.value.since,
      until: dateWindow.value.until,
      objective: objective.value || undefined,
      clickType: 'inline_link_clicks',
    })
    overview.value = response
    // Default to the objective that actually holds the spend.
    if (!objective.value) {
      const preferred = (response.objectives ?? []).find(item => item.supported)
      if (preferred?.objective) {
        objective.value = preferred.objective
        await loadOverview(isRefresh)
        return
      }
    }
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
  accountId.value = ''
}

const initialize = async () => {
  if (props.workspaceOverview) {
    overview.value = props.workspaceOverview
    objective.value = props.workspaceOverview.scope?.objective || OBJECTIVE_SALES
    dateStart.value = props.workspaceOverview.window.since
    dateEnd.value = props.workspaceOverview.window.until
  }
  loading.value = true
  try {
    connections.value = (await platformApi.getAllConnections()).filter(item => item.platform === 'Meta' && item.status === 'active')
    for (const connection of connections.value) {
      connectionId.value = connection.id
      await loadAccounts()
      if (accounts.value.length) break
    }
    if (!props.workspaceOverview) await loadOverview()
  } catch (error) {
    if (!overview.value) errorMessage.value = error instanceof Error ? error.message : '数据加载失败'
  } finally {
    loading.value = false
  }
}
const changePeriod = () => {
  const next = windowForDays(Number(period.value))
  dateStart.value = next.since
  dateEnd.value = next.until
  loadOverview()
}
const changeDateRange = () => {
  if (dateStart.value > dateEnd.value) dateEnd.value = dateStart.value
  period.value = String(dateRangeDays.value)
  loadOverview()
}
const changeConnection = async () => { await loadAccounts(); await loadOverview() }
const changeAccount = () => loadOverview()
const handleRefresh = () => loadOverview(true)
const selectObjective = (value: string | null) => {
  if (!value || objective.value === value) return
  objective.value = value
  loadOverview()
}
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

watch([objective, accountId, period], () => { goToLevel('account'); search.value = ''; hierarchyPage.value = 1 })

let trendChartResizeObserver: ResizeObserver | null = null
watch(chartPanelRef, (element, previousElement) => {
  if (previousElement) trendChartResizeObserver?.unobserve(previousElement)
  if (!element) return
  chartPanelWidth.value = element.clientWidth
  trendChartResizeObserver?.observe(element)
}, { flush: 'post' })

onMounted(() => {
  trendChartResizeObserver = new ResizeObserver(entries => {
    chartPanelWidth.value = entries[0]?.contentRect.width ?? chartPanelRef.value?.clientWidth ?? 0
  })
  if (chartPanelRef.value) {
    chartPanelWidth.value = chartPanelRef.value.clientWidth
    trendChartResizeObserver.observe(chartPanelRef.value)
  }
  void initialize()
})
watch(() => props.workspaceOverview, value => {
  if (!value) return
  overview.value = value
  objective.value = value.scope?.objective || OBJECTIVE_SALES
  dateStart.value = value.window.since
  dateEnd.value = value.window.until
  loading.value = false
})
onBeforeUnmount(() => {
  window.clearTimeout(toastTimer)
  trendChartResizeObserver?.disconnect()
})
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

        <section class="analysis-filter-card" aria-label="数据分析视图">
          <div class="analysis-filter-head"><div class="analysis-filter-tab active"><span class="material-symbols-outlined" aria-hidden="true">tune</span><strong>分析视图</strong></div><span class="analysis-filter-count">当前范围 · {{ overview?.data_quality.row_count ?? 0 }} 条事实数据</span></div>
          <div class="analysis-filter-controls">
            <label class="analysis-filter-chip"><span>连接：</span><select v-model="connectionId" aria-label="分析连接" @change="changeConnection"><option v-if="!connections.length" value="">暂无 Meta 连接</option><option v-for="item in connections" :key="item.id" :value="item.id">{{ item.account_name || 'Meta 连接' }}</option></select></label>
            <label class="analysis-filter-chip"><span>账户：</span><select v-model="accountId" aria-label="分析账户" @change="changeAccount"><option value="">全部 active 账户</option><option v-if="!accounts.length" value="">暂无活跃账户</option><option v-for="item in accounts" :key="item.id" :value="item.sub_account_id.replace(/^act_/, '')">{{ item.name }}</option></select></label>
            <label class="analysis-filter-chip"><span>目标：</span><select v-model="objective" aria-label="分析目标" @change="() => loadOverview()"><option value="">自动选择</option><option v-for="item in objectives.filter(item => item.supported)" :key="item.objective ?? 'supported'" :value="item.objective ?? ''">{{ item.label }}</option></select></label>
            <div class="analysis-filter-chip time-filter-chip">
              <div class="date-picker-hitbox">
                <span class="material-symbols-outlined" aria-hidden="true">calendar_today</span>
                <span class="date-picker-value" aria-hidden="true">{{ formatDateLabel(dateStart) }}</span>
                <input ref="dateStartInput" v-model="dateStart" type="date" :max="dateEnd" aria-label="分析开始日期" @click="openDatePicker(dateStartInput)" @change="changeDateRange">
              </div>
              <div class="date-picker-hitbox date-picker-end">
                <span aria-hidden="true">至</span>
                <span class="date-picker-value" aria-hidden="true">{{ formatDateLabel(dateEnd) }}</span>
                <span class="material-symbols-outlined" aria-hidden="true">calendar_today</span>
                <input ref="dateEndInput" v-model="dateEnd" type="date" :min="dateStart" :max="dateInput(new Date())" aria-label="分析结束日期" @click="openDatePicker(dateEndInput)" @change="changeDateRange">
              </div>
            </div>
          </div>
        </section>

        <nav v-if="objectives.length" class="objective-switch" aria-label="投放目标">
          <div class="objective-switch-title"><span class="material-symbols-outlined" aria-hidden="true">tune</span><span>分析视图</span></div>
          <div class="objective-tabs">
            <button
              v-for="item in objectives.filter(item => item.supported)"
              :key="item.objective ?? 'supported'"
              type="button"
              class="objective-tab"
              :class="{ active: objective === item.objective }"
              @click="selectObjective(item.objective)"
            >
              <span class="objective-name">{{ item.label }}</span>
              <span class="objective-spend">{{ formatMoney(item.spend) }}</span>
              <span class="objective-share">{{ formatPercent(item.spend_share, 0) }} · {{ item.adsets }} 个 AdSet</span>
            </button>
          </div>
          <div v-for="item in objectives.filter(item => !item.supported)" :key="item.objective ?? 'unsupported'" class="objective-reference" title="该目标尚未确定统一的结果指标">
            <span class="objective-name">{{ item.label }}</span>
            <span class="objective-spend">{{ formatMoney(item.spend) }}</span>
            <span class="objective-share">{{ formatPercent(item.spend_share, 0) }} · 参考</span>
          </div>
        </nav>

        <p v-if="!supportedObjective" class="scope-note">当前目标没有经过验证的结果指标，只展示消耗与流量。</p>

        <section class="replay-card result-card overview-card" aria-label="结果总览">
          <div class="replay-card-head"><div><h2>结果总览</h2><p>{{ scope?.objective_label }} 目标 · 与上一周期对比</p></div><span class="soft-chip">{{ overview?.previous?.window.since }} 至 {{ overview?.previous?.window.until }}</span></div>
          <div class="result-stats">
            <article v-for="stat in resultStats" :key="stat.label" class="result-stat" :class="{ primary: stat.primary }">
              <span class="result-label">{{ stat.label }}</span>
              <div class="result-value">{{ stat.value }}</div>
              <span class="result-delta" :class="stat.delta.tone">{{ stat.delta.text || '—' }}</span>
            </article>
          </div>
          <div class="result-traffic">
            <span v-for="metric in trafficMetrics" :key="metric.label" class="traffic-item"><small>{{ metric.label }}</small><b>{{ metric.value }}</b></span>
          </div>
        </section>

        <div class="diagnostic-grid">
        <section v-if="isSales && funnelSteps.length" class="replay-card">
          <div class="replay-card-head"><div><h2>事件漏斗</h2><p>Meta 归因事件，不是去重用户</p></div><span v-if="biggestDropStep" class="soft-chip warn">流失最大：{{ biggestDropStep.label }} {{ biggestDropStep.fromPreviousText }}</span></div>
          <div class="funnel-body">
            <div v-for="step in funnelSteps" :key="step.key" class="funnel-row">
              <span class="funnel-label">{{ step.label }}</span>
              <div class="funnel-track"><i :style="{ width: `${step.width}%` }" :class="{ danger: biggestDropStep?.key === step.key }"></i></div>
              <b class="funnel-value">{{ step.valueText }}</b>
              <span class="funnel-rate" :class="{ danger: biggestDropStep?.key === step.key }">{{ step.fromPreviousText ?? '起点' }}</span>
            </div>
          </div>
        </section>

        <section class="replay-card trend-replay-card">
          <div class="replay-card-head trend-card-head"><div><h2>趋势监控</h2><p>自定义指标随时间变化 · {{ dateRangeDays }} 天</p></div><div class="trend-head-actions"><div class="trend-metric-pills" role="group" aria-label="选择趋势指标（支持多选）"><button v-for="metric in trendMetricColumns" :key="metric" type="button" :class="{ active: selectedTrendChartMetrics.includes(metric) }" :aria-pressed="selectedTrendChartMetrics.includes(metric)" @click="toggleTrendMetric(metric)">{{ trendMetricOptions.find(option => option.key === metric)?.label }}</button></div><MetricSelector :model-value="trendMetricColumns" :options="availableTrendMetrics" @update:model-value="updateTrendMetrics" /></div></div>
          <div class="trend-grid">
            <div ref="chartPanelRef" class="chart-panel">
              <div class="chart-legend"><span v-for="metric in selectedTrendChartMetrics" :key="metric" class="legend-item"><i class="legend-dot" :style="{ backgroundColor: trendMetricOptions.find(item => item.key === metric)?.color }"></i>{{ trendMetricOptions.find(item => item.key === metric)?.label }}</span></div>
              <div v-if="!trendPoints.length" class="chart-empty">所选窗口暂无日级投放数据</div>
              <svg v-else viewBox="60 24 830 161" preserveAspectRatio="xMidYMid meet" role="img" :aria-label="`近 ${period} 天${selectedTrendChartMetrics.map(metric => trendMetricOptions.find(item => item.key === metric)?.label).join('、')}趋势图`">
                <g stroke="#ecebea" stroke-width="1"><path d="M52 32H892M52 73H892M52 114H892M52 155H892" /></g>
                <g opacity=".78"><rect v-for="bar in trendBars" :key="`bar-${bar.date}-${bar.metric}`" :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" :fill="bar.color" rx="2" /></g>
                <path v-if="spendPath" :d="spendPath" fill="none" stroke="#4f8fe8" stroke-width="1.4" />
                                <g fill="#4f8fe8" stroke="#fff" stroke-width="1"><circle v-for="point in trendPoints" v-show="point.spendY != null" :key="`spend-${point.date}`" :cx="point.x" :cy="point.spendY ?? 0" r="2.1" /></g>
                                <g v-if="activeTrendPoint" class="chart-active-markers" aria-hidden="true">
                  <line :x1="activeTrendPoint.x" :x2="activeTrendPoint.x" y1="24" y2="155" />
                  <rect v-for="bar in activeTrendPoint.bars" :key="bar.metric" :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" :stroke="bar.color" rx="2" />
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
                  height="131"
                  role="button"
                  tabindex="0"
                  :aria-label="point.ariaLabel"
                  @mouseenter="hoveredTrendIndex = index"
                  @mouseleave="hoveredTrendIndex = null"
                  @focus="hoveredTrendIndex = index"
                  @blur="hoveredTrendIndex = null"
                  @click="toggleTrendSelection(index)"
                  @keydown.enter.prevent="toggleTrendSelection(index)"
                  @keydown.space.prevent="toggleTrendSelection(index)"
                />
                <g class="chart-axis-labels" :style="{ fontSize: `${trendAxisFontSize}px` }">
                  <text
                    v-for="tick in visibleTrendAxisPoints"
                    :key="`axis-${tick.date}`"
                    :x="tick.x"
                    y="170"
                    text-anchor="middle"
                    dominant-baseline="middle"
                  >{{ tick.label }}</text>
                </g>
              </svg>
              <div v-if="activeTrendPoint" class="chart-tooltip" :style="{ left: `${activeTrendPoint.tooltipLeft}%` }" role="status" aria-live="polite">
                <strong>{{ activeTrendPoint.date }}</strong>
                <div v-for="metric in activeTrendPoint.metricValues" :key="metric.metric"><span><i class="legend-dot" :style="{ backgroundColor: metric.color }"></i>{{ metric.label }}</span><b>{{ metric.text }}</b></div>
              </div>
            </div>
          </div>
        </section>
        </div>

        <section class="replay-card hierarchy-card">
          <div class="replay-card-head">
            <div>
              <h2>投放层级分析</h2>
              <p>查看账户、Campaign 与 AdSet 的完整关系</p>
              <nav class="crumbs legacy-crumbs" aria-label="下钻路径">
                <template v-for="(crumb, index) in breadcrumb" :key="crumb.level">
                  <button type="button" class="crumb" :class="{ current: index === breadcrumb.length - 1 }" @click="goToLevel(crumb.level)">{{ crumb.label }}</button>
                  <span v-if="index < breadcrumb.length - 1" class="crumb-sep" aria-hidden="true">/</span>
                </template>
              </nav>
            </div>
            <div class="hierarchy-actions">
              <label class="hierarchy-search"><span class="material-symbols-outlined" aria-hidden="true">search</span><input v-model="hierarchyQuery" type="search" placeholder="搜索名称或 ID" aria-label="搜索层级名称或 ID"></label>
              <button type="button" @click="expandAllHierarchy">全部展开</button><button type="button" @click="collapseHierarchy">收起</button>
              <MetricSelector :model-value="hierarchyMetricColumns" :options="availableTrendMetrics" @update:model-value="updateHierarchyMetrics" />
            </div>
          </div>

          <div v-if="attentionRows.length" class="attention-bar">
            <span class="attention-text"><b>{{ attentionRows.length }}</b> 个{{ levelLabels[level] }}需要处理，共消耗 {{ formatMoney(attentionSpend) }}</span>
            <button type="button" class="attention-toggle" @click="showAllRows = !showAllRows">{{ showAllRows ? '只看需要处理' : `查看全部 ${entityRows.length} 个` }}</button>
          </div>

          <div class="hierarchy-tree-wrap">
            <div class="hierarchy-tree-head" :style="hierarchyGridStyle"><span>层级 / 名称</span><span>状态</span><span v-for="metric in hierarchyMetricColumns" :key="metric">{{ trendMetricOptions.find(option => option.key === metric)?.label }}</span></div>
            <div v-if="!hierarchyRows.length" class="data-empty">当前窗口没有可展示的层级数据</div>
            <div v-for="row in hierarchyRows" :key="row.key" class="hierarchy-tree-row" :style="hierarchyGridStyle">
              <div class="hierarchy-tree-name" :style="{ '--depth': row.depth }"><button v-if="row.hasChildren" type="button" class="tree-expander" :class="{ open: expandedHierarchy.has(row.key) }" @click="toggleHierarchy(row.key)">›</button><span v-else class="tree-expander placeholder">›</span><span class="tree-icon" :class="row.kind">{{ row.kind === 'account' ? 'A' : row.kind === 'campaign' ? 'C' : 'U' }}</span><span><strong>{{ row.name }}</strong><small>{{ row.detail }}</small></span></div>
              <span class="tree-status" :class="{ warning: row.status !== '投放中' && row.status !== '已连接' }"><i></i>{{ row.status }}</span>
              <span v-for="metric in hierarchyMetricColumns" :key="metric">{{ formatAnalysisMetric(row.metrics, metric) }}</span>
            </div>
          </div>
          <div v-if="hierarchyFilteredGroups.length" class="hierarchy-pagination" aria-label="投放层级分页">
            <span>第 {{ hierarchyPageStart }}–{{ hierarchyPageEnd }} 个，共 {{ hierarchyFilteredGroups.length }} 个账户 · 每页最多 {{ HIERARCHY_PAGE_SIZE }} 个</span>
            <div class="hierarchy-pagination__controls">
              <button type="button" :disabled="hierarchyPage === 1" aria-label="上一页" @click="goToHierarchyPage(hierarchyPage - 1)"><span class="material-symbols-outlined" aria-hidden="true">chevron_left</span></button>
              <strong>第 {{ hierarchyPage }} / {{ hierarchyPageCount }} 页</strong>
              <button type="button" :disabled="hierarchyPage === hierarchyPageCount" aria-label="下一页" @click="goToHierarchyPage(hierarchyPage + 1)"><span class="material-symbols-outlined" aria-hidden="true">chevron_right</span></button>
            </div>
          </div>

          <div class="table-wrap legacy-drill-table">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ levelLabels[level] }}</th>
                  <th v-for="metric in hierarchyMetricColumns" :key="metric">{{ trendMetricOptions.find(option => option.key === metric)?.label }}</th>
                  <th>环比</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!visibleRows.length"><td :colspan="hierarchyMetricColumns.length + 3" class="data-empty">当前窗口没有可展示的{{ levelLabels[level] }}</td></tr>
                <tr v-for="row in visibleRows" :key="row.id" :class="{ drillable: level !== 'adset' }" @click="level !== 'adset' && drillInto(row)">
                  <td><strong>{{ row.name }}</strong><small>{{ row.subtitle || row.id }}</small></td>
                  <td v-for="metric in hierarchyMetricColumns" :key="metric">{{ formatAnalysisMetric(row.metrics, metric) }}</td>
                  <td><span class="cell-delta" :class="row.efficiencyDelta.tone">{{ row.efficiencyDelta.text || '—' }}</span></td>
                  <td><span v-for="flag in row.flags" :key="flag.label" class="quiet-badge" :class="flag.tone">{{ flag.label }}</span><span v-if="!row.flags.length" class="row-dot"></span></td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td v-for="metric in hierarchyMetricColumns" :key="metric">{{ formatAnalysisMetric(current, metric) }}</td>
                  <td></td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
          <p v-if="level !== 'adset'" class="table-hint">点击任意行下钻到 {{ level === 'account' ? 'Campaign' : 'AdSet' }}</p>
        </section>

        <AnalysisMetricTable
          title="日明细"
          subtitle="逐日核对真实 Meta 事实数据；空字段不补值"
          entity-label="日期"
          search-placeholder="搜索日期"
          :rows="dailyAnalysisRows"
          :columns="dailyMetricColumns"
          :currency="overview?.window.currency"
          :mixed-currency="overview?.window.mixed_currency"
          :totals="{ spend: current.spend, conversion_value: current.revenue, conversions: current.results, roas: current.roas, clicks: current.clicks, ctr: current.ctr, impressions: current.impressions, result_cost: current.cost }"
        >
          <template #actions><MetricSelector :model-value="dailyMetricColumns" :options="availableTrendMetrics" @update:model-value="updateDailyMetrics" /></template>
        </AnalysisMetricTable>

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
.dashboard-shell.embedded .date-range-filter,
.dashboard-shell.embedded .sync-button,
.dashboard-shell.embedded .refresh-button { width: 100%; min-width: 0; }
.dashboard-shell.embedded .date-range-filter input { width: 100%; }
.dashboard-shell.embedded .replay-content { padding: 12px 12px 52px; }
.dashboard-shell.embedded .result-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
.content { width: min(100%,1440px); max-width: 1440px; margin: 0 auto; padding: 30px clamp(24px,3vw,48px) 74px; }

.replay-bar { align-items: center; }
.replay-title { align-items: center; }
.replay-title .page-icon { background: #f6f5f4; color: #37352f; }
.replay-title h1 { font-size: 16px; }
.replay-actions { gap: 8px; }
.date-range-filter { height: 34px; display: inline-flex; align-items: center; gap: 6px; padding: 0 9px; border: 1px solid var(--hairline-strong); border-radius: 8px; background: #fff; color: var(--steel); font-size: 11px; white-space: nowrap; }
.date-range-filter .material-symbols-outlined { font-size: 15px; }
.date-range-filter input { width: 112px; border: 0; outline: 0; background: transparent; color: var(--slate); font: inherit; font-size: 11px; }
.trend-head-actions { display: flex; align-items: center; gap: 8px; }
.trend-metric-pills { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }.trend-metric-pills button { height: 30px; padding: 0 10px; border: 1px solid var(--hairline); border-radius: 7px; background: #fff; color: var(--slate); font: inherit; font-size: 11px; cursor: pointer; }.trend-metric-pills button.active { border-color: #a9cef8; background: #eff7ff; color: #1769aa; font-weight: 650; }
.trend-metric-select { display: inline-flex; align-items: center; gap: 6px; color: var(--steel); font-size: 11px; white-space: nowrap; }
.trend-metric-select select { height: 30px; padding: 0 24px 0 8px; border: 1px solid var(--hairline-strong); border-radius: 7px; background: #fff; color: var(--charcoal); font: inherit; font-size: 11px; }
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

.content.replay-content { width: min(100%,1440px); max-width: 1440px; margin: 0 auto; padding-top: 24px; padding-bottom: 64px; display: flex; flex-direction: column; }
.replay-content > .analysis-filter-card { order: 0; }.replay-content > .dashboard-feedback { order: 1; }.replay-content > .objective-switch { display: none; }.replay-content > .scope-note { order: 2; }.replay-content > .overview-card { order: 3; }.replay-content > .diagnostic-grid { order: 4; }.replay-content > :deep(.analysis-table-card) { order: 5; }.replay-content > .hierarchy-card { order: 6; }
.overview-card { border-radius: 12px; }.overview-card .replay-card-head { background: #fff; }.trend-replay-card,.hierarchy-card { border-radius: 12px; }
.dashboard-feedback { display:flex; flex-wrap:wrap; gap:6px 12px; margin-bottom: 10px; padding: 9px 12px; border: 1px solid var(--hairline); border-radius: 8px; background: var(--surface-soft); color: var(--slate); font-size: 12px; }
.dashboard-feedback strong{color:var(--charcoal)}
.dashboard-feedback.warning{border-color:#f0d8a8;background:#fffaf0}
.dashboard-feedback.warning strong{color:#946200}
.dashboard-feedback.error { border-color: #f0c9c9; background: #fff5f5; color: #a33a3a; }
.analysis-filter-card { margin-bottom: 12px; overflow: hidden; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; }
.analysis-filter-head { min-height: 46px; display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 0 14px; border-bottom: 1px solid var(--hairline-soft); }
.analysis-filter-tab { position: relative; display: inline-flex; align-items: center; gap: 7px; height: 46px; color: var(--slate); font-size: 13px; }
.analysis-filter-tab::after { content: ''; position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: var(--workspace-action-primary,#137fec); }
.analysis-filter-tab .material-symbols-outlined { color: #3276cc; font-size: 17px; }.analysis-filter-count { color: var(--steel); font-size: 11px; }
.analysis-filter-controls { display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)) minmax(260px, 1.5fr); gap: 7px; padding: 9px 14px; }
.analysis-filter-chip { min-width: 0; height: 34px; display: flex; align-items: center; gap: 4px; padding: 0 10px; border-radius: 8px; background: var(--surface); color: var(--steel); font-size: 11px; white-space: nowrap; }
.analysis-filter-chip select,.analysis-filter-chip input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: var(--charcoal); font: inherit; font-size: 12px; font-weight: 600; }.analysis-filter-chip input { width: 0; }
.time-filter-chip { gap: 0; padding: 0; overflow: hidden; background: #fff; box-shadow: inset 0 0 0 1px var(--hairline); }
.date-picker-hitbox { position: relative; min-width: 0; height: 100%; flex: 1; display: flex; align-items: center; gap: 7px; padding: 0 10px; color: var(--steel); cursor: pointer; transition: background-color .16s ease; }
.date-picker-hitbox:hover,.date-picker-hitbox:focus-within { background: var(--surface); }
.date-picker-hitbox input { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.date-picker-hitbox .material-symbols-outlined { flex: 0 0 auto; font-size: 15px; }
.date-picker-value { min-width: 0; flex: 1; color: var(--charcoal); font-size: 12px; font-weight: 600; }
.date-picker-end { padding-left: 4px; }
.date-picker-end .date-picker-value { text-align: left; }
.quiet-badge { display: inline-flex; align-items: center; min-height: 22px; margin-left: 4px; padding: 2px 8px; border: 1px solid var(--hairline); border-radius: 999px; background: #fff; color: var(--steel); font-size: 10px; font-weight: 600; white-space: nowrap; }
.quiet-badge:first-child { margin-left: 0; }
.quiet-badge.warn { border-color: #f0d8a8; background: #fff6e4; color: #9a6700; }
.quiet-badge.bad { border-color: #f0c9c9; background: #fdecec; color: #b4402e; }
button.quiet-badge { cursor: pointer; font-family: inherit; }

.objective-switch { display: flex; align-items: stretch; gap: 20px; margin-bottom: 18px; padding: 0 2px 12px; border-bottom: 1px solid var(--hairline); }
.objective-switch-title { display: inline-flex; align-items: center; gap: 6px; min-width: 84px; color: var(--steel); font-size: 11px; font-weight: 600; letter-spacing: .02em; }
.objective-switch-title .material-symbols-outlined { font-size: 16px; }
.objective-tabs { display: flex; align-items: stretch; gap: 4px; min-width: 0; }
.objective-tab { position: relative; display: grid; grid-template-columns: auto auto; grid-template-rows: auto auto; column-gap: 8px; align-items: baseline; min-width: 150px; padding: 2px 16px 0; border: 0; border-radius: 0; background: transparent; color: var(--slate); font: inherit; text-align: left; cursor: pointer; }
.objective-tab::after { content: ""; position: absolute; right: 16px; bottom: -13px; left: 16px; height: 2px; background: transparent; }
.objective-tab:hover { color: var(--ink); }
.objective-tab.active { color: var(--ink); }
.objective-tab.active::after { background: var(--workspace-action-primary,#137fec); }
.objective-name { grid-row: 1; color: inherit; font-size: 13px; font-weight: 600; }
.objective-spend { grid-row: 1; color: var(--ink); font-size: 13px; font-weight: 650; }
.objective-share { grid-column: 1 / -1; color: var(--steel); font-size: 11px; }
.objective-reference { display: grid; grid-template-columns: auto auto; grid-template-rows: auto auto; column-gap: 8px; align-items: baseline; min-width: 150px; padding: 2px 16px 0; border-left: 1px solid var(--hairline-soft); color: var(--stone); opacity: .82; }
.objective-reference .objective-name { color: var(--steel); }
.objective-reference .objective-spend { color: var(--slate); }
.objective-reference .objective-share { grid-column: 1 / -1; color: var(--stone); }
.scope-note { margin: 0 0 12px; color: #946200; font-size: 12px; }

.replay-card { margin-top: 20px; border: 1px solid var(--hairline); border-radius: 10px; background: #fff; overflow: hidden; }
.replay-card-head { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 18px; border-bottom: 1px solid var(--hairline-soft); }
.diagnostic-grid { display: block; margin: 0; }
.diagnostic-grid > .trend-replay-card { margin-top: 20px; }
.diagnostic-grid > .replay-card:not(.trend-replay-card) { display: none; }
.diagnostic-grid .replay-card-head { min-height: 62px; }
.diagnostic-grid .chart-panel { height: 274px; }
.diagnostic-grid .chart-panel svg { height: 246px; }
.replay-card-head h2 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.replay-card-head p { margin: 3px 0 0; color: var(--steel); font-size: 12px; }
.soft-chip { display: inline-flex; align-items: center; min-height: 26px; padding: 3px 9px; border-radius: 6px; background: var(--surface); color: var(--slate); font-size: 11px; font-weight: 600; white-space: nowrap; }
.soft-chip.warn { background: #fff6e4; color: #9a6700; }

.result-card { margin-top: 0; }
.result-stats { display: grid; grid-template-columns: 1.1fr 1.35fr 1.2fr repeat(3, minmax(0,1fr)); }
.result-stat { position: relative; padding: 18px 20px; }
.result-stat:not(:last-child)::after { content: ""; position: absolute; top: 20%; right: 0; bottom: 20%; width: 1px; background: #f0efed; }
.result-stat.primary { background: #fcfdff; }
.result-label { color: var(--steel); font-size: 12px; font-weight: 600; }
.result-value { margin-top: 8px; color: var(--ink); font-size: 22px; line-height: 1.15; font-weight: 650; letter-spacing: -.4px; }
.result-stat.primary .result-value { font-size: 27px; }
.result-delta { display: inline-flex; align-items: center; margin-top: 8px; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.result-delta.good { background: #edf8f0; color: #16804a; }
.result-delta.bad { background: #fdecec; color: #b4402e; }
.result-delta.neutral { background: #f0efed; color: var(--slate); }
.result-delta.none { padding-left: 0; background: transparent; color: var(--stone); }
.result-traffic { display: flex; flex-wrap: wrap; padding: 11px 20px; border-top: 1px solid var(--hairline-soft); background: var(--surface-soft); }
.traffic-item { display: inline-flex; align-items: baseline; gap: 6px; }
.traffic-item:not(:last-child) { margin-right: 18px; padding-right: 18px; border-right: 1px solid var(--hairline-soft); }
.traffic-item small { color: var(--steel); font-size: 11px; }
.traffic-item b { color: var(--charcoal); font-size: 13px; font-weight: 600; }

.funnel-body { display: grid; gap: 10px; padding: 14px 16px; }
.funnel-row { display: grid; grid-template-columns: 72px minmax(0,1fr) 84px 64px; align-items: center; gap: 12px; }
.funnel-label { color: var(--slate); font-size: 12px; }
.funnel-track { height: 8px; border-radius: 999px; background: #f0efed; overflow: hidden; }
.funnel-track i { display: block; height: 100%; border-radius: inherit; background: #4f8fe8; transition: width .2s ease; }
.funnel-track i.danger { background: #dd7d00; }
.funnel-value { color: var(--ink); font-size: 13px; font-weight: 600; text-align: right; }
.funnel-rate { color: var(--steel); font-size: 11px; text-align: right; }
.funnel-rate.danger { color: #b4402e; font-weight: 600; }

.trend-grid { display: grid; grid-template-columns: minmax(0,1fr); gap: 8px; padding: 8px; }
.chart-panel { position: relative; min-width: 0; height: 252px; min-height: 0; padding: 7px 2px 0; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fcfcfb; }
.chart-empty { height: 208px; display: grid; place-items: center; color: var(--stone); font-size: 12px; }
.chart-legend { display: flex; align-items: center; gap: 14px; padding-left: 8px; color: var(--steel); font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 5px; height: 5px; border-radius: 50%; }
.legend-dot.spend { background: #4f8fe8; }.legend-dot.conversions { background: #20a464; }
.chart-panel svg { display: block; width: 100%; height: 202px; margin-top: -2px; overflow: visible; }
.chart-axis-labels text { fill: var(--stone); }
.chart-hit-area { fill: transparent; cursor: pointer; outline: none; }
.chart-hit-area:focus { fill: rgb(79 143 232 / 4%); }
.chart-active-markers { pointer-events: none; }
.chart-active-markers line { stroke: rgb(100 116 139 / 28%); stroke-width: .75; stroke-dasharray: 3 3; }
.chart-active-markers rect { fill: none; stroke: #20a464; stroke-width: 1.2; }
.chart-active-markers circle { fill: #ffffff; stroke-width: 1.5; }
.chart-active-markers circle.spend { stroke: #4f8fe8; }
.chart-tooltip { position: absolute; z-index: 4; top: 28px; width: 152px; padding: 8px 9px; border: 1px solid var(--hairline); border-radius: 7px; background: rgb(255 255 255 / 96%); box-shadow: rgba(15,15,15,.12) 0 8px 24px; color: var(--charcoal); pointer-events: none; transform: translateX(-50%); }
.chart-tooltip > strong { display: block; margin-bottom: 5px; color: var(--ink); font-size: 12px; }
.chart-tooltip > div { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 19px; color: var(--steel); font-size: 11px; }
.chart-tooltip span { display: inline-flex; align-items: center; gap: 4px; }
.chart-tooltip b { color: var(--charcoal); font-size: 12px; font-weight: 600; }

.crumbs { display: flex; align-items: center; gap: 5px; margin-top: 4px; }
.crumb { padding: 0; border: 0; background: transparent; color: var(--workspace-action-primary,#137fec); font: inherit; font-size: 12px; cursor: pointer; }
.crumb.current { color: var(--steel); cursor: default; }
.crumb-sep { color: var(--stone); font-size: 11px; }
.table-controls { display: flex; align-items: center; gap: 8px; }
.table-search { height: 30px; width: 168px; padding: 0 10px; border: 1px solid var(--hairline-strong); border-radius: 7px; outline: none; background: #fff; color: var(--charcoal); font: inherit; font-size: 12px; }
.table-search:focus { border-color: var(--workspace-action-primary,#137fec); }
.attention-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 16px; border-bottom: 1px solid var(--hairline-soft); background: #fffaf0; }
.attention-text { color: #946200; font-size: 12px; }
.attention-text b { color: #7a5200; }
.attention-toggle { padding: 4px 10px; border: 1px solid #f0d8a8; border-radius: 6px; background: #fff; color: #946200; font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; }
.attention-toggle:hover { border-color: #d9b978; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; min-width: 860px; border-collapse: collapse; font-size: 12px; }
.data-table th,.data-table td { height: 42px; padding: 0 12px; border-bottom: 1px solid var(--hairline-soft); text-align: right; white-space: nowrap; }
.data-table th:first-child,.data-table td:first-child { text-align: left; }
.data-table th { height: 36px; color: var(--steel); font-size: 11px; font-weight: 600; background: var(--surface-soft); }
.data-table tbody tr.drillable { cursor: pointer; }
.data-table tbody tr:hover { background: #f7fbff; }
.data-table tbody tr.active { background: #f2f8ff; }
.data-table td strong { display: block; max-width: 280px; overflow: hidden; color: var(--ink); font-size: 12px; text-overflow: ellipsis; }
.data-table td small { display: block; max-width: 280px; margin-top: 2px; overflow: hidden; color: var(--stone); font-size: 10px; text-overflow: ellipsis; }
.data-table tfoot td { height: 42px; border-top: 1px solid var(--hairline-strong); border-bottom: 0; color: var(--ink); font-weight: 600; background: #fff; }
.data-empty { text-align: center!important; color: var(--stone); }
.cell-delta { font-size: 11px; font-weight: 600; }
.cell-delta.good { color: #16804a; }
.cell-delta.bad { color: #b4402e; }
.cell-delta.neutral { color: var(--slate); }
.cell-delta.none { color: var(--stone); font-weight: 400; }
.row-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #cfe8d8; }
.table-hint { margin: 0; padding: 9px 16px; border-top: 1px solid var(--hairline-soft); color: var(--stone); font-size: 11px; }
.legacy-crumbs,.legacy-drill-table,.hierarchy-card > .attention-bar,.hierarchy-card > .table-hint { display: none; }
.hierarchy-actions { display: flex; align-items: center; gap: 7px; }.hierarchy-search { width: 250px; height: 34px; display: flex; align-items: center; gap: 6px; padding: 0 9px; border: 1px solid var(--hairline-strong); border-radius: 8px; }.hierarchy-search .material-symbols-outlined { color: var(--stone); font-size: 17px; }.hierarchy-search input { min-width: 0; flex: 1; border: 0; outline: 0; font: inherit; font-size: 12px; }.hierarchy-actions > button { height: 34px; padding: 0 10px; border: 1px solid var(--hairline-strong); border-radius: 7px; background: #fff; color: var(--slate); font: inherit; font-size: 11px; cursor: pointer; }
.hierarchy-tree-wrap { overflow-x: auto; }
.hierarchy-tree-head,.hierarchy-tree-row { display: grid; align-items: center; gap: 10px; padding: 0 16px; }.hierarchy-tree-head { min-height: 42px; border-bottom: 1px solid var(--hairline); background: var(--surface-soft); color: var(--steel); font-size: 11px; font-weight: 600; }.hierarchy-tree-head span:not(:first-child),.hierarchy-tree-row > span { text-align: right; }.hierarchy-tree-row { min-height: 58px; border-bottom: 1px solid var(--hairline-soft); color: var(--charcoal); font-size: 12px; font-variant-numeric: tabular-nums; }.hierarchy-tree-row:hover { background: #fafcff; }.hierarchy-tree-name { min-width: 0; display: flex; align-items: center; gap: 8px; padding-left: calc(var(--depth) * 28px); }.hierarchy-tree-name > span:last-child { min-width: 0; }.hierarchy-tree-name strong,.hierarchy-tree-name small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.hierarchy-tree-name small { margin-top: 3px; color: var(--stone); font-size: 10px; }.tree-expander { width: 20px; height: 20px; display: grid; place-items: center; padding: 0; border: 0; background: transparent; color: var(--steel); font-size: 20px; cursor: pointer; transition: transform .15s ease; }.tree-expander.open { transform: rotate(90deg); }.tree-expander.placeholder { opacity: 0; }.tree-icon { width: 26px; height: 26px; display: grid; place-items: center; flex: 0 0 auto; border: 1px solid #cfe1f5; border-radius: 7px; background: #eef6ff; color: #3276cc; font-size: 10px; font-weight: 700; }.tree-icon.campaign { border-radius: 50%; background: #f6f5f4; color: #6b6862; border-color: #ddd9d3; }.tree-icon.adset { width: 22px; height: 22px; border: 0; background: transparent; }.tree-status { justify-self: end; display: inline-flex; align-items: center; gap: 5px; width: fit-content; padding: 4px 8px; border-radius: 999px; background: #e8f7ee; color: #12804a; font-size: 10px; font-weight: 600; }.tree-status i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }.tree-status.warning { background: #fff4df; color: #a86400; }

.hierarchy-pagination { min-height: 50px; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 16px; color: var(--steel); font-size: 11px; }
.hierarchy-pagination__controls { display: flex; align-items: center; gap: 18px; }
.hierarchy-pagination__controls strong { min-width: 70px; color: var(--slate); font-size: 13px; font-weight: 650; text-align: center; }
.hierarchy-pagination__controls button { width: 30px; height: 30px; display: grid; place-items: center; padding: 0; border: 1px solid var(--hairline-strong); border-radius: 7px; background: #fff; color: var(--slate); cursor: pointer; }
.hierarchy-pagination__controls button:hover:not(:disabled) { border-color: #a9cef8; background: #f7fbff; color: var(--workspace-action-primary,#137fec); }
.hierarchy-pagination__controls button:disabled { border-color: var(--hairline); color: var(--stone); cursor: not-allowed; opacity: .55; }
.hierarchy-pagination__controls .material-symbols-outlined { font-size: 18px; }

.platform-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: stretch; gap: 8px; padding: 10px; }
.platform-card { --accent: #4f8fe8; min-width: 0; align-self: stretch; border: 1px solid var(--hairline); border-radius: 9px; overflow: hidden; background: #fff; }

.toast { position: fixed; z-index: 90; left: 50%; bottom: 52px; max-width: calc(100vw - 32px); padding: 10px 13px; border: 1px solid var(--hairline,#e5e3df); border-radius: 8px; background: #fff; color: #37352f; font-size: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 44px -10px; opacity: 0; pointer-events: none; transform: translate(-50%,8px); transition: opacity .16s ease,transform .16s ease; }
.toast.show { opacity: 1; transform: translate(-50%,0); }

@media (max-width: 1220px) {
  .result-stats { grid-template-columns: repeat(3,1fr); }
  .result-stat:nth-child(3)::after { display: none; }
  .result-stat:nth-child(-n+3) { border-bottom: 1px solid #f3f2f0; }
  .platform-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .dashboard-shell:not(.embedded) .replay-title { flex: 0 0 auto; }.dashboard-shell:not(.embedded) .replay-title p { display: none; }.dashboard-shell:not(.embedded) .replay-actions { min-width: 0; overflow-x: auto; }.dashboard-shell:not(.embedded) .filter-field,.dashboard-shell:not(.embedded) .date-range-filter,.dashboard-shell:not(.embedded) .sync-button,.dashboard-shell:not(.embedded) .refresh-button { flex: 0 0 auto; }
  .trend-head-actions { align-items: flex-end; flex-direction: column; }
  .trend-grid,.diagnostic-grid { grid-template-columns: 1fr; }
  .analysis-filter-controls { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .diagnostic-grid { gap: 16px; }
  .replay-card-head { flex-wrap: wrap; }
  .table-controls { width: 100%; justify-content: space-between; }
  .table-search { width: 100%; }
}
@media (max-width: 620px) {
  .replay-content { padding: 12px 12px 52px; }
  .analysis-filter-controls { grid-template-columns: 1fr; padding: 8px 10px; }
  .analysis-filter-head { padding: 0 10px; }
  .dashboard-shell:not(.embedded) .replay-title h1 { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
  .dashboard-shell:not(.embedded) .sync-button,.dashboard-shell:not(.embedded) .refresh-button { width: 34px; min-width: 34px; padding: 0; }
  .dashboard-shell:not(.embedded) .sync-label,.dashboard-shell:not(.embedded) .refresh-label { display: none; }
  .objective-switch { align-items: flex-start; flex-direction: column; gap: 8px; margin-bottom: 14px; padding-bottom: 10px; }
  .objective-switch-title { min-width: 0; }
  .objective-tabs { width: 100%; overflow-x: auto; }
  .objective-tab { min-width: 142px; padding-right: 12px; padding-left: 12px; }
  .objective-tab::after { right: 12px; bottom: -11px; left: 12px; }
  .objective-reference { min-width: 142px; padding-right: 12px; padding-left: 12px; border-top: 1px solid var(--hairline-soft); border-left: 0; padding-top: 8px; }
  .result-stats { grid-template-columns: repeat(2,1fr); }
  .result-stat { padding: 14px 12px; }
  .result-stat:nth-child(2n)::after { display: none; }
  .result-stat.primary .result-value { font-size: 22px; }
  .objective-tab { flex: 1 1 44%; min-width: 0; }
  .funnel-row { grid-template-columns: 56px minmax(0,1fr) 66px 52px; gap: 8px; }
  .traffic-item:not(:last-child) { margin-right: 12px; padding-right: 12px; }
  .hierarchy-pagination { align-items: flex-start; flex-direction: column; }
  .hierarchy-pagination__controls { width: 100%; justify-content: space-between; }
}

@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
