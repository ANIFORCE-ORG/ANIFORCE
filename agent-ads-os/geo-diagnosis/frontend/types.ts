export interface GeoAuditRequest {
  project_id?: string
  brand?: string | null
  url: string
  category?: string | null
  competitors?: string[]
  market?: string
}

export interface GeoAuditReport {
  id: string
  project_id?: string | null
  input: GeoAuditRequest
  domain: string
  scores: {
    mention_rate: number
    citation_rate: number
    geo_readiness: number
    agent_hits: number
    fact_correctness: number
    shortlist_win_rate: number
  }
  competitor_leader: string
  agents: Array<{ name: string; purpose: string; hits: number }>
  pages: Array<{ path: string; page_type: string; agent_visits: number; diagnosis: string; status: string }>
  crawl_summary: {
    requested_url: string
    final_url: string
    sitemap_url?: string | null
    robots_status: string
    pages_requested: number
    pages_analyzed: number
    pages_failed: number
    ai_assets: Record<string, string>
    errors: string[]
  }
  extracted_signals: Array<{ name: string; value: string; status: string }>
  prompts: Array<{ prompt: string; mentioned: boolean; cited: boolean; leading_competitor: string }>
  fixes: Array<{ title: string; body: string; priority: number }>
  offer_json: Record<string, unknown>
  created_at: string
}
