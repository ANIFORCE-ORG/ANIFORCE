import type { Campaign } from '@/api/campaigns'
import type { Material } from '@/api/materials'

export type MaterialMediaKind = 'image' | 'video'
export type MaterialSourceKind = 'oss' | 'local' | 'imported' | 'meta_import' | 'tiktok_import' | 'ai_generated' | 'unknown'

export interface MaterialMetrics {
  spend: number
  impressions: number
  clicks: number
  conversions: number
  revenue: number
  ctr: number
  roas: number
  cpc: number
  cpa: number
}

export interface MaterialRow {
  id: string
  material: Material
  name: string
  status: string
  statusLabel: string
  mediaKind: MaterialMediaKind
  source: MaterialSourceKind
  sourceLabel: string
  format: string
  ratio: string
  durationLabel: string
  fileSizeLabel: string
  createdAtLabel: string
  tags: string[]
  platforms: string[]
  campaigns: Campaign[]
  associatedCampaignCount: number
  associatedAccountCount: number
  transportCount: number
  reviewStatus: string
  score: number
  fatigue: number
  previewUrl?: string
  mimeType?: string
  metrics: MaterialMetrics
}

export interface MaterialOverview {
  spend: number
  impressions: number
  clicks: number
  ctr: number
  roas: number
  cpc: number
  shortVideoSpend: number
  spendingMaterials: number
  averageImpressions: number
  averageClicks: number
}

export interface MaterialAnalysis {
  title: string
  body: string
  tone: 'good' | 'warning' | 'info'
  icon: string
}

export const emptyMetrics = (): MaterialMetrics => ({
  spend: 0,
  impressions: 0,
  clicks: 0,
  conversions: 0,
  revenue: 0,
  ctr: 0,
  roas: 0,
  cpc: 0,
  cpa: 0,
})

export const toMaterialRows = (
  materials: Material[],
  campaigns: Campaign[],
  previewSources: Map<string, string>,
  mimeTypes: Map<string, string>
): MaterialRow[] => {
  const campaignById = new Map(campaigns.map(campaign => [campaign.id, campaign]))

  return materials.map((material, index) => {
    const linkedCampaigns = material.campaign_ids
      .map(campaignId => campaignById.get(campaignId))
      .filter((campaign): campaign is Campaign => Boolean(campaign))
    const platforms = Array.from(new Set([
      ...(material.platforms || []),
      ...linkedCampaigns.map(campaign => campaign.platform).filter(Boolean),
    ]))
    const previewUrl = previewSources.get(material.id) || material.poster_url || material.preview_url || material.thumbnail_url || material.url
    const mimeType = mimeTypes.get(material.id) || guessMimeType(previewUrl || material.url)
    const mediaKind = resolveMediaKind(material, mimeType)
    const metrics = estimateMetrics(material, linkedCampaigns)
    const source = resolveSource(material.source, material.url)
    const fatigue = material.fatigue ?? estimateFatigue(material, metrics)

    return {
      id: material.id,
      material,
      name: material.name || material.id,
      status: material.status,
      statusLabel: statusLabel(material.status),
      mediaKind,
      source,
      sourceLabel: sourceLabel(source),
      format: material.format || formatFromUrl(previewUrl || material.url),
      ratio: material.ratio || (mediaKind === 'video' ? '9:16' : '未知'),
      durationLabel: formatDuration(material.duration),
      fileSizeLabel: formatFileSize(material.file_size),
      createdAtLabel: formatDateTime(material.created_at),
      tags: material.tags || [],
      platforms,
      campaigns: linkedCampaigns,
      associatedCampaignCount: linkedCampaigns.length || material.campaign_ids.length,
      associatedAccountCount: new Set(linkedCampaigns.map(campaign => campaign.account_id).filter(Boolean)).size,
      transportCount: Math.max(1, linkedCampaigns.length || material.campaign_ids.length || Math.ceil((index + 1) / 2)),
      reviewStatus: material.review_status || reviewStatusFromState(material.status),
      score: material.score ?? estimateScore(metrics, material.ctr_estimate),
      fatigue,
      previewUrl,
      mimeType,
      metrics,
    }
  })
}

export const calculateOverview = (rows: MaterialRow[]): MaterialOverview => {
  const total = rows.reduce((acc, row) => {
    acc.spend += row.metrics.spend
    acc.impressions += row.metrics.impressions
    acc.clicks += row.metrics.clicks
    acc.conversions += row.metrics.conversions
    acc.revenue += row.metrics.revenue
    if (row.mediaKind === 'video') {
      acc.shortVideoSpend += row.metrics.spend
    }
    return acc
  }, { ...emptyMetrics(), shortVideoSpend: 0 })

  return {
    spend: total.spend,
    impressions: total.impressions,
    clicks: total.clicks,
    ctr: total.impressions > 0 ? total.clicks / total.impressions * 100 : 0,
    roas: total.spend > 0 ? total.revenue / total.spend : 0,
    cpc: total.clicks > 0 ? total.spend / total.clicks : 0,
    shortVideoSpend: total.shortVideoSpend,
    spendingMaterials: rows.filter(row => row.metrics.spend > 0).length,
    averageImpressions: rows.length ? total.impressions / rows.length : 0,
    averageClicks: rows.length ? total.clicks / rows.length : 0,
  }
}

