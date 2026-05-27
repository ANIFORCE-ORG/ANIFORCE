/**
 * 认证 API 类型定义
 * 
 * 注意：登录/登出功能已由 Pinia Store (store/auth.ts) 统一管理
 * 此文件仅保留类型定义和后端 API 接口定义
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

export interface SendEmailCodeRequest {
  email: string
  scenario: 'register' | 'reset_password'
}

export interface ResetPasswordRequest {
  email: string
  code: string
  new_password: string
}

/**
 * 刷新 access token（后端接口）
 * 注意：此函数仅用于后端 API 调用，不处理 localStorage
 */
export async function refreshToken(refreshToken: string): Promise<LoginResponse> {
  return await http.post<LoginResponse>('/auth/refresh', { refresh_token: refreshToken })
}

export async function sendEmailCode(data: SendEmailCodeRequest): Promise<{ message?: string }> {
  return await http.post<{ message?: string }>('/auth/email/send-code', data)
}

export async function resetPassword(data: ResetPasswordRequest): Promise<{ message?: string }> {
  return await http.post<{ message?: string }>('/auth/password/reset', data)
}
