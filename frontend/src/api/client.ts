/**
 * HTTP 客户端：通过 Vite 代理访问 backend（/api -> FastAPI）
 */

import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const AUTH_TOKEN_KEY = 'sdweb_access_token'

export const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    const url = String(config.url || '')
    if (!url.includes('/auth/login')) {
      const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default apiClient
