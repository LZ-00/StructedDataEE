import { apiClient } from '@/api/client'
import type {
  ModelConfigFormOptions,
  ModelRecord,
  ModelTestResult,
  ModelDownloadResult
} from '@/types/api'

export const modelConfigService = {
  checkHealth(): Promise<{ status: string }> {
    return apiClient.get('/health')
  },

  getOptions(): Promise<ModelConfigFormOptions> {
    return apiClient.get('/models/options')
  },

  listModels(includeDisabled = false): Promise<{ models: ModelRecord[] }> {
    return apiClient.get('/models', { params: { include_disabled: includeDisabled } })
  },

  getModel(id: string): Promise<ModelRecord> {
    return apiClient.get(`/models/${id}`)
  },

  createModel(body: Record<string, unknown>): Promise<ModelRecord> {
    return apiClient.post('/models', body)
  },

  updateModel(id: string, body: Record<string, unknown>): Promise<ModelRecord> {
    return apiClient.put(`/models/${id}`, body)
  },

  deleteModel(id: string): Promise<{ success: boolean }> {
    return apiClient.delete(`/models/${id}`)
  },

  testModel(id: string): Promise<ModelTestResult> {
    return apiClient.post(`/models/${id}/test`, undefined, { timeout: 600000 })
  },

  downloadModel(modelId: string, baseDir: string): Promise<ModelDownloadResult> {
    return apiClient.post('/models/download', { modelId, baseDir })
  }
}
