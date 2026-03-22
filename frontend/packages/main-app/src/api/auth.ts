/**
 * 认证 API
 */
import { http } from './http'

export interface LoginRequest {
  email: string
  password: string
}

export interface User {
  id: string
  email: string
  name: string
}

export interface LoginResponse {
  success: boolean
  data: {
    user: User
    access_token: string
    refresh_token: string
    token_type: string
  }
}

/**
 * 用户登录
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await http.post<LoginResponse>('/auth/login', { email, password })
  
  // 保存 token 到 localStorage
  if (response.success && response.data.access_token) {
    localStorage.setItem('access_token', response.data.access_token)
    localStorage.setItem('refresh_token', response.data.refresh_token)
    localStorage.setItem('user', JSON.stringify(response.data.user))
  }
  
  return response
}

/**
 * 用户登出
 */
export function logout(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

/**
 * 获取当前用户
 */
export function getCurrentUser(): User | null {
  const userStr = localStorage.getItem('user')
  if (!userStr) return null
  try {
    return JSON.parse(userStr)
  } catch {
    return null
  }
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token')
}
