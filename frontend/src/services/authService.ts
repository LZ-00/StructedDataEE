import { apiClient } from '@/api/client'
import type { LoginResponse } from '@/types/api'

export const authService = {
  login(username: string, password: string): Promise<LoginResponse> {
    return apiClient.post('/auth/login', { username, password })
  }
}
