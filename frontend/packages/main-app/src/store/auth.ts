import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import axios from 'axios'

export interface User {
  id: string
  name: string
  email: string
  avatar?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials {
  name: string
  email: string
  password: string
}

export interface LoginResponse {
  success: boolean
  data?: {
    user: User
    access_token: string
    refresh_token?: string
  }
  message?: string
}

const AUTH_STORAGE_KEY = 'animagus_auth'
const TOKEN_STORAGE_KEY = 'animagus_token'

export const useAuthStore = defineStore('auth', () => {
  // 从localStorage初始化状态
  const storedUser = localStorage.getItem(AUTH_STORAGE_KEY)
  const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
  
  const user = ref<User | null>(storedUser ? JSON.parse(storedUser) : null)
  const token = ref<string | null>(storedToken)

  const isLoggedIn = computed(() => !!user.value && !!token.value)

  // 监听状态变化,自动持久化到localStorage
  watch(user, (newUser) => {
    if (newUser) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newUser))
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY)
    }
  })

  watch(token, (newToken) => {
    if (newToken) {
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken)
      // 设置axios默认header
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      delete axios.defaults.headers.common['Authorization']
    }
  })

  // 真实的登录API
  async function login(credentials: LoginCredentials): Promise<LoginResponse> {
    try {
      // 调用后端登录API
      const response = await axios.post<LoginResponse>('/api/v1/auth/login', credentials)
      
      if (response.data.success && response.data.data) {
        user.value = response.data.data.user
        token.value = response.data.data.access_token
        return response.data
      }
      
      return {
        success: false,
        message: response.data.message || '登录失败'
      }
    } catch (error: any) {
      console.error('登录错误:', error)
      
      // 根据 HTTP 状态码和错误详情返回不同的错误信息
      const status = error.response?.status
      const detail = error.response?.data?.detail
      
      let errorMessage = '网络错误，请稍后重试'
      
      if (status === 404) {
        // 邮箱未注册
        errorMessage = detail || '该邮箱尚未注册'
      } else if (status === 401) {
        // 密码错误
        errorMessage = detail || '密码错误'
      } else if (detail) {
        // 其他错误，使用后端返回的详细信息
        errorMessage = detail
      } else if (error.response?.data?.message) {
        // 使用 message 字段
        errorMessage = error.response.data.message
      }
      
      return {
        success: false,
        message: errorMessage
      }
    }
  }

  // 用户注册API
  async function register(credentials: RegisterCredentials): Promise<LoginResponse> {
    try {
      // 调用后端注册API
      const response = await axios.post<LoginResponse>('/api/v1/auth/register', credentials)
      
      if (response.data.success && response.data.data) {
        user.value = response.data.data.user
        token.value = response.data.data.access_token
        return response.data
      }
      
      return {
        success: false,
        message: response.data.message || '注册失败'
      }
    } catch (error: any) {
      console.error('注册错误:', error)
      return {
        success: false,
        message: error.response?.data?.detail || error.response?.data?.message || '网络错误,请稍后重试'
      }
    }
  }

  // Demo模式的假登录(用于开发测试)
  function fakeLogin() {
    user.value = {
      id: 'admin-001',
      name: 'Admin',
      email: 'admin@animagus.ai',
    }
    token.value = 'fake-jwt-token-demo-' + Date.now()
  }

  // 退出登录
  function logout() {
    user.value = null
    token.value = null
  }

  // 验证token有效性
  async function validateToken(): Promise<boolean> {
    if (!token.value) return false
    
    try {
      const response = await axios.get('/api/v1/auth/validate')
      return response.data.success
    } catch (error) {
      // token无效,清除登录状态
      logout()
      return false
    }
  }

  return { 
    user, 
    token, 
    isLoggedIn, 
    login,
    register,
    fakeLogin, 
    logout,
    validateToken
  }
})
