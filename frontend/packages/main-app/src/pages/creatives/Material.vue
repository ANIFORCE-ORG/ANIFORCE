<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ConfirmDialog from '@/components/toasts/ConfirmDialog.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { getCampaigns, type Campaign } from '@/api/campaigns'
import { deleteMaterial, getMaterialImage, getMaterials, updateMaterial, uploadMaterialWithMetadata, type Material } from '@/api/materials'
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
  rights: '商业投放授权',
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
const uploadPlatformOptions = ['Meta', 'Facebook', 'Instagram', 'TikTok', 'Google']

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
  uploadPoster.value = null
  uploadPosterPreview.value = ''
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
    rights: '商业投放授权',
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
    uploadFiles.value = [validFiles[0]]
    void prepareUploadMetadata(validFiles[0])
  }
}

const removeFile = (index: number) => {
  uploadFiles.value.splice(index, 1)
  if (index === 0) resetUploadForm()
}

const prepareUploadMetadata = async (file: File) => {
  probingUpload.value = true
  if (uploadPosterPreview.value) URL.revokeObjectURL(uploadPosterPreview.value)
  uploadPoster.value = null
  uploadPosterPreview.value = ''

  const baseName = file.name.replace(/\.[^.]+$/, '')
  const ext = file.name.split('.').pop()?.toUpperCase() || ''
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
  if (!uploadFile.value) {
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
    const file = uploadFile.value
    uploadProgress.value.set(file.name, 0)
    const ctrEstimate = uploadForm.value.ctrEstimate.trim() ? Number(uploadForm.value.ctrEstimate) : undefined
    if (ctrEstimate !== undefined && !Number.isFinite(ctrEstimate)) {
      showError('CTR 预估必须是数字')
      return
    }
    await uploadMaterialWithMetadata(file, {
      name: uploadForm.value.name.trim(),
      status: uploadForm.value.status,
      tags: uploadForm.value.tagsText.split(',').map(tag => tag.trim()).filter(Boolean),
      ctr_estimate: ctrEstimate,
      duration: uploadForm.value.duration ? Number(uploadForm.value.duration) : undefined,
      width: uploadForm.value.width ? Number(uploadForm.value.width) : undefined,
      height: uploadForm.value.height ? Number(uploadForm.value.height) : undefined,
      ratio: uploadForm.value.ratio || undefined,
      format: uploadForm.value.format || undefined,
      media_kind: uploadForm.value.mediaKind === 'video' ? 'video' : 'image',
      source: uploadForm.value.source,
      creator: uploadForm.value.creator.trim() || undefined,
      rights: uploadForm.value.rights.trim() || undefined,
      platforms: uploadForm.value.platforms,
      review_status: '待审核',
      source_account: uploadForm.value.sourceAccount.trim() || undefined,
      placements: uploadForm.value.placementsText.split(',').map(item => item.trim()).filter(Boolean),
      campaign_ids: uploadForm.value.campaignIds,
    }, uploadPoster.value || undefined)
    uploadProgress.value.set(file.name, 100)
    success('素材已上传，详情字段和视频封面已保存')
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
            <button class="inline-flex items-center gap-[5px] px-[10px] py-[6px] rounded-md border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" @click="refreshMaterials">
              <span class="material-symbols-outlined text-[15px]" :class="{ 'animate-spin': loading }">sync</span>
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
        class="fixed right-[18px] top-[18px] bottom-[18px] z-50 flex w-[460px] max-w-[calc(100vw-32px)] flex-col overflow-hidden rounded-md border border-slate-200 bg-slate-50 shadow-2xl transition-all duration-200 dark:border-slate-700 dark:bg-slate-950"
        :class="detailOpen ? 'translate-x-0 opacity-100' : 'translate-x-[calc(100%+28px)] opacity-0 pointer-events-none'"
      >
        <div class="h-[54px] shrink-0 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-[14px]">
          <h2 class="text-[13px] font-bold text-slate-900 dark:text-white">素材详情</h2>
          <div v-if="selectedRow" class="flex items-center gap-[6px]">
            <button class="rounded-md p-[5px] text-slate-500 hover:bg-slate-100 hover:text-primary dark:hover:bg-slate-800" title="编辑素材" @click="openEditMaterial(selectedRow)">
              <span class="material-symbols-outlined text-[15px]">edit</span>
            </button>
            <span class="rounded border px-[6px] py-[3px] text-[10px] font-medium" :class="statusClass(selectedRow.status)">{{ selectedRow.statusLabel }}</span>
            <button class="rounded-md p-[5px] text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title="关闭详情" @click="closeDetailDrawer">
              <span class="material-symbols-outlined text-[15px]">close</span>
            </button>
          </div>
        </div>

        <div v-if="selectedRow" class="flex-1 overflow-y-auto p-[14px]">
          <div class="overflow-hidden rounded-md border border-slate-200 dark:border-slate-700 bg-black">
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
            <div v-else class="h-[300px] flex items-center justify-center text-slate-500">
              <span class="material-symbols-outlined text-[40px]">broken_image</span>
            </div>
          </div>

          <div class="mt-[12px]">
            <h3 class="text-[14px] font-bold text-slate-900 dark:text-white leading-snug">{{ selectedRow.name }}</h3>
            <p class="mt-[4px] break-all text-[10px] text-slate-500 dark:text-slate-400">{{ selectedRow.id }}</p>
          </div>

          <div class="mt-[12px] grid grid-cols-3 gap-[8px]">
            <div class="detail-metric"><span>评分</span><strong>{{ selectedRow.score }}</strong></div>
            <div class="detail-metric"><span>疲劳</span><strong>{{ selectedRow.fatigue }}</strong></div>
            <div class="detail-metric"><span>ROAS</span><strong>{{ formatNumber(selectedRow.metrics.roas, 2) }}</strong></div>
          </div>

          <div class="mt-[12px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
            <dl class="divide-y divide-slate-100 dark:divide-slate-800 text-[11px]">
              <div class="detail-row"><dt>素材类型</dt><dd>{{ selectedRow.mediaKind === 'video' ? '视频' : '图片' }} · {{ selectedRow.format }}</dd></div>
              <div class="detail-row"><dt>来源</dt><dd>{{ selectedRow.sourceLabel }}</dd></div>
              <div class="detail-row"><dt>文件大小</dt><dd>{{ selectedRow.fileSizeLabel }}</dd></div>
              <div class="detail-row"><dt>比例/时长</dt><dd>{{ selectedRow.ratio }} / {{ selectedRow.durationLabel }}</dd></div>
              <div class="detail-row"><dt>审核状态</dt><dd>{{ selectedRow.reviewStatus }}</dd></div>
              <div class="detail-row"><dt>关联计划</dt><dd>{{ selectedRow.associatedCampaignCount }} 个</dd></div>
              <div class="detail-row"><dt>关联账号</dt><dd>{{ selectedRow.associatedAccountCount }} 个</dd></div>
              <div class="detail-row"><dt>平台</dt><dd>{{ selectedRow.platforms.length ? selectedRow.platforms.join(', ') : '-' }}</dd></div>
            </dl>
          </div>

          <div class="mt-[12px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-[12px]">
            <h4 class="text-[12px] font-bold text-slate-900 dark:text-white">绑定计划</h4>
            <div v-if="selectedRow.campaigns.length" class="mt-[8px] space-y-[7px]">
              <div v-for="campaign in selectedRow.campaigns" :key="campaign.id" class="rounded-md bg-slate-50 dark:bg-slate-800 px-[9px] py-[7px]">
                <p class="truncate text-[11px] font-semibold text-slate-900 dark:text-white">{{ campaign.name }}</p>
                <p class="mt-[3px] text-[10px] text-slate-500 dark:text-slate-400">{{ campaign.platform }} · {{ campaign.status }} · {{ formatCurrency(campaign.spent || 0) }}</p>
              </div>
            </div>
            <p v-else class="mt-[8px] text-[11px] text-slate-500 dark:text-slate-400">暂无绑定计划</p>
          </div>

          <div class="mt-[12px] flex items-center gap-[8px]">
            <button class="flex-1 rounded-md border border-slate-200 bg-white px-[10px] py-[8px] text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800" @click="openEditMaterial(selectedRow)">
              编辑信息
            </button>
            <button class="flex-1 rounded-md border border-red-200 bg-white px-[10px] py-[8px] text-[11px] font-semibold text-red-600 hover:bg-red-50 dark:border-red-900 dark:bg-slate-900 dark:hover:bg-red-950/30" @click="askDeleteMaterial(selectedRow)">
              删除记录
            </button>
          </div>
        </div>

        <div v-else class="flex flex-1 items-center justify-center px-[24px] text-center text-[11px] text-slate-500">
          选择一条素材查看详情
        </div>
      </aside>
    </main>

    <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-[16px]" @click.self="closeUploadModal">
      <div class="w-full max-w-[620px] overflow-hidden rounded-md bg-white shadow-2xl dark:bg-slate-800">
        <div class="flex items-center justify-between border-b border-slate-200 px-[18px] py-[12px] dark:border-slate-700">
          <h2 class="text-[16px] font-bold text-slate-900 dark:text-white">上传素材</h2>
          <button class="rounded-md p-[6px] hover:bg-slate-100 dark:hover:bg-slate-700" @click="closeUploadModal">
            <span class="material-symbols-outlined text-[18px] text-slate-600 dark:text-slate-300">close</span>
          </button>
        </div>
        <div class="max-h-[calc(100vh-180px)] overflow-y-auto p-[18px]">
          <div class="grid gap-[14px] lg:grid-cols-[220px_1fr]">
            <div>
              <div
                class="rounded-md border-2 border-dashed p-[22px] text-center transition-colors"
                :class="isDragging ? 'border-primary bg-primary/5' : 'border-slate-300 hover:border-primary dark:border-slate-600 dark:hover:border-primary'"
                @drop="handleDrop"
                @dragover="handleDragOver"
                @dragleave="handleDragLeave"
              >
                <div class="flex flex-col items-center gap-[10px]">
                  <div class="flex h-[42px] w-[42px] items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700">
                    <span class="material-symbols-outlined text-[24px] text-slate-400">cloud_upload</span>
                  </div>
                  <div>
                    <p class="text-[11px] text-slate-700 dark:text-slate-300">
                      拖拽或
                      <label class="cursor-pointer font-semibold text-primary hover:text-primary/80">
                        选择文件
                        <input type="file" accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/quicktime" class="hidden" @change="handleFileSelect" />
                      </label>
                    </p>
                    <p class="mt-[5px] text-[10px] text-slate-500 dark:text-slate-400">单次上传 1 个素材，支持 MP4/MOV 自动抽封面</p>
                  </div>
                </div>
              </div>

              <div v-if="uploadFile" class="mt-[12px] rounded-md bg-slate-50 p-[10px] dark:bg-slate-700">
                <div class="flex items-center justify-between gap-[8px]">
                  <div class="flex min-w-0 items-center gap-[9px]">
                    <span class="material-symbols-outlined text-[16px] text-slate-400">{{ uploadFile.type.startsWith('video/') ? 'movie' : 'image' }}</span>
                    <div class="min-w-0">
                      <p class="truncate text-[11px] font-medium text-slate-900 dark:text-white">{{ uploadFile.name }}</p>
                      <p class="mt-[2px] text-[10px] text-slate-500 dark:text-slate-400">{{ uploadForm.fileSize || (uploadFile.size / 1024 / 1024).toFixed(2) + ' MB' }}</p>
                    </div>
                  </div>
                  <button class="rounded p-[4px] hover:bg-slate-200 dark:hover:bg-slate-600" @click="removeFile(0)">
                    <span class="material-symbols-outlined text-[14px] text-slate-500">close</span>
                  </button>
                </div>
                <div v-if="uploadPosterPreview" class="mt-[10px] overflow-hidden rounded-md border border-slate-200 bg-black dark:border-slate-600">
                  <img :src="uploadPosterPreview" alt="视频封面" class="h-[160px] w-full object-contain" />
                </div>
                <div v-else class="mt-[10px] flex h-[120px] items-center justify-center rounded-md border border-slate-200 bg-white text-[10px] text-slate-500 dark:border-slate-600 dark:bg-slate-800">
                  {{ probingUpload ? '正在读取素材信息...' : '图片素材使用原图缩略图，视频会自动生成封面' }}
                </div>
              </div>
            </div>

            <div class="grid gap-[10px] sm:grid-cols-2">
              <label class="block sm:col-span-2">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">素材名称</span>
                <input v-model="uploadForm.name" class="edit-input" type="text" placeholder="选择文件后自动预填" />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">状态</span>
                <select v-model="uploadForm.status" class="edit-input">
                  <option value="ready">待投放</option>
                  <option value="running">投放中</option>
                  <option value="fatigue">已疲劳</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">来源</span>
                <select v-model="uploadForm.source" class="edit-input">
                  <option value="oss_upload">OSS 上传</option>
                  <option value="local">本地上传</option>
                  <option value="meta_import">Meta 导入</option>
                  <option value="tiktok_import">TikTok 导入</option>
                  <option value="ai_generated">AI 生成</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">广告账户</span>
                <input v-model="uploadForm.sourceAccount" class="edit-input" type="text" placeholder="例如 FunGame_Meta_JP_Android" />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">CTR 预估 (%)</span>
                <input v-model="uploadForm.ctrEstimate" class="edit-input" type="text" inputmode="decimal" />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">媒体类型</span>
                <input v-model="uploadForm.mediaKind" class="edit-input" type="text" readonly />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">格式</span>
                <input v-model="uploadForm.format" class="edit-input" type="text" />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">尺寸</span>
                <input class="edit-input" type="text" :value="uploadForm.width && uploadForm.height ? `${uploadForm.width} × ${uploadForm.height}` : ''" readonly />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">比例 / 时长</span>
                <input class="edit-input" type="text" :value="`${uploadForm.ratio || '-'} / ${uploadForm.duration ? uploadForm.duration + 's' : '-'}`" readonly />
              </label>
              <label class="block sm:col-span-2">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">标签</span>
                <input v-model="uploadForm.tagsText" class="edit-input" type="text" placeholder="用英文逗号分隔，例如 hook, ugc, jp" />
              </label>
              <div class="sm:col-span-2">
                <span class="mb-[6px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">平台</span>
                <div class="flex flex-wrap gap-[6px]">
                  <label v-for="platform in uploadPlatformOptions" :key="platform" class="inline-flex items-center gap-[5px] rounded-md border border-slate-200 px-[8px] py-[5px] text-[10px] text-slate-700 dark:border-slate-700 dark:text-slate-300">
                    <input v-model="uploadForm.platforms" type="checkbox" :value="platform" class="h-[12px] w-[12px]" />
                    {{ platform }}
                  </label>
                </div>
              </div>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">版位</span>
                <input v-model="uploadForm.placementsText" class="edit-input" type="text" placeholder="Feed, Reels" />
              </label>
              <label class="block">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">版权</span>
                <input v-model="uploadForm.rights" class="edit-input" type="text" />
              </label>
              <label class="block sm:col-span-2">
                <span class="mb-[5px] block text-[11px] font-medium text-slate-700 dark:text-slate-300">关联计划</span>
                <select v-model="uploadForm.campaignIds" multiple class="edit-input min-h-[72px]">
                  <option v-for="campaign in campaigns" :key="campaign.id" :value="campaign.id">{{ campaign.name }} · {{ campaign.account_id || campaign.platform }}</option>
                </select>
              </label>
            </div>
          </div>
        </div>
        <div class="flex items-center justify-end gap-[8px] border-t border-slate-200 px-[18px] py-[12px] dark:border-slate-700">
          <button class="rounded-md px-[12px] py-[7px] text-[11px] font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700" @click="closeUploadModal">取消</button>
          <button class="inline-flex items-center gap-[6px] rounded-md bg-primary px-[12px] py-[7px] text-[11px] font-semibold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="!uploadFile || uploading || probingUpload" @click="completeUpload">
            <span v-if="uploading" class="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>
            {{ uploading ? '上传中...' : '完成上传' }}
          </button>
        </div>
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
