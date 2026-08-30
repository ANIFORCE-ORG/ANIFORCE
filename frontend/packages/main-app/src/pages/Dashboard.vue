<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import AnalysisMetricTable from '@/components/dashboard/AnalysisMetricTable.vue'
import { navItems } from '@/config/navigation'
import { formatDashboardMoney, formatDashboardNumber, useDashboardScope } from '@/data/dashboard'

const props = withDefaults(defineProps<{
  embedded?: boolean
}>(), {
  embedded: false,
})

const router = useRouter()
const activeSession = ref('sess-g001')
const formatDateInput = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const today = new Date()
const rangeStartDefault = new Date(today)
rangeStartDefault.setDate(today.getDate() - 6)
const todayInput = formatDateInput(today)
const baselineDateStart = formatDateInput(rangeStartDefault)
const dateStart = ref(baselineDateStart)
const dateEnd = ref(todayInput)
const dailyDateStart = ref(baselineDateStart)
const dailyDateEnd = ref(todayInput)
const dateStartInput = ref<HTMLInputElement | null>(null)
const dateEndInput = ref<HTMLInputElement | null>(null)
const rangeDaysBetween = (startValue: string, endValue: string) => {
  const [startYear, startMonth, startDay] = startValue.split('-').map(Number)
  const [endYear, endMonth, endDay] = endValue.split('-').map(Number)
  const start = Date.UTC(startYear, startMonth - 1, startDay)
  const end = Date.UTC(endYear, endMonth - 1, endDay)
  return Math.max(1, Math.floor((end - start) / 86400000) + 1)
}
const dateFactorFor = (startValue: string) => {
  const start = Date.parse(`${startValue}T00:00:00Z`)
  const baseline = Date.parse(`${baselineDateStart}T00:00:00Z`)
  const shiftDays = Number.isFinite(start) ? Math.round((start - baseline) / 86400000) : 0
  return Math.min(1.22, Math.max(.78, 1 + shiftDays * .006))
}
const dateRangeDays = computed(() => rangeDaysBetween(dateStart.value, dateEnd.value))
const dateContextFactor = computed(() => dateFactorFor(dateStart.value))
const dailyDateRangeDays = computed(() => rangeDaysBetween(dailyDateStart.value, dailyDateEnd.value))
const dailyDateContextFactor = computed(() => dateFactorFor(dailyDateStart.value))
watch([dateStart, dateEnd], ([start, end]) => {
  dailyDateStart.value = start
  dailyDateEnd.value = end
})
const workspaceOwner = ref('juci-li')
const activeAccountScope = ref('all')
const ownerOptions = [
  { value: 'juci-li', label: 'Juci Li' },
  { value: 'mia-chen', label: 'Mia Chen' },
  { value: 'alex-wang', label: 'Alex Wang' },
]
const platform = ref('all')
const project = ref('all')
const account = ref('all')
const objective = ref('all')
const syncing = ref(false)
const refreshing = ref(false)
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimer: number | undefined
let refreshTimer: number | undefined
let syncTimer: number | undefined

const sessions = ref([
  { id: 'sess-g001', name: 'Candy Blast 投放咨询', active: true },
  { id: 'sess-g002', name: '素材优化建议', active: false },
  { id: 'sess-g003', name: '东南亚市场测试', active: false },
  { id: 'sess-d001', name: 'DramaBox 新剧推广', active: false },
])

const {
  projectOptions,
  channelOptions,
  accountOptions,
  allAccountOptions,
  objectiveOptions,
  filteredAccounts,
  aggregate,
  funnelTotals,
  trendPoints,
  selectedAccountLabel,
} = useDashboardScope(project, platform, account, objective, dateRangeDays, dateContextFactor, workspaceOwner, activeAccountScope)
const formatRangeDate = (value: string) => value.replace(/-/g, '/')
const dateRangeLabel = computed(() => `${formatRangeDate(dateStart.value)} – ${formatRangeDate(dateEnd.value)}`)
const sampleDateLabel = (index: number, total: number) => {
  const [year, month, day] = dateStart.value.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  const offset = total <= 1 ? 0 : Math.round((dateRangeDays.value - 1) * index / (total - 1))
  date.setDate(date.getDate() + offset)
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const dailyTrendPoints = computed(() => {
  const source = trendPoints.value
  const count = Math.max(1, dateRangeDays.value)
  if (!source.length) return []
  const interpolate = (field: 'rawSpend' | 'rawRevenue' | 'rawConversions' | 'rawClicks' | 'rawCtr' | 'rawRoas', position: number) => {
    const leftIndex = Math.floor(position)
    const rightIndex = Math.min(source.length - 1, Math.ceil(position))
    const ratio = position - leftIndex
    return source[leftIndex][field] + (source[rightIndex][field] - source[leftIndex][field]) * ratio
  }
  const raw = Array.from({ length: count }, (_, index) => {
    const position = count <= 1 ? 0 : index / (count - 1) * (source.length - 1)
    return {
      rawSpend: interpolate('rawSpend', position),
      rawRevenue: interpolate('rawRevenue', position),
      rawConversions: interpolate('rawConversions', position),
      rawClicks: interpolate('rawClicks', position),
      rawCtr: interpolate('rawCtr', position),
      rawRoas: interpolate('rawRoas', position),
    }
  })
  const normalizeTotal = (field: 'rawSpend' | 'rawConversions' | 'rawClicks', target: number) => {
    const total = raw.reduce((sum, item) => sum + item[field], 0)
    const scale = total ? target / total : 1
    raw.forEach(item => { item[field] *= scale })
  }
  normalizeTotal('rawSpend', aggregate.value.spend)
  normalizeTotal('rawConversions', aggregate.value.conversions)
  normalizeTotal('rawClicks', funnelTotals.value.clicks)
  raw.forEach(item => { item.rawRevenue = item.rawSpend * item.rawRoas })
  return raw.map((item, index) => ({ ...item, date: sampleDateLabel(index, count) }))
})
const displayTrendPoints = computed(() => {
  const raw = dailyTrendPoints.value.map(item => ({ ...item, axisLabel: item.date }))
  const values = (field: keyof typeof raw[number]) => raw.map(item => item[field])
  const range = (field: 'rawSpend' | 'rawRevenue' | 'rawConversions' | 'rawClicks' | 'rawCtr' | 'rawRoas') => {
    const items = values(field) as number[]
    return { min: Math.min(...items), max: Math.max(...items) }
  }
  const spendRange = range('rawSpend')
  const revenueRange = range('rawRevenue')
  const orderRange = range('rawConversions')
  const clickRange = range('rawClicks')
  const ctrRange = range('rawCtr')
  const roasRange = range('rawRoas')
  const scaleY = (value: number, min: number, max: number) => max === min ? 94 : 142 - (value - min) / (max - min) * 94
  const maxRevenue = Math.max(revenueRange.max, 1)
  const count = raw.length
  return raw.map((item, index) => {
    const x = count <= 1 ? 475 : 91 + index * 768 / (count - 1)
    const barHeight = 24 + item.rawRevenue / maxRevenue * 81
    return {
      ...item,
      spend: formatDashboardMoney(item.rawSpend),
      revenue: formatDashboardMoney(item.rawRevenue),
      orders: formatDashboardNumber(Math.round(item.rawConversions)),
      clicks: formatDashboardNumber(Math.round(item.rawClicks)),
      ctr: `${item.rawCtr.toFixed(2)}%`,
      roas: `${item.rawRoas.toFixed(2)}x`,
      x,
      spendY: scaleY(item.rawSpend, spendRange.min, spendRange.max),
      roasY: scaleY(item.rawRoas, roasRange.min, roasRange.max),
      ordersY: scaleY(item.rawConversions, orderRange.min, orderRange.max),
      clicksY: scaleY(item.rawClicks, clickRange.min, clickRange.max),
      ctrY: scaleY(item.rawCtr, ctrRange.min, ctrRange.max),
      barY: 155 - barHeight,
      barHeight,
      tooltipLeft: count <= 1 ? 50 : 6 + index / (count - 1) * 88,
    }
  })
})
const trendAxisTicks = computed(() => {
  const points = displayTrendPoints.value
  if (!points.length) return []
  const targetCount = dateRangeDays.value <= 14 ? points.length : dateRangeDays.value <= 31 ? 8 : dateRangeDays.value <= 90 ? 7 : dateRangeDays.value <= 180 ? 6 : 5
  if (points.length <= targetCount) return points.map((point, index) => ({ point, index }))
  const step = Math.ceil((points.length - 1) / Math.max(1, targetCount - 1))
  const indexes = Array.from({ length: Math.floor((points.length - 1) / step) + 1 }, (_, index) => index * step)
  return indexes.map(index => ({ point: points[index], index }))
})
const roasPath = computed(() => displayTrendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.roasY}`).join(''))
const ctrPath = computed(() => displayTrendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.ctrY}`).join(''))
const formatUsMoney = (value: number) => `US${formatDashboardMoney(value, 2)}`
const percentBadge = (current: number, previous: number, inverse = false) => {
  if (!previous) return { label: '—', tone: 'neutral' }
  const delta = (current - previous) / previous * 100
  const positive = inverse ? delta <= 0 : delta >= 0
  return {
    label: `${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(1)}%`,
    tone: positive ? 'positive' : 'negative',
  }
}
const pointBadge = (current: number, previous: number) => {
  const delta = current - previous
  return {
    label: `${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta).toFixed(2)}x`,
    tone: delta >= 0 ? 'positive' : 'negative',
  }
}
const overviewMetrics = computed(() => {
  const revenue = aggregate.value.spend * aggregate.value.kpiRoas
  const previousRevenue = aggregate.value.previousSpend * aggregate.value.previousKpiRoas
  const averageOrderValue = aggregate.value.conversions ? revenue / aggregate.value.conversions : 0
  const previousAverageOrderValue = aggregate.value.previousConversions ? previousRevenue / aggregate.value.previousConversions : 0
  return [
    { label: '花费', value: formatUsMoney(aggregate.value.spend), delta: percentBadge(aggregate.value.spend, aggregate.value.previousSpend, true) },
    { label: '收入', value: formatUsMoney(revenue), delta: percentBadge(revenue, previousRevenue) },
    { label: 'ROAS', value: `${aggregate.value.kpiRoas.toFixed(2)}x`, delta: pointBadge(aggregate.value.kpiRoas, aggregate.value.previousKpiRoas) },
    { label: '订单', value: formatDashboardNumber(aggregate.value.conversions), delta: percentBadge(aggregate.value.conversions, aggregate.value.previousConversions) },
    { label: '客单价', value: formatUsMoney(averageOrderValue), delta: percentBadge(averageOrderValue, previousAverageOrderValue) },
    { label: '每单成本', value: formatUsMoney(aggregate.value.cpi), delta: percentBadge(aggregate.value.cpi, aggregate.value.previousCpi, true) },
  ]
})
const overviewSecondaryMetrics = computed(() => {
  const impressions = funnelTotals.value.impressions
  const clicks = funnelTotals.value.clicks
  return [
    { label: '曝光', value: formatDashboardNumber(impressions) },
    { label: '链接点击', value: formatDashboardNumber(clicks) },
    { label: 'CTR', value: `${(impressions ? clicks / impressions * 100 : 0).toFixed(2)}%` },
    { label: 'CPM', value: formatUsMoney(impressions ? aggregate.value.spend / impressions * 1000 : 0) },
    { label: 'CPC', value: formatUsMoney(clicks ? aggregate.value.spend / clicks : 0) },
  ]
})

