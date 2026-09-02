/**
 * HTTP 客户端配置
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: any
  signal?: AbortSignal
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

  /**
   * 检查 token 是否过期
   */
  private isTokenExpired(token: string): boolean {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      const decoded = JSON.parse(jsonPayload)
      
      if (!decoded.exp) return true
      
      // exp 是秒级时间戳，需要转换为毫秒
      const expirationTime = decoded.exp * 1000
      const currentTime = Date.now()
      
      return currentTime >= expirationTime
    } catch {
      return true
    }
  }

  /**
   * 处理登出逻辑
   */
  private handleLogout(): void {
    // 清除所有认证信息（与 Pinia Store 保持一致）
    localStorage.removeItem('animagus_token')
    localStorage.removeItem('animagus_auth')
    
    // 跳转到登录页
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = this.getAuthToken()

    // 检查 token 是否过期（排除登录和注册接口）
    if (token && 
        !endpoint.includes('/auth/login') && 
        !endpoint.includes('/auth/register')) {
      
      if (this.isTokenExpired(token)) {
        // Token 已过期，登出并跳转登录页
        this.handleLogout()
        throw new Error('登录已过期，请重新登录')
      }
    }

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
      signal: options.signal,
    }

    if (options.body) {
      config.body = JSON.stringify(options.body)
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        // 处理 401 未授权错误
        if (response.status === 401) {
          this.handleLogout()
          throw new Error('认证失败，请重新登录')
        }

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

  async patch<T>(endpoint: string, body?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PATCH', body })
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' })
  }
}

export const http = new HttpClient(API_BASE_URL)
