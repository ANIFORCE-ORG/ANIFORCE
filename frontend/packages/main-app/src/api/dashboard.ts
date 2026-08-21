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
  trend: DashboardTrendPoint[]
  data_quality: {
    status: 'accessible_with_rows' | 'accessible_with_no_rows' | 'accessible_with_zero_delivery' | 'partial_error'
    row_count: number
  }
}

export interface MetaDashboardOverviewParams {
  connectionId: string
  accountId?: string
  since: string
  until: string
  resultActionType?: MetaResultActionType
  clickType?: DashboardClickType
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
