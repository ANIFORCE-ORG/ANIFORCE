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
  created_at: string
  updated_at: string
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

  saveGoogleConfig: (data: GoogleConfigRequest) =>
    http.post<PlatformConnectionResponse>('/platform-auth/google/config', data),

  getGoogleConfig: () =>
    http.get<PlatformConnectionResponse | null>('/platform-auth/google/config'),

  getGoogleAuthorizeUrl: (connectionId: string) =>
    http.get<{ authorize_url: string }>(`/platform-auth/google/authorize_url/${connectionId}`),
}
