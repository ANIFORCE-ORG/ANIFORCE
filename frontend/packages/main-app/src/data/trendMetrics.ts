export type TrendMetric =
  | 'spend'
  | 'impressions'
  | 'clicks'
  | 'conversions'
  | 'conversion_value'
  | 'ctr'
  | 'result_cost'
  | 'roas'

export type TrendMetricFormat = 'number' | 'money' | 'percent' | 'ratio'

export type TrendMetricOption = {
  key: TrendMetric
  label: string
  color: string
  format: TrendMetricFormat
}

/** Fields currently exposed by /dashboard/meta-overview. Keep this list data-driven. */
export const trendMetricOptions: TrendMetricOption[] = [
  { key: 'spend', label: '花费', color: '#4f8fe8', format: 'money' },
  { key: 'impressions', label: '曝光', color: '#64748b', format: 'number' },
  { key: 'clicks', label: '点击', color: '#0891b2', format: 'number' },
  { key: 'conversions', label: '转化', color: '#20a464', format: 'number' },
  { key: 'conversion_value', label: '转化价值', color: '#8b5cf6', format: 'money' },
  { key: 'ctr', label: 'CTR', color: '#d946ef', format: 'percent' },
  { key: 'result_cost', label: '结果成本', color: '#64748b', format: 'money' },
  { key: 'roas', label: 'ROAS', color: '#dd7d00', format: 'ratio' },
]

export const formatTrendMetricValue = (
  metric: TrendMetric,
  value: number | null | undefined,
  currency: string | null = 'USD',
  mixedCurrency = false,
) => {
  if (value == null) return '—'
  const option = trendMetricOptions.find(item => item.key === metric)
  if (option?.format === 'money') {
    if (mixedCurrency) return '多币种'
    if (!currency) return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value)
  }
  if (option?.format === 'percent') return `${(value * 100).toFixed(2)}%`
  if (option?.format === 'ratio') return `${value.toFixed(2)}x`
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}
