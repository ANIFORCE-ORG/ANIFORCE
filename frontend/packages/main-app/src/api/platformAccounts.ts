import { http } from './http'

export interface PlatformAccount {
  id: string
  platform: string
  account_id: string
  account_name: string
  status: string
  currency?: string
  timezone?: string
  business_manager_id?: string
  account_type?: string
  account_property?: string
  source_type?: string
  remark?: string
  balance: number
  amount_spent: number
  available_balance: number
  frozen_balance: number
  survival_days?: number
  usage_days?: number
  meta_account_status?: number
  last_sync_at?: string
  connected_at: string
  has_token: boolean
}

export interface PlatformAccountOperation {
  id: string
  account_pk: string
  operation_type: string
  status: string
  amount?: number
  currency?: string
  target_id?: string
  note?: string
  payload: Record<string, any>
  created_at: string
}

export interface PlatformConnectionConfig {
  id: string
  platform: string
  status: string
  app_id?: string
  has_app_secret: boolean
  redirect_uri?: string
  scopes: string[]
  last_error?: string
  last_connected_at?: string
}

export async function getPlatformAccounts(params?: {
  platform?: string
  status?: string
}): Promise<PlatformAccount[]> {
  const query = new URLSearchParams()
  if (params?.platform) query.set('platform', params.platform)
  if (params?.status) query.set('status', params.status)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return http.get<PlatformAccount[]>(`/platform/accounts${suffix}`)
}

export async function getPlatformConnectUrl(platform: 'meta' | 'google' | 'tiktok'): Promise<{
  auth_url: string
  state: string
}> {
  return http.post(`/platform/connect?platform=${platform}`)
}

export async function getPlatformConnectionConfig(platform: 'meta'): Promise<PlatformConnectionConfig> {
  return http.get(`/platform/connections/${platform}/config`)
}

export async function savePlatformConnectionConfig(
  platform: 'meta',
  data: {
    app_id: string
    app_secret: string
    redirect_uri?: string
    scopes?: string[]
  }
): Promise<PlatformConnectionConfig> {
  return http.put(`/platform/connections/${platform}/config`, data)
}

export async function getPlatformStatus(platform: 'meta' | 'google' | 'tiktok'): Promise<{
  platform: string
  configured: boolean
  redirect_uri: string
  required_permissions: string[]
}> {
  return http.get(`/platform/status?platform=${platform}`)
}

export async function connectPlatformToken(data: {
  platform: 'meta' | 'google' | 'tiktok'
  access_token: string
  refresh_token?: string
  account_id?: string
  account_name?: string
  currency?: string
  timezone?: string
  business_manager_id?: string
  source_type?: string
  remark?: string
}): Promise<{ accounts: PlatformAccount[] }> {
  return http.post('/platform/connect-token', data)
}

export async function createPlatformAccountOperation(
  accountId: string,
  data: {
    operation_type: 'open' | 'recharge' | 'clear' | 'bind' | 'recycle'
    amount?: number
    currency?: string
    target_id?: string
    note?: string
    payload?: Record<string, any>
  }
): Promise<{ account: PlatformAccount; operation: PlatformAccountOperation }> {
  return http.post(`/platform/accounts/${accountId}/operations`, data)
}

export async function getPlatformAccountOperations(accountId: string): Promise<PlatformAccountOperation[]> {
  return http.get(`/platform/accounts/${accountId}/operations`)
}

export async function addTestPlatformAccount(platform: string): Promise<PlatformAccount> {
  return http.post(`/platform/accounts/test?platform=${platform}`)
}

export async function disconnectPlatformAccount(accountId: string): Promise<{ message: string }> {
  return http.delete(`/platform/accounts/${accountId}`)
}

export async function createMetaCampaign(data: {
  platform_account_id: string
  project_id: string
  name: string
  objective: string
  status: string
  budget: number
  budget_type: 'daily' | 'lifetime'
  special_ad_categories?: string[]
  bid_strategy?: string
  create_local_record?: boolean
}): Promise<any> {
  return http.post('/platform/meta/campaigns', data)
}
