<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { navItems } from '@/config/navigation'
import { useToast } from '@/composables/useToast'
import {
  getMaterialImage,
  getMaterials,
  getMetaAdAccounts,
  syncMetaMaterials,
  uploadMaterialWithMetadata,
  type Material,
  type MaterialSyncRun,
  type MetaAdAccountOption,
} from '@/api/materials'

const { success, error: showError } = useToast()

const materials = ref<Material[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const typeFilter = ref('all')
const sourceFilter = ref('all')
const sort = ref('created_at')
const previewUrls = ref(new Map<string, string>())
const selectedMaterial = ref<Material | null>(null)
const selectedPreview = ref('')
const showPreview = ref(false)
const showUpload = ref(false)
const uploadFiles = ref<File[]>([])
const uploadName = ref('')
const uploadTags = ref('')
const uploading = ref(false)
const uploadProgress = ref(new Map<string, number>())
const showImport = ref(false)
const accounts = ref<MetaAdAccountOption[]>([])
const selectedAccountKey = ref('')
const assetTypes = ref<Array<'image' | 'video'>>(['image', 'video'])
const loadingAccounts = ref(false)
const importing = ref(false)
const syncResult = ref<MaterialSyncRun | null>(null)

const filteredMaterials = computed(() => {
  const query = search.value.trim().toLowerCase()
  return [...materials.value]
    .filter(material => {
      const matchesQuery = !query || [material.name, ...(material.tags || []), material.original_url]
        .filter(Boolean)
        .some(value => String(value).toLowerCase().includes(query))
      const matchesType = typeFilter.value === 'all' || material.media_kind === typeFilter.value
      const matchesSource = sourceFilter.value === 'all' || material.source === sourceFilter.value
      return matchesQuery && matchesType && matchesSource
    })
    .sort((left, right) => {
      if (sort.value === 'name') return (left.name || '').localeCompare(right.name || '')
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
    })
})

const selectedAccount = computed(() => {
  const [connectionId, accountId] = selectedAccountKey.value.split('|')
  return accounts.value.find(account => account.connection_id === connectionId && account.account_id === accountId)
})

const isVideo = (material: Material) => material.media_kind === 'video' || material.type === 'full_video'
const previewFor = (material: Material) => previewUrls.value.get(material.id) || material.thumbnail_url || material.preview_url || material.url
const formatBytes = (size?: number) => {
  if (!size) return '-'
  return size < 1024 * 1024 ? `${Math.round(size / 1024)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`
}
const formatDate = (value?: string) => value ? new Date(value).toLocaleString() : '-'
const formatDuration = (value?: number) => value ? `${Math.round(value)} 秒` : '-'
const sourceLabel = (source?: string) => ({ oss_upload: '本地上传', meta_import: 'Meta 导入' }[source || ''] || source || '-')
const statusLabel = (status?: string) => ({ processing: '处理中', ready: '可用', failed: '失败', running: '可用', fatigue: '可用' }[status || ''] || status || '-')

const loadMaterials = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await getMaterials({ limit: 200 })
    materials.value = data
    await Promise.all(data.map(async material => {
      if (previewUrls.value.has(material.id)) return
      try {
        const preview = await getMaterialImage(material.id, true)
        const url = preview.url || preview.data
        if (url) previewUrls.value.set(material.id, url)
      } catch {
        // A missing preview must not block the library.
      }
    }))
  } catch (err) {
    error.value = err instanceof Error ? err.message : '素材加载失败'
  } finally {
    loading.value = false
  }
}

const openPreview = async (material: Material) => {
  selectedMaterial.value = material
  selectedPreview.value = previewFor(material)
  showPreview.value = true
  if (!selectedPreview.value || selectedPreview.value === material.url) {
    try {
      const preview = await getMaterialImage(material.id, false)
      selectedPreview.value = preview.url || preview.data || selectedPreview.value
    } catch (err) {
      showError(err instanceof Error ? err.message : '素材预览失败')
    }
  }
}

