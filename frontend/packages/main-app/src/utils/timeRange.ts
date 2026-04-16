/**
 * 时间范围工具函数
 */

export interface TimeRange {
  value: string
  label: string
}

export const TIME_RANGES: TimeRange[] = [
  { value: 'realtime', label: '实时' },
  { value: 'today', label: '今日' },
  { value: 'yesterday', label: '昨日' },
  { value: '7days', label: '近7日' },
  { value: '30days', label: '近30日' }
]

/**
 * 根据时间范围返回数据倍数
 * 用于模拟不同时间范围的数据量
 */
export function getTimeMultiplier(range: string): number {
  const multipliers: Record<string, number> = {
    'realtime': 0.05,   // 实时数据约为全天的5%
    'today': 0.6,       // 今日数据约为全天的60%
    'yesterday': 1.0,   // 昨日完整数据
    '7days': 7.0,       // 近7日累计
    '30days': 30.0      // 近30日累计
  }
  return multipliers[range] || 1.0
}

/**
 * 获取时间范围的日期范围
 */
export function getDateRange(range: string): { start: Date; end: Date } {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  switch (range) {
    case 'realtime':
      // 最近1小时
      return {
        start: new Date(now.getTime() - 60 * 60 * 1000),
        end: now
      }
    case 'today':
      return {
        start: today,
        end: now
      }
    case 'yesterday':
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      return {
        start: yesterday,
        end: today
      }
    case '7days':
      const sevenDaysAgo = new Date(today)
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
      return {
        start: sevenDaysAgo,
        end: now
      }
    case '30days':
      const thirtyDaysAgo = new Date(today)
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
      return {
        start: thirtyDaysAgo,
        end: now
      }
    default:
      return {
        start: today,
        end: now
      }
  }
}

/**
 * 格式化日期范围显示
 */
export function formatDateRange(range: string): string {
  const { start, end } = getDateRange(range)
  const formatDate = (date: Date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  if (range === 'realtime') {
    return '实时数据'
  }

  return `${formatDate(start)} ~ ${formatDate(end)}`
}
