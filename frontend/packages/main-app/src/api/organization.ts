/**
 * 组织管理 API
 */
import { http } from './http'

export interface OrganizationCreateRequest {
  name: string
  org_code: string
  description?: string
}

export interface OrganizationJoinRequest {
  org_code: string
  invite_code: string
}

export interface OrganizationResponse {
  id: string
  name: string
  org_code: string
  description: string | null
  owner_id: string
  status: string
  member_count: number
  role: string
  created_at: string
}

export interface InviteCodeResponse {
  invite_code: string
  expires_at: string | null
}

export interface OrganizationMember {
  id: string
  user_id: string
  user_name: string
  user_email: string
  role: string
  joined_at: string
}

export interface MembersListResponse {
  members: OrganizationMember[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const organizationApi = {
  /**
   * 创建组织
   */
  create: (data: OrganizationCreateRequest) =>
    http.post<OrganizationResponse>('/organizations', data),

  /**
   * 加入组织
   */
  join: (data: OrganizationJoinRequest) =>
    http.post<OrganizationResponse>('/organizations/join', data),

  /**
   * 获取我的组织列表
   */
  getMyOrganizations: () =>
    http.get<OrganizationResponse[]>('/organizations'),

  /**
   * 离开组织
   */
  leave: (organizationId: string) =>
    http.delete(`/organizations/${organizationId}`),

  /**
   * 解散组织
   */
  disband: (organizationId: string) =>
    http.delete(`/organizations/${organizationId}/disband`),

  /**
   * 获取邀请码
   */
  getInviteCode: (organizationId: string) =>
    http.get<InviteCodeResponse>(`/organizations/${organizationId}/invite-code`),

  /**
   * 获取组织成员列表
   */
  getMembers: (organizationId: string, params?: { page?: number; page_size?: number; search?: string }) => {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.search) queryParams.append('search', params.search)
    const queryString = queryParams.toString()
    return http.get<MembersListResponse>(
      `/organizations/${organizationId}/members${queryString ? `?${queryString}` : ''}`
    )
  },

  /**
   * 添加组织成员
   */
  addMember: (organizationId: string, email: string) =>
    http.post(`/organizations/${organizationId}/members?email=${encodeURIComponent(email)}`),

  /**
   * 移除组织成员
   */
  removeMember: (organizationId: string, userId: string) =>
    http.delete(`/organizations/${organizationId}/members/${userId}`),
}
