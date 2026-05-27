import { http } from './http'

export interface PlatformAccount {
  id: string
  org_id?: string
  connection_id?: string
  platform: string
  account_id: string
  external_account_id?: string
  account_name: string
  business_name?: string
  auth_status?: string
  account_status?: string
  readiness_status?: 'ready' | 'warning' | 'blocked' | 'unknown'
  currency?: string
  timezone?: string
  last_sync_at?: string
}

export interface PlatformAccountAssetStatus {
  label: string
  status: 'connected' | 'missing' | 'optional' | 'unknown'
  detail?: string
}

export async function getPlatformAccounts(params?: {
  platform?: string
  status?: string
  org_id?: string
}): Promise<PlatformAccount[]> {
  const queryParams = new URLSearchParams()
  if (params?.platform) queryParams.append('platform', params.platform)
  if (params?.status) queryParams.append('status', params.status)
  if (params?.org_id) queryParams.append('org_id', params.org_id)

  const query = queryParams.toString()
  const endpoint = `/platform-accounts${query ? `?${query}` : ''}`
  const response = await http.get<PlatformAccount[] | { accounts: PlatformAccount[] }>(endpoint)
  return Array.isArray(response) ? response : response.accounts
}

export async function syncPlatformAccounts(platform: string): Promise<void> {
  await http.post('/platform-accounts/sync', { platform })
}

export async function getPlatformAccountReadiness(
  platformAccountId: string
): Promise<{ checks: PlatformAccountAssetStatus[] }> {
  return http.get<{ checks: PlatformAccountAssetStatus[] }>(`/platform-accounts/${platformAccountId}/readiness`)
}

export async function bindProjectPlatformAccount(
  projectId: string,
  platformAccountId: string
): Promise<void> {
  await http.post(`/projects/${projectId}/platform-accounts`, {
    platform_account_id: platformAccountId,
  })
}
