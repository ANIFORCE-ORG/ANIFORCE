import { computed, type Ref } from 'vue'

type DailyMetric = { date: string; spend: number; conversions: number; roas: number }
type FunnelMetric = { impressions: number; clicks: number; installs: number; registrations: number; payments: number }
type DashboardAccount = {
  id: string
  owners: string[]
  project: string
  projectLabel: string
  channel: string
  channelLabel: string
  account: string
  campaigns: number
  score: number
  className: string
  ctr: number
  cvr: number
  previousCtr: number
  previousCvr: number
  previousSpend: number
  previousConversions: number
  previousKpiRoas: number
  kpiRoas: number
  displayRoas: number
  funnel: FunnelMetric
  daily: DailyMetric[]
}

const accounts: DashboardAccount[] = [
  {
    id: 'candy-meta-ua', owners: ['juci-li', 'mia-chen'], project: 'candy', projectLabel: 'CANDY BLASTER', channel: 'meta', channelLabel: 'Meta',
    account: 'Candy Blast Meta UA', campaigns: 3, score: 72, className: '', ctr: 4.2, cvr: 9.3,
    previousCtr: 3.6, previousCvr: 9.6, previousSpend: 6854, previousConversions: 1204,
    previousKpiRoas: 2.28, kpiRoas: 2.48, displayRoas: 2.39,
    funnel: { impressions: 330000, clicks: 18000, installs: 3900, registrations: 2220, payments: 300 },
    daily: [
      { date: '05-21', spend: 770, conversions: 123, roas: 2.21 }, { date: '05-22', spend: 847, conversions: 137, roas: 2.27 },
      { date: '05-23', spend: 925, conversions: 151, roas: 2.34 }, { date: '05-24', spend: 1079, conversions: 176, roas: 2.41 },
      { date: '05-25', spend: 1156, conversions: 196, roas: 2.48 }, { date: '05-26', spend: 1387, conversions: 239, roas: 2.55 },
      { date: '05-27', spend: 1541, conversions: 287, roas: 2.62 },
    ],
  },
  {
    id: 'candy-meta-retarget', owners: ['juci-li', 'mia-chen'], project: 'candy', projectLabel: 'CANDY BLASTER', channel: 'meta', channelLabel: 'Meta',
    account: 'Candy Blast Meta Retargeting', campaigns: 2, score: 63, className: '', ctr: 3.95, cvr: 9.05,
    previousCtr: 3.35, previousCvr: 9.35, previousSpend: 4569, previousConversions: 802,
    previousKpiRoas: 2.129993434, kpiRoas: 2.279961052, displayRoas: 2.19,
    funnel: { impressions: 220000, clicks: 12000, installs: 2600, registrations: 1480, payments: 200 },
    daily: [
      { date: '05-21', spend: 514, conversions: 82, roas: 2.01 }, { date: '05-22', spend: 565, conversions: 91, roas: 2.07 },
      { date: '05-23', spend: 616, conversions: 100, roas: 2.14 }, { date: '05-24', spend: 719, conversions: 117, roas: 2.21 },
      { date: '05-25', spend: 770, conversions: 130, roas: 2.28 }, { date: '05-26', spend: 924, conversions: 159, roas: 2.35 },
      { date: '05-27', spend: 1027, conversions: 192, roas: 2.42 },
    ],
  },
  {
    id: 'dramabox-google', owners: ['juci-li', 'alex-wang'], project: 'drama', projectLabel: 'DramaBox', channel: 'google', channelLabel: 'Google',
    account: 'DramaBox Google Ads', campaigns: 3, score: 54, className: 'google', ctr: 3.6, cvr: 8.6,
    previousCtr: 3.2, previousCvr: 8.9, previousSpend: 7670, previousConversions: 1312,
    previousKpiRoas: 2.00, kpiRoas: 2.18, displayRoas: 2.12,
    funnel: { impressions: 400000, clicks: 20000, installs: 4100, registrations: 2300, payments: 300 },
    daily: [
      { date: '05-21', spend: 1552, conversions: 257, roas: 2.37 }, { date: '05-22', spend: 1465, conversions: 242, roas: 2.29 },
      { date: '05-23', spend: 1379, conversions: 228, roas: 2.20 }, { date: '05-24', spend: 1293, conversions: 214, roas: 2.12 },
      { date: '05-25', spend: 1121, conversions: 185, roas: 2.06 }, { date: '05-26', spend: 948, conversions: 157, roas: 1.99 },
      { date: '05-27', spend: 862, conversions: 143, roas: 1.93 },
    ],
  },
  {
    id: 'candy-tiktok-us', owners: ['juci-li', 'mia-chen'], project: 'candy', projectLabel: 'CANDY BLASTER', channel: 'tiktok', channelLabel: 'TikTok',
    account: 'Candy Blast TikTok US', campaigns: 4, score: 78, className: 'tiktok', ctr: 4.4, cvr: 9.7,
    previousCtr: 3.6, previousCvr: 9.1, previousSpend: 6227, previousConversions: 1127,
    previousKpiRoas: 2.59, kpiRoas: 2.77, displayRoas: 2.86,
    funnel: { impressions: 290000, clicks: 18420, installs: 4234, registrations: 2420, payments: 328 },
    daily: [
      { date: '05-21', spend: 700, conversions: 121, roas: 2.63 }, { date: '05-22', spend: 770, conversions: 135, roas: 2.72 },
      { date: '05-23', spend: 840, conversions: 147, roas: 2.80 }, { date: '05-24', spend: 980, conversions: 171, roas: 2.89 },
      { date: '05-25', spend: 1050, conversions: 184, roas: 2.97 }, { date: '05-26', spend: 1260, conversions: 220, roas: 3.08 },
      { date: '05-27', spend: 1400, conversions: 248, roas: 3.15 },
    ],
  },
]

