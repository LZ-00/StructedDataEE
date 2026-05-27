import { apiClient } from '@/api/client'
import type { DocumentExtractionResult, ExtractionItem } from '@/types'
import type { ExtractionWorkspaceOptions } from '@/types/api'

const AUTH_TOKEN_KEY = 'sdweb_access_token'

export interface ExtractionStepState {
  title: string
  description: string
  status: 'wait' | 'process' | 'finish' | 'error'
}

export type ChunkProgressStatus =
  | 'pending'
  | 'irrelevant'
  | 'relevant'
  | 'extracting'
  | 'done'
  | 'skipped'
  | 'error'

export interface ExtractionChunkPreview {
  chunk_id: string
  text: string
  document_name?: string | null
  chapter?: string | null
  paragraph_index?: number
  language?: string
  token_count?: number
  status: ChunkProgressStatus
  relevance_reason?: string | null
}

export interface ExtractStreamHandlers {
  onStepInit?: (steps: Array<{ title: string; description: string }>) => void
  onStep?: (index: number, status: string) => void
  onStage?: (stage: string, message: string) => void
  onParsed?: (totalChars: number, filename?: string | null) => void
  onChunked?: (chunks: ExtractionChunkPreview[]) => void
  onRelevanceDone?: (
    chunkId: string,
    index: number,
    total: number,
    isRelevant: boolean,
    reason?: string | null
  ) => void
  onExtractStart?: (chunkId: string, index: number, total: number) => void
  onItem?: (item: ExtractionItem) => void
  onDone?: (result: DocumentExtractionResult) => void
  onCancelled?: (message: string) => void
  onError?: (message: string) => void
}

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '/api'
}

function parseSsePayload(
  line: string,
  handlers: ExtractStreamHandlers
): DocumentExtractionResult | null {
  const trimmed = line.trim()
  if (!trimmed.startsWith('data:')) return null
  const jsonStr = trimmed.slice(5).trim()
  if (!jsonStr) return null
  let payload: Record<string, unknown>
  try {
    payload = JSON.parse(jsonStr)
  } catch {
    return null
  }

  if (payload.type === 'step_init' && Array.isArray(payload.steps)) {
    handlers.onStepInit?.(
      payload.steps as Array<{ title: string; description: string }>
    )
  } else if (payload.type === 'step') {
    handlers.onStep?.(payload.index as number, payload.status as string)
  } else if (payload.type === 'stage') {
    handlers.onStage?.(String(payload.stage || ''), String(payload.message || ''))
  } else if (payload.type === 'parsed') {
    handlers.onParsed?.(
      Number(payload.total_chars || 0),
      (payload.filename as string | null | undefined) ?? null
    )
  } else if (payload.type === 'chunked' && Array.isArray(payload.chunks)) {
    const chunks = (payload.chunks as Array<Record<string, unknown>>).map((c) => ({
      chunk_id: String(c.chunk_id),
      text: String(c.text || ''),
      document_name: (c.document_name as string | null) ?? null,
      chapter: (c.chapter as string | null) ?? null,
      paragraph_index: c.paragraph_index as number | undefined,
      language: c.language as string | undefined,
      token_count: c.token_count as number | undefined,
      status: 'pending' as ChunkProgressStatus
    }))
    handlers.onChunked?.(chunks)
  } else if (payload.type === 'relevance_done') {
    handlers.onRelevanceDone?.(
      String(payload.chunk_id),
      Number(payload.index ?? 0),
      Number(payload.total ?? 0),
      Boolean(payload.is_relevant),
      (payload.reason as string | null) ?? null
    )
  } else if (payload.type === 'extract_start') {
    handlers.onExtractStart?.(
      String(payload.chunk_id),
      Number(payload.index ?? 0),
      Number(payload.total ?? 0)
    )
  } else if (payload.type === 'item' && payload.item) {
    handlers.onItem?.(payload.item as ExtractionItem)
  } else if (payload.type === 'done' && payload.result) {
    const result = payload.result as DocumentExtractionResult
    handlers.onDone?.(result)
    return result
  } else if (payload.type === 'cancelled') {
    handlers.onCancelled?.(String(payload.message || '用户已中止抽取'))
  } else if (payload.type === 'error') {
    handlers.onError?.(String(payload.message || '抽取失败'))
  }
  return null
}

async function readSseStream(
  res: Response,
  handlers: ExtractStreamHandlers
): Promise<DocumentExtractionResult | null> {
  const reader = res.body?.getReader()
  if (!reader) {
    throw new Error('浏览器不支持流式响应')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: DocumentExtractionResult | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      for (const line of part.split('\n')) {
        const doneResult = parseSsePayload(line, handlers)
        if (doneResult) finalResult = doneResult
      }
    }
  }

  if (buffer.trim()) {
    for (const line of buffer.split('\n')) {
      const doneResult = parseSsePayload(line, handlers)
      if (doneResult) finalResult = doneResult
    }
  }

  return finalResult
}

export const extractionService = {
  getOptions(): Promise<ExtractionWorkspaceOptions> {
    return apiClient.get('/extraction/options')
  },

  extractFromFile(
    file: File,
    model: string,
    taskDescription: string
  ): Promise<DocumentExtractionResult> {
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
  }): Promise<DocumentExtractionResult> {
    return apiClient.post('/extraction/extract-text', payload)
  },

  async extractFromFileStream(
    file: File,
    model: string,
    taskDescription: string,
    handlers: ExtractStreamHandlers,
    signal?: AbortSignal
  ): Promise<DocumentExtractionResult | null> {
    const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model', model)
    formData.append('task_description', taskDescription)

    const res = await fetch(`${apiBaseUrl()}/extraction/extract/stream`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
      signal
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `抽取请求失败 HTTP ${res.status}`)
    }

    return readSseStream(res, handlers)
  },

  async extractFromTextStream(
    payload: { text: string; model: string; task_description: string },
    handlers: ExtractStreamHandlers,
    signal?: AbortSignal
  ): Promise<DocumentExtractionResult | null> {
    const token = sessionStorage.getItem(AUTH_TOKEN_KEY)
    const res = await fetch(`${apiBaseUrl()}/extraction/extract-text/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(payload),
      signal
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `抽取请求失败 HTTP ${res.status}`)
    }

    return readSseStream(res, handlers)
  }
}
