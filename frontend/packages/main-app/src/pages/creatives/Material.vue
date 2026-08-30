<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import MaterialLibraryView from '@/components/materials/MaterialLibraryView.vue'
import {
  deleteMaterial,
  getMaterialImage,
  getMaterials,
  getMetaAdAccounts,
  syncMetaMaterials,
  publishMaterialToMeta,
  refreshMaterialPlatformAsset,
  updateMaterial,
  uploadMaterialWithMetadata,
  type Material,
  type MaterialSyncRun,
  type MetaAdAccountOption,
  type MaterialPlatformAsset,
} from '@/api/materials'
import { navItems } from '@/config/navigation'
import { useToast } from '@/composables/useToast'
import { MAX_TREND_METRICS } from '@/data/trendMetrics'
import { toMaterialRows, type MaterialRow } from './materialsAdapter'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { success, error: showError } = useToast()

const activeSession = ref('sess_g001')
const loading = ref(false)
const error = ref('')
const materials = ref<Material[]>([])
const materialOriginals = ref<Map<string, string>>(new Map())
const materialPreviewAttemptIndexes = ref<Map<string, number>>(new Map())
const selectedMaterialId = ref<string | null>(null)
const detailOpen = ref(false)
const deletingMaterial = ref<MaterialRow | null>(null)
const deleting = ref(false)
const editingMaterial = ref<MaterialRow | null>(null)
const editForm = ref({
  name: '',
  tagsText: '',
})
const savingEdit = ref(false)

const showUploadModal = ref(false)
const uploadFiles = ref<File[]>([])
const uploadPoster = ref<Blob | null>(null)
const uploadPosterPreview = ref('')
const probingUpload = ref(false)
const uploadForm = ref({
  name: '',
  tagsText: '',
  format: '',
  width: '',
  height: '',
  ratio: '',
  duration: '',
  fileSize: '',
})
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref<Map<string, number>>(new Map())

const showMetaSyncModal = ref(false)
const metaAccounts = ref<MetaAdAccountOption[]>([])
const loadingMetaAccounts = ref(false)
const selectedMetaAccountKey = ref('')
const metaSyncAssetTypes = ref<Array<'image' | 'video'>>(['image', 'video'])
const syncingMeta = ref(false)
const metaSyncResult = ref<MaterialSyncRun | null>(null)
const showMetaPublishModal = ref(false)
const publishingMeta = ref(false)
const publishMaterial = ref<MaterialRow | null>(null)
const publishAssetType = ref<'image' | 'video'>('image')
const publishPlatform = ref('Meta')
const publishAccountKeys = ref<string[]>([])
const publishError = ref('')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场拓展', active: false },
])

type UploadMediaMetadata = {
  width: number
  height: number
  ratio: string
  duration?: number
  poster?: Blob
}

const uploadFile = computed(() => uploadFiles.value[0] || null)
const uploadPreviewUrl = ref('')
const uploadIsVideo = computed(() => uploadFile.value?.type.startsWith('video/') || false)

type OverviewCard = {
  label: string
  value: string
  sub: string
}

type AnalysisCard = {
  badge: string
  title: string
  body: string
  badgeClass: string
}

const materialDateStart = ref('2026-08-24')
const materialDateEnd = ref('2026-08-30')
const materialDateStartInput = ref<HTMLInputElement | null>(null)
const materialDateEndInput = ref<HTMLInputElement | null>(null)
const materialRangeDays = computed(() => {
  const start = Date.parse(`${materialDateStart.value}T00:00:00`)
  const end = Date.parse(`${materialDateEnd.value}T00:00:00`)
  return Number.isFinite(start) && Number.isFinite(end) ? Math.max(1, Math.round((end - start) / 86400000) + 1) : 1
})
const materialDateRangeLabel = computed(() => `${materialDateStart.value.replace(/-/g, '/')} – ${materialDateEnd.value.replace(/-/g, '/')}`)

function openMaterialDatePicker(boundary: 'start' | 'end'): void {
  const input = boundary === 'start' ? materialDateStartInput.value : materialDateEndInput.value
  if (!input) return
  input.focus()
  if (typeof input.showPicker === 'function') input.showPicker()
}