const segmentPerformance = [
  { accountId: 'candy-meta-ua', name: 'US / iOS / Broad', detail: '可控量 · CPI $5.62 · ROAS 2.82x' },
  { accountId: 'candy-meta-ua', name: 'US / Android / LAL 2%', detail: '观察 · CPI $6.12 · ROAS 2.41x' },
  { accountId: 'candy-tiktok-us', name: 'US / Android / Spark', detail: '加预算 · CPI $5.25 · ROAS 3.04x' },
  { accountId: 'dramabox-google', name: 'US / Search / Core', detail: '稳定 · CPI $5.95 · ROAS 2.22x' },
  { accountId: 'dramabox-google', name: 'US / PMax / Creative', detail: '降预算 · CPI $8.97 · ROAS 1.86x' },
  { accountId: 'candy-tiktok-us', name: 'CA / Drama Fans', detail: '继续测 · CPI $6.31 · ROAS 2.06x' },
]

const metaObjectiveOptions = [
  { value: 'app-promotion', label: '应用推广', factor: 0.62 },
  { value: 'sales', label: '销售', factor: 0.24 },
  { value: 'traffic', label: '流量', factor: 0.09 },
  { value: 'engagement', label: '互动', factor: 0.05 },
]

const numberFormatter = new Intl.NumberFormat('zh-CN')
const spendOf = (item: DashboardAccount) => item.daily.reduce((total, day) => total + day.spend, 0)
const conversionsOf = (item: DashboardAccount) => item.daily.reduce((total, day) => total + day.conversions, 0)
export const formatDashboardMoney = (value: number, digits = 0) => `$${value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}`
export const formatDashboardNumber = (value: number) => numberFormatter.format(value)

const percentDelta = (current: number, previous: number) => {
  if (!previous) return '—'
  const delta = (current - previous) / previous * 100
  return `${delta >= 0 ? '+' : '−'}${Math.abs(delta).toFixed(1)}%`
}

const pointDelta = (current: number, previous: number, suffix: string) => {
  const delta = current - previous
  return `${delta >= 0 ? '+' : '−'}${Math.abs(delta).toFixed(1)}${suffix}`
}

