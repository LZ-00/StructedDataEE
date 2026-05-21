/**
 * @deprecated 请优先使用 @/services 下的领域服务；此处保留兼容导出。
 */

export { apiClient as default } from '@/api/client'
export { authService } from '@/services/authService'
export { dashboardService } from '@/services/dashboardService'
export { extractionService } from '@/services/extractionService'
export { evaluationService } from '@/services/evaluationService'
export { distillationService, finetuneService } from '@/services/distillationService'

import { authService } from '@/services/authService'
import { dashboardService } from '@/services/dashboardService'
import { extractionService } from '@/services/extractionService'
import { evaluationService } from '@/services/evaluationService'
import { distillationService, finetuneService } from '@/services/distillationService'
import type { EvaluationConfig } from '@/types'
import type { ExtractionResult } from '@/types'
import type { EvaluationRunResponse, LoginResponse } from '@/types/api'

/** 聚合 API 门面，便于渐进迁移 */
export const api = {
  login: (username: string, password: string): Promise<LoginResponse> =>
    authService.login(username, password),

  extractFromFile: (
    file: File,
    model: string,
    taskDescription: string
  ): Promise<ExtractionResult> =>
    extractionService.extractFromFile(file, model, taskDescription),

  extractFromText: (payload: {
    text: string
    model: string
    task_description: string
  }): Promise<ExtractionResult> => extractionService.extractFromText(payload),

  evaluateStream: (
    config: EvaluationConfig,
    handlers: Parameters<typeof evaluationService.evaluateStream>[1],
    signal?: AbortSignal
  ) => evaluationService.evaluateStream(config, handlers, signal),

  getDashboardStats: () => dashboardService.getStats(),

  generateDistillationDataset: (body: {
    teacherModel: string
    trainingDataset: string
    instruction: string
  }) => distillationService.generateDataset(body),

  runFineTuning: (body: Record<string, unknown>) => finetuneService.runFineTuning(body),

  publishModel: (modelName: string) => finetuneService.publishModel(modelName)
}

export type { LoginResponse, EvaluationRunResponse }
