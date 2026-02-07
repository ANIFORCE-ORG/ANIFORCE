import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: string
  name: string
  email: string
  avatar?: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  const isLoggedIn = computed(() => !!user.value)

  function fakeLogin() {
    user.value = {
      id: 'admin-001',
      name: 'Admin',
      email: 'admin@animagus.ai',
    }
    token.value = 'fake-jwt-token-demo'
  }

  function logout() {
    user.value = null
    token.value = null
  }

  return { user, token, isLoggedIn, fakeLogin, logout }
})
