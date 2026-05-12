import { http } from './http'

export type AIScenario =
  | 'project_draft'
  | 'plan_extract'
  | 'material_recommend'
  | 'material_copy'
  | 'plan_review'
  | 'campaign_diagnosis'
  | 'report_summary'
  | 'chat_general'

export interface AIMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface AIRunRequest {
  scenario: AIScenario
  project_id?: string
  campaign_id?: string
  material_id?: string
  messages?: AIMessage[]
  context?: Record<string, any>
  response_schema?: Record<string, any>
}

export interface AIRunResponse {
  scenario: AIScenario
  status: 'draft' | 'suggested' | 'blocked' | 'failed'
  output: Record<string, any>
  usage: {
    usage_log_id: string
    provider: string
    model: string
    input_tokens: number
    output_tokens: number
    total_tokens: number
    estimated_cost_usd: number
    daily_limit_remaining?: number
  }
  requires_human_confirm: boolean
}

export interface AIUsageLog {
  id: string
  project_id?: string
  campaign_id?: string
  scenario: AIScenario
  provider?: string
  model?: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  status: string
  error_message?: string
  created_at?: string
}

export async function runAI(data: AIRunRequest): Promise<AIRunResponse> {
  return http.post<AIRunResponse>('/ai/run', data)
}

export async function getAIUsageSummary(params?: {
  project_id?: string
}): Promise<{
  total_tokens: number
  estimated_cost_usd: number
  by_scenario: Record<string, { total_tokens: number; estimated_cost_usd: number }>
}> {
  const query = new URLSearchParams()
  if (params?.project_id) query.set('project_id', params.project_id)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return http.get(`/ai/usage/summary${suffix}`)
}

export async function getAIUsageLogs(params?: {
  project_id?: string
  scenario?: AIScenario
  limit?: number
}): Promise<AIUsageLog[]> {
  const query = new URLSearchParams()
  if (params?.project_id) query.set('project_id', params.project_id)
  if (params?.scenario) query.set('scenario', params.scenario)
  if (params?.limit) query.set('limit', String(params.limit))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return http.get<AIUsageLog[]>(`/ai/usage/logs${suffix}`)
}

export async function setAIUsageBudget(data: {
  scope_type?: 'user' | 'project'
  scope_id?: string
  daily_token_limit?: number
  monthly_token_limit?: number
  daily_cost_limit_usd?: number
  monthly_cost_limit_usd?: number
  enabled?: boolean
}): Promise<Record<string, any>> {
  return http.post('/ai/usage/budget', data)
}

