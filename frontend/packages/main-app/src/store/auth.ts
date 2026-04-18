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

export interface LoginResponse {
  success: boolean
  data?: {
    user: User
    token: string
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
        token.value = response.data.data.token
        return response.data
      }
      
      return {
        success: false,
        message: response.data.message || '登录失败'
      }
    } catch (error: any) {
      console.error('登录错误:', error)
      return {
        success: false,
        message: error.response?.data?.message || '网络错误,请稍后重试'
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
    fakeLogin, 
    logout,
    validateToken
  }
})
