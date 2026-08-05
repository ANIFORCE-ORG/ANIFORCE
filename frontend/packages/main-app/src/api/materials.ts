/**
 * 素材管理 API
 */

import { http } from './http'

export interface Material {
  id: string
  user_id: string
  project_ids: string[]
  campaign_ids: string[]
  name: string
  original_filename?: string
  type: string
  status: string // legacy compatibility only
  lifecycle_status?: 'active' | 'archived'
  processing_status?: 'processing' | 'ready' | 'failed'
  url: string
  thumbnail_url?: string
  ctr_estimate?: number
  tags: string[]
  duration?: number
  file_size?: number
  created_at: string
  media_kind?: 'image' | 'video'
  format?: string
  width?: number
  height?: number
  ratio?: string
  original_url?: string
  preview_url?: string
  poster_url?: string
  source?: string
  creator?: string
  rights?: string
  platforms?: string[]
  review_status?: string
  source_account?: string
  placements?: string[]
  score?: number
  fatigue?: number
  last_used_at?: string
  processing_error?: string
  platform_assets?: MaterialPlatformAsset[]
}

export interface MaterialPlatformAsset {
  id: string
  material_id?: string
  connection_id?: string
  platform: string
  ad_account_id: string
  ad_account_name?: string
  asset_type: 'image' | 'video'
  external_asset_id: string
  image_hash?: string
  remote_name?: string
  remote_status?: string
  normalized_status?: 'unknown' | 'processing' | 'ready' | 'failed'
  remote_url?: string
  remote_thumbnail_url?: string
  last_seen_at?: string
}

export interface UploadMaterialMetadata {
  name: string
  status?: string
  tags?: string[]
  ctr_estimate?: number
  duration?: number
  width?: number
  height?: number
  ratio?: string
  format?: string
  media_kind?: 'image' | 'video'
  source?: string
  creator?: string
  rights?: string
  platforms?: string[]
  review_status?: string
  source_account?: string
  placements?: string[]
  campaign_ids?: string[]
}

export interface MaterialImage {
  material_id: string
  filename: string
  mime_type: string
  size: number
  data: string // Base64 encoded data URL; empty when url is provided
  url?: string // Signed/private object URL
}

export interface AvailableImage {
  filename: string
  size: number
  url: string
}

interface MaterialsResponse {
  materials: Material[]
}

interface ImagesResponse {
  images: AvailableImage[]
}

interface UploadMaterialsResponse {
  materials: Material[]
}

export interface MetaAdAccountOption {
  account_id: string
  account_name: string
  channel: string
  connection_id: string
}

export interface MaterialMetaAssetResult {
  action: 'created' | 'reused' | 'updated' | 'deleted' | 'skipped'
  platform_asset: MaterialPlatformAsset
  run_id?: string
}

export interface MaterialSyncRun {
  run_id: string
  status: 'running' | 'processing' | 'succeeded' | 'partially_succeeded' | 'failed'
  direction?: 'import' | 'export' | 'delete'
  platform?: string
  connection_id?: string
  ad_account_id: string
  discovered_count: number
  created_count: number
  reused_count: number
  updated_count: number
  skipped_count: number
  processing_count?: number
  failed_count: number
  error_summary?: string
  started_at: string
  finished_at?: string
}

/**
 * 获取素材列表
 */
export async function getMaterials(params?: {
  project_id?: string
  campaign_id?: string
  type?: string
  limit?: number
}): Promise<Material[]> {
  const queryParams = new URLSearchParams()
  if (params?.project_id) queryParams.append('project_id', params.project_id)
  if (params?.campaign_id) queryParams.append('campaign_id', params.campaign_id)
  if (params?.type) queryParams.append('type', params.type)
  if (params?.limit) queryParams.append('limit', params.limit.toString())

  const query = queryParams.toString()
  const endpoint = `/materials${query ? `?${query}` : ''}`

  const response = await http.get<MaterialsResponse>(endpoint)
  return response.materials
}

/**
 * 获取素材详情
 */
export async function getMaterialDetail(materialId: string): Promise<Material> {
  return http.get<Material>(`/materials/${materialId}`)
}

export async function publishMaterialToMeta(
  materialId: string,
  data: { platform?: string; connection_id: string; ad_account_id: string; asset_type: 'image' | 'video' },
): Promise<MaterialMetaAssetResult> {
  return http.post<MaterialMetaAssetResult>(`/materials/${materialId}/platform-assets/publish`, data)
}