const hoveredTrendIndex = ref<number | null>(null)
const selectedTrendIndex = ref<number | null>(null)
const activeTrendIndex = computed(() => hoveredTrendIndex.value ?? selectedTrendIndex.value)
const activeTrendPoint = computed(() => {
  const index = activeTrendIndex.value
  return index === null ? null : { ...displayTrendPoints.value[index], index }
})

const toggleTrendSelection = (index: number) => {
  selectedTrendIndex.value = selectedTrendIndex.value === index ? null : index
}

type TrendMetric = 'spend' | 'revenue' | 'roas' | 'orders' | 'clicks' | 'ctr'
const trendMetricOptions: Array<{ key: TrendMetric, label: string }> = [
  { key: 'spend', label: '花费' },
  { key: 'revenue', label: '收入' },
  { key: 'roas', label: 'ROAS' },
  { key: 'orders', label: '订单' },
  { key: 'clicks', label: '点击' },
  { key: 'ctr', label: 'CTR' },
]
const activeTrendMetrics = ref<TrendMetric[]>(['spend', 'revenue', 'roas'])
const trendMetricPickerOpen = ref(false)
const hasTrendMetric = (metric: TrendMetric) => activeTrendMetrics.value.includes(metric)
const selectedTrendMetricOptions = computed(() => trendMetricOptions.filter(item => hasTrendMetric(item.key)))
const activeTrendMetricLabel = computed(() => selectedTrendMetricOptions.value.map(item => item.label).join('、'))
const trendBarMetricOrder: TrendMetric[] = ['spend', 'revenue', 'orders', 'clicks']
const selectedTrendBarMetrics = computed(() => trendBarMetricOrder.filter(hasTrendMetric))
const trendPointSpacing = computed(() => displayTrendPoints.value.length <= 1 ? 48 : 768 / (displayTrendPoints.value.length - 1))
const trendBarGap = computed(() => Math.min(3, Math.max(.45, trendPointSpacing.value * .08)))
const trendBarWidth = computed(() => {
  const count = Math.max(1, selectedTrendBarMetrics.value.length)
  const groupWidth = Math.min(48, Math.max(2.4, trendPointSpacing.value * .74))
  return Math.max(.8, Math.min(18, (groupWidth - (count - 1) * trendBarGap.value) / count))
})
const trendBarX = (pointX: number, metric: TrendMetric) => {
  const metrics = selectedTrendBarMetrics.value
  const index = metrics.indexOf(metric)
  if (index < 0) return pointX
  const totalWidth = metrics.length * trendBarWidth.value + Math.max(0, metrics.length - 1) * trendBarGap.value
  return pointX - totalWidth / 2 + index * (trendBarWidth.value + trendBarGap.value)
}
const trendHitWidth = computed(() => Math.max(4, Math.min(128, trendPointSpacing.value)))
const trendChartHeight = computed(() => dateRangeDays.value <= 7 ? 260 : dateRangeDays.value <= 31 ? 280 : dateRangeDays.value <= 90 ? 300 : 320)
const toggleTrendMetric = (metric: TrendMetric) => {
  if (hasTrendMetric(metric) && activeTrendMetrics.value.length === 1) return
  activeTrendMetrics.value = hasTrendMetric(metric)
    ? activeTrendMetrics.value.filter(item => item !== metric)
    : [...activeTrendMetrics.value, metric]
}
type HierarchyView = 'project' | 'channel'
type HierarchyPlatform = 'all' | 'meta' | 'google' | 'tiktok'
const hierarchyPlatformOptions: Array<{ value: HierarchyPlatform, label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'meta', label: 'Meta' },
  { value: 'google', label: 'Google' },
  { value: 'tiktok', label: 'TikTok' },
]
type HierarchyNode = {
  id: string
  kind: 'project' | 'channel' | 'account' | 'campaign' | 'ad-unit'
  label: string
  detail: string
  platform: HierarchyPlatform
  status: string
  budget: number
  spend: number
  roas: number
  objects: number
  children: HierarchyNode[]
}
const hierarchyView = ref<HierarchyView>('channel')
const hierarchyPlatform = ref<HierarchyPlatform>('all')
const hierarchySearch = ref('')
const hierarchyExpanded = ref<Set<string>>(new Set())
const campaignNames: Record<string, string[]> = {
  'candy-meta-ua': ['UGC 通关挑战', '高价值用户扩量', '美区素材扩量'],
  'candy-meta-retarget': ['LAL 价值优化', '再营销召回'],
  'dramabox-google': ['搜索核心词扩量', 'PMax 高价值用户', '日韩短剧兴趣词'],
  'candy-tiktok-us': ['Spark 素材测试', '美国 Broad 扩量', '互动人群再营销', '高留存素材组'],
}
const accountSpend = (item: any) => item.daily.reduce((total: number, day: any) => total + day.spend, 0)
const accountConversions = (item: any) => item.daily.reduce((total: number, day: any) => total + day.conversions, 0)
type AnalysisTableRow = {
  id: string
  name: string
  detail: string
  spend: number
  revenue: number
  orders: number
  roas: number
  delta: number
  clicks: number
  ctr: number
  status: string
  statusTone: 'normal' | 'warning' | 'danger'
}
const getAnalysisStatus = (roas: number, delta: number, orders: number): Pick<AnalysisTableRow, 'status' | 'statusTone'> => {
  if (!orders) return { status: '0 订单', statusTone: 'warning' }
  if (roas < 1) return { status: 'ROAS < 1', statusTone: 'danger' }
  if (roas < 2 || delta < -12) return { status: roas < 2 ? 'ROAS 偏低' : '环比下降', statusTone: 'warning' }
  return { status: '正常', statusTone: 'normal' }
}
const dateAtOffset = (startValue: string, offset: number) => {
  const [year, month, day] = startValue.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  date.setDate(date.getDate() + offset)
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`
}
const dailyAnalysisRows = computed<AnalysisTableRow[]>(() => {
  const count = Math.min(Math.max(dailyDateRangeDays.value, 1), 366)
  const localScale = dailyDateRangeDays.value / dateRangeDays.value * dailyDateContextFactor.value / dateContextFactor.value
  const scopedSpend = aggregate.value.spend * localScale
  const scopedOrders = aggregate.value.conversions * localScale
  const scopedClicks = funnelTotals.value.clicks * localScale
  const scopedRoas = aggregate.value.kpiRoas * (1 + (dailyDateContextFactor.value / dateContextFactor.value - 1) * .35)
  const weights = Array.from({ length: count }, (_, index) => .84 + ((index * 5) % 9) * .04)
  const weightTotal = weights.reduce((total, value) => total + value, 0)
  const roasOffsets = weights.map((_, index) => ((index % 5) - 2) * .07)
  const weightedRoasOffset = roasOffsets.reduce((total, offset, index) => total + offset * weights[index], 0) / weightTotal
  const scopedCtr = funnelTotals.value.impressions ? funnelTotals.value.clicks / funnelTotals.value.impressions * 100 : 0
  return weights.map((weight, index) => {
    const spend = scopedSpend * weight / weightTotal
    const roas = Math.max(.1, scopedRoas + roasOffsets[index] - weightedRoasOffset)
    const orders = scopedOrders * weight / weightTotal
    const clicks = scopedClicks * weight / weightTotal
    const delta = ((index * 11) % 23) - 9
    return {
      id: `day-${dateAtOffset(dailyDateStart.value, index)}`,
      name: dateAtOffset(dailyDateStart.value, index),
      detail: '按当前筛选范围汇总',
      spend,
      revenue: spend * roas,
      orders,
      roas,
      delta,
      clicks,
      ctr: scopedCtr,
      ...getAnalysisStatus(roas, delta, orders),
    }
  })
})
const accountAnalysisRows = computed<AnalysisTableRow[]>(() => filteredAccounts.value.map((item: any) => {
  const spend = accountSpend(item)
  const orders = accountConversions(item)
  const delta = item.previousSpend ? (spend - item.previousSpend) / item.previousSpend * 100 : 0
  return {
    id: item.id,
    name: item.account,
    detail: `${item.channelLabel} · ${item.projectLabel} · ${item.id}`,
    spend,
    revenue: spend * item.kpiRoas,
    orders,
    roas: item.kpiRoas,
    delta,
    clicks: item.funnel.clicks,
    ctr: item.funnel.impressions ? item.funnel.clicks / item.funnel.impressions * 100 : 0,
    ...getAnalysisStatus(item.kpiRoas, delta, orders),
  }
}))
const projectAnalysisRows = computed<AnalysisTableRow[]>(() => {
  const projects = [...new Map(filteredAccounts.value.map((item: any) => [item.project, item.projectLabel])).entries()]
  return projects.map(([projectId, projectLabel]) => {
    const items = filteredAccounts.value.filter((item: any) => item.project === projectId)
    const spend = items.reduce((total: number, item: any) => total + accountSpend(item), 0)
    const revenue = items.reduce((total: number, item: any) => total + accountSpend(item) * item.kpiRoas, 0)
    const previousSpend = items.reduce((total: number, item: any) => total + item.previousSpend, 0)
    const orders = items.reduce((total: number, item: any) => total + accountConversions(item), 0)
    const clicks = items.reduce((total: number, item: any) => total + item.funnel.clicks, 0)
    const impressions = items.reduce((total: number, item: any) => total + item.funnel.impressions, 0)
    const roas = spend ? revenue / spend : 0
    const delta = previousSpend ? (spend - previousSpend) / previousSpend * 100 : 0
    return {
      id: String(projectId),
      name: String(projectLabel),
      detail: `${items.length} 个投放账户 · ${items.reduce((total: number, item: any) => total + item.campaigns, 0)} 个投放任务`,
      spend, revenue, orders, roas, delta, clicks,
      ctr: impressions ? clicks / impressions * 100 : 0,
      ...getAnalysisStatus(roas, delta, orders),
    }
  })
})
const taskAnalysisRows = computed<AnalysisTableRow[]>(() => filteredAccounts.value.flatMap((item: any) => {
  const spend = accountSpend(item)
  const orders = accountConversions(item)
  const names = campaignNames[item.id] || []
  const accountCtr = item.funnel.impressions ? item.funnel.clicks / item.funnel.impressions * 100 : 0
  return Array.from({ length: item.campaigns }, (_, index) => {
    const taskSpend = spend / item.campaigns
    const roas = Math.max(.1, item.kpiRoas + (index - (item.campaigns - 1) / 2) * .08)
    const delta = ((index * 13 + item.account.length) % 37) - 16
    const taskOrders = orders / item.campaigns
    return {
      id: `task-${item.id}-${index + 1}`,
      name: names[index] || `${item.channelLabel} 投放任务 ${index + 1}`,
      detail: `${item.account} · Campaign ${String(index + 1).padStart(2, '0')}`,
      spend: taskSpend,
      revenue: taskSpend * roas,
      orders: taskOrders,
      roas,
      delta,
      clicks: item.funnel.clicks / item.campaigns,
      ctr: accountCtr,
      ...getAnalysisStatus(roas, delta, taskOrders),
    }
  })
}))
const adUnitAnalysisRows = computed<AnalysisTableRow[]>(() => taskAnalysisRows.value.flatMap(task => [0, 1].map((unitIndex) => {
  const weight = unitIndex ? .42 : .58
  const spend = task.spend * weight
  const roas = Math.max(.1, task.roas + (unitIndex ? -.09 : .07))
  const delta = task.delta + (unitIndex ? -4.6 : 3.2)
  const orders = task.orders * weight
  return {
    id: `unit-${task.id}-${unitIndex + 1}`,
    name: `${task.name} · ${unitIndex ? '拓量广告单元' : '核心广告单元'}`,
    detail: `${task.id} · AD Unit ${String(unitIndex + 1).padStart(2, '0')}`,
    spend,
    revenue: spend * roas,
    orders,
    roas,
    delta,
    clicks: task.clicks * weight,
    ctr: task.ctr,
    ...getAnalysisStatus(roas, delta, orders),
  }
})))
const createAccountNode = (item: any): HierarchyNode => {
  const spend = accountSpend(item)
  const names = campaignNames[item.id] || []
  const children = Array.from({ length: item.campaigns }, (_, index): HierarchyNode => {
    const weight = 1 / item.campaigns
    const campaignLabel = names[index] || `${item.channelLabel} 投放计划 ${index + 1}`
    const campaignSpend = spend * weight
    const campaignRoas = Math.max(.1, item.kpiRoas + (index - (item.campaigns - 1) / 2) * .08)
    const adUnits = [
      { label: '核心受众广告单元', weight: .58, delta: .06 },
      { label: '拓量测试广告单元', weight: .42, delta: -.08 },
    ].map((unit, unitIndex): HierarchyNode => ({
      id: `ad-unit-${item.id}-${index}-${unitIndex}`,
      kind: 'ad-unit',
      label: `${campaignLabel} · ${unit.label}`,
      detail: `${item.id} · Ad Unit ${String(unitIndex + 1).padStart(2, '0')}`,
      platform: item.channel,
      status: '投放中',
      budget: campaignSpend * unit.weight * 1.35,
      spend: campaignSpend * unit.weight,
      roas: Math.max(.1, campaignRoas + unit.delta),
      objects: Math.max(1, Math.round(accountConversions(item) * weight * unit.weight)),
      children: [],
    }))
    return {
      id: `campaign-${item.id}-${index}`,
      kind: 'campaign',
      label: campaignLabel,
      detail: `${item.id} · 投放计划 ${String(index + 1).padStart(2, '0')} · 2 个广告单元`,
      platform: item.channel,
      status: '投放中',
      budget: campaignSpend * 1.35,
      spend: campaignSpend,
      roas: campaignRoas,
      objects: adUnits.length,
      children: adUnits,
    }
  })
  return {
    id: `account-${item.id}`,
    kind: 'account',
    label: item.account,
    detail: `${item.id} · ${item.campaigns} Campaign`,
    platform: item.channel,
    status: '已连接',
    budget: spend * 1.35,
    spend,
    roas: item.kpiRoas,
    objects: item.campaigns,
    children,
  }
}
const makeGroupNode = (id: string, kind: 'project' | 'channel', label: string, detail: string, platformValue: HierarchyPlatform, accounts: any[]): HierarchyNode => {
  const accountNodes = accounts.map(createAccountNode)
  const spend = accountNodes.reduce((total, item) => total + item.spend, 0)
  const budget = accountNodes.reduce((total, item) => total + item.budget, 0)
  const roas = spend ? accountNodes.reduce((total, item) => total + item.spend * item.roas, 0) / spend : 0
  return { id, kind, label, detail, platform: platformValue, status: '已连接', budget, spend, roas, objects: accountNodes.length, children: accountNodes }
}
const hierarchyTree = computed<HierarchyNode[]>(() => {
  const scopedAccounts = filteredAccounts.value.filter(item => hierarchyPlatform.value === 'all' || item.channel === hierarchyPlatform.value)
  if (hierarchyView.value === 'channel') {
    return ['meta', 'google', 'tiktok'].flatMap(channelId => {
      const items = scopedAccounts.filter(item => item.channel === channelId)
      if (!items.length) return []
      return [makeGroupNode(`channel-${channelId}`, 'channel', items[0].channelLabel, `${items.length} 个广告账户`, channelId as HierarchyPlatform, items)]
    })
  }
  const projects = [...new Map(scopedAccounts.map(item => [item.project, item.projectLabel])).entries()]
  return projects.map(([projectId, projectLabel]) => {
    const items = scopedAccounts.filter(item => item.project === projectId)
    const channels = [...new Map(items.map(item => [item.channel, item.channelLabel])).entries()]
    const channelNodes = channels.map(([channelId, channelLabel]) => makeGroupNode(
      `project-${projectId}-${channelId}`,
      'channel',
      channelLabel,
      `${items.filter(item => item.channel === channelId).length} 个广告账户`,
      channelId as HierarchyPlatform,
      items.filter(item => item.channel === channelId),
    ))
    const projectNode = makeGroupNode(`project-${projectId}`, 'project', projectLabel, `${channelNodes.length} 个渠道`, 'all', items)
    projectNode.children = channelNodes
    projectNode.objects = channelNodes.length
    return projectNode
  })
})
const filterHierarchyNode = (node: HierarchyNode, query: string): HierarchyNode | null => {
  const children = node.children.map(child => filterHierarchyNode(child, query)).filter((child): child is HierarchyNode => Boolean(child))
  const matches = !query || `${node.label} ${node.detail} ${node.id}`.toLowerCase().includes(query)
  return matches || children.length ? { ...node, children } : null
}
const visibleHierarchyTree = computed(() => hierarchyTree.value
  .map(node => filterHierarchyNode(node, hierarchySearch.value.trim().toLowerCase()))
  .filter((node): node is HierarchyNode => Boolean(node)))
const hierarchyRows = computed(() => {
  const rows: Array<HierarchyNode & { level: number }> = []
  const walk = (items: HierarchyNode[], level: number) => items.forEach(item => {
    rows.push({ ...item, level })
    if ((hierarchySearch.value || hierarchyExpanded.value.has(item.id)) && item.children.length) walk(item.children, level + 1)
  })
  walk(visibleHierarchyTree.value, 0)
  return rows
})
const hierarchyIcon = (node: HierarchyNode) => node.kind === 'project' ? 'P' : node.kind === 'account' ? 'A' : node.kind === 'campaign' ? 'C' : node.kind === 'ad-unit' ? 'U' : node.label.charAt(0)
const toggleHierarchy = (id: string) => {
  const next = new Set(hierarchyExpanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  hierarchyExpanded.value = next
}
const collectHierarchyBranches = (items: HierarchyNode[], result = new Set<string>()) => {
  items.forEach(item => {
    if (item.children.length) result.add(item.id)
    collectHierarchyBranches(item.children, result)
  })
  return result
}
const expandHierarchy = () => { hierarchyExpanded.value = collectHierarchyBranches(hierarchyTree.value) }
const collapseHierarchy = () => { hierarchyExpanded.value = new Set() }
const changeHierarchyView = (view: HierarchyView) => {
  hierarchyView.value = view
  hierarchyExpanded.value = new Set()
}

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

const changeDateRange = (boundary: 'start' | 'end') => {
  if (dateStart.value > dateEnd.value) {
    if (boundary === 'start') dateEnd.value = dateStart.value
    else dateStart.value = dateEnd.value
  }
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  showToast(`统计区间：${formatRangeDate(dateStart.value)} 至 ${formatRangeDate(dateEnd.value)}，下方数据已同步更新`)
}

const openDatePicker = (boundary: 'start' | 'end') => {
  const input = boundary === 'start' ? dateStartInput.value : dateEndInput.value
  if (!input) return
  input.focus()
  if (typeof input.showPicker === 'function') input.showPicker()
}

const handleTimeFilterClick = (event: MouseEvent) => {
  if ((event.target as HTMLElement).tagName === 'INPUT') return
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  openDatePicker(event.clientX < rect.left + rect.width * .52 ? 'start' : 'end')
}

const resetAnalysisFilters = () => {
  project.value = 'all'
  platform.value = 'all'
  account.value = 'all'
  objective.value = 'all'
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  hierarchyPlatform.value = 'all'
  hierarchySearch.value = ''
  hierarchyExpanded.value = new Set()
}

const changeWorkspaceOwner = () => {
  activeAccountScope.value = 'all'
  resetAnalysisFilters()
  const label = ownerOptions.find(item => item.value === workspaceOwner.value)?.label || '当前负责人'
  showToast(`负责人：${label}，账号和项目范围已同步更新`)
}

const changeActiveAccountScope = () => {
  resetAnalysisFilters()
  const label = allAccountOptions.value.find(item => item.id === activeAccountScope.value)?.account || '全部 active 账号'
  showToast(`账号范围：${label}，项目列表和下方数据已同步更新`)
}

const changePlatform = () => {
  account.value = 'all'
  if (platform.value !== 'meta') objective.value = 'all'
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  const label = channelOptions.value.find(item => item.value === platform.value)?.label || '全部渠道'
  showToast(`渠道：${label}，下方数据已同步更新`)
}

const changeProject = () => {
  if (platform.value !== 'all' && !channelOptions.value.some(item => item.value === platform.value)) platform.value = 'all'
  account.value = 'all'
  if (platform.value !== 'meta') objective.value = 'all'
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  const label = projectOptions.value.find(item => item.value === project.value)?.label || '全部项目'
  showToast(`项目：${label}，下方数据已同步更新`)
}

const changeAccount = () => {
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  showToast(`账户：${selectedAccountLabel.value}，下方数据已同步更新`)
}

const changeObjective = () => {
  if (objective.value !== 'all') {
    platform.value = 'meta'
    if (project.value !== 'all' && !channelOptions.value.some(item => item.value === 'meta')) project.value = 'all'
    account.value = 'all'
  }
  hoveredTrendIndex.value = null
  selectedTrendIndex.value = null
  const label = objectiveOptions.find(item => item.value === objective.value)?.label || '全部投放目标'
  showToast(`Meta 投放目标：${label}，下方数据已同步更新`)
}

const handleRefresh = () => {
  window.clearTimeout(refreshTimer)
  refreshing.value = false
  requestAnimationFrame(() => { refreshing.value = true })
  showToast('视图已刷新')
  refreshTimer = window.setTimeout(() => { refreshing.value = false }, 700)
}

const handleSyncData = () => {
  window.clearTimeout(syncTimer)
  syncing.value = false
  requestAnimationFrame(() => { syncing.value = true })
  showToast('广告数据已同步')
  syncTimer = window.setTimeout(() => { syncing.value = false }, 850)
}

onBeforeUnmount(() => {
  window.clearTimeout(toastTimer)
  window.clearTimeout(refreshTimer)
  window.clearTimeout(syncTimer)
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
          <label class="header-scope-field owner-scope-field">
            <select v-model="workspaceOwner" aria-label="选择负责人" @change="changeWorkspaceOwner">
              <option v-for="item in ownerOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label class="header-scope-field account-scope-field">
            <select v-model="activeAccountScope" aria-label="选择 active 账号" @change="changeActiveAccountScope">
              <option value="all">全部 active 账号</option>
              <option v-for="item in allAccountOptions" :key="item.id" :value="item.id">{{ item.account }}</option>
            </select>
          </label>
          <button class="sync-button" :class="{ syncing }" type="button" aria-label="同步数据" @click="handleSyncData">
            <span class="icon material-symbols-outlined" aria-hidden="true">sync</span><span>数据同步</span>
          </button>
          <button class="refresh-button" :class="{ refreshing }" type="button" aria-label="刷新视图" @click="handleRefresh">
            <span class="icon material-symbols-outlined" aria-hidden="true">refresh</span><span class="refresh-label">刷新视图</span>
          </button>
        </div>
      </header>

      <div class="content replay-content workspace-page-content">
        <section class="analysis-filter-card" aria-label="数据分析视图">
          <div class="analysis-filter-head">
            <div class="analysis-filter-tab active"><span class="material-symbols-outlined" aria-hidden="true">tune</span><strong>分析视图</strong></div>
            <span class="analysis-filter-count" aria-live="polite">当前范围 · {{ filteredAccounts.length }} 个账户</span>
          </div>
          <div class="analysis-filter-controls">
            <label class="analysis-filter-chip project-filter-chip">
              <span>项目：</span>
              <select v-model="project" aria-label="分析视图筛选项目" @change="changeProject">
                <option value="all">全部项目</option>
                <option v-for="item in projectOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="analysis-filter-chip channel-filter-chip">
              <span>渠道：</span>
              <select v-model="platform" aria-label="分析视图筛选渠道" @change="changePlatform">
                <option value="all">全部渠道</option>
                <option v-for="item in channelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="analysis-filter-chip account-filter-chip">
              <span>账户：</span>
              <select v-model="account" aria-label="分析视图筛选账户" @change="changeAccount">
                <option value="all">全部账户</option>
                <option v-for="item in accountOptions" :key="item.id" :value="item.id">{{ item.account }}</option>
              </select>
            </label>
            <label class="analysis-filter-chip objective-filter-chip">
              <span>投放目标：</span>
              <select v-model="objective" aria-label="Meta 投放目标" @change="changeObjective">
                <option value="all">全部投放目标</option>
                <option v-for="item in objectiveOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <div class="analysis-filter-chip time-filter-chip" role="group" aria-label="自定义时间区间" @click="handleTimeFilterClick">
              <span class="material-symbols-outlined" aria-hidden="true">calendar_today</span>
              <span>时间：</span>
              <div class="time-date-hotspot" role="button" tabindex="0" aria-label="修改开始日期" @click.stop="openDatePicker('start')" @keydown.enter.prevent="openDatePicker('start')" @keydown.space.prevent="openDatePicker('start')">
                <input ref="dateStartInput" v-model="dateStart" tabindex="-1" type="date" :max="dateEnd" aria-label="开始日期" @change="changeDateRange('start')">
              </div>
              <span class="time-range-separator" aria-hidden="true">至</span>
              <div class="time-date-hotspot" role="button" tabindex="0" aria-label="修改结束日期" @click.stop="openDatePicker('end')" @keydown.enter.prevent="openDatePicker('end')" @keydown.space.prevent="openDatePicker('end')">
                <input ref="dateEndInput" v-model="dateEnd" tabindex="-1" type="date" :min="dateStart" :max="todayInput" aria-label="结束日期" @change="changeDateRange('end')">
              </div>
            </div>
          </div>
        </section>

        <section class="overview-card" aria-labelledby="overview-title">
          <div class="overview-card-head">
            <span class="material-symbols-outlined" aria-hidden="true">monitoring</span>
            <strong id="overview-title">数据总览</strong>
            <span>当前筛选范围</span>
          </div>
          <div class="replay-kpis">
            <article v-for="metric in overviewMetrics" :key="metric.label" class="replay-kpi">
              <div class="kpi-head"><span>{{ metric.label }}</span></div>
              <div class="kpi-value" :class="{ dense: metric.value.length >= 12 }">{{ metric.value }}</div>
              <span class="kpi-delta" :class="metric.delta.tone">{{ metric.delta.label }}</span>
            </article>
          </div>
          <div class="overview-secondary-row" aria-label="辅助指标">
            <div v-for="metric in overviewSecondaryMetrics" :key="metric.label" class="overview-secondary-item">
              <span>{{ metric.label }}</span><strong>{{ metric.value }}</strong>
            </div>
          </div>
        </section>

        <section class="replay-card">
          <div class="replay-card-head trend-card-head">
            <div><h2>趋势监控</h2><p>自定义指标随时间变化 · {{ trendGranularityLabel }}</p></div>
            <div class="trend-metric-customizer">
              <div class="trend-metric-options" role="group" aria-label="已选趋势指标">
                <button v-for="item in selectedTrendMetricOptions" :key="item.key" type="button" :data-trend-metric="item.key" class="active" aria-pressed="true" :title="`移除${item.label}`" @click="toggleTrendMetric(item.key)">{{ item.label }}</button>
              </div>
              <button class="trend-custom-button" type="button" :aria-expanded="trendMetricPickerOpen" @click="trendMetricPickerOpen = !trendMetricPickerOpen"><span class="material-symbols-outlined" aria-hidden="true">tune</span>自定义指标</button>
              <div v-if="trendMetricPickerOpen" class="trend-metric-popover" role="dialog" aria-label="自定义趋势指标">
                <strong>选择趋势指标</strong>
                <label v-for="item in trendMetricOptions" :key="item.key"><input type="checkbox" :checked="hasTrendMetric(item.key)" @change="toggleTrendMetric(item.key)"><span><i class="legend-dot" :class="item.key"></i>{{ item.label }}</span></label>
                <small>至少保留 1 个指标</small>
                <button type="button" @click="trendMetricPickerOpen = false">完成</button>
              </div>
            </div>
          </div>
          <div class="trend-grid">
            <div class="chart-panel" :style="{ '--trend-chart-height': `${trendChartHeight}px`, '--trend-svg-height': `${trendChartHeight - 40}px` }">
              <div class="chart-legend"><span v-for="item in selectedTrendMetricOptions" :key="item.key" class="legend-item"><i class="legend-dot" :class="item.key"></i>{{ item.label }}</span></div>
              <svg viewBox="60 24 830 138" preserveAspectRatio="none" role="img" :aria-label="`${dateRangeLabel} ${activeTrendMetricLabel}趋势图`">
                <g stroke="#ecebea" stroke-width="1"><path d="M52 32H892M52 73H892M52 114H892M52 155H892" /></g>
                <g v-if="hasTrendMetric('spend')" class="chart-bars spend"><rect v-for="point in displayTrendPoints" :key="`spend-bar-${point.date}`" :x="trendBarX(point.x, 'spend')" :y="point.spendY" :width="trendBarWidth" :height="155 - point.spendY" rx="2" /></g>
                <g v-if="hasTrendMetric('revenue')" class="chart-bars revenue"><rect v-for="point in displayTrendPoints" :key="`revenue-bar-${point.date}`" :x="trendBarX(point.x, 'revenue')" :y="point.barY" :width="trendBarWidth" :height="point.barHeight" rx="2" /></g>
                <g v-if="hasTrendMetric('orders')" class="chart-bars orders"><rect v-for="point in displayTrendPoints" :key="`orders-bar-${point.date}`" :x="trendBarX(point.x, 'orders')" :y="point.ordersY" :width="trendBarWidth" :height="155 - point.ordersY" rx="2" /></g>
                <g v-if="hasTrendMetric('clicks')" class="chart-bars clicks"><rect v-for="point in displayTrendPoints" :key="`clicks-bar-${point.date}`" :x="trendBarX(point.x, 'clicks')" :y="point.clicksY" :width="trendBarWidth" :height="155 - point.clicksY" rx="2" /></g>
                <path v-if="hasTrendMetric('roas')" :d="roasPath" fill="none" stroke="#dd7d00" stroke-width="1.35" />
                <path v-if="hasTrendMetric('ctr')" :d="ctrPath" fill="none" stroke="#d946ef" stroke-width="1.35" />
                <g v-if="hasTrendMetric('roas')" fill="#dd7d00" stroke="#fff" stroke-width="1"><circle v-for="point in displayTrendPoints" :key="`roas-${point.date}`" :cx="point.x" :cy="point.roasY" r="2.1" /></g>
                <g v-if="hasTrendMetric('ctr')" fill="#d946ef" stroke="#fff" stroke-width="1"><circle v-for="point in displayTrendPoints" :key="`ctr-${point.date}`" :cx="point.x" :cy="point.ctrY" r="2.1" /></g>
                <g v-if="activeTrendPoint" class="chart-active-markers" aria-hidden="true">
                  <line :x1="activeTrendPoint.x" :x2="activeTrendPoint.x" y1="24" y2="155" />
                  <rect v-if="hasTrendMetric('spend')" class="spend" :x="trendBarX(activeTrendPoint.x, 'spend')" :y="activeTrendPoint.spendY" :width="trendBarWidth" :height="155 - activeTrendPoint.spendY" rx="2" />
                  <rect v-if="hasTrendMetric('revenue')" class="revenue" :x="trendBarX(activeTrendPoint.x, 'revenue')" :y="activeTrendPoint.barY" :width="trendBarWidth" :height="activeTrendPoint.barHeight" rx="2" />
                  <rect v-if="hasTrendMetric('orders')" class="orders" :x="trendBarX(activeTrendPoint.x, 'orders')" :y="activeTrendPoint.ordersY" :width="trendBarWidth" :height="155 - activeTrendPoint.ordersY" rx="2" />
                  <rect v-if="hasTrendMetric('clicks')" class="clicks" :x="trendBarX(activeTrendPoint.x, 'clicks')" :y="activeTrendPoint.clicksY" :width="trendBarWidth" :height="155 - activeTrendPoint.clicksY" rx="2" />
                  <circle v-if="hasTrendMetric('roas')" class="roas" :cx="activeTrendPoint.x" :cy="activeTrendPoint.roasY" r="3.5" />
                  <circle v-if="hasTrendMetric('ctr')" class="ctr" :cx="activeTrendPoint.x" :cy="activeTrendPoint.ctrY" r="3.5" />
                </g>
                <rect
                  v-for="(point, index) in displayTrendPoints"
                  :key="`hit-${point.date}`"
                  class="chart-hit-area"
                  :class="{ selected: selectedTrendIndex === index }"
                  :x="point.x - trendHitWidth / 2"
                  y="24"
                  :width="trendHitWidth"
                  height="138"
                  role="button"
                  tabindex="0"
                  :aria-label="`${point.date}，花费 ${point.spend}，收入 ${point.revenue}，ROAS ${point.roas}，订单 ${point.orders}，点击 ${point.clicks}，CTR ${point.ctr}`"
                  @mouseenter="hoveredTrendIndex = index"
                  @mouseleave="hoveredTrendIndex = null"
                  @focus="hoveredTrendIndex = index"
                  @blur="hoveredTrendIndex = null"
                  @click="toggleTrendSelection(index)"
                  @keydown.enter.prevent="toggleTrendSelection(index)"
                  @keydown.space.prevent="toggleTrendSelection(index)"
                />
              </svg>
              <div
                v-if="activeTrendPoint"
                class="chart-tooltip"
                :style="{ left: `${activeTrendPoint.tooltipLeft}%` }"
                role="status"
                aria-live="polite"
              >
                <strong>{{ activeTrendPoint.date }}</strong>
                <div v-if="hasTrendMetric('spend')"><span><i class="legend-dot spend"></i>花费</span><b>{{ activeTrendPoint.spend }}</b></div>
                <div v-if="hasTrendMetric('revenue')"><span><i class="legend-dot revenue"></i>收入</span><b>{{ activeTrendPoint.revenue }}</b></div>
                <div v-if="hasTrendMetric('roas')"><span><i class="legend-dot roas"></i>ROAS</span><b>{{ activeTrendPoint.roas }}</b></div>
                <div v-if="hasTrendMetric('orders')"><span><i class="legend-dot orders"></i>订单</span><b>{{ activeTrendPoint.orders }}</b></div>
                <div v-if="hasTrendMetric('clicks')"><span><i class="legend-dot clicks"></i>点击</span><b>{{ activeTrendPoint.clicks }}</b></div>
                <div v-if="hasTrendMetric('ctr')"><span><i class="legend-dot ctr"></i>CTR</span><b>{{ activeTrendPoint.ctr }}</b></div>
              </div>
              <div class="chart-axis-labels" aria-hidden="true">
                <button
                  v-for="tick in trendAxisTicks"
                  :key="`axis-${tick.point.date}`"
                  type="button"
                  :style="{ left: `${(tick.point.x - 60) / 830 * 100}%` }"
                  :class="{ active: activeTrendIndex === tick.index, selected: selectedTrendIndex === tick.index }"
                  @mouseenter="hoveredTrendIndex = tick.index"
                  @mouseleave="hoveredTrendIndex = null"
                  @focus="hoveredTrendIndex = tick.index"
                  @blur="hoveredTrendIndex = null"
                  @click="toggleTrendSelection(tick.index)"
                >{{ tick.point.axisLabel }}</button>
              </div>
            </div>
          </div>
        </section>

        <AnalysisMetricTable
          title="分天数据概览"
          subtitle="按日期查看当前筛选范围内的投放表现"
          entity-label="日期"
          search-placeholder="搜索日期"
          date-filter
          v-model:date-start="dailyDateStart"
          v-model:date-end="dailyDateEnd"
          :max-date="todayInput"
          :rows="dailyAnalysisRows"
        />

        <section class="replay-card hierarchy-card" aria-label="投放层级分析">
          <div class="hierarchy-card-head">
            <span class="material-symbols-outlined" aria-hidden="true">account_tree</span>
            <div><h2>投放层级分析</h2><p>查看项目、渠道、账户、投放计划与广告单元的完整关系</p></div>
          </div>
          <div class="hierarchy-toolbar">
            <div class="hierarchy-toolbar-left">
              <div class="hierarchy-view-switch" role="group" aria-label="层级视角">
                <button type="button" :class="{ active: hierarchyView === 'project' }" @click="changeHierarchyView('project')">按项目</button>
                <button type="button" :class="{ active: hierarchyView === 'channel' }" @click="changeHierarchyView('channel')">按渠道</button>
              </div>
              <label class="hierarchy-search-field">
                <span class="material-symbols-outlined" aria-hidden="true">search</span>
                <input v-model="hierarchySearch" type="search" placeholder="搜索名称或 ID" aria-label="搜索层级名称或 ID">
              </label>
            </div>
            <div class="hierarchy-toolbar-right" role="group" aria-label="层级渠道筛选">
              <button v-for="item in hierarchyPlatformOptions" :key="item.value" type="button" :data-hierarchy-platform="item.value" :class="['hierarchy-filter-button', { active: hierarchyPlatform === item.value }]" @click="hierarchyPlatform = item.value">{{ item.label }}</button>
              <button class="hierarchy-action-button" type="button" @click="expandHierarchy">全部展开</button>
              <button class="hierarchy-action-button" type="button" @click="collapseHierarchy">收起</button>
            </div>
          </div>
          <div class="hierarchy-table-head" role="row"><span>层级 / 名称</span><span>状态</span><span>预算</span><span>花费</span><span>ROAS</span><span>对象数</span></div>
          <div class="hierarchy-table-body" role="tree" aria-label="项目与渠道层级">
            <div
              v-for="node in hierarchyRows"
              :key="node.id"
              class="hierarchy-row"
              role="treeitem"
              :aria-level="node.level + 1"
              :aria-expanded="node.children.length ? hierarchyExpanded.has(node.id) : undefined"
            >
              <div class="hierarchy-name" :style="{ '--level': node.level }">
                <button v-if="node.children.length" class="hierarchy-expander" :class="{ open: hierarchyExpanded.has(node.id) }" type="button" :aria-label="hierarchyExpanded.has(node.id) ? `收起 ${node.label}` : `展开 ${node.label}`" @click.stop="toggleHierarchy(node.id)">›</button>
                <span v-else class="hierarchy-expander placeholder" aria-hidden="true">›</span>
                <span class="hierarchy-node-icon" :class="[node.platform, node.kind]">{{ hierarchyIcon(node) }}</span>
                <span class="hierarchy-node-copy"><strong>{{ node.label }}</strong><small>{{ node.detail }}</small></span>
              </div>
              <span class="hierarchy-status" data-label="状态"><i></i>{{ node.status }}</span>
              <span class="hierarchy-number" data-label="预算">{{ formatUsMoney(node.budget) }}</span>
              <span class="hierarchy-number" data-label="花费">{{ formatUsMoney(node.spend) }}</span>
              <span class="hierarchy-number" data-label="ROAS">{{ node.roas.toFixed(2) }}x</span>
              <span class="hierarchy-number" data-label="对象数">{{ node.objects }}</span>
            </div>
            <div v-if="!hierarchyRows.length" class="hierarchy-empty">没有匹配的层级数据</div>
          </div>
        </section>

        <AnalysisMetricTable
          title="投放账户分析"
          subtitle="按广告账户查看渠道投放效率"
          entity-label="账户"
          search-placeholder="搜索账户名称或 ID"
          :rows="accountAnalysisRows"
        />

        <AnalysisMetricTable
          title="投放项目分析"
          subtitle="对应 ANIFORCE 项目层级的汇总表现"
          entity-label="项目"
          search-placeholder="搜索项目名称或 ID"
          :rows="projectAnalysisRows"
        />

        <AnalysisMetricTable
          title="投放任务分析"
          subtitle="对应 ANIFORCE Campaign 任务层级的投放表现"
          entity-label="任务"
          search-placeholder="搜索任务名称或 ID"
          :rows="taskAnalysisRows"
        />

        <AnalysisMetricTable
          title="投放广告单元分析"
          subtitle="对应 ANIFORCE 广告单元层级的素材与定向表现"
          entity-label="广告单元"
          search-placeholder="搜索广告单元名称或 ID"
          :rows="adUnitAnalysisRows"
        />
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

.dashboard-shell.embedded .header-scope-field,
.dashboard-shell.embedded .header-scope-field select,
.dashboard-shell.embedded .filter-field .period-select,
.dashboard-shell.embedded .sync-button,
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

.dashboard-shell.embedded .overview-secondary-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-shell.embedded .analysis-filter-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-shell.embedded .analysis-filter-chip,
.dashboard-shell.embedded .analysis-filter-chip select {
  width: 100%;
  min-width: 0;
}

.dashboard-shell.embedded .account-filter-chip,
.dashboard-shell.embedded .objective-filter-chip,
.dashboard-shell.embedded .time-filter-chip {
  grid-column: 1 / -1;
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
.header-scope-field { display: inline-flex; flex: 0 0 auto; align-items: center; min-width: 0; }
.header-scope-field select { height: 34px; padding: 0 30px 0 11px; border: 1px solid var(--hairline-strong); border-radius: 8px; outline: none; background: #fff; color: var(--charcoal); font-family: inherit; font-size: 13px; font-weight: 500; cursor: pointer; }
.header-scope-field select:focus { border-color: #9abce8; box-shadow: 0 0 0 2px rgb(79 143 232 / 12%); }
.owner-scope-field select { width: 118px; }
.account-scope-field select { width: 210px; }
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
.refresh-button .icon { font-size: 15px; }
.sync-button { height: 34px; min-width: 108px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px; border: 1px solid var(--hairline-strong); border-radius: 8px; background: #fff; color: var(--charcoal); font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer; transition: background-color .16s ease,border-color .16s ease; }
.dashboard-shell .sync-button { min-width: 108px; }
.dashboard-shell .refresh-button { min-width: 116px; }
.dashboard-shell .sync-button,.dashboard-shell .refresh-button { flex: 0 0 auto; white-space: nowrap; }
.sync-button:hover { border-color: #aaa69f; background: var(--surface-soft); }
.sync-button .icon { font-size: 16px; }
.refreshing .icon,.syncing .icon { animation: spin .65s ease; }
@keyframes spin { to { transform: rotate(360deg); } }

.replay-content { width: 100%; max-width: none; margin: 0; padding-top: 24px; padding-bottom: 64px; }
.quiet-badge { display: inline-flex; align-items: center; min-height: 28px; padding: 4px 10px; border: 1px solid var(--hairline); border-radius: 999px; background: #fff; color: var(--steel); font-size: 11px; font-weight: 600; white-space: nowrap; }
button.quiet-badge { cursor: pointer; font-family: inherit; }

.analysis-filter-card { margin-bottom: 12px; overflow: hidden; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; }
.analysis-filter-head { min-height: 46px; display: flex; align-items: stretch; justify-content: space-between; gap: 14px; padding: 0 14px; border-bottom: 1px solid var(--hairline-soft); }
.analysis-filter-tab { position: relative; display: inline-flex; align-items: center; gap: 7px; padding: 0 4px; color: var(--slate); white-space: nowrap; }
.analysis-filter-tab.active::after { content: ""; position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: var(--workspace-action-primary,#137fec); }
.analysis-filter-tab .material-symbols-outlined { color: #3276cc; font-size: 17px; }
.analysis-filter-tab strong { font-size: 13px; font-weight: 600; }
.analysis-filter-count { align-self: center; color: var(--steel); font-size: 11px; font-weight: 500; white-space: nowrap; }
.analysis-filter-controls { display: grid; grid-template-columns: minmax(150px,.8fr) minmax(138px,.75fr) minmax(205px,1.2fr) minmax(220px,1.18fr) minmax(326px,1.7fr); align-items: center; gap: 6px; padding: 9px 14px; background: #fff; }
.analysis-filter-chip { width: 100%; min-width: 0; height: 32px; display: inline-flex; align-items: center; padding: 0 10px; border-radius: 8px; background: var(--surface); color: var(--slate); white-space: nowrap; }
.analysis-filter-chip.account-filter-chip,.analysis-filter-chip.objective-filter-chip { min-width: 0; }
.analysis-filter-chip.time-filter-chip { min-width: 0; margin-left: 0; background: #fff; box-shadow: inset 0 0 0 1px var(--hairline); cursor: pointer; }
.analysis-filter-chip.time-filter-chip > .material-symbols-outlined { margin-right: 5px; color: var(--steel); font-size: 14px; }
.analysis-filter-chip > span { flex: 0 0 auto; color: var(--steel); font-size: 12px; line-height: 1.2; font-weight: 500; }
.analysis-filter-chip select { min-width: 0; flex: 1; padding: 0 20px 0 0; border: 0; outline: none; background: transparent; color: var(--charcoal); font-family: inherit; font-size: 12px; line-height: 1.2; font-weight: 600; cursor: pointer; }
.analysis-filter-chip.objective-filter-chip select { min-width: 108px; }
.time-date-hotspot { min-width: 0; flex: 1 1 0; display: flex; align-items: center; border-radius: 5px; cursor: pointer; }
.time-date-hotspot:focus-visible { outline: 2px solid rgb(79 143 232 / 24%); outline-offset: 1px; }
.time-filter-chip input { width: 100%; min-width: 0; height: 24px; padding: 0 2px; border: 0; outline: none; background: transparent; color: var(--charcoal); color-scheme: light; font-family: inherit; font-size: 11px; font-weight: 600; pointer-events: none; cursor: pointer; }
.time-filter-chip input::-webkit-calendar-picker-indicator { width: 13px; height: 13px; margin-left: 1px; padding: 0; opacity: .58; cursor: pointer; }
.analysis-filter-chip .time-range-separator { margin: 0 5px; color: var(--steel); font-weight: 400; }
.analysis-filter-chip:focus-within { box-shadow: 0 0 0 2px rgb(79 143 232 / 14%); }
.overview-card { overflow: hidden; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; }
.overview-card-head { min-height: 44px; display: flex; align-items: center; gap: 7px; padding: 0 16px; border-bottom: 1px solid var(--hairline-soft); color: var(--slate); }
.overview-card-head .material-symbols-outlined { color: #3276cc; font-size: 17px; }
.overview-card-head strong { color: var(--charcoal); font-size: 13px; font-weight: 600; }
.overview-card-head > span:last-child { margin-left: auto; color: var(--steel); font-size: 11px; font-weight: 500; }
.replay-kpis { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 0; margin-top: 0; overflow: hidden; background: #fff; }
.replay-kpi { position: relative; min-width: 0; padding: 20px 14px 18px; border: 0; border-radius: 0; background: #fff; }
.replay-kpi:nth-child(2),.replay-kpi:nth-child(3) { background: #fbfcfd; }
.replay-kpi:not(:last-child)::after { content: ""; position: absolute; top: 20%; right: 0; bottom: 20%; width: 1px; background: #f0efed; }
.kpi-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--steel); font-size: 13px; font-weight: 600; }
.kpi-head .icon { color: var(--steel); font-size: 18px; font-weight: 400; }
.kpi-value { margin-top: 11px; color: var(--ink); font-size: clamp(20px,1.65vw,28px); line-height: 1.08; font-weight: 650; letter-spacing: -.55px; white-space: nowrap; }
.kpi-value.dense { font-size: clamp(18px,1.4vw,24px); letter-spacing: -.8px; }
.kpi-delta { width: fit-content; display: inline-flex; align-items: center; margin-top: 10px; padding: 3px 7px; border-radius: 4px; background: #f0efed; color: var(--slate); font-size: 11px; font-weight: 600; }
.kpi-delta.positive { background: #e8f7ee; color: #12804a; }
.kpi-delta.negative { background: #fdecec; color: #c73c36; }
.overview-secondary-row { min-height: 52px; display: grid; grid-template-columns: repeat(5,minmax(0,1fr)); align-items: center; border-top: 1px solid var(--hairline); background: #fafaf9; }
.overview-secondary-item { position: relative; min-width: 0; display: flex; align-items: baseline; gap: 8px; padding: 10px 18px; white-space: nowrap; }
.overview-secondary-item:not(:last-child)::after { content: ""; position: absolute; top: 24%; right: 0; bottom: 24%; width: 1px; background: #e8e6e2; }
.overview-secondary-item span { color: var(--steel); font-size: 12px; }
.overview-secondary-item strong { overflow: hidden; color: var(--ink); font-size: 14px; font-weight: 650; text-overflow: ellipsis; }

.replay-card { margin-top: 16px; border: 1px solid var(--hairline); border-radius: 12px; background: #fff; overflow: hidden; }
.replay-card-head { min-height: 58px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--hairline-soft); }
.replay-card-head h2 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.replay-card-head p { margin: 3px 0 0; color: var(--steel); font-size: 12px; }
.soft-chip { display: inline-flex; align-items: center; min-height: 26px; padding: 3px 9px; border-radius: 6px; background: var(--surface); color: var(--slate); font-size: 11px; font-weight: 600; }
.trend-card-head { min-height: 64px; }
.trend-metric-customizer { position: relative; display: flex; align-items: center; justify-content: flex-end; gap: 7px; }
.trend-metric-options { display: inline-flex; align-items: center; gap: 6px; }
.trend-metric-options button { min-width: 54px; height: 32px; padding: 0 12px; border: 1px solid var(--hairline); border-radius: 8px; background: #fff; color: var(--slate); font-family: inherit; font-size: 12px; font-weight: 500; cursor: pointer; transition: border-color .16s ease,background-color .16s ease,color .16s ease,box-shadow .16s ease; }
.trend-metric-options button:hover { border-color: #b8d4f5; background: #f7fbff; color: #276fca; }
.trend-metric-options button.active { border-color: #9fc9fb; background: #eef6ff; color: #176bc3; font-weight: 600; box-shadow: inset 0 0 0 1px rgb(50 118 204 / 5%); }
.trend-metric-options button:focus-visible { outline: 2px solid rgb(50 118 204 / 24%); outline-offset: 2px; }
.trend-custom-button { height: 32px; display: inline-flex; align-items: center; gap: 5px; padding: 0 10px; border: 1px solid var(--hairline); border-radius: 8px; background: #fff; color: var(--charcoal); font-family: inherit; font-size: 11px; font-weight: 600; white-space: nowrap; cursor: pointer; }
.trend-custom-button:hover { border-color: #b8d4f5; background: #f7fbff; }.trend-custom-button .material-symbols-outlined { font-size: 15px; }
.trend-metric-popover { position: absolute; z-index: 12; top: 40px; right: 0; width: 220px; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 7px; padding: 12px; border: 1px solid var(--hairline); border-radius: 10px; background: #fff; box-shadow: rgba(15,15,15,.16) 0 12px 32px; }
.trend-metric-popover > strong,.trend-metric-popover > small { grid-column: 1 / -1; }.trend-metric-popover > strong { color: var(--ink); font-size: 12px; }.trend-metric-popover > small { color: var(--steel); font-size: 10px; }
.trend-metric-popover label { min-height: 30px; display: flex; align-items: center; gap: 6px; padding: 0 7px; border-radius: 6px; background: var(--surface-soft); color: var(--charcoal); font-size: 11px; cursor: pointer; }.trend-metric-popover label span { display: inline-flex; align-items: center; gap: 5px; }.trend-metric-popover input { accent-color: #3276cc; }
.trend-metric-popover > button { grid-column: 1 / -1; height: 30px; border: 0; border-radius: 6px; background: #3276cc; color: #fff; font-family: inherit; font-size: 11px; font-weight: 600; cursor: pointer; }

.trend-grid { display: grid; grid-template-columns: minmax(0,1fr); align-items: start; padding: 8px; }
.chart-panel { position: relative; min-width: 0; height: var(--trend-chart-height,280px); min-height: 0; padding: 7px 2px 0; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fcfcfb; transition: height .2s ease; }
.chart-legend { display: flex; align-items: center; gap: 14px; padding-left: 8px; color: var(--steel); font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 5px; height: 5px; border-radius: 50%; }
.legend-dot.spend { background: #4f8fe8; }.legend-dot.revenue,.legend-dot.conversions { background: #20a464; }.legend-dot.roas { background: #dd7d00; }.legend-dot.orders { background: #8b5cf6; }.legend-dot.clicks { background: #0891b2; }.legend-dot.ctr { background: #d946ef; }
.chart-panel svg { display: block; width: 100%; height: var(--trend-svg-height,230px); margin-top: -2px; overflow: visible; transition: height .2s ease; }
.chart-bars { opacity: .76; }.chart-bars.spend { fill: #4f8fe8; }.chart-bars.revenue { fill: #20a464; }.chart-bars.orders { fill: #8b5cf6; }.chart-bars.clicks { fill: #0891b2; }
.chart-axis-labels { position: absolute; z-index: 3; right: 2px; bottom: 0; left: 2px; height: 24px; overflow: hidden; color: var(--stone); font-size: 11px; line-height: 1; }
.chart-axis-labels button { position: absolute; top: 0; width: auto; min-width: 0 !important; height: 24px; min-height: 24px !important; display: inline-flex; align-items: center; justify-content: center; padding: 0 1px; overflow: hidden; border: 0; background: transparent; color: inherit; cursor: pointer; font: inherit; line-height: inherit; text-align: center; white-space: nowrap; transform: translateX(-50%); }
.chart-axis-labels button.active { color: var(--charcoal); font-weight: 600; }
.chart-axis-labels button.selected { color: #3276cc; }
.chart-hit-area { fill: transparent; cursor: pointer; outline: none; }
.chart-hit-area:focus { fill: rgb(79 143 232 / 4%); }
.chart-active-markers { pointer-events: none; }
.chart-active-markers line { stroke: rgb(100 116 139 / 28%); stroke-width: .75; stroke-dasharray: 3 3; }
.chart-active-markers rect { fill: none; stroke-width: 1.2; }.chart-active-markers rect.spend { stroke: #4f8fe8; }.chart-active-markers rect.revenue { stroke: #20a464; }.chart-active-markers rect.orders { stroke: #8b5cf6; }.chart-active-markers rect.clicks { stroke: #0891b2; }
.chart-active-markers circle { fill: #ffffff; stroke-width: 1.5; }
.chart-active-markers circle.spend { stroke: #4f8fe8; }
.chart-active-markers circle.roas { stroke: #dd7d00; }
.chart-active-markers circle.orders { stroke: #8b5cf6; }.chart-active-markers circle.clicks { stroke: #0891b2; }.chart-active-markers circle.ctr { stroke: #d946ef; }
.chart-tooltip { position: absolute; z-index: 4; top: 28px; width: 146px; padding: 8px 9px; border: 1px solid var(--hairline); border-radius: 7px; background: rgb(255 255 255 / 96%); box-shadow: rgba(15,15,15,.12) 0 8px 24px; color: var(--charcoal); pointer-events: none; transform: translateX(-50%); }
.chart-tooltip > strong { display: block; margin-bottom: 5px; color: var(--ink); font-size: 12px; }
.chart-tooltip > div { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 19px; color: var(--steel); font-size: 11px; }
.chart-tooltip span { display: inline-flex; align-items: center; gap: 4px; }
.chart-tooltip b { color: var(--charcoal); font-size: 12px; font-weight: 600; }
.hierarchy-card { min-height: 0; }
.hierarchy-card-head { min-height: 52px; display: flex; align-items: center; gap: 9px; padding: 8px 16px; border-bottom: 1px solid var(--hairline-soft); background: #fff; }
.hierarchy-card-head > .material-symbols-outlined { color: #3276cc; font-size: 18px; }
.hierarchy-card-head h2 { margin: 0; color: var(--ink); font-size: 15px; font-weight: 600; }
.hierarchy-card-head p { margin: 3px 0 0; color: var(--steel); font-size: 12px; }
.hierarchy-toolbar { min-height: 50px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 7px 14px; border-bottom: 1px solid var(--hairline-soft); background: #fff; }
.hierarchy-toolbar-left,.hierarchy-toolbar-right { display: flex; align-items: center; gap: 8px; min-width: 0; }
.hierarchy-toolbar-right { justify-content: flex-end; }
.hierarchy-view-switch { display: inline-flex; flex: 0 0 auto; align-items: center; padding: 3px; border-radius: 9px; background: var(--surface); }
.hierarchy-view-switch button { height: 32px; padding: 0 13px; border: 0; border-radius: 7px; background: transparent; color: var(--slate); font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
.hierarchy-view-switch button.active { background: #fff; color: var(--ink); box-shadow: 0 1px 3px rgb(15 15 15 / 12%); }
.hierarchy-search-field { width: min(250px,24vw); min-width: 180px; height: 38px; display: flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid var(--hairline); border-radius: 9px; background: #fff; color: var(--steel); }
.hierarchy-search-field:focus-within { border-color: #9fc9fb; box-shadow: 0 0 0 2px rgb(50 118 204 / 10%); }
.hierarchy-search-field .material-symbols-outlined { font-size: 18px; }
.hierarchy-search-field input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--charcoal); font-family: inherit; font-size: 12px; }
.hierarchy-search-field input::placeholder { color: var(--stone); }
.hierarchy-filter-button,.hierarchy-action-button { height: 34px; padding: 0 12px; border: 1px solid var(--hairline); border-radius: 8px; background: #fff; color: var(--slate); font-family: inherit; font-size: 12px; font-weight: 500; white-space: nowrap; cursor: pointer; }
.hierarchy-filter-button:hover,.hierarchy-action-button:hover { border-color: #c7d9ee; background: #f8fbff; }
.hierarchy-filter-button.active { border-color: #9fc9fb; background: #eef6ff; color: #176bc3; font-weight: 600; }
.hierarchy-action-button { color: var(--charcoal); font-weight: 600; }
.hierarchy-table-head,.hierarchy-row { width: 100%; min-width: 0; display: grid; grid-template-columns: minmax(190px,1.7fr) minmax(70px,.7fr) minmax(76px,.78fr) minmax(76px,.78fr) minmax(52px,.55fr) minmax(46px,.48fr); align-items: center; column-gap: clamp(5px,.75vw,12px); }
.hierarchy-table-head { min-height: 38px; padding: 0 16px; border-bottom: 1px solid var(--hairline); background: #fafaf9; color: var(--steel); font-size: 11px; font-weight: 600; }
.hierarchy-table-head span:not(:first-child) { text-align: right; }
.hierarchy-table-body { width: 100%; overflow: hidden; }
.hierarchy-row { position: relative; min-height: 54px; padding: 5px 16px; border-bottom: 1px solid var(--hairline-soft); background: #fff; color: var(--slate); }
.hierarchy-row:last-child { border-bottom: 0; }
.hierarchy-name { min-width: 0; display: flex; align-items: center; gap: 9px; padding-left: calc(var(--level) * 25px); }
.hierarchy-expander { width: 18px; height: 24px; display: inline-grid; flex: 0 0 18px; place-items: center; padding: 0; border: 0; background: transparent; color: var(--steel); font-family: inherit; font-size: 20px; line-height: 1; cursor: pointer; transform: rotate(0); transition: transform .14s ease,color .14s ease; }
.hierarchy-expander:hover { color: #176bc3; }
.hierarchy-expander.open { transform: rotate(90deg); }
.hierarchy-expander.placeholder { opacity: 0; }
.hierarchy-node-icon { width: 30px; height: 30px; display: grid; flex: 0 0 30px; place-items: center; border: 1px solid #bcd9fb; border-radius: 7px; background: #eef6ff; color: #1d73d1; font-size: 12px; font-weight: 650; }
.hierarchy-node-icon.google { border-color: #f2d49f; background: #fff7e8; color: #ba6b00; }
.hierarchy-node-icon.tiktok { border-color: #d2d2d2; background: #f4f4f3; color: #242424; }
.hierarchy-node-icon.all { border-color: #d6d3ce; background: #f6f5f4; color: #5f5b56; }
.hierarchy-node-icon.campaign { border-radius: 50%; background: #f1f6fc; }
.hierarchy-node-icon.ad-unit { border-style: dashed; border-radius: 5px; background: #fff; font-size: 10px; }
.hierarchy-node-copy { min-width: 0; }
.hierarchy-node-copy strong,.hierarchy-node-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hierarchy-node-copy strong { color: var(--ink); font-size: 13px; font-weight: 600; }
.hierarchy-node-copy small { margin-top: 3px; color: var(--stone); font-size: 11px; }
.hierarchy-status { width: fit-content; justify-self: end; display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; background: #e9f7ef; color: #137849; font-size: 11px; font-weight: 600; white-space: nowrap; }
.hierarchy-status i { width: 5px; height: 5px; border-radius: 50%; background: #18945a; }
.hierarchy-number { justify-self: end; color: var(--charcoal); font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.hierarchy-empty { min-height: 200px; display: grid; place-items: center; color: var(--steel); font-size: 12px; }

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

.platform-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: stretch; gap: 8px; padding: 10px; }
.platform-card { --accent: #4f8fe8; min-width: 0; align-self: stretch; border: 1px solid var(--hairline); border-radius: 9px; overflow: hidden; background: #fff; }
.platform-card.google { --accent: #dd7d00; }.platform-card.tiktok { --accent: #16a05d; }
.platform-top { padding: 10px; }
.platform-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.platform-heading h3 { margin: 0; color: var(--ink); font-size: 14px; }.platform-heading p { margin: 3px 0 0; color: var(--steel); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
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
.daily-roas { display: inline-flex; align-items: center; gap: 5px; color: var(--ink); font-weight: 600; }.daily-roas::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--accent); }

.toast { position: fixed; z-index: 90; left: 50%; bottom: 52px; max-width: calc(100vw - 32px); padding: 10px 13px; border: 1px solid var(--hairline,#e5e3df); border-radius: 8px; background: #fff; color: #37352f; font-size: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 44px -10px; opacity: 0; pointer-events: none; transform: translate(-50%,8px); transition: opacity .16s ease,transform .16s ease; }
.toast.show { opacity: 1; transform: translate(-50%,0); }

@media (max-width: 1220px) {
  .replay-kpis { grid-template-columns: repeat(3,1fr); }.replay-kpi:nth-child(3)::after,.replay-kpi:nth-child(6)::after { display: none; }.replay-kpi:nth-child(-n+3) { border-bottom: 1px solid #f3f2f0; }
  .platform-grid { grid-template-columns: 1fr; }.platform-card { display: grid; grid-template-columns: 310px minmax(0,1fr); align-items: start; }.platform-card .platform-top { border-right: 1px solid var(--hairline-soft); }.platform-card .daily-table { margin: 8px; }
}
@media (max-width: 900px) {
  .dashboard-shell:not(.embedded) .replay-bar { align-items: flex-start; flex-direction: column; padding-top: 9px; padding-bottom: 9px; }.dashboard-shell:not(.embedded) .replay-title { flex: 0 0 auto; }.dashboard-shell:not(.embedded) .replay-title p { display: none; }.dashboard-shell:not(.embedded) .replay-actions { width: 100%; min-width: 0; flex-wrap: wrap; overflow: visible; }.dashboard-shell:not(.embedded) .header-scope-field,.dashboard-shell:not(.embedded) .filter-field,.dashboard-shell:not(.embedded) .refresh-button { flex: 0 0 auto; }
  .analysis-filter-controls { grid-template-columns: repeat(2,minmax(0,1fr)); }.analysis-filter-chip.account-filter-chip,.analysis-filter-chip.objective-filter-chip,.analysis-filter-chip.time-filter-chip { grid-column: 1 / -1; }
  .trend-grid,.replay-split { grid-template-columns: 1fr; }
  .overview-secondary-row { grid-template-columns: repeat(3,minmax(0,1fr)); }.overview-secondary-item { border-bottom: 1px solid #efede9; }
  .hierarchy-toolbar { align-items: stretch; flex-direction: column; }.hierarchy-toolbar-left,.hierarchy-toolbar-right { width: 100%; }.hierarchy-toolbar-right { justify-content: flex-start; flex-wrap: wrap; overflow: visible; padding-bottom: 2px; }.hierarchy-search-field { width: 100%; }.hierarchy-table-head { display: none; }.hierarchy-row { grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px 12px; padding: 12px 14px; }.hierarchy-name { grid-column: 1 / -1; }.hierarchy-row > span { min-width: 0; display: flex; align-items: center; justify-content: space-between; gap: 6px; justify-self: stretch; text-align: right; }.hierarchy-row > span::before { content: attr(data-label); color: var(--stone); font-size: 9px; font-weight: 500; }.hierarchy-status { width: 100%; justify-content: flex-end; }
  .platform-card { display: block; }.platform-card .platform-top { border-right: 0; }
}
@media (max-width: 620px) {
  .replay-content { padding: 12px 12px 52px; }.replay-kpis { grid-template-columns: repeat(2,1fr); }.replay-kpi { border-bottom: 1px solid #f3f2f0; }.replay-kpi:nth-child(3)::after { display: block; }.replay-kpi:nth-child(2n)::after { display: none; }.replay-kpi:nth-last-child(-n+2) { border-bottom: 0; }
  .analysis-filter-controls { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); }.analysis-filter-chip,.analysis-filter-chip.account-filter-chip,.analysis-filter-chip.objective-filter-chip,.analysis-filter-chip.time-filter-chip { min-width: 0; }.analysis-filter-chip.account-filter-chip,.analysis-filter-chip.objective-filter-chip,.analysis-filter-chip.time-filter-chip { grid-column: 1 / -1; }.analysis-filter-chip.time-filter-chip { width: 100%; margin-left: 0; }.time-filter-chip input { width: auto; min-width: 0; flex: 1 1 0; }
  .dashboard-shell:not(.embedded) .replay-title h1 { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }.dashboard-shell:not(.embedded) .refresh-button { width: 31px; min-width: 31px; padding: 0; }.dashboard-shell:not(.embedded) .refresh-label { display: none; }
  .overview-secondary-row { grid-template-columns: repeat(2,minmax(0,1fr)); }.overview-secondary-item:nth-last-child(-n+2) { border-bottom: 0; }
  .trend-card-head { align-items: flex-start; flex-direction: column; }.trend-metric-customizer { width: 100%; justify-content: flex-start; flex-wrap: wrap; }.trend-metric-options { flex-wrap: wrap; }.trend-metric-options button { flex: 0 1 auto; }.trend-metric-popover { right: auto; left: 0; }.hierarchy-toolbar-left { align-items: stretch; flex-direction: column; }.hierarchy-view-switch { width: fit-content; }
  .segment-grid { grid-template-columns: 1fr; }.funnel-row { grid-template-columns: 36px minmax(0,1fr) 48px; }.funnel-row small { display: none; }
}
@media (max-width: 480px) {
  .hierarchy-row { grid-template-columns: repeat(2,minmax(0,1fr)); }
}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
