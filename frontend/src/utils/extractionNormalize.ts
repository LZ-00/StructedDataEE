import type {
  DocumentExtractionResult,
  DocumentMeta,
  ExtractionItem,
  MaterialExtractionRecord
} from '@/types'

function emptyMeta(): DocumentMeta {
  return {
    filename: null,
    total_chars: 0,
    chunk_count: 0,
    relevant_count: 0,
    warnings: []
  }
}

function coerceScalarToOptionalString(value: unknown): string | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'boolean') return null
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return String(value)
    return String(value)
  }
  if (typeof value === 'string') {
    const text = value.trim()
    return text || null
  }
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => coerceScalarToOptionalString(item))
      .filter((item): item is string => Boolean(item))
    return parts.length ? parts.join(', ') : null
  }
  const text = String(value).trim()
  return text || null
}

function coerceRecordKind(
  value: unknown
): MaterialExtractionRecord['record_kind'] {
  if (typeof value !== 'string') return undefined
  const v = value.trim()
  if (
    v === 'complete' ||
    v === 'process_only' ||
    v === 'mechanics_only' ||
    v === 'merged'
  ) {
    return v
  }
  return undefined
}

function coerceChunkIds(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map((v) => String(v).trim())
    .filter((v) => Boolean(v))
}

function normalizeRecord(raw: unknown): MaterialExtractionRecord {
  const obj = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const out = {} as MaterialExtractionRecord
  out.welding_power = coerceScalarToOptionalString(obj.welding_power)
  out.welding_speed = coerceScalarToOptionalString(obj.welding_speed)
  out.defocusing_distance = coerceScalarToOptionalString(obj.defocusing_distance)
  out.shielding_gas = coerceScalarToOptionalString(obj.shielding_gas)
  out.shielding_gas_flow_rate = coerceScalarToOptionalString(obj.shielding_gas_flow_rate)
  out.tensile_strength = coerceScalarToOptionalString(obj.tensile_strength)
  out.yield_strength = coerceScalarToOptionalString(obj.yield_strength)
  out.elongation_rate = coerceScalarToOptionalString(obj.elongation_rate)
  out.record_kind = coerceRecordKind(obj.record_kind)
  out.source_chunk_ids = coerceChunkIds(obj.source_chunk_ids)
  out.merge_note = coerceScalarToOptionalString(obj.merge_note)
  return out
}

function normalizeItem(raw: unknown): ExtractionItem | null {
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as Record<string, unknown>
  const records = Array.isArray(obj.records) ? obj.records.map(normalizeRecord) : []
  const relRaw = obj.relevance && typeof obj.relevance === 'object'
    ? (obj.relevance as Record<string, unknown>)
    : {}
  return {
    chunk_id: String(obj.chunk_id ?? ''),
    source_text: String(obj.source_text ?? ''),
    relevance: {
      is_relevant: Boolean(relRaw.is_relevant),
      reason: relRaw.reason == null ? null : String(relRaw.reason)
    },
    records,
    error: obj.error == null ? null : String(obj.error)
  }
}

export function normalizeExtractionResult(raw: unknown): DocumentExtractionResult {
  const obj = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const metaRaw = obj.document_meta && typeof obj.document_meta === 'object'
    ? (obj.document_meta as Record<string, unknown>)
    : {}
  const items = Array.isArray(obj.items)
    ? obj.items.map(normalizeItem).filter((i): i is ExtractionItem => !!i && i.chunk_id.length > 0)
    : []
  const records = Array.isArray(obj.records)
    ? obj.records.map(normalizeRecord)
    : items.flatMap((item) => item.records)
  return {
    document_meta: {
      filename: metaRaw.filename == null ? null : String(metaRaw.filename),
      total_chars: Number(metaRaw.total_chars ?? 0),
      chunk_count: Number(metaRaw.chunk_count ?? items.length),
      relevant_count: Number(metaRaw.relevant_count ?? items.length),
      warnings: Array.isArray(metaRaw.warnings) ? metaRaw.warnings.map((w) => String(w)) : []
    },
    items,
    records
  }
}

export function emptyExtractionResult(): DocumentExtractionResult {
  return {
    document_meta: emptyMeta(),
    items: [],
    records: []
  }
}