export async function refreshMaterialPlatformAsset(
  materialId: string,
  assetId: string,
): Promise<MaterialMetaAssetResult> {
  return http.post<MaterialMetaAssetResult>(`/materials/${materialId}/platform-assets/${assetId}/refresh`, {})
}

/**
 * 获取素材预览资源。OSS 素材优先返回签名 URL，本地素材返回 Base64 data URL。
 */
export async function getMaterialImage(
  materialId: string,
  thumbnail: boolean = false
): Promise<MaterialImage> {
  const queryParams = new URLSearchParams()
  if (thumbnail) queryParams.append('thumbnail', 'true')
  
  const query = queryParams.toString()
  const endpoint = `/materials/${materialId}/image${query ? `?${query}` : ''}`
  
  return http.get<MaterialImage>(endpoint)
}

/**
 * 获取所有可用图像列表
 */
export async function getAvailableImages(): Promise<AvailableImage[]> {
  const response = await http.get<ImagesResponse>('/materials/images/list')
  return response.images
}

/**
 * 创建新素材
 */
export async function createMaterial(data: {
  name: string
  type: string
  url: string
  thumbnail_url?: string
  project_ids?: string[]
  campaign_ids?: string[]
  tags?: string[]
  ctr_estimate?: number
}): Promise<Material> {
  return http.post<Material>('/materials', data)
}

/**
 * 更新素材基础信息
 */
export async function updateMaterial(
  materialId: string,
  data: Partial<Pick<Material, 'name' | 'status' | 'tags' | 'thumbnail_url' | 'ctr_estimate'>>
): Promise<Material> {
  return http.patch<Material>(`/materials/${materialId}`, data)
}

/**
 * 上传素材文件
 */
export async function uploadMaterials(files: File[]): Promise<Material[]> {
  const token = localStorage.getItem('animagus_token')
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))

  const response = await fetch('/api/v1/materials/upload', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
  }

  const data = await response.json() as UploadMaterialsResponse
  return data.materials
}

/**
 * 上传单个素材并保存详情字段。
 */
export async function uploadMaterialWithMetadata(
  file: File,
  metadata: UploadMaterialMetadata,
  poster?: Blob
): Promise<Material> {
  const token = localStorage.getItem('animagus_token')
  const formData = new FormData()
  formData.append('file', file)
  if (poster) {
    formData.append('poster', poster, `${file.name.replace(/\.[^.]+$/, '')}_poster.jpg`)
  }

  Object.entries(metadata).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      formData.append(key, JSON.stringify(value))
    } else {
      formData.append(key, String(value))
    }
  })

  const response = await fetch('/api/v1/materials/upload-with-metadata', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
  }

  return response.json() as Promise<Material>
}

/**
 * 获取当前用户已绑定的 Meta 广告账户。
 */
export async function getMetaAdAccounts(): Promise<MetaAdAccountOption[]> {
  return http.get<MetaAdAccountOption[]>('/platform-auth/ad-accounts?channel=Meta')
}

/**
 * 从单个 Meta 广告账户同步图片和视频到 ANIFORCE 素材库。
 */
export async function syncMetaMaterials(data: {
  connection_id: string
  ad_account_id: string
  asset_types: Array<'image' | 'video'>
}): Promise<MaterialSyncRun> {
  return http.post<MaterialSyncRun>('/materials/sync/meta', data)
}

/**
 * 查询素材同步结果。
 */
export async function getMaterialSyncRun(runId: string): Promise<MaterialSyncRun> {
  return http.get<MaterialSyncRun>(`/materials/sync-runs/${runId}`)
}

/**
 * 添加素材到项目
 */
export async function addMaterialToProject(
  materialId: string,
  projectId: string
): Promise<void> {
  await http.post(`/materials/${materialId}/projects/${projectId}`)
}

/**
 * 从项目移除素材
 */
export async function removeMaterialFromProject(
  materialId: string,
  projectId: string
): Promise<void> {
  await http.delete(`/materials/${materialId}/projects/${projectId}`)
}

/**
 * 删除素材
 */
export async function deleteMaterial(materialId: string): Promise<void> {
  await http.delete(`/materials/${materialId}`)
}
