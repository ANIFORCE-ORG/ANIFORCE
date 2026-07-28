<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { getCampaigns, type Campaign } from '@/api/campaigns'
import {
  deleteMaterial,
  getMaterialImage,
  getMaterials,
  getMetaAdAccounts,
  syncMetaMaterials,
  updateMaterial,
  uploadMaterialWithMetadata,
  type Material,
  type MaterialSyncRun,
  type MetaAdAccountOption,
} from '@/api/materials'
import { navItems } from '@/config/navigation'
import { useToast } from '@/composables/useToast'
import {
  buildAnalysis,
  calculateOverview,
  formatCompactNumber,
  formatCurrency,
  formatNumber,
  formatPercent,
  toMaterialRows,
  type MaterialRow,
} from './materialsAdapter'

const router = useRouter()
const auth = useAuthStore()
const { success, error: showError } = useToast()

const activeSession = ref('sess_g001')
const loading = ref(false)
const error = ref('')
const materials = ref<Material[]>([])
const campaigns = ref<Campaign[]>([])
const materialPreviews = ref<Map<string, string>>(new Map())
const materialOriginals = ref<Map<string, string>>(new Map())
const materialMimeTypes = ref<Map<string, string>>(new Map())
const selectedMaterialId = ref<string | null>(null)
const detailOpen = ref(false)
const deletingMaterial = ref<MaterialRow | null>(null)
const deleting = ref(false)
const editingMaterial = ref<MaterialRow | null>(null)
const editForm = ref({
  name: '',
  status: 'ready',
  tagsText: '',
  ctrEstimate: '',
})
const savingEdit = ref(false)

const searchQuery = ref('')
const periodFilter = ref('7d')
const accountFilter = ref('all')
const statusFilter = ref('all')
const platformFilter = ref('all')
const sourceFilter = ref('all')
const ratioFilter = ref('all')
const metricFilter = ref('all')
const sortKey = ref('created_at')

const showUploadModal = ref(false)
const uploadFiles = ref<File[]>([])
const uploadPoster = ref<Blob | null>(null)
const uploadPosterPreview = ref('')
const probingUpload = ref(false)
const uploadForm = ref({
  name: '',
  status: 'ready',
  tagsText: '',
  ctrEstimate: '',
  source: 'oss_upload',
  sourceAccount: '',
  platforms: ['Meta'],
  placementsText: '',
  campaignIds: [] as string[],
  creator: '',
  rights: '自有素材',
  materialType: '自动识别',
  materialUsage: '信息流素材',
  materialTags: ['新上传'] as string[],
  metaNote: '',
  mediaKind: '',
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

const materialRows = computed(() => toMaterialRows(
  materials.value,
  campaigns.value,
  materialPreviews.value,
  materialMimeTypes.value,
))

const platformOptions = computed(() => {
  const names = new Set<string>()
  materialRows.value.forEach(row => row.platforms.forEach(platform => names.add(platform)))
  return Array.from(names).sort()
})

const accountOptions = computed(() => {
  const names = new Set<string>()
  campaigns.value.forEach(campaign => {
    if (campaign.account_id) names.add(campaign.account_id)
  })
  materialRows.value.forEach(row => {
    if (row.material.source_account) names.add(row.material.source_account)
  })
  return Array.from(names).sort()
})

const uploadFile = computed(() => uploadFiles.value[0] || null)
const uploadPreviewUrl = ref('')
const uploadIsVideo = computed(() => uploadFile.value?.type.startsWith('video/') || false)
const uploadPlatformOptions = ['Meta', 'Facebook', 'Instagram', 'TikTok', 'Google']
const uploadTagOptions = ['新上传', 'UGC', 'Gameplay', 'Reward', 'Static']

const filteredRows = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  let rows = materialRows.value.filter(row => {
    if (statusFilter.value !== 'all' && row.status !== statusFilter.value) return false
    if (accountFilter.value !== 'all') {
      const campaignAccounts = row.campaigns.map(campaign => campaign.account_id).filter(Boolean)
      if (row.material.source_account !== accountFilter.value && !campaignAccounts.includes(accountFilter.value)) return false
    }
    if (platformFilter.value !== 'all' && !row.platforms.includes(platformFilter.value)) return false
    if (sourceFilter.value !== 'all' && row.source !== sourceFilter.value) return false
    if (ratioFilter.value !== 'all' && row.ratio !== ratioFilter.value) return false
    if (metricFilter.value === 'high_ctr' && row.metrics.ctr < 2) return false
    if (metricFilter.value === 'fatigue' && row.fatigue < 70) return false
    if (metricFilter.value === 'low_score' && row.score >= 60) return false
    if (!query) return true
    return [
      row.name,
      row.id,
      row.sourceLabel,
      row.statusLabel,
      row.format,
      ...row.tags,
      ...row.platforms,
    ].some(value => value.toLowerCase().includes(query))
  })

  rows = [...rows].sort((a, b) => {
    if (sortKey.value === 'spend') return b.metrics.spend - a.metrics.spend
    if (sortKey.value === 'ctr') return b.metrics.ctr - a.metrics.ctr
    if (sortKey.value === 'roas') return b.metrics.roas - a.metrics.roas
    if (sortKey.value === 'fatigue') return b.fatigue - a.fatigue
    return new Date(b.material.created_at).getTime() - new Date(a.material.created_at).getTime()
  })

  return rows
})

