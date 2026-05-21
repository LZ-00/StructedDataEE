import { apiClient } from '@/api/client'
import type { DashboardCharts, DashboardStats, StatCardMeta } from '@/types/api'

export const dashboardService = {
  getStats(): Promise<DashboardStats> {
    return apiClient.get('/dashboard/stats')
  },

  getStatCards(): Promise<StatCardMeta[]> {
    return apiClient.get('/dashboard/stat-cards')
  },

  getCharts(): Promise<DashboardCharts> {
    return apiClient.get('/dashboard/charts')
  }
}
