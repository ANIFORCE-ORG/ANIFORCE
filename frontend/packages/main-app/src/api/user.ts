import axios from 'axios'

const API_BASE = '/api/v1/user'

export interface UpdateNameRequest {
  name: string
}

export interface UpdatePasswordRequest {
  current_password: string
  new_password: string
}

export interface UserResponse {
  id: string
  email: string
  name: string
}

export const userApi = {
  async updateName(data: UpdateNameRequest): Promise<UserResponse> {
    if (import.meta.env.VITE_DEMO_MODE === 'true') {
      return { id: 'admin-001', email: 'admin@animagus.ai', name: data.name }
    }
    const response = await axios.put(`${API_BASE}/name`, data)
    return response.data.data
  },

  async updatePassword(data: UpdatePasswordRequest): Promise<void> {
    if (import.meta.env.VITE_DEMO_MODE === 'true') return
    await axios.put(`${API_BASE}/password`, data)
  }
}
