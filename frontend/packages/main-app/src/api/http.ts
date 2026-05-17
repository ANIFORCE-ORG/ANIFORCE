/**
 * HTTP 客户端配置
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: any
}

class HttpClient {
  private baseURL: string
  private defaultHeaders: Record<string, string>

  constructor(baseURL: string) {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('animagus_token')
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = this.getAuthToken()

    const headers = {
      ...this.defaultHeaders,
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const config: RequestInit = {
      method: options.method || 'GET',
      headers,
    }

    if (options.body) {
      config.body = JSON.stringify(options.body)
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        const error: any = new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
        error.response = {
          status: response.status,
          data: errorData
        }
        throw error
      }

      return await response.json()
    } catch (error) {
      console.error('HTTP request failed:', error)
      throw error
    }
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' })
  }

  async post<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body })
  }

  async put<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PUT', body })
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' })
  }
}

export const http = new HttpClient(API_BASE_URL)
