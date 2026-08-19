import { http } from './http'

export interface MetaConfigRequest {
  account_name: string
  app_id: string
  app_secret?: string
  scopes: string[]
  connection_id?: string
}

export interface GoogleConfigRequest {
  account_name: string
  client_id: string
  client_secret?: string
  scopes: string[]
  connection_id?: string
}

export interface PlatformConnectionResponse {
  id: string
  platform: string
  account_id: string
  account_name: string | null
  status: string
  scopes: string[] | null
  token_expires_at: string | null
  created_at: string
  updated_at: string
}

export interface SubAccountRequest {
  name: string
  sub_account_id: string
  bm_customer_id?: string
}

export interface SubAccountResponse {
  id: string
  name: string
  sub_account_id: string
  bm_customer_id?: string
  status: string
  updated_at: string
}

export interface SubAccountSummary {
  total: number
  active: number
  disabled: number
  pending_review: number
  other: number
}

export interface SubAccountPageResponse {
  items: SubAccountResponse[]
  page: number
  page_size: number
  total: number
  has_more: boolean
  summary: SubAccountSummary
}

export const platformApi = {
  saveMetaConfig: (data: MetaConfigRequest) =>
    http.post<PlatformConnectionResponse>('/platform-auth/meta/config', data),

  getMetaConfig: () =>
    http.get<PlatformConnectionResponse | null>('/platform-auth/meta/config'),

  getAllConnections: () =>
    http.get<PlatformConnectionResponse[]>('/platform-auth/connections'),

  deleteConnection: (connectionId: string) =>
    http.delete(`/platform-auth/connections/${connectionId}`),

  getMetaAuthorizeUrl: (connectionId: string) =>
    http.get<{ authorize_url: string }>(`/platform-auth/meta/authorize_url/${connectionId}`),

  startMetaOAuth: () =>
    http.post<{ authorize_url: string; connection_id: string }>('/platform-auth/meta/start_oauth'),

  startGoogleOAuth: () =>
    http.post<{ authorize_url: string; connection_id: string }>('/platform-auth/google/start_oauth'),

  syncMetaAdAccounts: (connectionId: string) =>
    http.post(`/platform-auth/meta/${connectionId}/sync-adaccounts`),

  syncGoogleAdAccounts: (connectionId: string) =>
    http.post(`/platform-auth/google/${connectionId}/sync-adaccounts`),

  saveGoogleConfig: (data: GoogleConfigRequest) =>
    http.post<PlatformConnectionResponse>('/platform-auth/google/config', data),

  getGoogleConfig: () =>
    http.get<PlatformConnectionResponse | null>('/platform-auth/google/config'),

  getGoogleAuthorizeUrl: (connectionId: string) =>
    http.get<{ authorize_url: string }>(`/platform-auth/google/authorize_url/${connectionId}`),

  // 子账号管理
  getSubAccounts: (connectionId: string, params: { page?: number; page_size?: number; search?: string; status?: string } = {}) => {
    const query = new URLSearchParams()
    if (params.page) query.set('page', String(params.page))
    if (params.page_size) query.set('page_size', String(params.page_size))
    if (params.search) query.set('search', params.search)
    if (params.status) query.set('status', params.status)
    const suffix = query.size ? `?${query.toString()}` : ''
    return http.get<SubAccountPageResponse>(`/platform-auth/google/${connectionId}/sub-accounts${suffix}`)
  },

  addSubAccount: (connectionId: string, data: SubAccountRequest) =>
    http.post<SubAccountResponse>(`/platform-auth/google/${connectionId}/sub-accounts`, data),

  deleteSubAccount: (connectionId: string, subAccountId: string) =>
    http.delete(`/platform-auth/google/${connectionId}/sub-accounts/${subAccountId}`),
}
