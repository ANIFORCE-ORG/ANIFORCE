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
  type: string
  status: string  // running | ready | fatigue
  url: string
  thumbnail_url?: string
  ctr_estimate?: number
  tags: string[]
  duration?: number
  file_size?: number
  created_at: string
  // 新增字段
  media_type?: string
  fatigue?: number
  is_hero?: boolean
  roi?: number
  spend?: number
  campaign_id?: string
}

export interface MaterialImage {
  material_id: string
  filename: string
  mime_type: string
  size: number
  data: string // Base64 encoded data URL
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

/**
 * 获取素材图像（Base64编码）
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
