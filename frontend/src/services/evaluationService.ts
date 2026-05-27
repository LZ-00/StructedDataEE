import { apiClient } from '@/api/client'
import type { EvaluationConfig, EvaluationRecordResult, EvaluationResult } from '@/types'
import type { EvaluationOptions } from '@/types/api'

const AUTH_TOKEN_KEY = 'sdweb_access_token'

export type EvaluationLogLevel = 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS'

export interface EvaluationLogLine {
  time: string
  level: EvaluationLogLevel
  message: string
}

export interface EvaluationStepState {
  title: string
  description: string
  status: 'wait' | 'process' | 'finish' | 'error'
}

export interface EvaluateStreamHandlers {
  onStepInit?: (steps: Array<{ title: string; description: string }>) => void
  onStep?: (index: number, status: string) => void
  onLog?: (line: EvaluationLogLine) => void
  onCotStart?: (index: number, total: number, preview: string) => void
  onCotDelta?: (text: string) => void
  onCotEnd?: (index: number) => void
  onSampleResult?: (record: EvaluationRecordResult) => void
  onDone?: (evaluation: EvaluationResult) => void
  onCancelled?: (message: string) => void
  onError?: (message: string) => void
}

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

export const evaluationService = {
  getOptions(): Promise<EvaluationOptions> {
    return apiClient.get('/evaluation/options')
  },

  async evaluateStream(
    config: EvaluationConfig,
    handlers: EvaluateStreamHandlers,
    signal?: AbortSignal
  ): Promise<EvaluationResult | null> {
    if (!config.file) {
      throw new Error('请先上传结构化抽取结果 JSON 文件')
    }
    const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
    const formData = new FormData()
    formData.set('model', config.model)
    formData.set('file', config.file)
    const res = await fetch(`${apiBaseUrl()}/evaluation/evaluate/stream`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: formData,
      signal
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(parseHttpErrorMessage(text, res.status))
    }

    const reader = res.body?.getReader()
    if (!reader) {
      throw new Error('浏览器不支持流式响应')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let finalEvaluation: EvaluationResult | null = null

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
        handlers.onStepInit?.(
          payload.steps as Array<{ title: string; description: string }>
        )
      } else if (payload.type === 'step') {
        handlers.onStep?.(payload.index as number, payload.status as string)
      } else if (payload.type === 'log') {
        handlers.onLog?.({
          time: String(payload.time || ''),
          level: (payload.level as EvaluationLogLevel) || 'INFO',
          message: String(payload.message || '')
        })
      } else if (payload.type === 'cot_start') {
        handlers.onCotStart?.(
          payload.index as number,
          payload.total as number,
          String(payload.preview || '')
        )
      } else if (payload.type === 'cot_delta') {
        handlers.onCotDelta?.(String(payload.text || ''))
      } else if (payload.type === 'cot_end') {
        handlers.onCotEnd?.(payload.index as number)
      } else if (payload.type === 'sample_result' && payload.record) {
        handlers.onSampleResult?.(payload.record as EvaluationRecordResult)
      } else if (payload.type === 'done' && payload.evaluation) {
        finalEvaluation = payload.evaluation as EvaluationResult
        handlers.onDone?.(finalEvaluation)
      } else if (payload.type === 'cancelled') {
        handlers.onCancelled?.(String(payload.message || '用户已中止评估'))
      } else if (payload.type === 'error') {
        handlers.onError?.(String(payload.message || '评估失败'))
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

    return finalEvaluation
  }
}

function parseHttpErrorMessage(rawText: string, status: number): string {
  if (!rawText) return `评估请求失败 HTTP ${status}`
  try {
    const parsed = JSON.parse(rawText) as { detail?: unknown; message?: unknown }
    if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
      return parsed.detail
    }
    if (typeof parsed.message === 'string' && parsed.message.trim()) {
      return parsed.message
    }
  } catch {
    // keep raw text fallback
  }
  return rawText || `评估请求失败 HTTP ${status}`
}