export const buildAnalysis = (rows: MaterialRow[], overview: MaterialOverview): MaterialAnalysis[] => {
  if (rows.length === 0) {
    return [{
      title: '暂无可分析素材',
      body: '上传或同步素材后，这里会根据投放表现给出筛选建议。',
      tone: 'info',
      icon: 'info',
    }]
  }

  const top = [...rows].sort((a, b) => b.metrics.revenue - a.metrics.revenue || b.metrics.roas - a.metrics.roas)[0]
  const highSpend = [...rows].sort((a, b) => b.metrics.spend - a.metrics.spend)[0]
  const highFatigue = rows.filter(row => row.fatigue >= 65)
  const lowRoas = rows.filter(row => row.metrics.spend > 0 && row.metrics.roas < 2)
  const bestCtr = [...rows].sort((a, b) => b.metrics.ctr - a.metrics.ctr)[0]
  const videoRows = rows.filter(row => row.mediaKind === 'video')
  const videoSpend = videoRows.reduce((sum, row) => sum + row.metrics.spend, 0)
  const videoImpressions = videoRows.reduce((sum, row) => sum + row.metrics.impressions, 0)
  const videoClicks = videoRows.reduce((sum, row) => sum + row.metrics.clicks, 0)
  const videoCtr = videoImpressions > 0 ? videoClicks / videoImpressions * 100 : 0

  return [
    {
      title: '优先放量',
      body: top
        ? `${top.name} 当前周期 ROAS ${formatNumber(top.metrics.roas, 2)}x，贡献收入 ${formatCurrency(top.metrics.revenue)}。建议保留主投放位，并扩展相似开头与同类版位。`
        : '当前素材缺少收入数据，建议先完成账号和计划绑定。',
      tone: 'good',
      icon: 'trending_up',
    },
    {
      title: lowRoas.length ? '预算预警' : '预算健康',
      body: highSpend
        ? `最高消耗素材为 ${highSpend.name}，周期消耗 ${formatCurrency(highSpend.metrics.spend)}。${lowRoas.length ? `${lowRoas.length} 个素材 ROAS 低于 2.0，建议降预算或替换前 3 秒钩子。` : '当前高消耗素材回收未出现明显异常，可继续观察频控。'}`
        : '当前周期暂无消耗素材，先完成素材绑定和投放测试。',
      tone: lowRoas.length ? 'warning' : 'good',
      icon: 'account_balance_wallet',
    },
    {
      title: highFatigue.length ? '疲劳风险' : '创意稳定',
      body: highFatigue.length
        ? `重点处理 ${highFatigue[0].name}，疲劳度 ${highFatigue[0].fatigue}%。建议补充同主题新剪辑。`
        : bestCtr ? `点击最高素材为 ${bestCtr.name}，CTR ${formatPercent(bestCtr.metrics.ctr)}，可作为新素材脚本参考。` : '当前点击数据不足，继续观察素材表现。',
      tone: highFatigue.length ? 'warning' : 'good',
      icon: 'battery_alert',
    },
    {
      title: '短视频表现',
      body: `${videoRows.length} 条视频素材，周期消耗 ${formatCurrency(videoSpend)}，CTR ${formatPercent(videoCtr)}。竖版素材适合继续在 Reels / TikTok 信息流做小预算扩量。`,
      tone: 'info',
      icon: 'movie',
    },
  ]
}

export const formatCurrency = (value: number): string => {
  if (value >= 1000000) return `$${formatNumber(value / 1000000, 2)}M`
  if (value >= 1000) return `$${formatNumber(value / 1000, 1)}K`
  return `$${formatNumber(value, 2)}`
}

export const formatCompactNumber = (value: number): string => {
  if (value >= 1000000) return `${formatNumber(value / 1000000, 2)}M`
  if (value >= 1000) return `${formatNumber(value / 1000, 1)}K`
  return Math.round(value).toLocaleString()
}

export const formatPercent = (value: number): string => `${formatNumber(value, 2)}%`

