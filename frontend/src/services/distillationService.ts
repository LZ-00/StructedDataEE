import { apiClient } from '@/api/client'
import type {
  DistillationCotSample,
  DistillationGenerateResponse,
  DistillationOptions,
  FinetuneTrainingDataset,
  FinetuneOptions
} from '@/types/api'

const AUTH_TOKEN_KEY = 'sdweb_access_token'

export type GenerationLogLevel = 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS'

export interface GenerationLogLine {
  time: string
  level: GenerationLogLevel
  message: string
}

export interface GenerationStepState {
  title: string
  description: string
  status: 'wait' | 'process' | 'finish' | 'error'
}

export interface GenerateDatasetStreamHandlers {
  onStepInit?: (steps: Array<{ title: string; description: string }>) => void
  onStep?: (index: number, status: string) => void
  onLog?: (line: GenerationLogLine) => void
  onDone?: (result: DistillationGenerateResponse) => void
  onCancelled?: (message: string) => void
  onError?: (message: string) => void
}

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

export const distillationService = {
  getOptions(): Promise<DistillationOptions> {
    return apiClient.get('/distillation/options')
  },

  generateDataset(body: {
    teacherModel: string
    trainingDataset: string
    instruction: string
  }): Promise<DistillationGenerateResponse> {
    return apiClient.post('/distillation/generate-dataset', body)
  },

  async generateDatasetStream(
    body: {
      teacherModel: string
      trainingDataset: string
      instruction: string
    },
    handlers: GenerateDatasetStreamHandlers,
    signal?: AbortSignal
  ): Promise<DistillationGenerateResponse | null> {
    const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
    const res = await fetch(`${apiBaseUrl()}/distillation/generate-dataset/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        teacherModel: body.teacherModel,
        trainingDataset: body.trainingDataset,
        instruction: body.instruction
      }),
      signal
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `生成请求失败 HTTP ${res.status}`)
    }

    const reader = res.body?.getReader()
    if (!reader) {
      throw new Error('浏览器不支持流式响应')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult: DistillationGenerateResponse | null = null

    const processLine = (line: string) => {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) return
      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr) return
      let payload: Record<string, unknown>
      try {
        payload = JSON.parse(jsonStr)
      } catch {
        return
      }

      if (payload.type === 'step_init' && Array.isArray(payload.steps)) {
        handlers.onStepInit?.(payload.steps as Array<{ title: string; description: string }>)
      } else if (payload.type === 'step') {
        handlers.onStep?.(payload.index as number, payload.status as string)
      } else if (payload.type === 'log') {
        handlers.onLog?.({
          time: String(payload.time || ''),
          level: (payload.level as GenerationLogLevel) || 'INFO',
          message: String(payload.message || '')
        })
      } else if (payload.type === 'done' && payload.result) {
        finalResult = payload.result as DistillationGenerateResponse
        handlers.onDone?.(finalResult)
      } else if (payload.type === 'cancelled') {
        handlers.onCancelled?.(String(payload.message || '用户已中止生成任务'))
      } else if (payload.type === 'error') {
        handlers.onError?.(String(payload.message || '生成失败'))
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        for (const line of part.split('\n')) {
          processLine(line)
        }
      }
    }

    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        processLine(line)
      }
    }

    return finalResult
  },

  saveDataset(body: {
    teacherModel: string
    trainingDataset: string
    samples: Array<{
      id: number
      context: string
      aiPrediction: string
      verifiedScore: string
      cotTrace: string
    }>
  }): Promise<{ success: boolean; message: string; save_path?: string; saved_count?: number }> {
    return apiClient.post('/distillation/save-dataset', body)
  },

  uploadTrainingDataset(file: File): Promise<{
    success: boolean
    message: string
    dataset: { value: string; label: string; path: string; modified_at: string }
  }> {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post('/distillation/upload-training-dataset', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  listFinetuneDatasets(): Promise<{ success: boolean; datasets: FinetuneTrainingDataset[] }> {
    return apiClient.get('/distillation/finetune-datasets')
  },

  async downloadTrainingTemplate(): Promise<Blob> {
    const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
    const res = await fetch(`${apiBaseUrl()}/distillation/training-dataset-template`, {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!res.ok) {
      throw new Error(`模板下载失败 HTTP ${res.status}`)
    }
    return res.blob()
  }
}

export type { DistillationCotSample }

export interface FinetuneRunResponse {
  success: boolean
  mode?: 'lora' | 'demo'
  checkpoint?: string
  suggested_model_name?: string
  base_model_registry_id?: string
  dataset_path?: string
  dataset_filename?: string
  dataset_sample_count?: number
  message: string
}

export interface FinetuneStreamHandlers {
  onStepInit?: (steps: Array<{ title: string; description: string }>) => void
  onStep?: (index: number, status: string) => void
  onLog?: (line: GenerationLogLine) => void
  onDone?: (result: FinetuneRunResponse) => void
  onError?: (message: string) => void
}

async function consumeSseStream(
  url: string,
  body: Record<string, unknown>,
  handlers: FinetuneStreamHandlers,
  signal?: AbortSignal
): Promise<FinetuneRunResponse | null> {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body),
    signal
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `请求失败 HTTP ${res.status}`)
  }
  const reader = res.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式响应')

  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: FinetuneRunResponse | null = null

  const processLine = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed.startsWith('data:')) return
    const jsonStr = trimmed.slice(5).trim()
    if (!jsonStr) return
    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(jsonStr)
    } catch {
      return
    }
    if (payload.type === 'step_init' && Array.isArray(payload.steps)) {
      handlers.onStepInit?.(payload.steps as Array<{ title: string; description: string }>)
    } else if (payload.type === 'step') {
      handlers.onStep?.(payload.index as number, payload.status as string)
    } else if (payload.type === 'log') {
      handlers.onLog?.({
        time: String(payload.time || ''),
        level: (payload.level as GenerationLogLevel) || 'INFO',
        message: String(payload.message || '')
      })
    } else if (payload.type === 'done' && payload.result) {
      finalResult = payload.result as FinetuneRunResponse
      handlers.onDone?.(finalResult)
    } else if (payload.type === 'error') {
      handlers.onError?.(String(payload.message || '失败'))
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      for (const line of part.split('\n')) processLine(line)
    }
  }
  if (buffer.trim()) {
    for (const line of buffer.split('\n')) processLine(line)
  }
  return finalResult
}

export const finetuneService = {
  getOptions(): Promise<FinetuneOptions> {
    return apiClient.get('/finetune/options')
  },

  runFineTuning(body: Record<string, unknown>): Promise<FinetuneRunResponse> {
    return apiClient.post('/finetune/run', body)
  },

  runFineTuningStream(
    body: Record<string, unknown>,
    handlers: FinetuneStreamHandlers,
    signal?: AbortSignal
  ): Promise<FinetuneRunResponse | null> {
    return consumeSseStream(
      `${apiBaseUrl()}/finetune/run/stream`,
      body,
      handlers,
      signal
    )
  },

  publishModel(
    modelName: string,
    extra?: { checkpoint?: string; baseModel?: string }
  ): Promise<{ success: boolean; message: string }> {
    return apiClient.post('/finetune/publish', {
      modelName,
      checkpoint: extra?.checkpoint,
      baseModel: extra?.baseModel
    })
  },

  uploadTrainingDataset(file: File): Promise<{
    success: boolean
    message: string
    dataset: FinetuneTrainingDataset
    sample_count: number
    removed: string[]
  }> {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post('/finetune/upload-training-dataset', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}
