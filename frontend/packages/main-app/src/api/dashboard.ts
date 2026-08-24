import { http } from './http'

export type MetaResultActionType = 'lead' | 'purchase' | 'mobile_app_install'
export type DashboardClickType = 'clicks' | 'inline_link_clicks'

export interface DashboardMetricDefinition {
  result_type: 'lead' | 'install' | 'purchase' | string | null
  result_action_type: MetaResultActionType
  result_cost_label: string
  roas_available: boolean
}

export interface DashboardMetrics {
  spend: number | null
  impressions: number | null
  clicks: number | null
  conversions: number | null
  conversion_value: number | null
  ctr: number | null
  result_cost: number | null
  roas: number | null
}

export interface DashboardTrendPoint extends DashboardMetrics {
  date: string
  accounts_with_facts?: number
  accounts_expected?: number
}

export interface MetaDashboardAccount {
  account_id: string
  account_name: string
  sync_status: 'succeeded' | 'failed' | 'cancelled' | 'running' | 'never_synced' | string
  data_status: 'with_delivery' | 'no_delivery' | 'no_facts' | string
  last_synced_at: string | null
  error_code: string | null
  error_message: string | null
  spend: number | null
  impressions: number | null
  clicks: number | null
  conversions: number | null
  ctr: number | null
  result_cost: number | null
  roas: number | null
}

export interface MetaDashboardAdSet {
  account_id: string
  account_name: string
  adset_id: string
  adset_name: string
  campaign_name: string | null
  spend: number | null
  impressions: number | null
  clicks: number | null
  conversions: number | null
  ctr: number | null
  result_cost: number | null
  roas: number | null
}

export interface MetaDashboardOverview {
  window: {
    since: string
    until: string
    currency: string | null
    timezone: string | null
    mixed_currency: boolean
    mixed_timezone: boolean
  }
  metric_definition: DashboardMetricDefinition
  kpis: DashboardMetrics
  previous?: {
    window: { since: string; until: string }
    kpis: DashboardMetrics
  }
  trend: DashboardTrendPoint[]
  accounts: MetaDashboardAccount[]
  adsets?: MetaDashboardAdSet[]
  data_quality: {
    status: 'accessible_with_rows' | 'accessible_with_no_rows' | 'accessible_with_zero_delivery' | 'partial_error'
    row_count: number
    accounts_with_rows?: number
    accounts_expected?: number
    coverage_percent?: number
    facts_scope?: string
  }
}

export interface MetaAdSetSyncRequest {
  connection_id: string
  account_ids: string[]
  since: string
  until: string
  level?: 'adset'
}

export interface MetaAdSetSyncAccountResult {
  account_id: string
  account_name: string | null
  sync_run_id: string
  status: 'succeeded' | 'failed'
  rows_written: number
  error_code?: string
  message?: string
}

export interface MetaAdSetSyncResponse {
  connection_id: string
  level: 'adset'
  window: { since: string; until: string }
  accounts: MetaAdSetSyncAccountResult[]
}

export interface MetaAdSetSyncProgress {
  total: number
  completed: number
  succeeded: number
  failed: number
  running: number
  rows_written: number
  percent: number
}

export interface MetaDashboardOverviewParams {
  connectionId: string
  accountId?: string
  since: string
  until: string
  resultActionType?: MetaResultActionType
  clickType?: DashboardClickType
}

export function syncMetaAdSetFacts(request: MetaAdSetSyncRequest, signal?: AbortSignal) {
  return http.post<MetaAdSetSyncResponse>('/meta-facts/sync', {
    ...request,
    account_ids: request.account_ids.map(id => id.replace(/^act_/, '')),
    level: 'adset',
  }, { signal })
}

export function cancelMetaAdSetSync(request: MetaAdSetSyncRequest) {
  return http.post<{ cancelled: number }>('/meta-facts/sync/cancel', {
    ...request,
    account_ids: request.account_ids.map(id => id.replace(/^act_/, '')),
    level: 'adset',
  })
}

export function getMetaAdSetSyncProgress(request: MetaAdSetSyncRequest) {
  return http.post<MetaAdSetSyncProgress>('/meta-facts/sync/progress', {
    ...request,
    account_ids: request.account_ids.map(id => id.replace(/^act_/, '')),
    level: 'adset',
  })
}

export function getMetaDashboardOverview(params: MetaDashboardOverviewParams) {
  const query = new URLSearchParams({
    connection_id: params.connectionId,
    since: params.since,
    until: params.until,
    result_action_type: params.resultActionType ?? 'lead',
    click_type: params.clickType ?? 'inline_link_clicks',
  })
  if (params.accountId) query.set('account_id', params.accountId.replace(/^act_/, ''))
  return http.get<MetaDashboardOverview>(`/dashboard/meta-overview?${query.toString()}`)
}
