/**
 * 联系信息 API
 */

import { http } from './http'

export interface ContactInfo {
  id: string
  name: string
  company: string
  contact: string
  message?: string
  source: string
  status: string
  created_at: string
}

export interface CreateContactRequest {
  name: string
  company: string
  contact: string
  message?: string
}

/**
 * 提交联系信息
 */
export async function submitContact(data: CreateContactRequest): Promise<ContactInfo> {
  return http.post<ContactInfo>('/contact', data)
}

/**
 * 获取联系信息列表（管理员）
 */
export async function getContactList(params?: {
  status?: string
  limit?: number
}): Promise<ContactInfo[]> {
  const queryParams = new URLSearchParams()
  if (params?.status) queryParams.append('status', params.status)
  if (params?.limit) queryParams.append('limit', params.limit.toString())

  const query = queryParams.toString()
  const endpoint = `/contact${query ? `?${query}` : ''}`

  return http.get<ContactInfo[]>(endpoint)
}
