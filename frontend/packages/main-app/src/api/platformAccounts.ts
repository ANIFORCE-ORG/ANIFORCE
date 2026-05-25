import { http } from './http'

export interface PlatformAccount {
  id: string
  platform: string
  account_id: string
  account_name: string
  business_name?: string
  auth_status?: string
  account_status?: string
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
}): Promise<PlatformAccount[]> {
  const queryParams = new URLSearchParams()
  if (params?.platform) queryParams.append('platform', params.platform)
  if (params?.status) queryParams.append('status', params.status)

  const query = queryParams.toString()
  const endpoint = `/platform-accounts${query ? `?${query}` : ''}`
  const response = await http.get<PlatformAccount[] | { accounts: PlatformAccount[] }>(endpoint)
  return Array.isArray(response) ? response : response.accounts
}

export async function syncPlatformAccounts(platform: string): Promise<void> {
  await http.post('/platform-accounts/sync', { platform })
}

export async function bindProjectPlatformAccount(
  projectId: string,
  platformAccountId: string
): Promise<void> {
  await http.post(`/projects/${projectId}/platform-accounts`, {
    platform_account_id: platformAccountId,
  })
}
