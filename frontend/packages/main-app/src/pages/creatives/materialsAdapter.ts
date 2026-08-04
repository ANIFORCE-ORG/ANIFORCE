import type { Material } from '@/api/materials'

export type MaterialMediaKind = 'image' | 'video'
export type MaterialSourceKind = 'oss' | 'local' | 'imported' | 'meta_import' | 'google_import' | 'tiktok_import' | 'ai_generated' | 'unknown'

export interface MaterialRow {
  id: string
  material: Material
  name: string
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
  previewUrl?: string
  mimeType?: string
}

export const toMaterialRows = (
  materials: Material[],
  previewSources: Map<string, string>,
  mimeTypes: Map<string, string>,
): MaterialRow[] => materials.map(material => {
  const previewUrl = previewSources.get(material.id)
    || material.poster_url
    || material.preview_url
    || material.thumbnail_url
    || material.url
  const mimeType = mimeTypes.get(material.id) || guessMimeType(previewUrl || material.url)
  const mediaKind = resolveMediaKind(material, mimeType)
  const source = resolveSource(material.source, material.url)

  return {
    id: material.id,
    material,
    name: material.name || material.id,
    mediaKind,
    source,
    sourceLabel: sourceLabel(source),
    format: material.format || formatFromUrl(previewUrl || material.url),
    ratio: material.ratio || '未知',
    durationLabel: formatDuration(material.duration),
    fileSizeLabel: formatFileSize(material.file_size),
    createdAtLabel: formatDateTime(material.created_at),
    tags: material.tags || [],
    platforms: Array.from(new Set(material.platform_assets?.map(asset => asset.platform) || [])),
    previewUrl,
    mimeType,
  }
})

const resolveMediaKind = (material: Material, mimeType?: string): MaterialMediaKind => {
  if (material.media_kind === 'image' || material.media_kind === 'video') return material.media_kind
  const urls = `${material.preview_url || ''} ${material.thumbnail_url || ''} ${material.url || ''}`.toLowerCase()
  return mimeType?.startsWith('video/') || /\.(mp4|mov|webm)(\?|$)/.test(urls) ? 'video' : 'image'
}

const resolveSource = (source?: string, url?: string): MaterialSourceKind => {
  if (source === 'oss_upload') return 'oss'
  if (source === 'meta_import' || source === 'google_import' || source === 'tiktok_import' || source === 'ai_generated') return source
  if (source === 'local') return 'local'
  if (!url) return 'unknown'
  if (url.includes('aliyuncs.com') || url.includes('oss-')) return 'oss'
  if (url.startsWith('/')) return 'local'
  return 'imported'
}

const sourceLabel = (source: MaterialSourceKind): string => ({
  oss: 'OSS 上传',
  local: '本地素材',
  imported: '外部导入',
  meta_import: 'Meta 导入',
  google_import: 'Google 导入',
  tiktok_import: 'TikTok 导入',
  ai_generated: 'AI 生成',
  unknown: '未知来源',
}[source])

const guessMimeType = (url?: string): string => {
  if (!url) return ''
  const ext = url.split('?')[0].split('.').pop()?.toLowerCase()
  const mimes: Record<string, string> = {
    jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp',
    gif: 'image/gif', mp4: 'video/mp4', mov: 'video/quicktime', webm: 'video/webm',
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
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  return `${Math.round(size / 1024)} KB`
}

const formatDateTime = (value?: string): string => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
