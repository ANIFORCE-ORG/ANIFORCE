export type TrendMetric =
  | 'spend' | 'revenue' | 'impressions' | 'clicks' | 'ctr' | 'cpc' | 'cpm' | 'conversions' | 'cvr' | 'cpa' | 'roas'
  | 'creativeImpressions' | 'videoViews' | 'videoViewRate' | 'completionRate' | 'engagementRate' | 'avgWatchTime' | 'fatigueRate'
  | 'metaReach' | 'metaFrequency' | 'metaLinkClicks' | 'metaLandingPageViews' | 'metaThruPlays'
  | 'googleInteractions' | 'googleInteractionRate' | 'googleViews' | 'googleViewRate' | 'googleAvgCpv'
  | 'tiktokVideoViews2s' | 'tiktokVideoViews6s' | 'tiktokVideoViews25' | 'tiktokVideoViews50' | 'tiktokVideoViews75' | 'tiktokVideoViews100' | 'tiktokEngagements'

export type TrendMetricGroup = 'overview' | 'creative' | 'meta' | 'google' | 'tiktok'
export type TrendMetricFormat = 'number' | 'money' | 'percent' | 'ratio' | 'seconds'

export type TrendMetricOption = {
  key: TrendMetric
  label: string
  color: string
  group: TrendMetricGroup
  format: TrendMetricFormat
  chart: 'bar' | 'line'
}

export const MAX_TREND_METRICS = 6

export const trendMetricOptions: TrendMetricOption[] = [
  { key: 'impressions', label: '曝光次数', color: '#5b8def', group: 'overview', format: 'number', chart: 'bar' },
  { key: 'spend', label: '花费', color: '#f5a33f', group: 'overview', format: 'money', chart: 'bar' },
  { key: 'revenue', label: '收入', color: '#20a464', group: 'overview', format: 'money', chart: 'bar' },
  { key: 'clicks', label: '点击', color: '#0891b2', group: 'overview', format: 'number', chart: 'bar' },
  { key: 'ctr', label: 'CTR', color: '#d946ef', group: 'overview', format: 'percent', chart: 'line' },
  { key: 'cpc', label: 'CPC', color: '#64748b', group: 'overview', format: 'money', chart: 'line' },
  { key: 'cpm', label: 'CPM', color: '#0f766e', group: 'overview', format: 'money', chart: 'line' },
  { key: 'conversions', label: '转化', color: '#8b5cf6', group: 'overview', format: 'number', chart: 'bar' },
  { key: 'cvr', label: 'CVR', color: '#a855f7', group: 'overview', format: 'percent', chart: 'line' },
  { key: 'cpa', label: 'CPA', color: '#475569', group: 'overview', format: 'money', chart: 'line' },
  { key: 'roas', label: 'ROAS', color: '#dd7d00', group: 'overview', format: 'ratio', chart: 'line' },
  { key: 'creativeImpressions', label: '素材曝光', color: '#4f8fe8', group: 'creative', format: 'number', chart: 'bar' },
  { key: 'videoViews', label: '视频播放', color: '#0ea5e9', group: 'creative', format: 'number', chart: 'bar' },
  { key: 'videoViewRate', label: '视频观看率', color: '#06b6d4', group: 'creative', format: 'percent', chart: 'line' },
  { key: 'completionRate', label: '完播率', color: '#14b8a6', group: 'creative', format: 'percent', chart: 'line' },
  { key: 'engagementRate', label: '互动率', color: '#10b981', group: 'creative', format: 'percent', chart: 'line' },
  { key: 'avgWatchTime', label: '平均观看时长', color: '#22c55e', group: 'creative', format: 'seconds', chart: 'line' },
  { key: 'fatigueRate', label: '疲劳度', color: '#ef4444', group: 'creative', format: 'percent', chart: 'line' },
  { key: 'metaReach', label: '覆盖人数', color: '#2563eb', group: 'meta', format: 'number', chart: 'bar' },
  { key: 'metaFrequency', label: '频次', color: '#3b82f6', group: 'meta', format: 'ratio', chart: 'line' },
  { key: 'metaLinkClicks', label: '链接点击', color: '#60a5fa', group: 'meta', format: 'number', chart: 'bar' },
  { key: 'metaLandingPageViews', label: '落地页浏览', color: '#1d4ed8', group: 'meta', format: 'number', chart: 'bar' },
  { key: 'metaThruPlays', label: 'ThruPlay', color: '#1e40af', group: 'meta', format: 'number', chart: 'bar' },
  { key: 'googleInteractions', label: '互动次数', color: '#f59e0b', group: 'google', format: 'number', chart: 'bar' },
  { key: 'googleInteractionRate', label: '互动率', color: '#d97706', group: 'google', format: 'percent', chart: 'line' },
  { key: 'googleViews', label: '观看次数', color: '#fbbf24', group: 'google', format: 'number', chart: 'bar' },
  { key: 'googleViewRate', label: '观看率', color: '#b45309', group: 'google', format: 'percent', chart: 'line' },
  { key: 'googleAvgCpv', label: '平均 CPV', color: '#92400e', group: 'google', format: 'money', chart: 'line' },
  { key: 'tiktokVideoViews2s', label: '2秒播放', color: '#111827', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokVideoViews6s', label: '6秒播放', color: '#374151', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokVideoViews25', label: '25%播放', color: '#4b5563', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokVideoViews50', label: '50%播放', color: '#6b7280', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokVideoViews75', label: '75%播放', color: '#9ca3af', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokVideoViews100', label: '100%播放', color: '#0f172a', group: 'tiktok', format: 'number', chart: 'bar' },
  { key: 'tiktokEngagements', label: '互动次数', color: '#be123c', group: 'tiktok', format: 'number', chart: 'bar' },
]

export const trendMetricGroups = ([
  { key: 'overview', label: '数据概览维度' },
  { key: 'creative', label: '创意素材维度' },
  { key: 'meta', label: 'Meta 核心指标' },
  { key: 'google', label: 'Google 核心指标' },
  { key: 'tiktok', label: 'TikTok 核心指标' },
] as Array<{ key: TrendMetricGroup; label: string }>).map(group => ({
  ...group,
  metrics: trendMetricOptions.filter(item => item.group === group.key),
}))

export const formatTrendMetricValue = (metric: TrendMetric, value: number) => {
  const format = trendMetricOptions.find(item => item.key === metric)?.format || 'number'
  if (format === 'money') return `US$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (format === 'percent') return `${value.toFixed(2)}%`
  if (format === 'ratio') return `${value.toFixed(2)}x`
  if (format === 'seconds') return `${value.toFixed(1)}s`
  return Math.round(value).toLocaleString('en-US')
}