const overview = computed(() => calculateOverview(filteredRows.value))
const analysisCards = computed(() => buildAnalysis(filteredRows.value, overview.value))
const selectedRow = computed(() => {
  if (!filteredRows.value.length) return null
  return filteredRows.value.find(row => row.id === selectedMaterialId.value) || filteredRows.value[0]
})
const selectedPreviewUrl = computed(() => {
  if (!selectedRow.value) return ''
  return materialOriginals.value.get(selectedRow.value.id) || selectedRow.value.previewUrl || ''
})

const overviewCards = computed(() => [
  { label: '周期消耗', value: formatCurrency(overview.value.spend), sub: `${accountLabel.value} · ${periodLabel(periodFilter.value)}`, icon: 'payments' },
  { label: '展示量', value: formatCompactNumber(overview.value.impressions), sub: `平均 ${formatCompactNumber(overview.value.averageImpressions)} / 素材`, icon: 'visibility' },
  { label: '点击量', value: formatCompactNumber(overview.value.clicks), sub: `平均 ${formatCompactNumber(overview.value.averageClicks)} / 素材`, icon: 'ads_click' },
  { label: '平均 ROAS', value: `${formatNumber(overview.value.roas, 2)}x`, sub: overview.value.roas >= 2.5 ? '回收健康' : overview.value.roas >= 1.8 ? '观察放量' : '需控预算', icon: 'monitoring' },
  { label: '短视频消耗', value: formatCurrency(overview.value.shortVideoSpend), sub: '按素材关联计划估算', icon: 'movie' },
])

const accountLabel = computed(() => accountFilter.value === 'all' ? '全部广告账户' : accountFilter.value)

onMounted(async () => {
  await loadPageData()
})

const loadPageData = async () => {
  try {
    loading.value = true
    error.value = ''
    if (!auth.isLoggedIn) {
      await auth.login({ email: 'test@animagus.com', password: 'test123' })
    }

    const [materialData, campaignData] = await Promise.all([
      getMaterials({ limit: 200 }),
      getCampaigns({ limit: 200 }),
    ])
    materials.value = materialData
    campaigns.value = campaignData

    await loadPreviewSources(materialData)
    if (!selectedMaterialId.value && materialData.length > 0) {
      selectedMaterialId.value = materialData[0].id
    }
  } catch (err: any) {
    error.value = err.message || '加载素材失败'
    showError(error.value)
  } finally {
    loading.value = false
  }
}

const loadPreviewSources = async (data: Material[]) => {
  await Promise.all(data.map(async material => {
    if (materialPreviews.value.has(material.id)) return
    try {
      const preview = await getMaterialImage(material.id, true)
      materialPreviews.value.set(material.id, preview.url || preview.data || '')
      materialMimeTypes.value.set(material.id, preview.mime_type || '')
    } catch {
      try {
        const original = await getMaterialImage(material.id, false)
        materialPreviews.value.set(material.id, original.url || original.data || '')
        materialMimeTypes.value.set(material.id, original.mime_type || '')
      } catch {
        if (material.thumbnail_url || material.url) {
          materialPreviews.value.set(material.id, material.thumbnail_url || material.url)
        }
      }
    }
  }))
}

