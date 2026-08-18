<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getMaterialImage, type Material } from '@/api/materials'
import { toMaterialRows, type MaterialRow } from '@/pages/creatives/materialsAdapter'

const props = withDefaults(defineProps<{
  materials: Material[]
  loading?: boolean
  embedded?: boolean
  allowDelete?: boolean
  selectedMaterialId?: string | null
  variant?: 'default' | 'notion'
}>(), {
  loading: false,
  embedded: false,
  allowDelete: false,
  selectedMaterialId: null,
  variant: 'default',
})

const emit = defineEmits<{
  select: [row: MaterialRow]
  mention: [material: Material]
  delete: [row: MaterialRow]
}>()

const previewSources = ref<Map<string, string>>(new Map())
const mimeTypes = ref<Map<string, string>>(new Map())
const searchQuery = ref('')
const accountFilter = ref('all')
const sourceFilter = ref('all')
const ratioFilter = ref('all')
const sortKey = ref('created_at')
const localSelectedId = ref<string | null>(props.selectedMaterialId)

watch(() => props.selectedMaterialId, value => {
  localSelectedId.value = value
})

watch(() => props.materials, materials => {
  void loadPreviewSources(materials)
}, { immediate: true })

const rows = computed(() => toMaterialRows(props.materials, previewSources.value, mimeTypes.value))
const accountOptions = computed(() => Array.from(new Set(
  props.materials.flatMap(material => material.platform_assets?.map(asset => asset.ad_account_id) || [])
)).sort())

const filteredRows = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const filtered = rows.value.filter(row => {
    if (accountFilter.value !== 'all' && !row.material.platform_assets?.some(asset => asset.ad_account_id === accountFilter.value)) return false
    if (sourceFilter.value !== 'all' && row.source !== sourceFilter.value) return false
    if (ratioFilter.value !== 'all' && row.ratio !== ratioFilter.value) return false
    if (!query) return true
    const accountTerms = row.material.platform_assets?.flatMap(asset => [
      asset.ad_account_name || '',
      asset.ad_account_id,
      asset.external_asset_id,
    ]) || []
    return [row.name, row.material.original_filename || '', row.id, row.sourceLabel, row.format, ...row.tags, ...row.platforms, ...accountTerms]
      .some(value => value.toLowerCase().includes(query))
  })
  return [...filtered].sort((a, b) => sortKey.value === 'name'
    ? a.name.localeCompare(b.name)
    : new Date(b.material.created_at).getTime() - new Date(a.material.created_at).getTime())
})

async function loadPreviewSources(materials: Material[]): Promise<void> {
  await Promise.all(materials.map(async material => {
    if (previewSources.value.has(material.id)) return
    try {
      const preview = await getMaterialImage(material.id, true)
      previewSources.value.set(material.id, preview.url || preview.data || '')
      mimeTypes.value.set(material.id, preview.mime_type || '')
    } catch {
      try {
        const original = await getMaterialImage(material.id, false)
        previewSources.value.set(material.id, original.url || original.data || '')
        mimeTypes.value.set(material.id, original.mime_type || '')
      } catch {
        previewSources.value.set(material.id, material.poster_url || material.preview_url || material.thumbnail_url || material.url || '')
      }
    }
  }))
  previewSources.value = new Map(previewSources.value)
  mimeTypes.value = new Map(mimeTypes.value)
}

function selectRow(row: MaterialRow): void {
  localSelectedId.value = row.id
  emit('select', row)
}

const platformAssetStatus = (status?: string) => ({
  processing: '发布处理中',
  ready: '已发布',
  failed: '发布失败',
  unknown: '待验证',
}[status || ''] || '待验证')

const platformClass = (platform?: string) => platform === 'Meta'
  ? 'platform-chip platform-chip-meta'
  : 'platform-chip'
</script>