const handleUploadFiles = (event: Event) => {
  const input = event.target as HTMLInputElement
  uploadFiles.value = Array.from(input.files || [])
  if (uploadFiles.value.length === 1) {
    uploadName.value = uploadFiles.value[0].name.replace(/\.[^.]+$/, '')
  }
}

const upload = async () => {
  if (!uploadFiles.value.length) return
  uploading.value = true
  uploadProgress.value.clear()
  const count = uploadFiles.value.length
  try {
    for (const [index, file] of uploadFiles.value.entries()) {
      uploadProgress.value.set(file.name, 0)
      await uploadMaterialWithMetadata(file, {
        name: count === 1 ? uploadName.value.trim() || file.name : `${file.name.replace(/\.[^.]+$/, '')}_${String(index + 1).padStart(2, '0')}`,
        tags: uploadTags.value.split(',').map(tag => tag.trim()).filter(Boolean),
        source: 'oss_upload',
        media_kind: file.type.startsWith('video/') ? 'video' : 'image',
        format: file.name.split('.').pop()?.toUpperCase(),
      })
      uploadProgress.value.set(file.name, 100)
    }
    showUpload.value = false
    uploadFiles.value = []
    uploadName.value = ''
    uploadTags.value = ''
    success(`已上传 ${count} 个素材`)
    await loadMaterials()
  } catch (err) {
    showError(err instanceof Error ? err.message : '素材上传失败')
  } finally {
    uploading.value = false
  }
}

const openImport = async () => {
  showImport.value = true
  syncResult.value = null
  loadingAccounts.value = true
  try {
    accounts.value = await getMetaAdAccounts()
    if (!selectedAccountKey.value && accounts.value[0]) {
      selectedAccountKey.value = `${accounts.value[0].connection_id}|${accounts.value[0].account_id}`
    }
  } catch (err) {
    showError(err instanceof Error ? err.message : 'Meta广告账户加载失败')
  } finally {
    loadingAccounts.value = false
  }
}