export const formatNumber = (value: number, digits = 1): string => {
  if (!Number.isFinite(value)) return '0'
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

const estimateMetrics = (material: Material, campaigns: Campaign[]): MaterialMetrics => {
  if (campaigns.length === 0) {
    const ctr = material.ctr_estimate || 0
    const impressions = material.status === 'running' || material.status === 'fatigue' ? 12000 : 0
    const clicks = impressions > 0 ? Math.round(impressions * ctr / 100) : 0
    return {
      ...emptyMetrics(),
      impressions,
      clicks,
      ctr,
      spend: clicks > 0 ? clicks * 0.62 : 0,
      conversions: clicks > 0 ? Math.round(clicks * 0.08) : 0,
      revenue: clicks > 0 ? clicks * 1.12 : 0,
      roas: clicks > 0 ? 1.8 : 0,
      cpc: clicks > 0 ? 0.62 : 0,
      cpa: clicks > 0 ? 7.75 : 0,
    }
  }

  const base = campaigns.reduce((acc, campaign) => {
    const materialCount = Math.max(1, campaign.material_ids?.length || campaigns.length)
    const spend = (campaign.spent || 0) / materialCount
    const impressions = Math.max(0, spend * 650)
    const ctr = material.ctr_estimate || (campaign.platform?.toLowerCase().includes('tiktok') ? 2.8 : 1.7)
    const clicks = Math.round(impressions * ctr / 100)
    const conversions = Math.round(clicks * 0.09)
    const revenue = spend * (campaign.status === 'running' ? 1.75 : 1.2)

    acc.spend += spend
    acc.impressions += impressions
    acc.clicks += clicks
    acc.conversions += conversions
    acc.revenue += revenue
    return acc
  }, emptyMetrics())

  base.ctr = base.impressions > 0 ? base.clicks / base.impressions * 100 : material.ctr_estimate || 0
  base.roas = base.spend > 0 ? base.revenue / base.spend : 0
  base.cpc = base.clicks > 0 ? base.spend / base.clicks : 0
  base.cpa = base.conversions > 0 ? base.spend / base.conversions : 0
  return base
}

const resolveMediaKind = (material: Material, mimeType?: string): MaterialMediaKind => {
  if (material.media_kind === 'image' || material.media_kind === 'video') return material.media_kind
  const urlText = `${material.preview_url || ''} ${material.thumbnail_url || ''} ${material.url || ''}`.toLowerCase()
  if (mimeType?.startsWith('video/') || /\.(mp4|mov|webm)(\?|$)/.test(urlText)) return 'video'
  return 'image'
}

const resolveSource = (source?: string, url?: string): MaterialSourceKind => {
  if (source === 'oss_upload') return 'oss'
  if (source === 'meta_import' || source === 'tiktok_import' || source === 'ai_generated') return source
  if (source === 'local') return 'local'
  if (!url) return 'unknown'
  if (url.includes('aliyuncs.com') || url.includes('oss-')) return 'oss'
  if (url.startsWith('/')) return 'local'
  return 'imported'
}

const sourceLabel = (source: MaterialSourceKind): string => {
  const labels: Record<MaterialSourceKind, string> = {
    oss: 'OSS 上传',
    local: '本地素材',
    imported: '外部导入',
    meta_import: 'Meta 导入',
    tiktok_import: 'TikTok 导入',
    ai_generated: 'AI 生成',
    unknown: '未知来源',
  }
  return labels[source]
}

const statusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    running: '投放中',
    ready: '待投放',
    fatigue: '已疲劳',
  }
  return labels[status] || status
}

const reviewStatusFromState = (status: string): string => {
  if (status === 'running') return '已通过'
  if (status === 'fatigue') return '需复审'
  return '待审核'
}

const estimateScore = (metrics: MaterialMetrics, ctrEstimate?: number): number => {
  const ctr = metrics.ctr || ctrEstimate || 0
  const roas = metrics.roas || 0
  return Math.max(35, Math.min(96, Math.round(ctr * 14 + roas * 18 + 28)))
}

const estimateFatigue = (material: Material, metrics: MaterialMetrics): number => {
  if (material.status === 'fatigue') return 84
  if (material.status === 'ready') return 18
  return Math.max(25, Math.min(78, Math.round(metrics.impressions / 12000 + metrics.spend / 120)))
}

const guessMimeType = (url?: string): string => {
  if (!url) return ''
  const ext = url.split('?')[0].split('.').pop()?.toLowerCase()
  const mimes: Record<string, string> = {
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    webp: 'image/webp',
    gif: 'image/gif',
    mp4: 'video/mp4',
    mov: 'video/quicktime',
    webm: 'video/webm',
  }
  return ext ? mimes[ext] || '' : ''
}

const formatFromUrl = (url?: string): string => {
  const ext = url?.split('?')[0].split('.').pop()
  return ext ? ext.toUpperCase() : 'UNKNOWN'
}

const formatDuration = (duration?: number): string => {
  if (!duration) return '-'
  const minutes = Math.floor(duration / 60)
  const seconds = duration % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

const formatFileSize = (size?: number): string => {
  if (!size) return '-'
  if (size >= 1024 * 1024) return `${formatNumber(size / 1024 / 1024, 2)} MB`
  return `${formatNumber(size / 1024, 0)} KB`
}

const formatDateTime = (value?: string): string => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