function handleMaterialDateRangeClick(event: MouseEvent): void {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  openMaterialDatePicker(event.clientX < rect.left + rect.width / 2 ? 'start' : 'end')
}
const materialFilterSearch = ref('')
const materialFilterAccount = ref('all')
const materialFilterSource = ref('all')
const materialFilterRatio = ref('all')
const materialFilterSort = ref<'created_at' | 'name'>('created_at')
const materialFilterAccountOptions = computed(() => {
  const accounts = new Map<string, string>()
  materials.value.forEach(material => material.platform_assets?.forEach(asset => {
    accounts.set(asset.ad_account_id, asset.ad_account_name || asset.ad_account_id)
  }))
  return Array.from(accounts, ([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label))
})
const overviewCards = computed<OverviewCard[]>(() => [
  {
    label: '当前结果',
    value: '7',
    sub: '图片与视频素材',
  },
  {
    label: '可投放',
    value: '3',
    sub: '可直接使用素材',
  },
  {
    label: '处理中',
    value: '2',
    sub: '待平台返回结果',
  },
  {
    label: '高疲劳',
    value: '3',
    sub: '建议替换或降预算',
  },
  {
    label: '平均评分',
    value: '78',
    sub: '质量与投放信号',
  },
])

const analysisCards = computed<AnalysisCard[]>(() => [
  {
    badge: '优先放量',
    title: 'CB_Meta_Reels_LevelWin_A',
    body: '该素材在当前周期 ROAS 2.76x，贡献收入 $23,239。建议保留主投放位，并扩展相似开头与同类版位。',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200',
  },
  {
    badge: '预算预警',
    title: 'CB_Archive_StaticReward_1x1_Old',
    body: '最高消耗素材为 $9,880。3 个素材 ROAS 低于 2.0，建议降预算或替换前 3 秒钩子。',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200',
  },
  {
    badge: '疲劳风险',
    title: '3 个高疲劳素材',
    body: '重点处理 CB_Archive_StaticReward_1x1_Old，疲劳度 88%。建议补充同主题新剪辑。',
    badgeClass: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-200',
  },
  {
    badge: '短视频表现',
    title: '3 条视频素材',
    body: '视频素材周期消耗 $14,600，CTR 4.04%。竖版素材适合继续在 Reels / TikTok 信息流做小预算扩量。',
    badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-200',
  },
])

type MaterialTrendMetric =
  | 'spend' | 'revenue' | 'impressions' | 'clicks' | 'ctr' | 'cpc' | 'cpm' | 'conversions' | 'cvr' | 'cpa' | 'roas'
  | 'creativeImpressions' | 'videoViews' | 'videoViewRate' | 'completionRate' | 'engagementRate' | 'avgWatchTime' | 'fatigueRate'
  | 'metaReach' | 'metaFrequency' | 'metaLinkClicks' | 'metaLandingPageViews' | 'metaThruPlays'
  | 'googleInteractions' | 'googleInteractionRate' | 'googleViews' | 'googleViewRate' | 'googleAvgCpv'
  | 'tiktokVideoViews2s' | 'tiktokVideoViews6s' | 'tiktokVideoViews25' | 'tiktokVideoViews50' | 'tiktokVideoViews75' | 'tiktokVideoViews100' | 'tiktokEngagements'
type MaterialTrendMetricGroup = 'overview' | 'creative' | 'meta' | 'google' | 'tiktok'
type MaterialTrendMetricFormat = 'number' | 'money' | 'percent' | 'ratio' | 'seconds'
type MaterialTrendPoint = Record<MaterialTrendMetric, number> & {
  label: string
  fullLabel: string
  x: number
}

const materialTrendMetricOptions: Array<{ key: MaterialTrendMetric; label: string; color: string; group: MaterialTrendMetricGroup; format: MaterialTrendMetricFormat }> = [
  { key: 'impressions', label: '曝光次数', color: '#5b8def', group: 'overview', format: 'number' },
  { key: 'spend', label: '花费', color: '#f5a33f', group: 'overview', format: 'money' },
  { key: 'revenue', label: '收入', color: '#20a464', group: 'overview', format: 'money' },
  { key: 'clicks', label: '点击', color: '#0891b2', group: 'overview', format: 'number' },
  { key: 'ctr', label: 'CTR', color: '#d946ef', group: 'overview', format: 'percent' },
  { key: 'cpc', label: 'CPC', color: '#64748b', group: 'overview', format: 'money' },
  { key: 'cpm', label: 'CPM', color: '#0f766e', group: 'overview', format: 'money' },
  { key: 'conversions', label: '转化', color: '#8b5cf6', group: 'overview', format: 'number' },
  { key: 'cvr', label: 'CVR', color: '#a855f7', group: 'overview', format: 'percent' },
  { key: 'cpa', label: 'CPA', color: '#475569', group: 'overview', format: 'money' },
  { key: 'roas', label: 'ROAS', color: '#16a34a', group: 'overview', format: 'ratio' },
  { key: 'creativeImpressions', label: '素材曝光', color: '#4f8fe8', group: 'creative', format: 'number' },
  { key: 'videoViews', label: '视频播放', color: '#0ea5e9', group: 'creative', format: 'number' },
  { key: 'videoViewRate', label: '视频观看率', color: '#06b6d4', group: 'creative', format: 'percent' },
  { key: 'completionRate', label: '完播率', color: '#14b8a6', group: 'creative', format: 'percent' },
  { key: 'engagementRate', label: '互动率', color: '#10b981', group: 'creative', format: 'percent' },
  { key: 'avgWatchTime', label: '平均观看时长', color: '#22c55e', group: 'creative', format: 'seconds' },
  { key: 'fatigueRate', label: '疲劳度', color: '#ef4444', group: 'creative', format: 'percent' },
  { key: 'metaReach', label: '覆盖人数', color: '#2563eb', group: 'meta', format: 'number' },
  { key: 'metaFrequency', label: '频次', color: '#3b82f6', group: 'meta', format: 'ratio' },
  { key: 'metaLinkClicks', label: '链接点击', color: '#60a5fa', group: 'meta', format: 'number' },
  { key: 'metaLandingPageViews', label: '落地页浏览', color: '#1d4ed8', group: 'meta', format: 'number' },
  { key: 'metaThruPlays', label: 'ThruPlay', color: '#1e40af', group: 'meta', format: 'number' },
  { key: 'googleInteractions', label: '互动次数', color: '#f59e0b', group: 'google', format: 'number' },
  { key: 'googleInteractionRate', label: '互动率', color: '#d97706', group: 'google', format: 'percent' },
  { key: 'googleViews', label: '观看次数', color: '#fbbf24', group: 'google', format: 'number' },
  { key: 'googleViewRate', label: '观看率', color: '#b45309', group: 'google', format: 'percent' },
  { key: 'googleAvgCpv', label: '平均 CPV', color: '#92400e', group: 'google', format: 'money' },
  { key: 'tiktokVideoViews2s', label: '2秒播放', color: '#111827', group: 'tiktok', format: 'number' },
  { key: 'tiktokVideoViews6s', label: '6秒播放', color: '#374151', group: 'tiktok', format: 'number' },
  { key: 'tiktokVideoViews25', label: '25%播放', color: '#4b5563', group: 'tiktok', format: 'number' },
  { key: 'tiktokVideoViews50', label: '50%播放', color: '#6b7280', group: 'tiktok', format: 'number' },
  { key: 'tiktokVideoViews75', label: '75%播放', color: '#9ca3af', group: 'tiktok', format: 'number' },
  { key: 'tiktokVideoViews100', label: '100%播放', color: '#0f172a', group: 'tiktok', format: 'number' },
  { key: 'tiktokEngagements', label: '互动次数', color: '#be123c', group: 'tiktok', format: 'number' },
]
const materialTrendMetricGroups = ([
  { key: 'overview', label: '数据概览维度' },
  { key: 'creative', label: '创意素材维度' },
  { key: 'meta', label: 'Meta 核心指标' },
  { key: 'google', label: 'Google 核心指标' },
  { key: 'tiktok', label: 'TikTok 核心指标' },
] as Array<{ key: MaterialTrendMetricGroup; label: string }>).map(group => ({
  ...group,
  metrics: materialTrendMetricOptions.filter(item => item.group === group.key),
}))
const activeMaterialTrendMetrics = ref<MaterialTrendMetric[]>(['impressions', 'spend'])
const materialTrendMetricPickerOpen = ref(false)
const hoveredMaterialTrendIndex = ref<number | null>(null)
const hasMaterialTrendMetric = (metric: MaterialTrendMetric) => activeMaterialTrendMetrics.value.includes(metric)
const isMaterialTrendMetricDisabled = (metric: MaterialTrendMetric) => !hasMaterialTrendMetric(metric) && activeMaterialTrendMetrics.value.length >= MAX_TREND_METRICS
const selectedMaterialTrendMetricOptions = computed(() => materialTrendMetricOptions.filter(item => hasMaterialTrendMetric(item.key)))
const toggleMaterialTrendMetric = (metric: MaterialTrendMetric) => {
  if (hasMaterialTrendMetric(metric) && activeMaterialTrendMetrics.value.length === 1) return
  if (isMaterialTrendMetricDisabled(metric)) return
  activeMaterialTrendMetrics.value = hasMaterialTrendMetric(metric)
    ? activeMaterialTrendMetrics.value.filter(item => item !== metric)
    : [...activeMaterialTrendMetrics.value, metric]
}

const materialTrendPoints = computed<MaterialTrendPoint[]>(() => {
  const singleDay = materialRangeDays.value === 1
  const count = singleDay ? 8 : materialRangeDays.value
  const startDate = new Date(`${materialDateStart.value}T00:00:00`)
  return Array.from({ length: count }, (_, index) => {
    const progress = count <= 1 ? 0 : index / (count - 1)
    const wave = Math.sin(index * 1.18) * .09 + Math.cos(index * .53) * .045
    const spend = (singleDay ? 92 : 390) * (1 + progress * .42 + wave)
    const impressions = Math.round(spend * (13.4 + (index % 4) * 1.1))
    const ctr = 3.22 + progress * .88 + Math.sin(index * .72) * .18
    const clicks = Math.round(impressions * ctr / 100)
    const conversions = Math.max(1, Math.round(clicks * (.074 + progress * .014 + (index % 3) * .003)))
    const roas = 2.02 + progress * .68 + Math.cos(index * .67) * .14
    const revenue = spend * roas
    const cpc = spend / Math.max(clicks, 1)
    const cpm = spend / Math.max(impressions, 1) * 1000
    const cvr = conversions / Math.max(clicks, 1) * 100
    const cpa = spend / Math.max(conversions, 1)
    const creativeImpressions = Math.round(impressions * (.84 + progress * .04))
    const videoViews = Math.round(creativeImpressions * (.48 + progress * .08))
    const videoViewRate = videoViews / Math.max(creativeImpressions, 1) * 100
    const completionRate = 18.5 + progress * 9.2 + Math.sin(index * .48) * 1.6
    const engagementRate = 4.1 + progress * 1.6 + Math.cos(index * .62) * .35
    const avgWatchTime = 5.8 + progress * 2.7 + Math.sin(index * .4) * .45
    const fatigueRate = 38 + progress * 24 + Math.max(0, Math.sin(index * .58) * 6)
    const metaReach = Math.round(impressions / (1.32 + progress * .22))
    const metaFrequency = impressions / Math.max(metaReach, 1)
    const metaLinkClicks = Math.round(clicks * .74)
    const metaLandingPageViews = Math.round(metaLinkClicks * .82)
    const metaThruPlays = Math.round(videoViews * .46)
    const googleInteractions = Math.round(clicks + videoViews * .07)
    const googleInteractionRate = googleInteractions / Math.max(impressions, 1) * 100
    const googleViews = Math.round(videoViews * .63)
    const googleViewRate = googleViews / Math.max(impressions, 1) * 100
    const googleAvgCpv = spend / Math.max(googleViews, 1)
    const tiktokVideoViews2s = Math.round(videoViews * .91)
    const tiktokVideoViews6s = Math.round(videoViews * .68)
    const tiktokVideoViews25 = Math.round(videoViews * .76)
    const tiktokVideoViews50 = Math.round(videoViews * .58)
    const tiktokVideoViews75 = Math.round(videoViews * .44)
    const tiktokVideoViews100 = Math.round(videoViews * completionRate / 100)
    const tiktokEngagements = Math.round(videoViews * engagementRate / 100)
    let label = ''
    let fullLabel = ''
    if (singleDay) {
      label = `${String(8 + index * 2).padStart(2, '0')}:00`
      fullLabel = `${materialDateStart.value.replace(/-/g, '/')} ${label}`
    } else {
      const date = new Date(startDate)
      date.setDate(startDate.getDate() + index)
      label = `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
      fullLabel = `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`
    }
    return {
      label,
      fullLabel,
      x: count <= 1 ? 480 : 84 + index * 792 / (count - 1),
      spend,
      revenue,
      impressions,
      clicks,
      conversions,
      ctr,
      cpc,
      cpm,
      cvr,
      cpa,
      roas,
      creativeImpressions,
      videoViews,
      videoViewRate,
      completionRate,
      engagementRate,
      avgWatchTime,
      fatigueRate,
      metaReach,
      metaFrequency,
      metaLinkClicks,
      metaLandingPageViews,
      metaThruPlays,
      googleInteractions,
      googleInteractionRate,
      googleViews,
      googleViewRate,
      googleAvgCpv,
      tiktokVideoViews2s,
      tiktokVideoViews6s,
      tiktokVideoViews25,
      tiktokVideoViews50,
      tiktokVideoViews75,
      tiktokVideoViews100,
      tiktokEngagements,
    }
  })
})
const niceMaterialTrendMax = (value: number) => {
  if (value <= 0) return 1
  const roughStep = value / 3
  const magnitude = 10 ** Math.floor(Math.log10(roughStep))
  return Math.ceil(roughStep / magnitude) * magnitude * 3
}
const materialTrendScales = computed(() => Object.fromEntries(materialTrendMetricOptions.map(({ key }) => {
  const max = Math.max(...materialTrendPoints.value.map(point => point[key]))
  return [key, niceMaterialTrendMax(max)]
})) as Record<MaterialTrendMetric, number>)
const materialTrendY = (metric: MaterialTrendMetric, value: number) => {
  const max = materialTrendScales.value[metric]
  return 146 - value / max * 108
}
const materialTrendPath = (metric: MaterialTrendMetric) => {
  const points = materialTrendPoints.value.map(point => ({ x: point.x, y: materialTrendY(metric, point[metric]) }))
  if (!points.length) return ''
  if (points.length === 1) return `M${points[0].x} ${points[0].y}`
  return points.slice(0, -1).reduce((path, point, index) => {
    const previous = points[index - 1] || point
    const next = points[index + 1]
    const afterNext = points[index + 2] || next
    const control1X = point.x + (next.x - previous.x) / 6
    const control1Y = point.y + (next.y - previous.y) / 6
    const control2X = next.x - (afterNext.x - point.x) / 6
    const control2Y = next.y - (afterNext.y - point.y) / 6
    return `${path} C${control1X} ${control1Y},${control2X} ${control2Y},${next.x} ${next.y}`
  }, `M${points[0].x} ${points[0].y}`)
}
const materialTrendAxisTicks = computed(() => {
  const points = materialTrendPoints.value
  if (points.length <= 8) return points.map((point, index) => ({ point, index }))
  const step = Math.ceil((points.length - 1) / 6)
  return Array.from({ length: Math.floor((points.length - 1) / step) + 1 }, (_, tickIndex) => {
    const index = tickIndex * step
    return { point: points[index], index }
  })
})
const materialTrendHitWidth = computed(() => materialTrendPoints.value.length <= 1 ? 72 : Math.max(10, 792 / (materialTrendPoints.value.length - 1)))
const activeMaterialTrendPoint = computed(() => hoveredMaterialTrendIndex.value === null ? null : materialTrendPoints.value[hoveredMaterialTrendIndex.value])
const materialTrendTooltipLeft = computed(() => {
  const index = hoveredMaterialTrendIndex.value
  return index === null || materialTrendPoints.value.length <= 1 ? 50 : 10 + index / (materialTrendPoints.value.length - 1) * 80
})
const primaryMaterialTrendMetric = computed(() => selectedMaterialTrendMetricOptions.value[0]?.key || 'impressions')
const secondaryMaterialTrendMetric = computed(() => selectedMaterialTrendMetricOptions.value[1]?.key || null)
const materialTrendAxisValues = (metric: MaterialTrendMetric) => {
  const max = materialTrendScales.value[metric]
  return [max, max * 2 / 3, max / 3, 0]
}
const formatMaterialTrendAxisValue = (value: number) => {
  if (Math.abs(value) >= 1000) return Math.round(value).toLocaleString('en-US')
  if (Math.abs(value) >= 10) return Math.round(value).toLocaleString('en-US')
  return value.toFixed(1).replace(/\.0$/, '')
}
const formatMaterialTrendValue = (metric: MaterialTrendMetric, value: number) => {
  const format = materialTrendMetricOptions.find(item => item.key === metric)?.format || 'number'
  if (format === 'money') return `US$${value.toFixed(2)}`
  if (format === 'percent') return `${value.toFixed(2)}%`
  if (format === 'ratio') return `${value.toFixed(2)}x`
  if (format === 'seconds') return `${value.toFixed(1)}s`
  return Math.round(value).toLocaleString('en-US')
}

const selectedRow = computed(() => {
  const material = materials.value.find(item => item.id === selectedMaterialId.value) || materials.value[0]
  if (!material) return null
  return toMaterialRows([material], new Map(), new Map())[0] || null
})
const selectedPreviewCandidates = computed(() => selectedRow.value ? getMaterialPreviewCandidates(selectedRow.value) : [])
const selectedPreviewUrl = computed(() => {
  if (!selectedRow.value) return ''
  const attemptIndex = materialPreviewAttemptIndexes.value.get(selectedRow.value.id) || 0
  return selectedPreviewCandidates.value[attemptIndex] || ''
})

const getMaterialPreviewCandidates = (row: MaterialRow) => {
  const candidates = [
    materialOriginals.value.get(row.id),
    row.previewUrl,
    row.material.poster_url,
    row.material.preview_url,
    row.material.thumbnail_url,
    row.material.url,
  ].filter((value): value is string => Boolean(value?.trim()))

  return Array.from(new Set(candidates))
}

const getMaterialPreviewFallback = (material: Material) => (
  material.poster_url ||
  material.preview_url ||
  material.thumbnail_url ||
  material.url ||
  ''
)

const setMaterialOriginalSource = (materialId: string, source: string) => {
  if (!source) return
  const nextOriginals = new Map(materialOriginals.value)
  nextOriginals.set(materialId, source)
  materialOriginals.value = nextOriginals

  const nextAttempts = new Map(materialPreviewAttemptIndexes.value)
  nextAttempts.delete(materialId)
  materialPreviewAttemptIndexes.value = nextAttempts
}

const handleSelectedPreviewError = () => {
  const row = selectedRow.value
  if (!row) return

  const candidates = getMaterialPreviewCandidates(row)
  const currentIndex = candidates.indexOf(selectedPreviewUrl.value)
  const nextAttempts = new Map(materialPreviewAttemptIndexes.value)
  nextAttempts.set(row.id, currentIndex >= 0 ? currentIndex + 1 : (nextAttempts.get(row.id) || 0) + 1)
  materialPreviewAttemptIndexes.value = nextAttempts
}

onMounted(async () => {
  await loadPageData()
})

const loadPageData = async () => {
  try {
    loading.value = true
    error.value = ''
    if (!auth.isLoggedIn) {
      await router.push('/login')
      return
    }

    const materialData = await getMaterials({ limit: 200 })
    materials.value = materialData

    const requestedMaterialId = typeof route.query.material_id === 'string' ? route.query.material_id : ''
    const requestedMaterial = materialData.find(material => material.id === requestedMaterialId)
    if (requestedMaterial) {
      selectedMaterialId.value = requestedMaterial.id
      detailOpen.value = true
      await loadOriginalSource(requestedMaterial)
    } else if (!selectedMaterialId.value && materialData.length > 0) {
      selectedMaterialId.value = materialData[0].id
    }
  } catch (err: any) {
    error.value = err.message || '加载素材失败'
    showError(error.value)
  } finally {
    loading.value = false
  }
}

const loadOriginalSource = async (material: Material) => {
  if (materialOriginals.value.has(material.id)) return
  try {
    const original = await getMaterialImage(material.id, false)
    setMaterialOriginalSource(material.id, original.url || original.data || getMaterialPreviewFallback(material))
  } catch {
    setMaterialOriginalSource(material.id, getMaterialPreviewFallback(material))
  }
}

const switchPanel = (item: any) => {
  if (item.path) router.push(item.path)
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => { s.active = s.id === session.id })
}

const selectRow = (row: MaterialRow) => {
  selectedMaterialId.value = row.id
  detailOpen.value = true
  void loadOriginalSource(row.material)
}

const closeDetailDrawer = () => {
  detailOpen.value = false
}

const refreshMaterials = async () => {
  await loadPageData()
  success('素材数据已刷新')
}

const uniqueMetaAccounts = (accounts: MetaAdAccountOption[]) => {
  const seen = new Set<string>()
  return accounts.filter(account => {
    const normalizedId = account.account_id.replace(/^act_/, '')
    if (seen.has(normalizedId)) return false
    seen.add(normalizedId)
    return true
  })
}

const openMetaSyncModal = async () => {
  showMetaSyncModal.value = true
  metaSyncResult.value = null
  loadingMetaAccounts.value = true
  try {
    metaAccounts.value = uniqueMetaAccounts(await getMetaAdAccounts())
    selectedMetaAccountKey.value = metaAccounts.value[0]
      ? `${metaAccounts.value[0].connection_id}|${metaAccounts.value[0].account_id}`
      : ''
  } catch (err: any) {
    showError(err.message || '加载 Meta 广告账户失败')
  } finally {
    loadingMetaAccounts.value = false
  }
}

const closeMetaSyncModal = () => {
  if (!syncingMeta.value) showMetaSyncModal.value = false
}

const openMetaPublishModal = async (row: MaterialRow, assetType: 'image' | 'video') => {
  publishMaterial.value = row
  publishAssetType.value = assetType
  publishPlatform.value = 'Meta'
  publishError.value = ''
  showMetaPublishModal.value = true
  loadingMetaAccounts.value = true
  try {
    metaAccounts.value = uniqueMetaAccounts(await getMetaAdAccounts())
    publishAccountKeys.value = []
  } catch (err: any) {
    publishError.value = err.message || '加载 Meta 广告账户失败'
  } finally {
    loadingMetaAccounts.value = false
  }
}

const closeMetaPublishModal = () => {
  if (!publishingMeta.value) showMetaPublishModal.value = false
}

const togglePublishAccount = (key: string) => {
  publishAccountKeys.value = publishAccountKeys.value.includes(key)
    ? publishAccountKeys.value.filter(item => item !== key)
    : [...publishAccountKeys.value, key]
}

const waitForPlatformAsset = async (
  materialId: string,
  asset: MaterialPlatformAsset,
): Promise<MaterialPlatformAsset> => {
  let current = asset
  if (current.normalized_status === 'ready' || current.normalized_status === 'failed') return current
  for (let attempt = 0; attempt < 6; attempt += 1) {
    await new Promise(resolve => window.setTimeout(resolve, 2000))
    current = (await refreshMaterialPlatformAsset(materialId, current.id)).platform_asset
    if (current.normalized_status === 'ready' || current.normalized_status === 'failed') return current
  }
  return current
}

const runMetaPublish = async () => {
  if (!publishMaterial.value || !publishAccountKeys.value.length) return
  publishingMeta.value = true
  publishError.value = ''
  let readyCount = 0
  let processingCount = 0
  const failures: string[] = []
  try {
    for (const key of publishAccountKeys.value) {
      const [connectionId, accountId] = key.split('|')
      const account = metaAccounts.value.find(item => `${item.connection_id}|${item.account_id}` === key)
      try {
        const result = await publishMaterialToMeta(publishMaterial.value.id, {
          platform: publishPlatform.value,
          connection_id: connectionId,
          ad_account_id: accountId,
          asset_type: publishAssetType.value,
        })
        const finalAsset = await waitForPlatformAsset(publishMaterial.value.id, result.platform_asset)
        if (finalAsset.normalized_status === 'failed') {
          throw new Error(finalAsset.last_error || 'Meta 处理素材失败')
        }
        if (finalAsset.normalized_status === 'ready') readyCount += 1
        else processingCount += 1
      } catch (err: any) {
        failures.push(`${account?.account_name || accountId}：${err.message || '发布失败'}`)
      }
    }
    const summary = `发布结果：成功 ${readyCount}，处理中 ${processingCount}，失败 ${failures.length}`
    if (failures.length) showError(summary)
    else success(summary)
    publishError.value = failures.join('\n')
    if (!failures.length) showMetaPublishModal.value = false
    await loadPageData()
  } finally {
    publishingMeta.value = false
  }
}

const runMetaSync = async () => {
  const account = metaAccounts.value.find(
    item => `${item.connection_id}|${item.account_id}` === selectedMetaAccountKey.value
  )
  if (!account) {
    showError('请选择 Meta 广告账户')
    return
  }
  if (!metaSyncAssetTypes.value.length) {
    showError('请至少选择一种素材类型')
    return
  }

  syncingMeta.value = true
  metaSyncResult.value = null
  try {
    const result = await syncMetaMaterials({
      connection_id: account.connection_id,
      ad_account_id: account.account_id,
      asset_types: metaSyncAssetTypes.value,
    })
    metaSyncResult.value = result
    if (result.status === 'succeeded') {
      success(`Meta 素材导入完成：新增 ${result.created_count}，更新 ${result.updated_count}`)
    } else if (result.status === 'partially_succeeded') {
      showError(`Meta 素材部分导入成功，失败 ${result.failed_count} 个`)
    } else {
      showError(result.error_summary || 'Meta 素材导入失败')
    }
    await loadPageData()
  } catch (err: any) {
    showError(err.message || 'Meta 素材导入失败')
  } finally {
    syncingMeta.value = false
  }
}

const openUploadModal = () => {
  showUploadModal.value = true
  uploadFiles.value = []
  resetUploadForm()
}

const closeUploadModal = () => {
  showUploadModal.value = false
  uploadFiles.value = []
  resetUploadForm()
  isDragging.value = false
}

const resetUploadForm = () => {
  if (uploadPosterPreview.value) URL.revokeObjectURL(uploadPosterPreview.value)
  if (uploadPreviewUrl.value) URL.revokeObjectURL(uploadPreviewUrl.value)
  uploadPoster.value = null
  uploadPosterPreview.value = ''
  uploadPreviewUrl.value = ''
  uploadForm.value = {
    name: '',
    tagsText: '',
    format: '',
    width: '',
    height: '',
    ratio: '',
    duration: '',
    fileSize: '',
  }
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) addFiles(Array.from(target.files))
  target.value = ''
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragging.value = false
  if (event.dataTransfer?.files) addFiles(Array.from(event.dataTransfer.files))
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const addFiles = (files: File[]) => {
  const validFiles = files.filter(file => {
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/quicktime']
    const maxSize = 100 * 1024 * 1024
    if (!validTypes.includes(file.type)) {
      showError(`文件 ${file.name} 格式不支持`)
      return false
    }
    if (file.size > maxSize) {
      showError(`文件 ${file.name} 超过100MB限制`)
      return false
    }
    return true
  })
  if (validFiles.length > 0) {
    uploadFiles.value = validFiles
    void prepareUploadMetadata(validFiles[0])
  }
}

const removeFile = (index: number) => {
  uploadFiles.value.splice(index, 1)
  if (index === 0) {
    if (uploadFiles.value[0]) void prepareUploadMetadata(uploadFiles.value[0])
    else resetUploadForm()
  }
}

const prepareUploadMetadata = async (file: File) => {
  probingUpload.value = true
  if (uploadPosterPreview.value) URL.revokeObjectURL(uploadPosterPreview.value)
  if (uploadPreviewUrl.value) URL.revokeObjectURL(uploadPreviewUrl.value)
  uploadPoster.value = null
  uploadPosterPreview.value = ''
  uploadPreviewUrl.value = ''

  const baseName = file.name.replace(/\.[^.]+$/, '')
  const ext = file.name.split('.').pop()?.toUpperCase() || ''
  uploadPreviewUrl.value = URL.createObjectURL(file)
  uploadForm.value.name = baseName
  uploadForm.value.format = ext
  uploadForm.value.fileSize = `${(file.size / 1024 / 1024).toFixed(2)} MB`

  try {
    const metadata = file.type.startsWith('video/')
      ? await probeVideo(file)
      : await probeImage(file)
    uploadForm.value.width = metadata.width ? String(metadata.width) : ''
    uploadForm.value.height = metadata.height ? String(metadata.height) : ''
    uploadForm.value.ratio = metadata.ratio || ''
    uploadForm.value.duration = metadata.duration ? String(Math.round(metadata.duration)) : ''
    if (metadata.poster) {
      uploadPoster.value = metadata.poster
      uploadPosterPreview.value = URL.createObjectURL(metadata.poster)
    }
  } catch (err: any) {
    showError(err.message || '读取素材元数据失败，仍可继续上传')
  } finally {
    probingUpload.value = false
  }
}

const probeImage = (file: File): Promise<UploadMediaMetadata> => {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      const width = image.naturalWidth
      const height = image.naturalHeight
      URL.revokeObjectURL(url)
      resolve({ width, height, ratio: ratioLabel(width, height) })
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片元数据读取失败'))
    }
    image.src = url
  })
}

const probeVideo = (file: File): Promise<UploadMediaMetadata> => {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.muted = true
    video.playsInline = true
    video.preload = 'metadata'

    const cleanup = () => {
      URL.revokeObjectURL(url)
      video.removeAttribute('src')
      video.load()
    }

    video.onloadedmetadata = () => {
      const seekTo = Math.min(0.2, Math.max(0, (video.duration || 1) / 10))
      video.currentTime = seekTo
    }
    video.onseeked = () => {
      const width = video.videoWidth
      const height = video.videoHeight
      const duration = video.duration || 0
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')?.drawImage(video, 0, 0, width, height)
      canvas.toBlob(blob => {
        cleanup()
        resolve({
          width,
          height,
          duration,
          ratio: ratioLabel(width, height),
          poster: blob || undefined,
        })
      }, 'image/jpeg', 0.82)
    }
    video.onerror = () => {
      cleanup()
      reject(new Error('视频元数据读取失败'))
    }
    video.src = url
  })
}

const ratioLabel = (width: number, height: number): string => {
  if (!width || !height) return ''
  const ratio = width / height
  if (Math.abs(ratio - 9 / 16) < 0.08) return '9:16'
  if (Math.abs(ratio - 1) < 0.08) return '1:1'
  if (Math.abs(ratio - 4 / 5) < 0.08) return '4:5'
  if (Math.abs(ratio - 16 / 9) < 0.08) return '16:9'
  return `${width}:${height}`
}

const completeUpload = async () => {
  if (!uploadFiles.value.length) {
    showError('请先选择要上传的文件')
    return
  }
  if (!uploadForm.value.name.trim()) {
    showError('素材名称不能为空')
    return
  }

  uploading.value = true
  uploadProgress.value.clear()
  try {
    const baseName = uploadForm.value.name.trim()
    const tags = Array.from(new Set(
      uploadForm.value.tagsText.split(',').map(tag => tag.trim()).filter(Boolean)
    ))

    for (const [index, file] of uploadFiles.value.entries()) {
      uploadProgress.value.set(file.name, 0)
      const isFirst = index === 0
      const mediaKind = file.type.startsWith('video/') ? 'video' : 'image'
      const name = uploadFiles.value.length > 1 ? `${baseName}_${String(index + 1).padStart(2, '0')}` : baseName
      await uploadMaterialWithMetadata(file, {
        name,
        tags,
        duration: isFirst && uploadForm.value.duration ? Number(uploadForm.value.duration) : undefined,
        width: isFirst && uploadForm.value.width ? Number(uploadForm.value.width) : undefined,
        height: isFirst && uploadForm.value.height ? Number(uploadForm.value.height) : undefined,
        ratio: isFirst ? uploadForm.value.ratio || undefined : undefined,
        format: file.name.split('.').pop()?.toUpperCase() || uploadForm.value.format || undefined,
        media_kind: mediaKind,
        source: 'oss_upload',
      }, isFirst ? uploadPoster.value || undefined : undefined)
      uploadProgress.value.set(file.name, 100)
    }

    success(`素材已上传：${uploadFiles.value.length} 个文件已保存`)
    closeUploadModal()
    await loadPageData()
  } catch (err: any) {
    showError(err.message || '上传失败，请稍后重试')
  } finally {
    uploading.value = false
    uploadProgress.value.clear()
  }
}

const askDeleteMaterial = (row: MaterialRow) => {
  deletingMaterial.value = row
}

const openEditMaterial = (row: MaterialRow) => {
  editingMaterial.value = row
  editForm.value = {
    name: row.name,
    tagsText: row.tags.join(', '),
  }
}

const closeEditMaterial = () => {
  if (!savingEdit.value) editingMaterial.value = null
}

const saveMaterialEdit = async () => {
  if (!editingMaterial.value) return
  const name = editForm.value.name.trim()
  if (!name) {
    showError('素材名称不能为空')
    return
  }

  savingEdit.value = true
  try {
    await updateMaterial(editingMaterial.value.id, {
      name,
      tags: editForm.value.tagsText.split(',').map(tag => tag.trim()).filter(Boolean),
    })
    success('素材信息已更新')
    editingMaterial.value = null
    await loadPageData()
  } catch (err: any) {
    showError(err.message || '保存素材失败')
  } finally {
    savingEdit.value = false
  }
}

const closeDeleteConfirm = () => {
  if (!deleting.value) deletingMaterial.value = null
}

const confirmDeleteMaterial = async () => {
  if (!deletingMaterial.value) return
  deleting.value = true
  try {
    await deleteMaterial(deletingMaterial.value.id)
    success('素材已从 ANIFORCE 删除，平台账户中的素材不受影响')
    if (selectedMaterialId.value === deletingMaterial.value.id) {
      selectedMaterialId.value = null
      detailOpen.value = false
    }
    deletingMaterial.value = null
    await loadPageData()
  } catch (err: any) {
    showError(err.message || '删除站内素材失败')
  } finally {
    deleting.value = false
  }
}

const platformAssetStatus = (status?: string) => ({ processing: '发布处理中', ready: '已发布', failed: '发布失败', unknown: '待验证' }[status || ''] || '待验证')
const materialFileStatus = (status?: string) => ({ processing: '处理中', ready: '已就绪', active: '已就绪', failed: '处理失败' }[status || ''] || status || '未知')
const platformClass = (platform?: string) => platform === 'Meta' ? 'platform-chip platform-chip-meta' : 'platform-chip'

</script>

<template>
  <div class="material-notion-page workspace-page-canvas relative flex h-screen w-full overflow-hidden dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="materials"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="min-w-0 flex-1 bg-transparent">
      <section class="min-w-0 flex h-full flex-col">
        <header data-workspace-page-header class="workspace-page-header flex shrink-0 items-center justify-between gap-[20px] border-b border-[#e5e3df] bg-white/90 px-[clamp(24px,3vw,48px)] dark:border-slate-800 dark:bg-slate-900">
          <div class="workspace-page-heading flex min-w-0 items-center gap-[8px]">
            <span class="workspace-page-heading-icon grid h-[26px] w-[26px] shrink-0 place-items-center rounded-[6px] bg-[#f6f5f4] text-[#37352f] dark:bg-slate-800 dark:text-slate-300">
              <span class="material-symbols-outlined text-[16px] leading-none">video_library</span>
            </span>
            <div class="workspace-page-heading-text min-w-0">
              <h1 class="m-0 text-[16px] font-semibold tracking-[-0.2px] text-[#1a1a1a] dark:text-white">素材管理</h1>
            </div>
          </div>
          <div class="flex items-center gap-[7px]">
            <button class="inline-flex min-h-[34px] items-center justify-center gap-[7px] rounded-[8px] border border-slate-200 bg-white px-[13px] text-[11px] font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800" @click="openMetaSyncModal">
              <span class="material-symbols-outlined text-[16px]">download</span>
              从 Meta 导入
            </button>
            <button type="button" class="material-create-button" @click="openUploadModal">
              <span class="material-symbols-outlined">upload</span>
              上传素材
            </button>
          </div>
        </header>

        <div class="material-notion-content workspace-page-content flex-1 overflow-y-auto px-[28px] py-[22px] max-md:px-[16px] max-md:py-[16px]">
          <div v-if="error" class="mb-[12px] rounded-md border border-red-200 bg-red-50 px-[12px] py-[9px] text-[11px] text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            {{ error }}
          </div>

          <div class="mb-[14px] space-y-[12px]">
            <section class="overview-filter-panel" aria-label="素材筛选与时间区间">
              <div class="overview-report-meta">
                <strong>素材</strong>
              </div>

              <div class="material-report-library-filters" aria-label="素材列表筛选">
                <label class="material-report-search">
                  <span class="material-symbols-outlined" aria-hidden="true">search</span>
                  <input v-model="materialFilterSearch" type="search" placeholder="搜索名称、文件名、标签或平台账户" aria-label="搜索素材" />
                </label>
                <select v-model="materialFilterAccount" aria-label="筛选广告账户">
                  <option value="all">全部广告账户</option>
                  <option v-for="item in materialFilterAccountOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                </select>
                <select v-model="materialFilterSource" aria-label="筛选素材来源">
                  <option value="all">全部来源</option>
                  <option value="oss">手动上传</option>
                  <option value="local">历史素材</option>
                  <option value="meta_import">Meta 导入</option>
                  <option value="google_import">Google 导入</option>
                  <option value="tiktok_import">TikTok 导入</option>
                </select>
                <select v-model="materialFilterRatio" aria-label="筛选素材比例">
                  <option value="all">全部比例</option>
                  <option value="9:16">9:16</option>
                  <option value="1:1">1:1</option>
                  <option value="4:5">4:5</option>
                  <option value="未知">未知</option>
                </select>
                <select v-model="materialFilterSort" aria-label="素材排序">
                  <option value="created_at">最近创建</option>
                  <option value="name">名称</option>
                </select>
              </div>

              <div class="overview-filter-controls">
                <div class="material-date-range" role="group" aria-label="时间筛选区间" @click="handleMaterialDateRangeClick">
                  <span class="material-symbols-outlined" aria-hidden="true">calendar_today</span>
                  <span class="material-date-prefix">时间：</span>
                  <div class="material-date-hotspot" role="button" tabindex="0" aria-label="筛选开始日期" @click.stop="openMaterialDatePicker('start')" @keydown.enter.prevent="openMaterialDatePicker('start')" @keydown.space.prevent="openMaterialDatePicker('start')">
                    <input ref="materialDateStartInput" v-model="materialDateStart" tabindex="-1" type="date" :max="materialDateEnd" aria-label="开始日期" />
                  </div>
                  <span class="material-date-separator">至</span>
                  <div class="material-date-hotspot" role="button" tabindex="0" aria-label="筛选结束日期" @click.stop="openMaterialDatePicker('end')" @keydown.enter.prevent="openMaterialDatePicker('end')" @keydown.space.prevent="openMaterialDatePicker('end')">
                    <input ref="materialDateEndInput" v-model="materialDateEnd" tabindex="-1" type="date" :min="materialDateStart" aria-label="结束日期" />
                  </div>
                </div>

              </div>
            </section>

            <section class="material-notion-section overview-metrics-panel overflow-hidden rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <div class="overview-strip">
                <div
                  v-for="card in overviewCards"
                  :key="card.label"
                  class="overview-metric"
                >
                  <div class="overview-metric-label text-[11px] font-semibold text-slate-500 dark:text-slate-400">{{ card.label }}</div>
                  <div class="overview-metric-value mt-[8px] truncate text-[21px] font-bold leading-none text-slate-900 dark:text-white">{{ card.value }}</div>
                  <div class="overview-metric-sub mt-[6px] truncate text-[10px] text-slate-500 dark:text-slate-400">{{ card.sub }}</div>
                </div>
              </div>
            </section>

            <section class="material-notion-section material-trend-panel" aria-labelledby="material-trend-title">
              <div class="material-trend-header">
                <div>
                  <strong id="material-trend-title">数据趋势</strong>
                  <p>{{ materialDateRangeLabel }} · 素材投放指标随时间变化</p>
                </div>
                <div class="material-trend-metric-actions">
                  <div class="material-trend-selected-metrics" aria-label="已选择趋势指标">
                    <button
                      v-for="item in selectedMaterialTrendMetricOptions"
                      :key="item.key"
                      type="button"
                      :title="`移除${item.label}`"
                      @click="toggleMaterialTrendMetric(item.key)"
                    >{{ item.label }}</button>
                  </div>
                  <button
                    type="button"
                    class="material-trend-custom-button"
                    :aria-expanded="materialTrendMetricPickerOpen"
                    @click="materialTrendMetricPickerOpen = !materialTrendMetricPickerOpen"
                  ><span class="material-symbols-outlined" aria-hidden="true">tune</span>自定义指标</button>
                  <div v-if="materialTrendMetricPickerOpen" class="material-trend-metric-popover" role="dialog" aria-label="自定义素材趋势指标">
                    <strong>选择趋势指标</strong>
                    <div v-for="group in materialTrendMetricGroups" :key="group.key" class="material-trend-metric-group">
                      <b>{{ group.label }}</b>
                      <div>
                        <label v-for="item in group.metrics" :key="item.key" :class="{ disabled: isMaterialTrendMetricDisabled(item.key) }">
                          <input type="checkbox" :checked="hasMaterialTrendMetric(item.key)" :disabled="isMaterialTrendMetricDisabled(item.key)" @change="toggleMaterialTrendMetric(item.key)" />
                          <span><i :style="{ backgroundColor: item.color }"></i>{{ item.label }}</span>
                        </label>
                      </div>
                    </div>
                    <small>至少保留 1 个指标，最多同时选择 {{ MAX_TREND_METRICS }} 个</small>
                    <button type="button" @click="materialTrendMetricPickerOpen = false">完成</button>
                  </div>
                </div>
              </div>
              <div class="material-trend-chart" @mouseleave="hoveredMaterialTrendIndex = null">
                <div class="material-trend-legend">
                  <span v-for="item in selectedMaterialTrendMetricOptions" :key="item.key"><i :style="{ backgroundColor: item.color }"></i>{{ item.label }}</span>
                </div>
                <div class="material-trend-y-axis left" aria-hidden="true">
                  <span v-for="value in materialTrendAxisValues(primaryMaterialTrendMetric)" :key="`left-${value}`">{{ formatMaterialTrendAxisValue(value) }}</span>
                </div>
                <div v-if="secondaryMaterialTrendMetric" class="material-trend-y-axis right" aria-hidden="true">
                  <span v-for="value in materialTrendAxisValues(secondaryMaterialTrendMetric)" :key="`right-${value}`">{{ formatMaterialTrendAxisValue(value) }}</span>
                </div>
                <svg viewBox="0 20 960 140" preserveAspectRatio="none" role="img" :aria-label="`${materialDateRangeLabel}素材数据趋势`">
                  <g class="material-trend-grid"><path d="M60 38H900M60 74H900M60 110H900M60 146H900" /></g>
                  <path
                    v-for="item in selectedMaterialTrendMetricOptions"
                    :key="`line-${item.key}`"
                    :d="materialTrendPath(item.key)"
                    fill="none"
                    :stroke="item.color"
                    stroke-width="2.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    vector-effect="non-scaling-stroke"
                  />
                  <line v-if="activeMaterialTrendPoint" class="material-trend-active-line" :x1="activeMaterialTrendPoint.x" :x2="activeMaterialTrendPoint.x" y1="24" y2="146" />
                  <g v-if="activeMaterialTrendPoint">
                    <circle
                      v-for="item in selectedMaterialTrendMetricOptions"
                      :key="`active-${item.key}`"
                      :cx="activeMaterialTrendPoint.x"
                      :cy="materialTrendY(item.key, activeMaterialTrendPoint[item.key])"
                      r="3.2"
                      fill="#fff"
                      :stroke="item.color"
                      stroke-width="2"
                      vector-effect="non-scaling-stroke"
                    />
                  </g>
                  <rect
                    v-for="(point, index) in materialTrendPoints"
                    :key="`material-trend-hit-${point.fullLabel}`"
                    class="material-trend-hit"
                    :x="point.x - materialTrendHitWidth / 2"
                    y="20"
                    :width="materialTrendHitWidth"
                    height="140"
                    tabindex="0"
                    role="button"
                    :aria-label="`${point.fullLabel}素材趋势数据`"
                    @mouseenter="hoveredMaterialTrendIndex = index"
                    @focus="hoveredMaterialTrendIndex = index"
                    @blur="hoveredMaterialTrendIndex = null"
                  />
                </svg>
                <div v-if="activeMaterialTrendPoint" class="material-trend-tooltip" :style="{ left: `${materialTrendTooltipLeft}%` }" role="status">
                  <strong>{{ activeMaterialTrendPoint.fullLabel }}</strong>
                  <div v-for="item in selectedMaterialTrendMetricOptions" :key="`tooltip-${item.key}`">
                    <span><i :style="{ backgroundColor: item.color }"></i>{{ item.label }}</span>
                    <b>{{ formatMaterialTrendValue(item.key, activeMaterialTrendPoint[item.key]) }}</b>
                  </div>
                </div>
                <div class="material-trend-axis" aria-hidden="true">
                  <span
                    v-for="tick in materialTrendAxisTicks"
                    :key="`axis-${tick.point.fullLabel}`"
                    :style="{ left: `${tick.point.x / 960 * 100}%` }"
                  >{{ tick.point.label }}</span>
                </div>
              </div>
            </section>

            <section class="material-notion-section material-analysis-panel overflow-hidden rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <div class="material-analysis-header flex items-center justify-between border-b border-slate-100 px-[14px] py-[10px] dark:border-slate-800">
                <div>
                  <strong class="text-[12px] font-semibold text-slate-900 dark:text-white">素材智能分析</strong>
                  <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">全部周期 · 7 个素材</p>
                </div>
                <button
                  type="button"
                  class="material-notion-action inline-flex min-h-[34px] items-center justify-center rounded-[8px] border border-primary bg-primary px-[13px] text-[11px] font-semibold text-white transition-colors duration-150 hover:bg-primary/90 dark:border-primary dark:bg-primary dark:text-white"
                  @click="success('素材智能分析已重新生成')"
                >
                  重新分析
                </button>
              </div>
              <div class="grid gap-[10px] p-[12px] md:grid-cols-2">
                <div
                  v-for="item in analysisCards"
                  :key="item.title"
                  class="material-analysis-card min-h-[112px] rounded-[8px] border border-slate-100 bg-slate-50/40 px-[13px] py-[12px] text-slate-900 dark:border-slate-800 dark:bg-slate-950/30 dark:text-white"
                >
                  <div :class="['inline-flex min-h-[22px] items-center rounded-full px-[8px] text-[10px] font-semibold', item.badgeClass]">{{ item.badge }}</div>
                  <h3 class="mt-[8px] break-words text-[12px] font-semibold leading-[1.45] text-slate-900 dark:text-white">{{ item.title }}</h3>
                  <p class="mt-[7px] text-[11px] leading-[1.65] text-slate-600 dark:text-slate-300">{{ item.body }}</p>
                </div>
              </div>
            </section>
          </div>

          <MaterialLibraryView
            :materials="materials"
            :loading="loading"
            :selected-material-id="selectedMaterialId"
            :show-toolbar="false"
            variant="notion"
            allow-delete
            v-model:search-query="materialFilterSearch"
            v-model:account-filter="materialFilterAccount"
            v-model:source-filter="materialFilterSource"
            v-model:ratio-filter="materialFilterRatio"
            v-model:sort-key="materialFilterSort"
            @select="selectRow"
            @delete="askDeleteMaterial"
          />
        </div>
      </section>

      <Teleport to="body">
        <div v-if="detailOpen" class="material-detail-backdrop fixed inset-0 z-[60] bg-slate-950/20" aria-hidden="true" @click="closeDetailDrawer"></div>
        <aside
        class="fixed bottom-0 right-0 top-0 z-[70] flex h-screen w-[min(620px,calc(100vw-52px))] max-w-[100vw] flex-col overflow-hidden border-l border-slate-200 bg-[#f6f7f9] shadow-2xl transition-all duration-200 dark:border-slate-800 dark:bg-slate-950 max-lg:w-screen"
        :class="detailOpen ? 'translate-x-0 opacity-100' : 'translate-x-[108%] opacity-0 pointer-events-none'"
      >
        <div class="flex h-[64px] shrink-0 items-center gap-[12px] border-b border-slate-200 bg-white px-[18px] pr-[22px] dark:border-slate-800 dark:bg-slate-900">
          <button class="grid h-[32px] w-[32px] place-items-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white" title="关闭详情" @click="closeDetailDrawer">
            <span class="material-symbols-outlined text-[22px]">close</span>
          </button>
          <div class="flex h-full items-center text-[14px] font-semibold">
            <span class="text-slate-900 dark:text-white">素材详情</span>
          </div>
        </div>

        <div v-if="selectedRow" class="flex-1 overflow-y-auto p-[18px] max-sm:p-[14px]">
          <div class="grid gap-[12px]">
            <aside class="rounded-md border border-slate-200 bg-white p-[18px] dark:border-slate-800 dark:bg-slate-900">
              <div class="mb-[12px] flex items-center justify-between gap-[10px]"><h3 class="text-[16px] font-bold text-slate-900 dark:text-white">原始素材</h3><span class="text-[11px] text-slate-400">{{ selectedRow.mediaKind === 'video' ? '视频' : '图片' }}</span></div>
              <div class="mt-[14px] overflow-hidden rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <div class="bg-black">
                  <video
                    v-if="selectedRow.mediaKind === 'video' && selectedPreviewUrl"
                    :src="selectedPreviewUrl"
                    class="aspect-[16/10] max-h-[480px] min-h-0 w-full object-contain"
                    controls
                    playsinline
                    preload="metadata"
                    @error="handleSelectedPreviewError"
                  />
                  <img
                    v-else-if="selectedPreviewUrl"
                    :src="selectedPreviewUrl"
                    :alt="selectedRow.name"
                    class="aspect-[16/10] max-h-[480px] min-h-0 w-full object-contain"
                    @error="handleSelectedPreviewError"
                  />
                  <div v-else class="relative grid aspect-[16/10] place-items-center overflow-hidden bg-slate-950">
                    <div class="absolute inset-0 bg-black/65"></div>
                    <div class="relative z-[1] flex flex-col items-center gap-[8px] text-center text-white/90">
                      <span class="material-symbols-outlined text-[38px] text-white/70">broken_image</span>
                      <span class="text-[13px] font-semibold">获取图片失败</span>
                      <span class="text-[11px] text-white/55">提示获取失败</span>
                    </div>
                  </div>
                </div>
                <div class="p-[12px]">
                  <strong class="block text-[13px] leading-snug text-slate-800 dark:text-slate-100">{{ selectedRow.name }}</strong>
                  <span class="mt-[5px] block break-all text-[10px] text-slate-400">ID: {{ selectedRow.id }}</span>
                </div>
                <button class="flex min-h-[38px] w-full items-center justify-center gap-[6px] border-t border-slate-100 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800" @click="openEditMaterial(selectedRow)">
                  <span class="material-symbols-outlined text-[14px]">edit</span>
                  编辑信息
                </button>
              </div>
              <dl class="mt-[18px] space-y-[13px] text-[12px]">
                <div><dt class="text-slate-400">素材类型</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.mediaKind === 'video' ? '视频' : '图片' }} · {{ selectedRow.format }}</dd></div>
                <div><dt class="text-slate-400">创建时间</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.createdAtLabel }}</dd></div>
                <div><dt class="text-slate-400">来源</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.sourceLabel }}</dd></div>
              </dl>
            </aside>

            <main class="space-y-[14px]">
              <section class="rounded-md border border-slate-200 bg-white p-[18px] dark:border-slate-800 dark:bg-slate-900">
                <h3 class="text-[15px] font-bold text-slate-900 dark:text-white">文件信息</h3>
                <dl class="mt-[14px] space-y-[12px] text-[12px]"><div class="detail-row"><dt>类型 / 格式</dt><dd>{{ selectedRow.mediaKind === 'video' ? '视频' : '图片' }} · {{ selectedRow.format }}</dd></div><div class="detail-row"><dt>尺寸 / 比例</dt><dd>{{ selectedRow.material.width && selectedRow.material.height ? `${selectedRow.material.width} × ${selectedRow.material.height}` : '-' }} · {{ selectedRow.material.ratio || '-' }}</dd></div><div class="detail-row"><dt>文件大小</dt><dd>{{ selectedRow.material.file_size ? `${(selectedRow.material.file_size / 1024 / 1024).toFixed(2)} MB` : '-' }}</dd></div><div class="detail-row"><dt>视频时长</dt><dd>{{ selectedRow.material.duration ? `${selectedRow.material.duration} 秒` : '-' }}</dd></div><div class="detail-row"><dt>处理状态</dt><dd>{{ materialFileStatus(selectedRow.material.processing_status || selectedRow.material.status) }}</dd></div></dl>
              </section>
              <section class="rounded-md border border-slate-200 bg-white p-[18px] dark:border-slate-800 dark:bg-slate-900">
                <div class="flex items-center justify-between"><h3 class="text-[15px] font-bold text-slate-900 dark:text-white">平台资产</h3><span class="text-[10px] text-slate-400">平台归属</span></div>
                <div v-if="selectedRow.material.platform_assets?.length" class="mt-[12px] space-y-[8px]"><div v-for="asset in selectedRow.material.platform_assets" :key="asset.id" class="flex items-center gap-[8px] border border-slate-200 px-[10px] py-[10px] dark:border-slate-700"><div class="min-w-0"><div class="flex flex-wrap items-center gap-[5px]"><span :class="platformClass(asset.platform)"><span class="account-dot"></span>{{ asset.platform }}</span><span class="account-chip">{{ asset.ad_account_name || asset.ad_account_id }}</span><span v-if="asset.ad_account_name" class="text-[9px] text-slate-400">{{ asset.ad_account_id }}</span></div><div class="mt-[5px] text-[10px] text-slate-400">{{ asset.asset_type === 'video' ? 'AdVideo' : 'AdImage' }} · {{ platformAssetStatus(asset.normalized_status) }}</div></div></div></div>
                <div v-else class="mt-[12px] border border-dashed border-slate-300 px-[12px] py-[12px] text-center text-[12px] text-slate-400 dark:border-slate-700">尚未发布到广告平台账户</div>
                <div class="mt-[12px] flex gap-[8px]"><button v-if="selectedRow.mediaKind === 'image'" class="flex-1 border border-slate-200 px-[8px] py-[8px] text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300" @click="openMetaPublishModal(selectedRow, 'image')">发布到平台</button><button v-if="selectedRow.mediaKind === 'video'" class="flex-1 border border-slate-200 px-[8px] py-[8px] text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300" @click="openMetaPublishModal(selectedRow, 'video')">发布到平台</button></div>
              </section>
              <section class="rounded-md border border-slate-200 bg-white p-[18px] dark:border-slate-800 dark:bg-slate-900">
                <h3 class="text-[15px] font-bold text-slate-900 dark:text-white">素材信息</h3>
                <dl class="mt-[14px] space-y-[12px] text-[12px]"><div class="detail-row"><dt>来源</dt><dd>{{ selectedRow.sourceLabel }}</dd></div><div class="detail-row"><dt>原始文件名</dt><dd class="break-all">{{ selectedRow.material.original_filename || '-' }}</dd></div><div class="detail-row"><dt>创建时间</dt><dd>{{ selectedRow.createdAtLabel }}</dd></div><div class="detail-row"><dt>标签</dt><dd>{{ selectedRow.tags.length ? selectedRow.tags.join(' · ') : '-' }}</dd></div></dl>
              </section>
            </main>
          </div>
        </div>

        <div v-else class="flex flex-1 items-center justify-center px-[24px] text-center text-[11px] text-slate-500">
          选择一条素材查看详情
        </div>
        </aside>
      </Teleport>
    </main>

    <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-[18px]" @click.self="closeUploadModal">
      <div class="max-h-[calc(100vh-36px)] w-full max-w-[860px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-900">
        <div class="sticky top-0 z-10 flex items-start justify-between gap-[16px] border-b border-slate-200 bg-white px-[18px] py-[16px] dark:border-slate-800 dark:bg-slate-900">
          <div>
            <h2 class="text-[20px] font-bold leading-tight text-slate-900 dark:text-white">上传到 ANIFORCE 素材库</h2>
            <p class="mt-[4px] text-[12px] text-slate-500 dark:text-slate-400">保存原始文件，之后可发布到一个或多个广告平台账户</p>
          </div>
          <button class="grid h-[36px] w-[36px] place-items-center rounded-md border border-slate-200 text-[22px] text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800" @click="closeUploadModal">×</button>
        </div>

        <div class="max-h-[calc(100vh-150px)] overflow-y-auto p-[18px]">
          <section>
            <div class="mb-[12px] flex items-center justify-between gap-[10px] text-[13px] font-bold text-slate-800 dark:text-slate-100">
              <span>素材文件</span>
              <span class="text-[12px] font-medium text-slate-400">图片 / 视频</span>
            </div>
            <div
              class="grid min-h-[220px] place-items-center overflow-hidden rounded-md border border-dashed border-slate-300 bg-slate-50 transition-colors dark:border-slate-700 dark:bg-slate-800/70"
              :class="isDragging ? 'border-primary bg-primary/5' : ''"
              @drop="handleDrop"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
            >
              <div v-if="!uploadFile" class="grid place-items-center gap-[10px] px-[24px] py-[28px] text-center">
                <span class="material-symbols-outlined text-[30px] text-slate-500">cloud_upload</span>
                <p class="text-[13px] text-slate-600 dark:text-slate-300">
                  将文件拖拽到此处，或
                  <label class="cursor-pointer font-bold text-primary hover:text-primary/80">
                    点击上传
                    <input type="file" multiple accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/quicktime" class="hidden" @change="handleFileSelect" />
                  </label>
                </p>
                <div class="max-w-[760px] space-y-[5px] text-[12px] leading-relaxed text-slate-400">
                  <p>图片：jpg、png、jpeg、webp 等格式，建议 16:9 / 4:5 / 1:1。</p>
                  <p>视频：mp4、mov，支持横版 16:9 或竖版 9:16，上传后自动抽取封面。</p>
                </div>
              </div>
              <div v-else class="grid w-full gap-[12px] p-[14px] md:grid-cols-[156px_minmax(0,1fr)_auto]">
                <div class="relative min-h-[112px] overflow-hidden rounded-md border border-slate-200 bg-black dark:border-slate-700">
                  <video v-if="uploadIsVideo && uploadPreviewUrl" :src="uploadPreviewUrl" class="h-full min-h-[112px] w-full object-contain" controls muted playsinline />
                  <img v-else-if="uploadPreviewUrl" :src="uploadPreviewUrl" :alt="uploadFile.name" class="h-full min-h-[112px] w-full object-cover" />
                  <div v-else class="grid h-full min-h-[112px] place-items-center text-[12px] text-slate-400">素材预览</div>
                  <span class="absolute left-[8px] top-[8px] rounded bg-slate-950/70 px-[8px] py-[3px] text-[10px] font-bold text-white">{{ uploadFiles.length > 1 ? `1 / ${uploadFiles.length}` : uploadIsVideo ? '视频' : '图片' }}</span>
                </div>
                <div class="grid gap-[7px]">
                  <div v-for="(file, index) in uploadFiles" :key="`${file.name}-${index}`" class="rounded-md border border-slate-100 bg-white p-[8px] dark:border-slate-700 dark:bg-slate-900">
                    <div class="flex items-center justify-between gap-[10px]">
                      <div class="min-w-0">
                        <b class="block truncate text-[12px] text-slate-800 dark:text-slate-100">{{ file.name }}</b>
                        <span class="mt-[2px] block text-[11px] text-slate-400">{{ (file.size / 1024 / 1024).toFixed(2) }} MB · {{ file.type || 'FILE' }}</span>
                      </div>
                      <button class="rounded p-[4px] text-slate-400 hover:bg-slate-100 hover:text-red-500 dark:hover:bg-slate-800" @click="removeFile(index)">
                        <span class="material-symbols-outlined text-[14px]">close</span>
                      </button>
                    </div>
                    <div v-if="uploadProgress.has(file.name)" class="mt-[8px] flex items-center gap-[8px]">
                      <span class="h-[8px] flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"><i class="block h-full rounded-full bg-emerald-500" :style="{ width: `${uploadProgress.get(file.name) || 0}%` }"></i></span>
                      <span class="text-[10px] font-semibold text-emerald-600">{{ uploadProgress.get(file.name) || 0 }}%</span>
                    </div>
                  </div>
                </div>
                <label class="self-center justify-self-end rounded-md border border-blue-200 bg-blue-50 px-[12px] py-[8px] text-[11px] font-semibold text-primary hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/30">
                  重新选择
                  <input type="file" multiple accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/quicktime" class="hidden" @change="handleFileSelect" />
                </label>
              </div>
            </div>
          </section>

          <section class="mt-[18px]">
            <div class="mb-[12px] flex items-center justify-between gap-[10px] text-[13px] font-bold text-slate-800 dark:text-slate-100">
              <span>素材信息</span>
              <span class="text-[12px] font-medium text-slate-400">仅填写素材相关内容</span>
            </div>
            <div class="grid gap-[12px] md:grid-cols-[1.2fr_.8fr]">
              <label class="block">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材名称</span>
                <input v-model="uploadForm.name" class="edit-input" type="text" placeholder="输入素材名称" />
              </label>
              <label class="block md:col-span-2">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材标签</span>
                <input v-model="uploadForm.tagsText" class="edit-input" type="text" placeholder="用逗号分隔，例如 UGC, summer, 9:16" />
              </label>
              <div class="grid gap-[12px] md:col-span-2 md:grid-cols-3">
                <label class="block"><span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">识别尺寸</span><input class="edit-input" type="text" :value="uploadForm.width && uploadForm.height ? `${uploadForm.width} × ${uploadForm.height}` : '-'" readonly /></label>
                <label class="block"><span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">比例 / 时长</span><input class="edit-input" type="text" :value="`${uploadForm.ratio || '-'} / ${uploadForm.duration ? uploadForm.duration + 's' : '-'}`" readonly /></label>
                <div class="rounded-md border border-slate-200 bg-slate-50 px-[10px] py-[9px] text-[11px] text-slate-500 dark:border-slate-700 dark:bg-slate-800">平台账户在发布素材时选择，本地上传不预设远端归属。</div>
              </div>
            </div>
          </section>
        </div>

        <div class="sticky bottom-0 flex items-center justify-end gap-[10px] border-t border-slate-200 bg-white px-[18px] py-[14px] dark:border-slate-800 dark:bg-slate-900">
          <button class="rounded-md px-[14px] py-[8px] text-[12px] font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" @click="closeUploadModal">取消</button>
          <button class="inline-flex items-center gap-[6px] rounded-md bg-primary px-[14px] py-[8px] text-[12px] font-semibold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="!uploadFile || uploading || probingUpload" @click="completeUpload">
            <span v-if="uploading" class="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
            <span v-else class="material-symbols-outlined text-[14px]">upload</span>
            {{ uploading ? '提交中...' : '提交素材' }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <Teleport to="body">
  <div v-if="showMetaSyncModal" class="material-meta-sync-backdrop fixed inset-0 z-[80] flex items-center justify-center bg-black/50 px-[16px]" @click.self="closeMetaSyncModal">
    <div class="w-full max-w-[560px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-800">
      <div class="flex items-center justify-between border-b border-slate-200 px-[18px] py-[14px] dark:border-slate-700">
        <div>
          <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">从 Meta 导入素材</h2>
          <p class="mt-[3px] text-[11px] text-slate-500 dark:text-slate-400">从一个广告账户导入图片和视频到 ANIFORCE 素材库</p>
        </div>
        <button class="rounded-md p-[6px] hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-700" :disabled="syncingMeta" @click="closeMetaSyncModal">
          <span class="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-300">close</span>
        </button>
      </div>

      <div class="space-y-[16px] p-[18px]">
        <label class="block">
          <span class="mb-[6px] block text-[11px] font-semibold text-slate-700 dark:text-slate-300">广告账户</span>
          <select v-model="selectedMetaAccountKey" class="edit-input" :disabled="loadingMetaAccounts || syncingMeta">
            <option value="" disabled>{{ loadingMetaAccounts ? '正在加载广告账户...' : '请选择广告账户' }}</option>
            <option v-for="account in metaAccounts" :key="`${account.connection_id}-${account.account_id}`" :value="`${account.connection_id}|${account.account_id}`">
              {{ account.account_name }} · {{ account.account_id }}
            </option>
          </select>
          <p v-if="!loadingMetaAccounts && metaAccounts.length === 0" class="mt-[7px] text-[11px] text-amber-600 dark:text-amber-400">暂无可用账户，请先在平台连接中完成 Meta 授权并同步广告账户。</p>
        </label>

        <div>
          <span class="mb-[8px] block text-[11px] font-semibold text-slate-700 dark:text-slate-300">素材类型</span>
          <div class="flex gap-[10px]">
            <label class="inline-flex min-h-[36px] flex-1 items-center gap-[8px] rounded-md border border-slate-200 px-[12px] text-[11px] font-medium text-slate-700 dark:border-slate-700 dark:text-slate-300">
              <input v-model="metaSyncAssetTypes" type="checkbox" value="image" :disabled="syncingMeta" class="h-[14px] w-[14px] accent-primary" />
              图片素材
            </label>
            <label class="inline-flex min-h-[36px] flex-1 items-center gap-[8px] rounded-md border border-slate-200 px-[12px] text-[11px] font-medium text-slate-700 dark:border-slate-700 dark:text-slate-300">
              <input v-model="metaSyncAssetTypes" type="checkbox" value="video" :disabled="syncingMeta" class="h-[14px] w-[14px] accent-primary" />
              视频素材
            </label>
          </div>
        </div>

        <div v-if="syncingMeta" class="flex min-h-[84px] items-center justify-center gap-[8px] rounded-md bg-slate-50 text-[12px] text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          <span class="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
          正在从 Meta 读取文件并保存到 ANIFORCE
        </div>

        <div v-if="metaSyncResult" class="rounded-md border border-slate-200 bg-slate-50 p-[12px] dark:border-slate-700 dark:bg-slate-900">
          <div class="text-[11px] font-semibold text-slate-800 dark:text-slate-100">导入结果 · {{ metaSyncResult.status }}</div>
          <div class="mt-[10px] grid grid-cols-5 gap-[8px] text-center">
            <div><b class="block text-[16px] text-slate-900 dark:text-white">{{ metaSyncResult.discovered_count }}</b><span class="text-[10px] text-slate-500">发现</span></div>
            <div><b class="block text-[16px] text-emerald-600">{{ metaSyncResult.created_count }}</b><span class="text-[10px] text-slate-500">新增</span></div>
            <div><b class="block text-[16px] text-blue-600">{{ metaSyncResult.updated_count }}</b><span class="text-[10px] text-slate-500">更新</span></div>
            <div><b class="block text-[16px] text-slate-600 dark:text-slate-300">{{ metaSyncResult.skipped_count }}</b><span class="text-[10px] text-slate-500">跳过</span></div>
            <div><b class="block text-[16px] text-red-600">{{ metaSyncResult.failed_count }}</b><span class="text-[10px] text-slate-500">失败</span></div>
          </div>
          <p v-if="metaSyncResult.error_summary" class="mt-[10px] break-words text-[10px] text-red-600 dark:text-red-400">{{ metaSyncResult.error_summary }}</p>
        </div>
      </div>

      <div class="flex items-center justify-end gap-[8px] border-t border-slate-200 px-[18px] py-[12px] dark:border-slate-700">
        <button class="rounded-md px-[12px] py-[7px] text-[11px] font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-700" :disabled="syncingMeta" @click="closeMetaSyncModal">关闭</button>
        <button class="inline-flex items-center gap-[6px] rounded-md bg-primary px-[12px] py-[7px] text-[11px] font-semibold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="syncingMeta || loadingMetaAccounts || !selectedMetaAccountKey || !metaSyncAssetTypes.length" @click="runMetaSync">
          <span v-if="syncingMeta" class="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
          <span v-else class="material-symbols-outlined text-[14px]">sync</span>
          {{ syncingMeta ? '导入中...' : '开始导入' }}
        </button>
      </div>
    </div>
  </div>
  </Teleport>

  <div v-if="showMetaPublishModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-[16px]" @click.self="closeMetaPublishModal">
    <div class="w-full max-w-[480px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-800">
      <div class="flex items-center justify-between border-b border-slate-200 px-[18px] py-[14px] dark:border-slate-700"><div><h2 class="text-[15px] font-bold text-slate-900 dark:text-white">发布素材</h2><p class="mt-[3px] text-[11px] text-slate-500 dark:text-slate-400">在目标账户创建媒体资产，不创建广告</p></div><button class="rounded-md p-[6px] hover:bg-slate-100 dark:hover:bg-slate-700" :disabled="publishingMeta" @click="closeMetaPublishModal"><span class="material-symbols-outlined text-[18px]">close</span></button></div>
      <div class="space-y-[14px] p-[18px]"><div class="rounded-md bg-slate-50 px-[12px] py-[10px] text-[12px] text-slate-600 dark:bg-slate-900 dark:text-slate-300"><span class="font-semibold">素材：</span>{{ publishMaterial?.name }}<span class="ml-[8px] text-slate-400">{{ publishAssetType === 'video' ? 'AdVideo' : 'AdImage' }}</span></div><div><span class="mb-[7px] block text-[11px] font-semibold text-slate-700 dark:text-slate-300">目标平台</span><div class="flex gap-[7px]"><button class="platform-option platform-option-active" type="button" @click="publishPlatform = 'Meta'"><span class="platform-dot platform-dot-meta"></span>Meta</button><button class="platform-option" type="button" disabled title="Google provider 尚未接入"><span class="platform-dot platform-dot-google"></span>Google<span class="coming-label">即将支持</span></button><button class="platform-option" type="button" disabled title="TikTok provider 尚未接入"><span class="platform-dot platform-dot-tiktok"></span>TikTok<span class="coming-label">即将支持</span></button></div></div><div><div class="mb-[6px] flex items-center justify-between"><span class="text-[11px] font-semibold text-slate-700 dark:text-slate-300">平台账户</span><span class="text-[10px] text-slate-400">已选 {{ publishAccountKeys.length }} 个</span></div><div v-if="loadingMetaAccounts" class="px-[10px] py-[18px] text-center text-[11px] text-slate-400">正在加载广告账户...</div><div v-else class="max-h-[220px] space-y-[6px] overflow-y-auto"> <label v-for="account in metaAccounts" :key="`${account.connection_id}|${account.account_id}`" class="flex cursor-pointer items-center gap-[9px] border border-slate-200 px-[10px] py-[9px] text-[11px] text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"><input type="checkbox" :checked="publishAccountKeys.includes(`${account.connection_id}|${account.account_id}`)" :disabled="publishingMeta" class="h-[14px] w-[14px] accent-primary" @change="togglePublishAccount(`${account.connection_id}|${account.account_id}`)" /><span class="min-w-0 truncate"><b>{{ account.account_name }}</b><span class="ml-[5px] text-slate-400">{{ account.account_id }}</span></span></label><div v-if="!metaAccounts.length" class="px-[10px] py-[18px] text-center text-[11px] text-slate-400">暂无可用 Meta 广告账户</div></div></div><p v-if="publishError" class="whitespace-pre-line rounded-md bg-red-50 px-[10px] py-[8px] text-[11px] text-red-600">{{ publishError }}</p></div>
      <div class="flex justify-end gap-[8px] border-t border-slate-200 px-[18px] py-[12px] dark:border-slate-700"><button class="rounded-md px-[12px] py-[7px] text-[11px] text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700" :disabled="publishingMeta" @click="closeMetaPublishModal">取消</button><button class="inline-flex items-center gap-[6px] rounded-md bg-primary px-[12px] py-[7px] text-[11px] font-semibold text-white disabled:opacity-50" :disabled="publishingMeta || loadingMetaAccounts || !publishAccountKeys.length" @click="runMetaPublish"><span v-if="publishingMeta" class="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>{{ publishingMeta ? '发布中...' : '确认发布' }}</button></div>
    </div>
  </div>

  <div v-if="editingMaterial" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-[16px]" @click.self="closeEditMaterial">
    <div class="w-full max-w-[480px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-800">
      <div class="flex items-center justify-between border-b border-slate-200 px-[18px] py-[12px] dark:border-slate-700">
        <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">编辑素材信息</h2>
        <button class="rounded-md p-[6px] hover:bg-slate-100 dark:hover:bg-slate-700" @click="closeEditMaterial">
          <span class="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-300">close</span>
        </button>
      </div>
      <div class="space-y-[12px] p-[18px]">
        <label class="block">
          <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">素材名称</span>
          <input v-model="editForm.name" class="edit-input" type="text" />
        </label>
        <label class="block">
          <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">标签</span>
          <input v-model="editForm.tagsText" class="edit-input" type="text" placeholder="用英文逗号分隔，例如 hook, ugc" />
        </label>
      </div>
      <div class="flex items-center justify-end gap-[8px] border-t border-slate-200 px-[18px] py-[12px] dark:border-slate-700">
        <button class="rounded-md px-[12px] py-[7px] text-[11px] font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700" @click="closeEditMaterial">取消</button>
        <button class="inline-flex items-center gap-[6px] rounded-md bg-primary px-[12px] py-[7px] text-[11px] font-semibold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="savingEdit" @click="saveMaterialEdit">
          <span v-if="savingEdit" class="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
          保存
        </button>
      </div>
    </div>
  </div>

  <ConfirmDialog
    :show="Boolean(deletingMaterial)"
    title="从 ANIFORCE 删除"
    :message="deletingMaterial ? `删除 ANIFORCE 中的素材「${deletingMaterial.name}」及站内文件？Meta 等平台账户中的素材不会被删除；之后可再次从平台导入。` : ''"
    confirm-text="删除站内素材"
    cancel-text="取消"
    confirm-button-class="bg-red-600 hover:bg-red-700"
    @confirm="confirmDeleteMaterial"
    @cancel="closeDeleteConfirm"
    @close="closeDeleteConfirm"
  />

  <ToastContainer />
</template>

<style scoped>
.material-notion-page {
  --mn-canvas: #ffffff;
  --mn-surface: #f6f5f4;
  --mn-surface-soft: #fafaf9;
  --mn-hairline: #e5e3df;
  --mn-hairline-soft: #ede9e4;
  --mn-ink: #37352f;
  --mn-muted: #787671;
  background: var(--mn-canvas);
  color: var(--mn-ink);
  font-family: var(--workspace-font-family);
}

.material-notion-content {
  background: var(--mn-canvas);
}

.material-notion-section {
  border-color: var(--mn-hairline);
  border-radius: 8px;
  box-shadow: none;
}

.overview-metrics-panel,
.material-analysis-panel {
  background: var(--mn-canvas);
}

.overview-metric-label,
.overview-metric-sub {
  color: var(--mn-muted);
}

.overview-metric-value {
  color: var(--mn-ink);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.material-analysis-header {
  border-color: var(--mn-hairline-soft);
  background: var(--mn-canvas);
}

.material-analysis-card {
  border-color: var(--mn-hairline-soft);
  background: var(--mn-surface-soft);
  box-shadow: none;
  transition: background-color 140ms ease, border-color 140ms ease;
}

.material-analysis-card:hover {
  border-color: var(--mn-hairline);
  background: var(--mn-surface);
}

.material-trend-panel {
  position: relative;
  overflow: visible;
  border: 1px solid var(--mn-hairline);
  background: var(--mn-canvas);
}

.material-trend-header {
  min-height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--mn-hairline-soft);
}

.material-trend-header strong {
  color: var(--mn-ink);
  font-size: 12px;
  font-weight: 600;
}

.material-trend-header p {
  margin: 2px 0 0;
  color: var(--mn-muted);
  font-size: 10px;
}

.material-trend-metric-actions {
  position: relative;
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
}

.material-trend-selected-metrics {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.material-trend-selected-metrics button,
.material-trend-custom-button {
  height: 32px;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 11px;
  border: 1px solid #c8dcf4;
  border-radius: 7px;
  background: #f3f8fe;
  color: #246ebd;
  font: inherit;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

.material-trend-selected-metrics button:hover {
  border-color: #a9c9ed;
  background: #ebf4fe;
}

.material-trend-custom-button {
  gap: 5px;
  border-color: var(--mn-hairline);
  background: #fff;
  color: var(--mn-ink);
}

.material-trend-custom-button:hover {
  background: var(--mn-surface-soft);
}

.material-trend-custom-button .material-symbols-outlined {
  font-size: 15px;
}

.material-trend-metric-popover {
  position: absolute;
  z-index: 30;
  top: 40px;
  right: 0;
  width: min(500px, calc(100vw - 48px));
  max-height: min(560px, 72vh);
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px;
  overflow-y: auto;
  border: 1px solid var(--mn-hairline);
  border-radius: 9px;
  background: #fff;
  box-shadow: rgb(15 15 15 / 15%) 0 12px 32px;
}

.material-trend-metric-popover > strong {
  color: var(--mn-ink);
  font-size: 12px;
}

.material-trend-metric-group {
  padding-top: 7px;
  border-top: 1px solid var(--mn-hairline-soft);
}

.material-trend-metric-group > b {
  display: block;
  margin-bottom: 6px;
  color: var(--mn-muted);
  font-size: 10px;
  font-weight: 600;
}

.material-trend-metric-group > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.material-trend-metric-popover label {
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 7px;
  border-radius: 6px;
  background: var(--mn-surface-soft);
  color: var(--mn-ink);
  font-size: 11px;
  cursor: pointer;
}

.material-trend-metric-popover label.disabled {
  cursor: not-allowed;
  opacity: .42;
}

.material-trend-metric-popover label span,
.material-trend-legend span,
.material-trend-tooltip span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.material-trend-metric-popover i,
.material-trend-legend i,
.material-trend-tooltip i {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;
  border-radius: 50%;
}

.material-trend-metric-popover > small {
  color: var(--mn-muted);
  font-size: 10px;
}

.material-trend-metric-popover > button {
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: #3276cc;
  color: #fff;
  font: inherit;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.material-trend-chart {
  position: relative;
  height: 246px;
  min-width: 0;
  padding: 10px 10px 8px;
  overflow: hidden;
  background: #fcfcfb;
}

.material-trend-legend {
  height: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--mn-muted);
  font-size: 11px;
}

.material-trend-chart svg {
  display: block;
  width: 100%;
  height: 200px;
}

.material-trend-grid {
  fill: none;
  stroke: #dfe4ea;
  stroke-width: 1;
  stroke-dasharray: 4 4;
  vector-effect: non-scaling-stroke;
}

.material-trend-y-axis {
  position: absolute;
  z-index: 2;
  top: 48px;
  bottom: 38px;
  width: 6.25%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #6f716f;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  pointer-events: none;
}

.material-trend-y-axis.left {
  left: 0;
  align-items: center;
  text-align: center;
}

.material-trend-y-axis.right {
  right: 0;
  align-items: center;
  text-align: center;
}

.material-trend-hit {
  fill: transparent;
  cursor: pointer;
  outline: none;
}

.material-trend-hit:focus {
  fill: rgb(79 143 232 / 4%);
}

.material-trend-active-line {
  stroke: rgb(100 116 139 / 32%);
  stroke-width: 1;
  stroke-dasharray: 3 3;
  vector-effect: non-scaling-stroke;
}

.material-trend-axis {
  position: absolute;
  right: 10px;
  bottom: 4px;
  left: 10px;
  height: 22px;
  color: #9b9994;
  font-size: 10px;
  line-height: 1;
}

.material-trend-axis span {
  position: absolute;
  top: 0;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  transform: translateX(-50%);
}

.material-trend-tooltip {
  position: absolute;
  z-index: 5;
  top: 42px;
  width: 164px;
  padding: 9px 10px;
  border: 1px solid var(--mn-hairline);
  border-radius: 8px;
  background: rgb(255 255 255 / 96%);
  box-shadow: rgb(15 15 15 / 13%) 0 10px 28px;
  color: var(--mn-ink);
  pointer-events: none;
  transform: translateX(-50%);
}

.material-trend-tooltip > strong {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
}

.material-trend-tooltip > div {
  min-height: 19px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--mn-muted);
  font-size: 10px;
}

.material-trend-tooltip b {
  color: var(--mn-ink);
  font-size: 11px;
  font-weight: 600;
}

:global(.dark) .material-trend-panel,
:global(.dark) .material-trend-chart,
:global(.dark) .material-trend-custom-button,
:global(.dark) .material-trend-metric-popover {
  border-color: rgb(51 65 85);
  background: rgb(15 23 42);
}

:global(.dark) .material-trend-header {
  border-color: rgb(51 65 85);
}

:global(.dark) .material-trend-grid {
  stroke: rgb(71 85 105 / 65%);
}

:global(.dark) .material-trend-y-axis {
  color: rgb(148 163 184);
}

:global(.dark) .material-trend-header strong,
:global(.dark) .material-trend-custom-button,
:global(.dark) .material-trend-metric-popover > strong,
:global(.dark) .material-trend-metric-popover label,
:global(.dark) .material-trend-tooltip,
:global(.dark) .material-trend-tooltip b {
  color: rgb(241 245 249);
}

:global(.dark) .material-trend-metric-popover label {
  background: rgb(30 41 59);
}

:global(.dark) .material-trend-tooltip {
  border-color: rgb(51 65 85);
  background: rgb(15 23 42 / 96%);
}

@media (max-width: 760px) {
  .material-trend-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .material-trend-metric-actions,
  .material-trend-selected-metrics {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .material-trend-metric-popover {
    right: auto;
    left: 0;
  }

  .material-trend-metric-group > div {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.material-notion-action {
  box-shadow: none;
}

.overview-filter-panel {
  display: flex;
  min-height: 54px;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  overflow-x: auto;
  border: 1px solid #e5e3df;
  border-radius: 8px;
  background: #ffffff;
  padding: 8px 12px;
}

.overview-report-meta {
  display: inline-flex;
  min-width: max-content;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  color: #787671;
  font-size: 11px;
  line-height: 1.5;
}

.overview-report-meta strong {
  color: #1a1a1a;
  font-size: 12px;
  font-weight: 600;
}

.overview-report-divider {
  width: 1px;
  height: 16px;
  background: #ede9e4;
}

.material-report-library-filters {
  min-width: 520px;
  display: flex;
  flex: 1 1 650px;
  align-items: center;
  gap: 6px;
}

.material-report-search {
  min-width: 160px;
  height: 34px;
  display: flex;
  flex: 1 1 220px;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--mn-hairline);
  border-radius: 7px;
  background: #fff;
}

.material-report-search .material-symbols-outlined {
  flex: 0 0 auto;
  color: #9b9a97;
  font-size: 16px;
}

.material-report-search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--mn-ink);
  font: inherit;
  font-size: 11px;
}

.material-report-search input::placeholder {
  color: #9b9a97;
}

.material-report-library-filters select {
  min-width: 104px;
  height: 34px;
  padding: 0 27px 0 9px;
  border: 1px solid var(--mn-hairline);
  border-radius: 7px;
  outline: 0;
  background-color: #fff;
  background-image: linear-gradient(45deg, transparent 50%, #787671 50%), linear-gradient(135deg, #787671 50%, transparent 50%);
  background-position: calc(100% - 12px) 50%, calc(100% - 8px) 50%;
  background-repeat: no-repeat;
  background-size: 4px 4px, 4px 4px;
  color: var(--mn-ink);
  font: inherit;
  font-size: 11px;
  white-space: nowrap;
  appearance: none;
  cursor: pointer;
}

.material-report-library-filters select:first-of-type {
  min-width: 126px;
}

.material-report-search:focus-within,
.material-report-library-filters select:focus-visible {
  border-color: #b7b5b0;
  box-shadow: 0 0 0 2px rgb(35 131 226 / 14%);
}

.overview-filter-controls {
  display: flex;
  min-width: max-content;
  margin-left: auto;
  align-items: center;
  gap: 6px;
  color: #37352f;
  font-size: 12px;
  line-height: 1.5;
}

.material-date-range {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 8px;
  border: 1px solid var(--mn-hairline);
  border-radius: 7px;
  background: #fff;
  white-space: nowrap;
}

.material-date-range > .material-symbols-outlined {
  color: #787671;
  font-size: 15px;
}

.material-date-prefix,
.material-date-separator {
  color: #5d5b54;
  font-size: 11px;
}

.material-date-hotspot {
  display: flex;
  min-width: 118px;
  height: 28px;
  align-items: center;
  border-radius: 5px;
  cursor: pointer;
}

.material-date-hotspot:focus-visible {
  outline: 2px solid rgb(35 131 226 / 18%);
  outline-offset: 1px;
}

.material-date-range input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #1a1a1a;
  font: inherit;
  font-size: 11px;
  font-weight: 500;
  pointer-events: none;
  cursor: pointer;
}

.material-date-range:focus-within {
  border-color: #b7b5b0;
  box-shadow: 0 0 0 2px rgb(35 131 226 / 14%);
}

.overview-filter-field,
.overview-date-range,
.overview-compare-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.overview-filter-label {
  color: #5d5b54;
}

.overview-period-select {
  min-height: 34px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 6px 24px 6px 4px;
  color: #1a1a1a;
  font: inherit;
  font-weight: 500;
  outline: none;
  cursor: pointer;
}

.overview-period-select:hover,
.overview-period-select:focus-visible {
  background: #f6f5f4;
}

.overview-filter-divider {
  width: 1px;
  height: 20px;
  background: #ede9e4;
}

.overview-date-range {
  color: #1a1a1a;
  font-weight: 500;
}

.overview-date-range .material-symbols-outlined {
  color: #787671;
  font-size: 18px;
}

.overview-compare-toggle {
  min-height: 34px;
  cursor: pointer;
  user-select: none;
}

.overview-compare-toggle input {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: #37352f;
}

.overview-comparison-field {
  margin-left: 2px;
  padding-left: 12px;
  border-left: 1px solid #ede9e4;
}

:global(.dark) .overview-filter-panel {
  border-color: rgb(51 65 85);
  background: rgb(15 23 42);
}

:global(.dark) .material-report-search,
:global(.dark) .material-report-library-filters select {
  border-color: rgb(51 65 85);
  background-color: rgb(15 23 42);
  color: rgb(241 245 249);
}

:global(.dark) .overview-filter-controls,
:global(.dark) .overview-period-select,
:global(.dark) .overview-date-range {
  color: rgb(241 245 249);
}

:global(.dark) .overview-report-meta {
  color: rgb(148 163 184);
}

:global(.dark) .overview-report-meta strong {
  color: rgb(241 245 249);
}

:global(.dark) .overview-filter-label,
:global(.dark) .overview-date-range .material-symbols-outlined {
  color: rgb(148 163 184);
}

:global(.dark) .overview-filter-divider {
  background-color: rgb(51 65 85);
}

:global(.dark) .overview-report-divider {
  background-color: rgb(51 65 85);
}

:global(.dark) .overview-comparison-field {
  border-color: rgb(51 65 85);
}

:global(.dark) .overview-period-select:hover,
:global(.dark) .overview-period-select:focus-visible {
  background: rgb(30 41 59);
}

.overview-strip {
  display: grid;
  overflow-x: auto;
  grid-template-columns: repeat(5, minmax(180px, 1fr));
  background: #ffffff;
}

.overview-metric {
  min-width: 0;
  min-height: 116px;
  padding: 18px 20px;
  border-left: 1px solid #ede9e4;
}

.overview-metric:first-child {
  border-left: 0;
}

:global(.dark) .overview-strip {
  background: rgb(15 23 42 / 40%);
}

:global(.dark) .overview-metric {
  border-left-color: rgb(51 65 85 / 45%);
}

.filter-select {
  min-width: 96px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid rgb(226 232 240);
  background: white;
  padding: 6px 28px 6px 10px;
  font-size: 11px;
  color: rgb(51 65 85);
  outline: none;
}

.filter-select:focus {
  border-color: rgb(var(--color-primary, 59 130 246));
  box-shadow: 0 0 0 1px rgb(var(--color-primary, 59 130 246));
}

.platform-option {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid rgb(226 232 240);
  border-radius: 999px;
  background: white;
  padding: 6px 9px;
  color: rgb(71 85 105);
  font-size: 10px;
  font-weight: 600;
}

.platform-option-active {
  border-color: rgb(147 197 253);
  background: rgb(239 246 255);
  color: rgb(30 64 175);
}

.platform-option:disabled { cursor: not-allowed; opacity: .45; }
.platform-dot { height: 7px; width: 7px; border-radius: 999px; }
.platform-dot-meta { background: rgb(37 99 235); }
.platform-dot-google { background: rgb(234 88 12); }
.platform-dot-tiktok { background: rgb(15 23 42); }
.coming-label { font-size: 9px; font-weight: 500; color: rgb(148 163 184); }

.filter-select, .edit-input { appearance: none; }
.filter-select { background-image: linear-gradient(45deg, transparent 50%, rgb(100 116 139) 50%), linear-gradient(135deg, rgb(100 116 139) 50%, transparent 50%); background-position: calc(100% - 12px) 50%, calc(100% - 8px) 50%; background-size: 4px 4px, 4px 4px; background-repeat: no-repeat; }

input[type='checkbox'] {
  appearance: none;
  height: 14px;
  width: 14px;
  flex: 0 0 auto;
  border: 1px solid rgb(148 163 184);
  border-radius: 4px;
  background: white;
}

input[type='checkbox']:checked {
  border-color: rgb(37 99 235);
  background: rgb(37 99 235);
  box-shadow: inset 0 0 0 3px white;
}

.detail-metric {
  border-radius: 6px;
  border: 1px solid rgb(226 232 240);
  background: white;
  padding: 9px;
}

.detail-metric span {
  display: block;
  font-size: 10px;
  color: rgb(100 116 139);
}

.detail-metric strong {
  margin-top: 5px;
  display: block;
  font-size: 16px;
  color: rgb(15 23 42);
}

.platform-chip, .account-chip, .source-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 180px;
  border: 1px solid rgb(191 219 254);
  border-radius: 999px;
  background: rgb(239 246 255);
  padding: 3px 7px;
  color: rgb(30 64 175);
  font-size: 10px;
  font-weight: 600;
}

.platform-chip-meta { border-color: rgb(191 219 254); background: rgb(239 246 255); color: rgb(30 64 175); }

.account-chip, .source-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 180px;
  border: 1px solid rgb(191 219 254);
  border-radius: 999px;
  background: rgb(239 246 255);
  padding: 3px 7px;
  color: rgb(30 64 175);
  font-size: 10px;
  font-weight: 600;
}

.source-chip {
  border-color: rgb(226 232 240);
  background: rgb(248 250 252);
  color: rgb(71 85 105);
}

/* Keep the library quiet: platform ownership gets color; file provenance stays neutral. */
tbody tr {
  transition: background-color 140ms ease, border-color 140ms ease;
}

:global(.dark) .source-chip {
  border-color: rgb(51 65 85);
  background: rgb(30 41 59);
  color: rgb(203 213 225);
}

.asset-status { color: rgb(5 150 105); font-size: 9px; font-weight: 600; }
.asset-status-missing { color: rgb(100 116 139); }

.account-dot {
  height: 6px;
  width: 6px;
  border-radius: 999px;
  background: rgb(37 99 235);
}

.detail-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 11px;
}

.detail-row dt {
  color: rgb(100 116 139);
}

.detail-row dd {
  max-width: 190px;
  text-align: right;
  color: rgb(30 41 59);
}

.edit-input {
  width: 100%;
  border-radius: 6px;
  border: 1px solid rgb(203 213 225);
  background: white;
  padding: 8px 10px;
  font-size: 12px;
  color: rgb(15 23 42);
  outline: none;
}

.edit-input:focus {
  border-color: rgb(var(--color-primary, 59 130 246));
  box-shadow: 0 0 0 1px rgb(var(--color-primary, 59 130 246));
}

.material-create-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  border: 1px solid var(--workspace-action-primary, #137fec);
  border-radius: 8px;
  background: var(--workspace-action-primary, #137fec);
  color: #ffffff;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color .16s ease, border-color .16s ease;
}

.material-create-button:hover {
  border-color: var(--workspace-action-primary-hover, #0f6fcf);
  background: var(--workspace-action-primary-hover, #0f6fcf);
}

.material-create-button .material-symbols-outlined {
  font-size: 16px;
}

:global(.dark) .filter-select {
  border-color: rgb(51 65 85);
  background: rgb(30 41 59);
  color: rgb(203 213 225);
}

:global(.dark) .detail-metric {
  border-color: rgb(51 65 85);
  background: rgb(15 23 42);
}

:global(.dark) .detail-metric strong {
  color: white;
}

:global(.dark) .detail-row dd {
  color: rgb(226 232 240);
}

:global(.dark) .edit-input {
  border-color: rgb(71 85 105);
  background: rgb(15 23 42);
  color: white;
}
</style>