const loadOriginalSource = async (material: Material) => {
  if (materialOriginals.value.has(material.id)) return
  try {
    const original = await getMaterialImage(material.id, false)
    materialOriginals.value.set(material.id, original.url || original.data || material.url || '')
  } catch {
    materialOriginals.value.set(material.id, material.url || material.thumbnail_url || '')
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

const openMetaSyncModal = async () => {
  showMetaSyncModal.value = true
  metaSyncResult.value = null
  loadingMetaAccounts.value = true
  try {
    metaAccounts.value = await getMetaAdAccounts()
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
      success(`Meta 素材同步完成：新增 ${result.created_count}，更新 ${result.updated_count}`)
    } else if (result.status === 'partially_succeeded') {
      showError(`Meta 素材部分同步成功，失败 ${result.failed_count} 个`)
    } else {
      showError(result.error_summary || 'Meta 素材同步失败')
    }
    await loadPageData()
  } catch (err: any) {
    showError(err.message || 'Meta 素材同步失败')
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
    status: 'ready',
    tagsText: '',
    ctrEstimate: '',
    source: 'oss_upload',
    sourceAccount: accountFilter.value !== 'all' ? accountFilter.value : '',
    platforms: ['Meta'],
    placementsText: 'Feed, Reels',
    campaignIds: [],
    creator: '',
    rights: '自有素材',
    materialType: '自动识别',
    materialUsage: '信息流素材',
    materialTags: ['新上传'],
    metaNote: '',
    mediaKind: '',
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
  uploadForm.value.mediaKind = file.type.startsWith('video/') ? 'video' : 'image'

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
    const extraTags = uploadForm.value.tagsText.split(',').map(tag => tag.trim()).filter(Boolean)
    const tags = Array.from(new Set([
      ...uploadForm.value.materialTags,
      ...extraTags,
      uploadForm.value.materialUsage,
      uploadForm.value.metaNote.trim() ? '有备注' : '',
    ].filter(Boolean)))
    const placements = uploadForm.value.materialUsage.includes('Reels')
      ? ['Reels', 'Stories']
      : uploadForm.value.materialUsage.includes('Feed') || uploadForm.value.materialUsage.includes('信息流')
        ? ['Feed', 'In-Feed']
        : [uploadForm.value.materialUsage]

    for (const [index, file] of uploadFiles.value.entries()) {
      uploadProgress.value.set(file.name, 0)
      const isFirst = index === 0
      const mediaKind = file.type.startsWith('video/') ? 'video' : 'image'
      const name = uploadFiles.value.length > 1 ? `${baseName}_${String(index + 1).padStart(2, '0')}` : baseName
      await uploadMaterialWithMetadata(file, {
        name,
        status: 'ready',
        tags,
        duration: isFirst && uploadForm.value.duration ? Number(uploadForm.value.duration) : undefined,
        width: isFirst && uploadForm.value.width ? Number(uploadForm.value.width) : undefined,
        height: isFirst && uploadForm.value.height ? Number(uploadForm.value.height) : undefined,
        ratio: isFirst ? uploadForm.value.ratio || undefined : undefined,
        format: file.name.split('.').pop()?.toUpperCase() || uploadForm.value.format || undefined,
        media_kind: mediaKind,
        source: 'oss_upload',
        creator: uploadForm.value.creator.trim() || undefined,
        rights: uploadForm.value.rights.trim() || undefined,
        platforms: uploadForm.value.platforms,
        review_status: '待审核',
        source_account: uploadForm.value.sourceAccount.trim() || undefined,
        placements,
        campaign_ids: uploadForm.value.campaignIds,
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
    status: row.status,
    tagsText: row.tags.join(', '),
    ctrEstimate: row.material.ctr_estimate?.toString() || '',
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
    const ctrEstimate = editForm.value.ctrEstimate.trim()
      ? Number(editForm.value.ctrEstimate)
      : undefined
    if (ctrEstimate !== undefined && !Number.isFinite(ctrEstimate)) {
      showError('CTR 预估必须是数字')
      return
    }

    await updateMaterial(editingMaterial.value.id, {
      name,
      status: editForm.value.status,
      tags: editForm.value.tagsText.split(',').map(tag => tag.trim()).filter(Boolean),
      ctr_estimate: ctrEstimate,
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
    success('素材记录已删除')
    if (selectedMaterialId.value === deletingMaterial.value.id) {
      selectedMaterialId.value = null
      detailOpen.value = false
    }
    deletingMaterial.value = null
    await loadPageData()
  } catch (err: any) {
    showError(err.message || '删除素材失败')
  } finally {
    deleting.value = false
  }
}

const statusClass = (status: string) => {
  const classes: Record<string, string> = {
    running: 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-300 dark:bg-emerald-900/20 dark:border-emerald-800',
    ready: 'text-blue-700 bg-blue-50 border-blue-200 dark:text-blue-300 dark:bg-blue-900/20 dark:border-blue-800',
    fatigue: 'text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-300 dark:bg-amber-900/20 dark:border-amber-800',
  }
  return classes[status] || 'text-slate-600 bg-slate-50 border-slate-200 dark:text-slate-300 dark:bg-slate-800 dark:border-slate-700'
}

const analysisClass = (tone: string) => {
  if (tone === 'good') return 'border-emerald-200 bg-emerald-50/70 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100'
  if (tone === 'warning') return 'border-amber-200 bg-amber-50/80 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100'
  return 'border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-100'
}

const periodLabel = (period: string) => {
  const labels: Record<string, string> = {
    '7d': '近 7 天',
    '14d': '近 14 天',
    '30d': '近 30 天',
    all: '全部周期',
  }
  return labels[period] || period
}
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="materials"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="flex-1 min-w-0 bg-white dark:bg-slate-900">
      <section class="min-w-0 flex h-full flex-col">
        <header class="h-[54px] shrink-0 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[18px]">
          <div class="min-w-0">
            <h1 class="text-[17px] font-bold text-slate-900 dark:text-white">素材管理</h1>
            <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">条式预览 · 数据评估 · OSS 预览</p>
          </div>
          <div class="flex items-center gap-[8px]">
            <button class="inline-flex items-center gap-[5px] px-[10px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" @click="openMetaSyncModal">
              <span class="material-symbols-outlined text-[15px]">sync</span>
              同步
            </button>
            <button class="inline-flex items-center gap-[5px] px-[10px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <span class="material-symbols-outlined text-[15px]">download</span>
              导出
            </button>
            <button class="inline-flex items-center gap-[5px] px-[12px] py-[6px] rounded-md bg-primary text-white text-[11px] font-semibold hover:bg-primary/90" @click="openUploadModal">
              <span class="material-symbols-outlined text-[15px]">upload</span>
              上传素材
            </button>
          </div>
        </header>

        <div class="flex-1 overflow-y-auto px-[18px] py-[16px]">
          <div v-if="error" class="mb-[12px] rounded-md border border-red-200 bg-red-50 px-[12px] py-[9px] text-[11px] text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            {{ error }}
          </div>

          <div class="overflow-x-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <div class="flex items-center justify-between border-b border-slate-100 px-[14px] py-[10px] dark:border-slate-800">
              <div>
                <strong class="text-[12px] text-slate-900 dark:text-white">素材周期看板</strong>
                <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">{{ accountLabel }} · {{ periodLabel(periodFilter) }} · {{ filteredRows.length }} 个素材</p>
              </div>
              <div class="text-[10px] text-slate-500 dark:text-slate-400">{{ overview.spendingMaterials }} 个素材产生消耗</div>
            </div>
            <div class="flex min-w-[980px] divide-x divide-slate-100 dark:divide-slate-800">
              <div v-for="card in overviewCards" :key="card.label" class="min-h-[82px] flex-1 px-[16px] py-[13px]">
                <div class="flex items-center gap-[6px] text-[12px] font-semibold text-slate-500 dark:text-slate-400">
                  <span>{{ card.label }}</span>
                  <span class="material-symbols-outlined text-[15px] text-slate-400">{{ card.icon }}</span>
                </div>
                <div class="mt-[7px] truncate text-[22px] font-bold leading-none text-slate-900 dark:text-white">{{ card.value }}</div>
                <div class="mt-[6px] truncate text-[11px] text-slate-500 dark:text-slate-400">{{ card.sub }}</div>
              </div>
            </div>
          </div>

          <div class="mt-[12px] overflow-x-auto rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <div class="flex items-center justify-between border-b border-slate-100 px-[14px] py-[10px] dark:border-slate-800">
              <div>
                <strong class="text-[12px] text-slate-900 dark:text-white">素材智能分析</strong>
                <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">基于当前账号、周期和筛选条件生成</p>
              </div>
              <button class="rounded-md border border-slate-200 px-[8px] py-[5px] text-[10px] font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800" @click="refreshMaterials">刷新分析</button>
            </div>
            <div class="flex min-w-[980px] gap-[12px] p-[12px]">
              <div v-for="item in analysisCards" :key="item.title" class="min-h-[112px] flex-1 rounded-md border px-[13px] py-[12px]" :class="analysisClass(item.tone)">
                <div class="inline-flex min-h-[22px] items-center gap-[6px] rounded-full bg-white/70 px-[8px] text-[11px] font-semibold dark:bg-slate-900/40">
                  <span class="material-symbols-outlined text-[14px]">{{ item.icon }}</span>
                  <span>{{ item.title }}</span>
                </div>
                <p class="mt-[8px] text-[12px] leading-relaxed opacity-85">{{ item.body }}</p>
              </div>
            </div>
          </div>

          <div class="mt-[14px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
            <div class="border-b border-slate-200 dark:border-slate-800 px-[12px] py-[11px]">
              <div class="flex flex-wrap items-center gap-[8px]">
                <div class="relative min-w-[220px] flex-1">
                  <span class="material-symbols-outlined absolute left-[9px] top-1/2 -translate-y-1/2 text-slate-400 text-[15px]">search</span>
                  <input v-model="searchQuery" type="text" placeholder="搜索素材名称、ID、标签、平台" class="w-full pl-[31px] pr-[10px] py-[7px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-[11px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary" />
                </div>
                <select v-model="periodFilter" class="filter-select">
                  <option value="7d">近 7 天</option>
                  <option value="14d">近 14 天</option>
                  <option value="30d">近 30 天</option>
                  <option value="all">全部周期</option>
                </select>
                <select v-model="accountFilter" class="filter-select min-w-[150px]">
                  <option value="all">全部广告账户</option>
                  <option v-for="account in accountOptions" :key="account" :value="account">{{ account }}</option>
                </select>
                <select v-model="statusFilter" class="filter-select">
                  <option value="all">全部状态</option>
                  <option value="running">投放中</option>
                  <option value="ready">待投放</option>
                  <option value="fatigue">已疲劳</option>
                </select>
                <select v-model="platformFilter" class="filter-select">
                  <option value="all">全部平台</option>
                  <option v-for="platform in platformOptions" :key="platform" :value="platform">{{ platform }}</option>
                </select>
                <select v-model="sourceFilter" class="filter-select">
                  <option value="all">全部来源</option>
                  <option value="oss">OSS 上传</option>
                  <option value="local">本地素材</option>
                  <option value="imported">外部导入</option>
                  <option value="unknown">未知来源</option>
                </select>
                <select v-model="ratioFilter" class="filter-select">
                  <option value="all">全部比例</option>
                  <option value="9:16">9:16</option>
                  <option value="1:1">1:1</option>
                  <option value="4:5">4:5</option>
                  <option value="未知">未知</option>
                </select>
                <select v-model="metricFilter" class="filter-select">
                  <option value="all">全部表现</option>
                  <option value="high_ctr">高 CTR</option>
                  <option value="fatigue">疲劳风险</option>
                  <option value="low_score">低评分</option>
                </select>
                <select v-model="sortKey" class="filter-select">
                  <option value="created_at">最近创建</option>
                  <option value="spend">消耗最高</option>
                  <option value="ctr">CTR 最高</option>
                  <option value="roas">ROAS 最高</option>
                  <option value="fatigue">疲劳最高</option>
                </select>
              </div>
            </div>

            <div class="overflow-x-auto">
              <table class="min-w-[1360px] w-full text-left">
                <thead class="bg-slate-50 dark:bg-slate-800/60 text-[10px] uppercase text-slate-500 dark:text-slate-400">
                  <tr>
                    <th class="px-[12px] py-[9px] font-semibold">素材</th>
                    <th class="px-[10px] py-[9px] font-semibold">打压搬运</th>
                    <th class="px-[10px] py-[9px] font-semibold">来源</th>
                    <th class="px-[10px] py-[9px] font-semibold">创建时间</th>
                    <th class="px-[10px] py-[9px] font-semibold">时长</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">消耗</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">展示</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">点击</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">CTR</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">ROAS</th>
                    <th class="px-[10px] py-[9px] font-semibold text-right">CPA</th>
                    <th class="px-[10px] py-[9px] font-semibold">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                  <tr v-if="loading">
                    <td colspan="12" class="px-[12px] py-[42px] text-center text-[11px] text-slate-500">
                      <span class="material-symbols-outlined text-[18px] animate-spin align-middle mr-[6px]">progress_activity</span>
                      正在加载素材数据
                    </td>
                  </tr>
                  <tr v-else-if="filteredRows.length === 0">
                    <td colspan="12" class="px-[12px] py-[42px] text-center text-[11px] text-slate-500">
                      暂无匹配素材
                    </td>
                  </tr>
                  <tr
                    v-for="row in filteredRows"
                    v-else
                    :key="row.id"
                    class="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60"
                    :class="selectedRow?.id === row.id ? 'bg-blue-50/70 dark:bg-blue-950/20' : ''"
                    @click="selectRow(row)"
                  >
                    <td class="px-[12px] py-[10px]">
                      <div class="flex items-center gap-[10px] min-w-[280px]">
                        <div class="relative h-[82px] w-[54px] shrink-0 overflow-hidden rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                          <img v-if="row.previewUrl" :src="row.previewUrl" :alt="row.name" class="h-full w-full object-cover" />
                          <span v-if="row.previewUrl && row.mediaKind === 'video'" class="absolute left-1/2 top-1/2 grid h-[28px] w-[28px] -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 border-white/90 bg-slate-950/40 text-white">
                            <span class="material-symbols-outlined text-[15px]">play_arrow</span>
                          </span>
                          <div v-if="!row.previewUrl" class="h-full w-full flex items-center justify-center">
                            <span class="material-symbols-outlined text-[18px] text-slate-400">image</span>
                          </div>
                        </div>
                        <div class="min-w-0">
                          <div class="flex items-center gap-[6px]">
                            <p class="truncate text-[12px] font-semibold text-slate-900 dark:text-white">{{ row.name }}</p>
                            <span class="rounded border px-[5px] py-[2px] text-[9px] font-medium" :class="statusClass(row.status)">{{ row.statusLabel }}</span>
                          </div>
                          <p class="mt-[3px] text-[10px] text-slate-500 dark:text-slate-400 truncate">{{ row.id }} · {{ row.format }} · {{ row.ratio }}</p>
                          <div class="mt-[5px] flex flex-wrap gap-[4px]">
                            <span v-for="tag in row.tags.slice(0, 3)" :key="tag" class="rounded bg-slate-100 dark:bg-slate-800 px-[5px] py-[2px] text-[9px] text-slate-600 dark:text-slate-300">{{ tag }}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="px-[10px] py-[10px] text-[11px] text-slate-700 dark:text-slate-300">{{ row.transportCount }} 次</td>
                    <td class="px-[10px] py-[10px] text-[11px] text-slate-700 dark:text-slate-300">{{ row.sourceLabel }}</td>
                    <td class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.createdAtLabel }}</td>
                    <td class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.durationLabel }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] font-semibold text-slate-900 dark:text-white">{{ formatCurrency(row.metrics.spend) }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] text-slate-700 dark:text-slate-300">{{ formatCompactNumber(row.metrics.impressions) }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] text-slate-700 dark:text-slate-300">{{ formatCompactNumber(row.metrics.clicks) }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] font-semibold text-emerald-600">{{ formatPercent(row.metrics.ctr) }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] text-slate-700 dark:text-slate-300">{{ formatNumber(row.metrics.roas, 2) }}</td>
                    <td class="px-[10px] py-[10px] text-right text-[11px] text-slate-700 dark:text-slate-300">{{ formatCurrency(row.metrics.cpa) }}</td>
                    <td class="px-[10px] py-[10px]">
                      <button class="rounded-md p-[5px] text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30" title="删除素材" @click.stop="askDeleteMaterial(row)">
                        <span class="material-symbols-outlined text-[15px]">delete</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <div v-if="detailOpen" class="fixed inset-0 z-40 bg-slate-950/20" @click="closeDetailDrawer"></div>
      <aside
        class="fixed right-0 top-0 bottom-0 z-50 flex h-screen w-[min(980px,64vw)] max-w-[100vw] flex-col overflow-hidden bg-slate-100 shadow-2xl transition-all duration-200 dark:bg-slate-950 max-lg:w-screen"
        :class="detailOpen ? 'translate-x-0 opacity-100' : 'translate-x-[108%] opacity-0 pointer-events-none'"
      >
        <div class="h-[54px] shrink-0 border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 flex items-center gap-[18px] pr-[18px]">
          <button class="grid h-[42px] w-[42px] place-items-center rounded-r-md bg-primary text-white hover:bg-primary/90" title="关闭详情" @click="closeDetailDrawer">
            <span class="material-symbols-outlined text-[22px]">close</span>
          </button>
          <div class="flex h-full items-center gap-[24px] text-[14px] font-semibold">
            <span class="flex h-full items-center border-b-2 border-primary text-slate-900 dark:text-white">详情</span>
            <span class="flex h-full items-center text-slate-500 dark:text-slate-400">分析</span>
          </div>
          <button v-if="selectedRow" class="ml-auto text-[12px] font-semibold text-primary hover:text-primary/80" @click="openEditMaterial(selectedRow)">编辑素材</button>
        </div>

        <div v-if="selectedRow" class="flex-1 overflow-y-auto p-[14px]">
          <div class="grid gap-[14px] xl:grid-cols-[230px_minmax(0,1fr)]">
            <aside class="rounded-md bg-white p-[18px] dark:bg-slate-900">
              <h3 class="text-[16px] font-bold text-slate-900 dark:text-white">基本信息</h3>
              <div class="mt-[12px] overflow-hidden rounded-md border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <div class="bg-black">
                  <video
                    v-if="selectedRow.mediaKind === 'video' && selectedPreviewUrl"
                    :src="selectedPreviewUrl"
                    class="max-h-[360px] w-full object-contain"
                    controls
                    playsinline
                    preload="metadata"
                  />
                  <img
                    v-else-if="selectedPreviewUrl"
                    :src="selectedPreviewUrl"
                    :alt="selectedRow.name"
                    class="max-h-[360px] w-full object-contain"
                  />
                  <div v-else class="grid h-[300px] place-items-center text-slate-500">
                    <span class="material-symbols-outlined text-[40px]">broken_image</span>
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
                <div><dt class="text-slate-400">素材评估</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">Score {{ selectedRow.score }} · 疲劳 {{ selectedRow.fatigue }}%</dd></div>
                <div><dt class="text-slate-400">素材类型</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.mediaKind === 'video' ? '视频' : '图片' }} · {{ selectedRow.format }}</dd></div>
                <div><dt class="text-slate-400">创建时间</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.createdAtLabel }}</dd></div>
                <div><dt class="text-slate-400">来源</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.sourceLabel }}</dd></div>
                <div><dt class="text-slate-400">授权状态</dt><dd class="mt-[5px] font-semibold text-slate-700 dark:text-slate-200">{{ selectedRow.material.rights || '-' }}</dd></div>
              </dl>
            </aside>

            <main class="space-y-[14px]">
              <section class="rounded-md bg-white p-[18px] dark:bg-slate-900">
                <div class="inline-flex border-b-2 border-primary pb-[7px] text-[15px] font-bold text-slate-900 dark:text-white">标准投放</div>
              </section>

              <section class="rounded-md bg-white p-[18px] dark:bg-slate-900">
                <div class="mb-[18px] flex flex-wrap items-center justify-between gap-[12px]">
                  <h3 class="text-[16px] font-bold text-slate-900 dark:text-white">数据概览</h3>
                  <div class="inline-flex min-h-[36px] items-center gap-[10px] rounded-md bg-slate-100 px-[12px] text-[12px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    <span>{{ periodLabel(periodFilter) }}</span>
                    <span class="material-symbols-outlined text-[15px]">date_range</span>
                  </div>
                </div>
                <div class="grid gap-[10px] md:grid-cols-5">
                  <div class="rounded-md bg-blue-50 p-[14px] dark:bg-blue-950/30"><span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">消耗</span><b class="mt-[8px] block text-[19px] text-slate-900 dark:text-white">{{ formatCurrency(selectedRow.metrics.spend) }}</b></div>
                  <div class="rounded-md bg-emerald-50 p-[14px] dark:bg-emerald-950/30"><span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">平均转化成本</span><b class="mt-[8px] block text-[19px] text-slate-900 dark:text-white">{{ formatCurrency(selectedRow.metrics.cpa) }}</b></div>
                  <div class="rounded-md bg-slate-100 p-[14px] dark:bg-slate-800"><span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">点击率</span><b class="mt-[8px] block text-[19px] text-slate-900 dark:text-white">{{ formatPercent(selectedRow.metrics.ctr) }}</b></div>
                  <div class="rounded-md bg-slate-100 p-[14px] dark:bg-slate-800"><span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">ROAS</span><b class="mt-[8px] block text-[19px] text-slate-900 dark:text-white">{{ formatNumber(selectedRow.metrics.roas, 2) }}x</b></div>
                  <div class="rounded-md bg-slate-100 p-[14px] dark:bg-slate-800"><span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">3秒播放率</span><b class="mt-[8px] block text-[19px] text-slate-900 dark:text-white">{{ selectedRow.mediaKind === 'video' ? '63%' : '-' }}</b></div>
                </div>
                <div class="mt-[22px] flex items-center justify-between text-[15px] font-bold text-slate-800 dark:text-slate-100">
                  <span>数据对比</span>
                  <span class="text-[12px] font-medium text-slate-400">消耗 / 转化成本</span>
                </div>
                <div class="relative mt-[18px] h-[250px] rounded-md border border-slate-100 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_49px,#e2e8f0_50px)] p-[18px] dark:border-slate-800 dark:bg-slate-900">
                  <div class="absolute left-[42px] right-[24px] bottom-[54px] h-[3px] rounded-full bg-primary"></div>
                  <div class="absolute left-[42px] right-[24px] bottom-[30px] flex justify-between text-[10px] text-slate-400">
                    <span>06-18</span><span>06-19</span><span>06-20</span><span>06-21</span><span>06-22</span><span>06-23</span><span>06-24</span><span>06-25</span>
                  </div>
                </div>
              </section>

              <section class="rounded-md bg-white p-[18px] dark:bg-slate-900">
                <div class="mb-[14px] flex items-center gap-[28px] text-[15px] font-bold">
                  <span class="border-b-2 border-primary pb-[7px] text-slate-900 dark:text-white">关联账户</span>
                  <span class="pb-[7px] text-slate-500">关联计划</span>
                </div>
                <div class="overflow-hidden rounded-md border border-slate-200 dark:border-slate-800">
                  <div class="grid min-h-[44px] grid-cols-[44px_1fr_1.2fr_90px_90px_90px] items-center bg-slate-100 text-[11px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    <span class="px-[10px]"><input type="checkbox" /></span><span>素材开关</span><span>账户/计划名称和ID</span><span>操作</span><span>素材状态</span><span>消耗</span>
                  </div>
                  <div v-if="selectedRow.campaigns.length" class="divide-y divide-slate-100 dark:divide-slate-800">
                    <div v-for="campaign in selectedRow.campaigns" :key="campaign.id" class="grid min-h-[58px] grid-cols-[44px_1fr_1.2fr_90px_90px_90px] items-center text-[11px] text-slate-600 dark:text-slate-300">
                      <span class="px-[10px]"><input type="checkbox" /></span><span>启用</span><span class="truncate pr-[10px]">{{ campaign.name }} · {{ campaign.id }}</span><span>查看</span><span>{{ campaign.status }}</span><span>{{ formatCurrency(campaign.spent || 0) }}</span>
                    </div>
                  </div>
                  <div v-else class="grid min-h-[180px] place-items-center text-[12px] text-slate-400">暂无数据</div>
                </div>
              </section>
            </main>
          </div>
        </div>

        <div v-else class="flex flex-1 items-center justify-center px-[24px] text-center text-[11px] text-slate-500">
          选择一条素材查看详情
        </div>
      </aside>
    </main>

    <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-[18px]" @click.self="closeUploadModal">
      <div class="max-h-[calc(100vh-36px)] w-full max-w-[860px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-900">
        <div class="sticky top-0 z-10 flex items-start justify-between gap-[16px] border-b border-slate-200 bg-white px-[18px] py-[16px] dark:border-slate-800 dark:bg-slate-900">
          <div>
            <h2 class="text-[20px] font-bold leading-tight text-slate-900 dark:text-white">手动提交素材</h2>
            <p class="mt-[4px] text-[12px] text-slate-500 dark:text-slate-400">素材基础信息</p>
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
                  <span class="absolute left-[8px] top-[8px bg-slate-950/70 px-[8px] py-[3px] text-[10px] font-bold text-white">{{ uploadFiles.length > 1 ? `1 / ${uploadFiles.length}` : uploadIsVideo ? '视频' : '图片' }}</span>
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
              <label class="block">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材类型</span>
                <select v-model="uploadForm.materialType" class="edit-input">
                  <option>自动识别</option><option>横版图片</option><option>竖版图片</option><option>横版视频</option><option>竖版视频</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材分组</span>
                <select v-model="uploadForm.materialUsage" class="edit-input">
                  <option>信息流素材</option><option>Reels / Stories</option><option>Feed 素材</option><option>落地页素材</option><option>素材库归档</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">授权状态</span>
                <select v-model="uploadForm.rights" class="edit-input">
                  <option>自有素材</option><option>达人授权</option><option>Spark 授权</option><option>商业可用</option><option>待确认</option>
                </select>
              </label>
              <div class="md:col-span-2">
                <span class="mb-[8px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材标签</span>
                <div class="flex flex-wrap gap-[8px]">
                  <label v-for="tag in uploadTagOptions" :key="tag" class="inline-flex min-h-[34px] items-center gap-[7px] rounded-md border border-slate-200 px-[12px] text-[11px] font-semibold text-slate-600 dark:border-slate-700 dark:text-slate-300">
                    <input v-model="uploadForm.materialTags" type="checkbox" :value="tag" class="h-[14px] w-[14px] accent-primary" />
                    {{ tag }}
                  </label>
                </div>
              </div>
              <label class="block md:col-span-2">
                <span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">素材备注</span>
                <textarea v-model="uploadForm.metaNote" class="edit-input min-h-[86px] resize-y" placeholder="补充素材亮点、授权说明或分组说明"></textarea>
              </label>
              <div class="grid gap-[12px] md:col-span-2 md:grid-cols-3">
                <label class="block"><span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">识别尺寸</span><input class="edit-input" type="text" :value="uploadForm.width && uploadForm.height ? `${uploadForm.width} × ${uploadForm.height}` : '-'" readonly /></label>
                <label class="block"><span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">比例 / 时长</span><input class="edit-input" type="text" :value="`${uploadForm.ratio || '-'} / ${uploadForm.duration ? uploadForm.duration + 's' : '-'}`" readonly /></label>
                <label class="block"><span class="mb-[6px] block text-[12px] font-semibold text-slate-600 dark:text-slate-300">平台</span><select v-model="uploadForm.platforms[0]" class="edit-input"><option v-for="platform in uploadPlatformOptions" :key="platform">{{ platform }}</option></select></label>
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

  <div v-if="showMetaSyncModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-[16px]" @click.self="closeMetaSyncModal">
    <div class="w-full max-w-[560px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-800">
      <div class="flex items-center justify-between border-b border-slate-200 px-[18px] py-[14px] dark:border-slate-700">
        <div>
          <h2 class="text-[15px] font-bold text-slate-900 dark:text-white">从 Meta 同步素材</h2>
          <p class="mt-[3px] text-[11px] text-slate-500 dark:text-slate-400">从一个广告账户导入图片和视频到 ANIFORCE 素材库</p>
        </div>
        <button class="rounded-md p-[6px] hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-700" :disabled="syncingMeta" @click="closeMetaSyncModal">
          <span class="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-300">close</span>
        </button>
      </div>

      <div class="space-y-[16px] p-[18px]">
        <label class="block">
          <span class="mb-[6px] block text-[11px] font-semibold text-slate-700 dark:text-slate-300">Meta 广告账户</span>
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
          正在读取 Meta 素材并转存 OSS
        </div>

        <div v-if="metaSyncResult" class="rounded-md border border-slate-200 bg-slate-50 p-[12px] dark:border-slate-700 dark:bg-slate-900">
          <div class="text-[11px] font-semibold text-slate-800 dark:text-slate-100">同步结果 · {{ metaSyncResult.status }}</div>
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
          {{ syncingMeta ? '同步中...' : '开始同步' }}
        </button>
      </div>
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
          <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">状态</span>
          <select v-model="editForm.status" class="edit-input">
            <option value="ready">待投放</option>
            <option value="running">投放中</option>
            <option value="fatigue">已疲劳</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">标签</span>
          <input v-model="editForm.tagsText" class="edit-input" type="text" placeholder="用英文逗号分隔，例如 hook, ugc" />
        </label>
        <label class="block">
          <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">CTR 预估 (%)</span>
          <input v-model="editForm.ctrEstimate" class="edit-input" type="text" inputmode="decimal" />
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
    title="删除素材"
    :message="deletingMaterial ? `确认删除素材「${deletingMaterial.name}」？当前后端会删除素材记录。` : ''"
    confirm-text="删除"
    cancel-text="取消"
    confirm-button-class="bg-red-600 hover:bg-red-700"
    @confirm="confirmDeleteMaterial"
    @cancel="closeDeleteConfirm"
    @close="closeDeleteConfirm"
  />

  <ToastContainer />
</template>

<style scoped>
.filter-select {
  min-width: 96px;
  border-radius: 6px;
  border: 1px solid rgb(226 232 240);
  background: white;
  padding: 7px 28px 7px 10px;
  font-size: 11px;
  color: rgb(51 65 85);
  outline: none;
}

.filter-select:focus {
  border-color: rgb(var(--color-primary, 59 130 246));
  box-shadow: 0 0 0 1px rgb(var(--color-primary, 59 130 246));
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
