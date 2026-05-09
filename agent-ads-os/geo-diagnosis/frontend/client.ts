import type { GeoAuditReport, GeoAuditRequest } from './types'

export class GeoDiagnosisClient {
  constructor(private baseUrl = '/api/v1') {}

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || error.message || 'GEO diagnosis request failed')
    }
    return response.json()
  }

  createAudit(data: GeoAuditRequest) {
    return this.request<GeoAuditReport>('/geo-audits', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listAudits(projectId: string) {
    const response = await this.request<{ audits: GeoAuditReport[] }>(
      `/geo-audits?project_id=${encodeURIComponent(projectId)}`,
    )
    return response.audits
  }

  getAudit(id: string) {
    return this.request<GeoAuditReport>(`/geo-audits/${id}`)
  }
}