<template>
  <div
    class="material-library rounded-md border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
    :class="{ 'material-library--notion': variant === 'notion' }"
  >
    <div class="material-library-toolbar border-b border-slate-200 px-[16px] py-[14px] dark:border-slate-800">
      <div class="flex flex-wrap items-center gap-[8px]">
        <div class="relative min-w-[220px] flex-1">
          <span class="material-symbols-outlined absolute left-[9px] top-1/2 -translate-y-1/2 text-[15px] text-slate-400">search</span>
          <input v-model="searchQuery" type="text" placeholder="搜索名称、文件名、标签或平台账户" class="material-library-search w-full rounded-md border border-slate-200 bg-white py-[7px] pl-[31px] pr-[10px] text-[11px] text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-700 dark:bg-slate-800 dark:text-white" />
        </div>
        <template v-if="!embedded">
          <select v-model="accountFilter" class="filter-select min-w-[150px]">
            <option value="all">全部广告账户</option>
            <option v-for="account in accountOptions" :key="account" :value="account">{{ account }}</option>
          </select>
          <select v-model="sourceFilter" class="filter-select">
            <option value="all">全部来源</option>
            <option value="oss">手动上传</option>
            <option value="local">历史素材</option>
            <option value="meta_import">Meta 导入</option>
            <option value="google_import">Google 导入</option>
            <option value="tiktok_import">TikTok 导入</option>
            <option value="imported">其他外部导入</option>
            <option value="unknown">未知来源</option>
          </select>
          <select v-model="ratioFilter" class="filter-select">
            <option value="all">全部比例</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
            <option value="4:5">4:5</option>
            <option value="未知">未知</option>
          </select>
          <select v-model="sortKey" class="filter-select">
            <option value="created_at">最近创建</option>
            <option value="name">名称</option>
          </select>
        </template>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left" :class="embedded ? 'min-w-[420px]' : 'min-w-[980px]'">
        <thead class="material-library-table-head bg-slate-50 text-[10px] uppercase text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
          <tr>
            <th class="px-[12px] py-[9px] font-semibold">素材</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">平台 / 账户</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">来源</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">类型 / 格式</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">尺寸 / 比例</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">大小 / 时长</th>
            <th v-if="!embedded" class="px-[10px] py-[9px] font-semibold">创建时间</th>
            <th class="px-[10px] py-[9px] font-semibold">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
          <tr v-if="loading">
            <td :colspan="embedded ? 2 : 8" class="px-[12px] py-[42px] text-center text-[11px] text-slate-500">
              <span class="material-symbols-outlined mr-[6px] animate-spin align-middle text-[18px]">progress_activity</span>
              正在加载素材数据
            </td>
          </tr>
          <tr v-else-if="filteredRows.length === 0">
            <td :colspan="embedded ? 2 : 8" class="px-[12px] py-[42px] text-center text-[11px] text-slate-500">暂无匹配素材</td>
          </tr>
          <tr
            v-for="row in filteredRows"
            v-else
            :key="row.id"
            class="material-library-row group relative cursor-pointer border-l-2 border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/60"
            :class="localSelectedId === row.id ? 'border-l-primary bg-primary/[.04] dark:bg-primary/[.08]' : ''"
            @click="selectRow(row)"
          >
            <td class="px-[12px] py-[10px]">
              <div class="flex min-w-0 items-center gap-[10px]" :class="embedded ? '' : 'min-w-[280px]'">
                <div
                  class="material-library-thumb relative shrink-0 overflow-hidden border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800"
                  :class="embedded
                    ? 'h-[62px] w-[62px] rounded-lg'
                    : 'h-[82px] w-[54px] rounded-md'"
                >
                  <img v-if="row.previewUrl" :src="row.previewUrl" :alt="row.name" class="h-full w-full object-cover" loading="lazy" />
                  <span v-if="row.previewUrl && row.mediaKind === 'video'" class="absolute left-1/2 top-1/2 grid h-[28px] w-[28px] -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 border-white/90 bg-slate-950/40 text-white">
                    <span class="material-symbols-outlined text-[15px]">play_arrow</span>
                  </span>
                  <div v-if="!row.previewUrl" class="flex h-full w-full items-center justify-center">
                    <span class="material-symbols-outlined text-[18px] text-slate-400">image</span>
                  </div>
                </div>
                <div class="min-w-0">
                  <p class="material-library-name truncate text-[12px] font-semibold text-slate-900 dark:text-white">{{ row.name }}</p>
                  <p class="material-library-meta mt-[3px] truncate text-[10px] text-slate-500 dark:text-slate-400">{{ row.id }} · {{ row.format }} · {{ row.ratio }}</p>
                  <div class="mt-[5px] flex flex-wrap gap-[4px]">
                    <span v-for="tag in row.tags.slice(0, 3)" :key="tag" class="material-library-tag rounded bg-slate-100 px-[5px] py-[2px] text-[9px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">{{ tag }}</span>
                  </div>
                </div>
              </div>
            </td>
            <td v-if="!embedded" class="max-w-[250px] px-[10px] py-[10px] text-[11px] text-slate-700 dark:text-slate-300">
              <div v-if="row.material.platform_assets?.length" class="space-y-[4px]">
                <div v-for="asset in row.material.platform_assets" :key="asset.id" class="flex flex-wrap items-center gap-[4px]">
                  <span :class="platformClass(asset.platform)"><span class="account-dot"></span>{{ asset.platform }}</span>
                  <span class="account-chip">{{ asset.ad_account_name || asset.ad_account_id }}</span>
                  <span v-if="asset.ad_account_name" class="text-[9px] text-slate-400">{{ asset.ad_account_id }}</span>
                  <span class="asset-status">{{ platformAssetStatus(asset.normalized_status) }}</span>
                </div>
              </div>
              <span v-else class="text-slate-400">未绑定</span>
            </td>
            <td v-if="!embedded" class="px-[10px] py-[10px] text-[11px] text-slate-700 dark:text-slate-300"><span class="source-chip">{{ row.sourceLabel }}</span></td>
            <td v-if="!embedded" class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.mediaKind === 'video' ? '视频' : '图片' }} · {{ row.format }}</td>
            <td v-if="!embedded" class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.material.width && row.material.height ? `${row.material.width} × ${row.material.height}` : '-' }} · {{ row.ratio }}</td>
            <td v-if="!embedded" class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.fileSizeLabel }}<span v-if="row.durationLabel !== '-'"> · {{ row.durationLabel }}</span></td>
            <td v-if="!embedded" class="px-[10px] py-[10px] text-[11px] text-slate-600 dark:text-slate-400">{{ row.createdAtLabel }}</td>
            <td class="px-[10px] py-[10px]">
              <div class="flex items-center gap-[2px]">
                <button v-if="embedded" class="rounded-md p-[5px] text-slate-400 hover:bg-primary/10 hover:text-primary" title="预览素材" @click.stop="selectRow(row)">
                  <span class="material-symbols-outlined text-[15px]">visibility</span>
                </button>
                <button
                  v-if="embedded"
                  class="mention-btn rounded-md border border-primary/20 bg-white/95 px-[8px] py-[5px] text-[10px] font-semibold text-primary opacity-0 shadow-sm transition-all hover:bg-primary/10 group-hover:opacity-100 dark:bg-slate-900/95"
                  title="引用到对话"
                  @click.stop="emit('mention', row.material)"
                >
                  @mention
                </button>
                <button v-if="allowDelete" class="rounded-md p-[5px] text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30" title="从 ANIFORCE 删除" @click.stop="emit('delete', row)">
                  <span class="material-symbols-outlined text-[15px]">delete</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.material-library--notion {
  border-color: #e5e3df;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
  color: #37352f;
}