export const useDashboardScope = (
  project: Ref<string>,
  channel: Ref<string>,
  account: Ref<string>,
  objective: Ref<string>,
  rangeDays: Ref<number>,
  dateContextFactor: Ref<number>,
  owner: Ref<string>,
  activeAccountScope: Ref<string>,
) => {
  const ownerAccounts = computed(() => accounts.filter(item => item.owners.includes(owner.value)))
  const scopeAccounts = computed(() => ownerAccounts.value.filter(item => activeAccountScope.value === 'all' || item.id === activeAccountScope.value))
  const allAccountOptions = computed(() => ownerAccounts.value.map(item => ({
    id: item.id,
    account: item.account,
    project: item.project,
    projectLabel: item.projectLabel,
    channel: item.channel,
    channelLabel: item.channelLabel,
  })))
  const projectOptions = computed(() => [...new Map(scopeAccounts.value.map(item => [item.project, { value: item.project, label: item.projectLabel }])).values()])
  const channelOptions = computed(() => [...new Map(scopeAccounts.value
    .filter(item => project.value === 'all' || item.project === project.value)
    .map(item => [item.channel, { value: item.channel, label: item.channelLabel }])).values()])
  const accountOptions = computed(() => scopeAccounts.value.filter(item =>
    (project.value === 'all' || item.project === project.value)
    && (channel.value === 'all' || item.channel === channel.value)))
  const filteredAccounts = computed(() => {
    const items = scopeAccounts.value.filter(item =>
      (project.value === 'all' || item.project === project.value)
      && (channel.value === 'all' || item.channel === channel.value)
      && (account.value === 'all' || item.id === account.value))
    const objectiveFactor = metaObjectiveOptions.find(item => item.value === objective.value)?.factor || 1
    const rangeFactor = Math.max(1, rangeDays.value) / 7 * dateContextFactor.value
    const scale = (value: number) => Math.max(1, Math.round(value * objectiveFactor * rangeFactor))
    const scopedItems = objective.value === 'all' ? items : items.filter(item => item.channel === 'meta')
    return scopedItems.map(item => ({
      ...item,
      campaigns: objective.value === 'all' ? item.campaigns : Math.max(1, Math.round(item.campaigns * objectiveFactor)),
      previousSpend: scale(item.previousSpend),
      previousConversions: scale(item.previousConversions),
      funnel: {
        impressions: scale(item.funnel.impressions), clicks: scale(item.funnel.clicks), installs: scale(item.funnel.installs),
        registrations: scale(item.funnel.registrations), payments: scale(item.funnel.payments),
      },
      daily: item.daily.map(day => ({ ...day, spend: scale(day.spend), conversions: scale(day.conversions) })),
    }))
  })

  const aggregate = computed(() => {
    const items = filteredAccounts.value
    const spend = items.reduce((total, item) => total + spendOf(item), 0)
    const conversions = items.reduce((total, item) => total + conversionsOf(item), 0)
    const previousSpend = items.reduce((total, item) => total + item.previousSpend, 0)
    const previousConversions = items.reduce((total, item) => total + item.previousConversions, 0)
    const weighted = (field: 'ctr' | 'cvr' | 'previousCtr' | 'previousCvr', by: 'spend' | 'conversions') => {
      const denominator = by === 'spend' ? spend : conversions
      if (!denominator) return 0
      return items.reduce((total, item) => total + item[field] * (by === 'spend' ? spendOf(item) : conversionsOf(item)), 0) / denominator
    }
    const kpiRoas = spend ? items.reduce((total, item) => total + item.kpiRoas * spendOf(item), 0) / spend : 0
    const previousKpiRoas = previousSpend ? items.reduce((total, item) => total + item.previousKpiRoas * item.previousSpend, 0) / previousSpend : 0
    return {
      spend, conversions, previousSpend, previousConversions, kpiRoas, previousKpiRoas,
      cpi: conversions ? spend / conversions : 0,
      previousCpi: previousConversions ? previousSpend / previousConversions : 0,
      ctr: weighted('ctr', 'spend'), previousCtr: weighted('previousCtr', 'spend'),
      cvr: weighted('cvr', 'conversions'), previousCvr: weighted('previousCvr', 'conversions'),
    }
  })

  const kpis = computed(() => {
    const data = aggregate.value
    const cvrWarning = data.cvr < 9.3
    return [
      { label: '总消耗', value: formatDashboardMoney(data.spend), delta: percentDelta(data.spend, data.previousSpend), icon: 'account_balance_wallet' },
      { label: '转化数', value: numberFormatter.format(data.conversions), delta: percentDelta(data.conversions, data.previousConversions), icon: 'download' },
      { label: 'CPI', value: formatDashboardMoney(data.cpi, 2), delta: percentDelta(data.cpi, data.previousCpi), icon: 'attach_money' },
      { label: 'ROAS', value: `${data.kpiRoas.toFixed(2)}x`, delta: pointDelta(data.kpiRoas, data.previousKpiRoas, 'x'), icon: 'trending_up' },
      { label: 'CTR', value: `${data.ctr.toFixed(1)}%`, delta: pointDelta(data.ctr, data.previousCtr, '%'), icon: 'ads_click' },
      { label: 'CVR', value: `${data.cvr.toFixed(1)}%`, delta: cvrWarning ? '需关注' : pointDelta(data.cvr, data.previousCvr, '%'), icon: 'target', warning: cvrWarning },
    ]
  })

  const funnelTotals = computed(() => filteredAccounts.value.reduce<FunnelMetric>((result, item) => ({
      impressions: result.impressions + item.funnel.impressions,
      clicks: result.clicks + item.funnel.clicks,
      installs: result.installs + item.funnel.installs,
      registrations: result.registrations + item.funnel.registrations,
      payments: result.payments + item.funnel.payments,
    }), { impressions: 0, clicks: 0, installs: 0, registrations: 0, payments: 0 }))

  const funnel = computed(() => {
    const totals = funnelTotals.value
    const rows = [
      { label: '曝光', value: totals.impressions, previous: totals.impressions },
      { label: '点击', value: totals.clicks, previous: totals.impressions },
      { label: '安装', value: totals.installs, previous: totals.clicks },
      { label: '注册', value: totals.registrations, previous: totals.installs },
      { label: '付费', value: totals.payments, previous: totals.registrations },
    ]
    return rows.map((item, index) => ({
      label: item.label,
      value: numberFormatter.format(item.value),
      rate: index === 0 ? '100%' : `${(item.previous ? item.value / item.previous * 100 : 0).toFixed(1)}%`,
      width: index === 0 ? 100 : Math.max(14, Math.sqrt(totals.impressions ? item.value / totals.impressions : 0) * 100),
    }))
  })

  const segments = computed(() => {
    const accountIds = new Set(filteredAccounts.value.map(item => item.id))
    return segmentPerformance.filter(item => accountIds.has(item.accountId))
  })

  const trendPoints = computed(() => {
    const dates = accounts[0].daily.map(day => day.date)
    const raw = dates.map(date => {
      const accountDays = filteredAccounts.value.map(item => ({ item, day: item.daily.find(day => day.date === date) })).filter(result => result.day)
      const spend = accountDays.reduce((total, result) => total + (result.day?.spend || 0), 0)
      const conversions = accountDays.reduce((total, result) => total + (result.day?.conversions || 0), 0)
      const roas = spend ? accountDays.reduce((total, result) => total + (result.day?.spend || 0) * (result.day?.roas || 0), 0) / spend : 0
      const clicks = accountDays.reduce((total, result) => {
        const accountTotal = spendOf(result.item)
        return total + (accountTotal ? (result.day?.spend || 0) / accountTotal * result.item.funnel.clicks : 0)
      }, 0)
      const impressions = accountDays.reduce((total, result) => {
        const accountTotal = spendOf(result.item)
        return total + (accountTotal ? (result.day?.spend || 0) / accountTotal * result.item.funnel.impressions : 0)
      }, 0)
      const ctr = impressions ? clicks / impressions * 100 : 0
      const revenue = spend * roas
      return { date, spend, revenue, conversions, roas, clicks, ctr }
    })
    const spends = raw.map(item => item.spend)
    const revenues = raw.map(item => item.revenue)
    const roases = raw.map(item => item.roas)
    const orders = raw.map(item => item.conversions)
    const clicks = raw.map(item => item.clicks)
    const ctrs = raw.map(item => item.ctr)
    const maxRevenue = Math.max(...revenues, 1)
    const minSpend = Math.min(...spends)
    const maxSpend = Math.max(...spends)
    const minRoas = Math.min(...roases)
    const maxRoas = Math.max(...roases)
    const minOrders = Math.min(...orders)
    const maxOrders = Math.max(...orders)
    const minClicks = Math.min(...clicks)
    const maxClicks = Math.max(...clicks)
    const minCtr = Math.min(...ctrs)
    const maxCtr = Math.max(...ctrs)
    const scaleY = (value: number, min: number, max: number) => max === min ? 94 : 142 - (value - min) / (max - min) * 94
    return raw.map((item, index) => {
      const x = 91 + index * 128
      const barHeight = 24 + item.revenue / maxRevenue * 81
      return {
        date: item.date,
        spend: formatDashboardMoney(item.spend),
        revenue: formatDashboardMoney(item.revenue),
        conversions: numberFormatter.format(item.conversions),
        orders: numberFormatter.format(item.conversions),
        clicks: numberFormatter.format(Math.round(item.clicks)),
        ctr: `${item.ctr.toFixed(2)}%`,
        roas: `${item.roas.toFixed(2)}x`,
        rawSpend: item.spend,
        rawRevenue: item.revenue,
        rawConversions: item.conversions,
        rawClicks: item.clicks,
        rawCtr: item.ctr,
        rawRoas: item.roas,
        x,
        spendY: scaleY(item.spend, minSpend, maxSpend),
        roasY: scaleY(item.roas, minRoas, maxRoas),
        ordersY: scaleY(item.conversions, minOrders, maxOrders),
        clicksY: scaleY(item.clicks, minClicks, maxClicks),
        ctrY: scaleY(item.ctr, minCtr, maxCtr),
        barY: 155 - barHeight,
        barHeight,
        tooltipLeft: index === 0 ? 10 : index === raw.length - 1 ? 90 : 19.2 + (index - 1) * 15.4,
      }
    })
  })

  const spendPath = computed(() => trendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.spendY}`).join(''))
  const roasPath = computed(() => trendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.roasY}`).join(''))
  const ordersPath = computed(() => trendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.ordersY}`).join(''))
  const clicksPath = computed(() => trendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.clicksY}`).join(''))
  const ctrPath = computed(() => trendPoints.value.map((point, index) => `${index ? 'L' : 'M'}${point.x} ${point.ctrY}`).join(''))

  const platforms = computed(() => filteredAccounts.value.map(item => {
    const spend = spendOf(item)
    const conversions = conversionsOf(item)
    return {
      name: item.channelLabel,
      account: item.account,
      campaigns: item.campaigns,
      score: item.score,
      className: item.className,
      spend: formatDashboardMoney(spend),
      conversions: numberFormatter.format(conversions),
      cpi: formatDashboardMoney(spend / conversions, 2),
      roas: `${item.displayRoas.toFixed(2)}x`,
      daily: item.daily.map(day => [day.date, formatDashboardMoney(day.spend), numberFormatter.format(day.conversions), `${day.roas.toFixed(2)}x`]),
    }
  }))

  const selectedAccountLabel = computed(() => accountOptions.value.find(item => item.id === account.value)?.account || '全部账户')

  return {
    projectOptions, channelOptions, accountOptions, allAccountOptions, objectiveOptions: metaObjectiveOptions, filteredAccounts, aggregate, kpis, funnelTotals, funnel, segments,
    trendPoints, spendPath, roasPath, ordersPath, clicksPath, ctrPath, platforms, selectedAccountLabel,
  }
}
