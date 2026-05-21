import { apiClient } from '@/api/client'
import type { ExtractionResult } from '@/types'
import type { ExtractionWorkspaceOptions } from '@/types/api'

export const extractionService = {
  getOptions(): Promise<ExtractionWorkspaceOptions> {
    return apiClient.get('/extraction/options')
  },

  extractFromFile(
    file: File,
    model: string,
    taskDescription: string
  ): Promise<ExtractionResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model', model)
    formData.append('task_description', taskDescription)
    return apiClient.post('/extraction/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  extractFromText(payload: {
    text: string
    model: string
    task_description: string
  }): Promise<ExtractionResult> {
    return apiClient.post('/extraction/extract-text', payload)
  }
}