const importFromMeta = async () => {
  if (!selectedAccount.value || !assetTypes.value.length) return
  importing.value = true
  try {
    syncResult.value = await syncMetaMaterials({
      connection_id: selectedAccount.value.connection_id,
      ad_account_id: selectedAccount.value.account_id,
      asset_types: assetTypes.value,
    })
    await loadMaterials()
  } catch (err) {
    showError(err instanceof Error ? err.message : 'Meta素材导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(() => void loadMaterials())
</script>

<template>
  <div class="flex h-[calc(100vh-100px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav :nav-items="navItems" active-panel="materials" />
    <main class="flex min-w-0 flex-1 flex-col bg-white dark:bg-slate-900">
      <header class="flex min-h-[62px] shrink-0 items-center justify-between gap-4 border-b border-slate-200 px-5 dark:border-slate-800">
        <div class="min-w-0"><h1 class="text-[17px] font-bold text-slate-900 dark:text-white">素材库</h1><p class="mt-1 text-[11px] text-slate-500 dark:text-slate-400">管理站内素材，以及素材在 Meta 广告账户中的资产分布</p></div>
        <div class="flex shrink-0 items-center gap-2"><button class="secondary-button" @click="openImport"><span class="material-symbols-outlined text-[16px]">cloud_download</span>导入 Meta</button><button class="primary-button" @click="showUpload = true"><span class="material-symbols-outlined text-[16px]">upload</span>上传素材</button></div>
      </header>

      <section class="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3 dark:border-slate-800">
        <label class="relative min-w-[220px] flex-1 sm:max-w-[340px]"><span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[17px] text-slate-400">search</span><input v-model="search" class="filter-input pl-9" placeholder="搜索名称或标签" /></label>
        <select v-model="typeFilter" class="filter-select"><option value="all">全部类型</option><option value="image">图片</option><option value="video">视频</option></select>
        <select v-model="sourceFilter" class="filter-select"><option value="all">全部来源</option><option value="oss_upload">本地上传</option><option value="meta_import">Meta 导入</option></select>
        <select v-model="sort" class="filter-select"><option value="created_at">最近创建</option><option value="name">名称</option></select>
        <span class="ml-auto text-[11px] text-slate-400">{{ filteredMaterials.length }} / {{ materials.length }} 个素材</span>
      </section>

      <div class="min-h-0 flex-1 overflow-auto p-5">
        <div v-if="error" class="mb-3 flex items-center justify-between border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700"><span>{{ error }}</span><button class="font-semibold" @click="loadMaterials">重试</button></div>
        <div v-if="loading" class="flex min-h-[300px] items-center justify-center border border-slate-200 dark:border-slate-800"><span class="material-symbols-outlined animate-spin text-primary">progress_activity</span></div>
        <div v-else-if="!filteredMaterials.length" class="flex min-h-[300px] flex-col items-center justify-center border border-dashed border-slate-300 text-center dark:border-slate-700"><span class="material-symbols-outlined text-[38px] text-slate-300">perm_media</span><p class="mt-3 text-[13px] font-semibold text-slate-700 dark:text-slate-200">暂无素材</p><p class="mt-1 text-[11px] text-slate-500">上传本地文件，或从 Meta 广告账户导入</p></div>
        <div v-else class="overflow-x-auto border border-slate-200 dark:border-slate-800">
          <table class="w-full min-w-[920px] text-left text-[12px]"><thead class="border-b border-slate-200 bg-slate-50 text-[11px] text-slate-500 dark:border-slate-800 dark:bg-slate-950"><tr><th class="w-[82px] px-3 py-3">预览</th><th class="px-3 py-3">素材</th><th class="px-3 py-3">文件事实</th><th class="px-3 py-3">来源</th><th class="px-3 py-3">平台资产</th><th class="px-3 py-3">状态</th><th class="px-3 py-3">创建时间</th><th class="w-[80px] px-3 py-3"></th></tr></thead><tbody><tr v-for="material in filteredMaterials" :key="material.id" class="border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/40"><td class="px-3 py-2"><button class="preview-tile" title="查看素材" @click="openPreview(material)"><img v-if="previewFor(material) && !isVideo(material)" :src="previewFor(material)" :alt="material.name" /><span v-else class="material-symbols-outlined text-[22px] text-slate-400">{{ isVideo(material) ? 'movie' : 'image' }}</span><span v-if="isVideo(material)" class="video-mark">play_arrow</span></button></td><td class="max-w-[230px] px-3 py-2"><button class="truncate text-left font-semibold text-slate-800 hover:text-primary dark:text-slate-100" @click="openPreview(material)">{{ material.name || material.id }}</button><div class="mt-1 truncate text-[10px] text-slate-400">{{ (material.tags || []).join(' · ') || '无标签' }}</div></td><td class="px-3 py-2 text-slate-500"><div>{{ material.media_kind || '-' }} · {{ material.format || '-' }}</div><div class="mt-1">{{ material.width && material.height ? `${material.width} × ${material.height}` : '-' }} · {{ formatBytes(material.file_size) }}<span v-if="isVideo(material)"> · {{ formatDuration(material.duration) }}</span></div></td><td class="px-3 py-2 text-slate-500">{{ sourceLabel(material.source) }}</td><td class="px-3 py-2 text-slate-500">未关联平台资产</td><td class="px-3 py-2"><span class="status-badge">{{ statusLabel(material.processing_status || material.status) }}</span></td><td class="px-3 py-2 text-slate-500">{{ formatDate(material.created_at) }}</td><td class="px-3 py-2 text-right"><button class="icon-button" title="查看预览" @click="openPreview(material)"><span class="material-symbols-outlined text-[17px]">open_in_new</span></button></td></tr></tbody></table>
        </div>
      </div>
    </main>

    <div v-if="showPreview && selectedMaterial" class="modal-backdrop" @click.self="showPreview = false"><div class="preview-panel"><header class="modal-header"><div class="min-w-0"><p class="eyebrow">Material</p><h2 class="truncate">{{ selectedMaterial.name }}</h2></div><button class="icon-button" @click="showPreview = false"><span class="material-symbols-outlined">close</span></button></header><div class="preview-stage"><video v-if="isVideo(selectedMaterial)" :src="selectedPreview" controls class="max-h-full max-w-full" /><img v-else :src="selectedPreview" :alt="selectedMaterial.name" class="max-h-full max-w-full object-contain" /></div><dl class="grid grid-cols-2 gap-4 border-t border-slate-200 p-5 text-[12px] dark:border-slate-800"><div><dt class="field-label">类型 / 格式</dt><dd>{{ selectedMaterial.media_kind || '-' }} · {{ selectedMaterial.format || '-' }}</dd></div><div><dt class="field-label">尺寸 / 比例</dt><dd>{{ selectedMaterial.width && selectedMaterial.height ? `${selectedMaterial.width} × ${selectedMaterial.height}` : '-' }} · {{ selectedMaterial.ratio || '-' }}</dd></div><div><dt class="field-label">文件大小</dt><dd>{{ formatBytes(selectedMaterial.file_size) }}</dd></div><div><dt class="field-label">创作者</dt><dd>{{ selectedMaterial.creator || '-' }}</dd></div><div class="col-span-2"><dt class="field-label">权利信息</dt><dd>{{ selectedMaterial.rights || '-' }}</dd></div></dl></div></div>

    <div v-if="showUpload" class="modal-backdrop" @click.self="!uploading && (showUpload = false)"><div class="modal-panel"><header class="modal-header"><div><p class="eyebrow">Local Upload</p><h2>上传素材</h2></div><button class="icon-button" :disabled="uploading" @click="showUpload = false"><span class="material-symbols-outlined">close</span></button></header><div class="space-y-4 p-5"><label class="upload-drop"><span class="material-symbols-outlined text-[30px] text-slate-400">cloud_upload</span><span class="mt-2 text-[13px] font-semibold">选择图片或视频</span><span class="mt-1 text-[11px] text-slate-500">支持批量上传到 ANIFORCE</span><input type="file" multiple accept="image/*,video/*" class="hidden" @change="handleUploadFiles" /></label><div v-if="uploadFiles.length" class="space-y-1 text-[11px] text-slate-600 dark:text-slate-300"><div v-for="file in uploadFiles" :key="file.name" class="flex justify-between"><span class="truncate">{{ file.name }}</span><span>{{ uploadProgress.get(file.name) || 0 }}%</span></div></div><input v-model="uploadName" class="filter-input" placeholder="单文件名称" /><input v-model="uploadTags" class="filter-input" placeholder="标签，用逗号分隔" /><button class="primary-button w-full justify-center" :disabled="uploading || !uploadFiles.length" @click="upload">{{ uploading ? '上传中...' : '开始上传' }}</button></div></div></div>

    <div v-if="showImport" class="modal-backdrop" @click.self="!importing && (showImport = false)"><div class="modal-panel"><header class="modal-header"><div><p class="eyebrow">Import From Meta</p><h2>导入 Meta 素材</h2></div><button class="icon-button" :disabled="importing" @click="showImport = false"><span class="material-symbols-outlined">close</span></button></header><div class="space-y-4 p-5"><label class="field-label">Meta 广告账户</label><select v-model="selectedAccountKey" class="filter-input" :disabled="loadingAccounts || importing"><option value="">请选择广告账户</option><option v-for="account in accounts" :key="`${account.connection_id}|${account.account_id}`" :value="`${account.connection_id}|${account.account_id}`">{{ account.account_name }} · {{ account.account_id }}</option></select><div><label class="field-label">导入类型</label><div class="mt-2 flex gap-5 text-[12px]"><label><input v-model="assetTypes" type="checkbox" value="image" class="mr-1 accent-primary" />图片</label><label><input v-model="assetTypes" type="checkbox" value="video" class="mr-1 accent-primary" />视频</label></div></div><div v-if="syncResult" class="border border-slate-200 bg-slate-50 p-3 text-[11px] dark:border-slate-700 dark:bg-slate-950"><div class="font-semibold">{{ syncResult.status === 'succeeded' ? '导入完成' : '导入结束' }}</div><div class="mt-2 grid grid-cols-3 gap-2 text-slate-600 dark:text-slate-300"><span>发现 {{ syncResult.discovered_count }}</span><span>新增 {{ syncResult.created_count }}</span><span>复用 {{ syncResult.reused_count }}</span><span>更新 {{ syncResult.updated_count }}</span><span>跳过 {{ syncResult.skipped_count }}</span><span>失败 {{ syncResult.failed_count }}</span></div><p v-if="syncResult.error_summary" class="mt-2 text-red-600">{{ syncResult.error_summary }}</p></div><button class="primary-button w-full justify-center" :disabled="importing || loadingAccounts || !selectedAccountKey || !assetTypes.length" @click="importFromMeta">{{ importing ? '导入中...' : '开始导入' }}</button></div></div></div>
  </div>
  <ToastContainer />
</template>

<style scoped>
.primary-button, .secondary-button, .icon-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 34px; border: 1px solid rgb(37 99 235); padding: 0 11px; font-size: 12px; font-weight: 600; }
.primary-button { background: rgb(37 99 235); color: white; }
.primary-button:hover { background: rgb(29 78 216); }
.primary-button:disabled { cursor: not-allowed; opacity: .5; }
.secondary-button, .icon-button { border-color: rgb(226 232 240); background: white; color: rgb(71 85 105); }
.secondary-button:hover, .icon-button:hover { background: rgb(248 250 252); }
.icon-button { min-width: 32px; padding: 0 7px; }
.filter-input, .filter-select { min-height: 34px; width: 100%; border: 1px solid rgb(226 232 240); background: white; padding: 0 10px; font-size: 12px; color: rgb(51 65 85); outline: none; }
.filter-select { width: auto; min-width: 112px; }
.status-badge { display: inline-flex; border: 1px solid rgb(167 243 208); background: rgb(236 253 245); padding: 2px 6px; color: rgb(4 120 87); font-size: 10px; font-weight: 600; }
.preview-tile { position: relative; display: flex; height: 48px; width: 68px; align-items: center; justify-content: center; overflow: hidden; background: rgb(241 245 249); }
.preview-tile img { height: 100%; width: 100%; object-fit: cover; }
.video-mark { position: absolute; inset: 0; display: grid; place-items: center; color: white; text-shadow: 0 1px 3px black; font-family: 'Material Symbols Outlined'; }
.modal-backdrop { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgb(15 23 42 / .45); padding: 16px; }
.modal-panel, .preview-panel { width: min(100%, 520px); overflow: hidden; border: 1px solid rgb(226 232 240); background: white; box-shadow: 0 20px 50px rgb(15 23 42 / .18); }
.preview-panel { width: min(100%, 760px); }
.modal-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgb(226 232 240); padding: 16px 20px; }
.modal-header h2 { margin-top: 3px; font-size: 16px; font-weight: 700; color: rgb(15 23 42); }
.preview-stage { display: flex; min-height: 330px; align-items: center; justify-content: center; background: rgb(15 23 42); padding: 20px; }
.upload-drop { display: flex; min-height: 150px; cursor: pointer; flex-direction: column; align-items: center; justify-content: center; border: 1px dashed rgb(148 163 184); background: rgb(248 250 252); text-align: center; }
.upload-drop:hover { border-color: rgb(59 130 246); background: rgb(239 246 255); }
.field-label, .eyebrow { color: rgb(100 116 139); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.eyebrow { color: rgb(37 99 235); }
.dark .secondary-button, .dark .icon-button, .dark .filter-input, .dark .filter-select, .dark .modal-panel, .dark .preview-panel { border-color: rgb(51 65 85); background: rgb(15 23 42); color: rgb(226 232 240); }
.dark .modal-header { border-color: rgb(51 65 85); }
</style>