.material-library--notion .material-library-toolbar {
  border-color: #ede9e4;
  background: #ffffff;
}

.material-library--notion .material-library-search {
  border-color: #e5e3df;
  border-radius: 6px;
  color: #37352f;
  box-shadow: none;
}

.material-library--notion .material-library-search::placeholder {
  color: #9b9a97;
}

.material-library--notion .material-library-search:focus {
  border-color: #b7b5b0;
  box-shadow: 0 0 0 2px rgba(35, 131, 226, 0.14);
}

.material-library--notion .filter-select {
  border-color: #e5e3df;
  background-color: #ffffff;
  color: #37352f;
}

.material-library--notion .filter-select:hover {
  background-color: #f6f5f4;
}

.material-library--notion .filter-select:focus {
  border-color: #b7b5b0;
  box-shadow: 0 0 0 2px rgba(35, 131, 226, 0.14);
}

.material-library--notion .material-library-table-head {
  background: #f6f5f4;
  color: #787671;
  text-transform: none;
}

.material-library--notion tbody {
  border-color: #ede9e4;
}

.material-library--notion .material-library-row {
  border-left-color: transparent;
}

.material-library--notion .material-library-row:hover {
  background: #fafaf9;
}

.material-library--notion .material-library-row.border-l-primary {
  border-left-color: #2383e2;
  background: rgba(35, 131, 226, 0.055);
}

.material-library--notion .material-library-thumb {
  border-color: #e5e3df;
  border-radius: 6px;
  background: #f6f5f4;
}

.material-library--notion .material-library-name {
  color: #37352f;
}

.material-library--notion .material-library-meta {
  color: #787671;
}

.material-library--notion .material-library-tag {
  border: 0;
  border-radius: 4px;
  background: #f1f1ef;
  color: #5d5b54;
}

.material-library--notion .account-chip,
.material-library--notion .source-chip {
  border-color: #e5e3df;
  background: #f6f5f4;
  color: #5d5b54;
}

.filter-select {
  min-width: 96px;
  height: 32px;
  appearance: none;
  border-radius: 6px;
  border: 1px solid rgb(226 232 240);
  background-color: white;
  background-image: linear-gradient(45deg, transparent 50%, rgb(100 116 139) 50%), linear-gradient(135deg, rgb(100 116 139) 50%, transparent 50%);
  background-position: calc(100% - 12px) 50%, calc(100% - 8px) 50%;
  background-repeat: no-repeat;
  background-size: 4px 4px, 4px 4px;
  padding: 6px 28px 6px 10px;
  font-size: 11px;
  color: rgb(51 65 85);
  outline: none;
}

.filter-select:focus {
  border-color: rgb(var(--color-primary, 59 130 246));
  box-shadow: 0 0 0 1px rgb(var(--color-primary, 59 130 246));
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

.source-chip {
  border-color: rgb(226 232 240);
  background: rgb(248 250 252);
  color: rgb(71 85 105);
}

:global(.dark) .source-chip {
  border-color: rgb(51 65 85);
  background: rgb(30 41 59);
  color: rgb(203 213 225);
}

.asset-status { color: rgb(5 150 105); font-size: 9px; font-weight: 600; }
.account-dot { height: 6px; width: 6px; border-radius: 999px; background: rgb(37 99 235); }
tbody tr { transition: background-color 140ms ease, border-color 140ms ease; }

.mention-btn { cursor: pointer; }

.mention-btn:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
  background: white !important;
  border-color: rgb(var(--color-primary)) !important;
}

.mention-btn:active {
  transform: translateY(0) scale(0.95);
  transition-duration: 0.1s;
}
</style>
