import type { DocumentExtractionResult, ExtractionItem, MaterialExtractionRecord } from '@/types'

export interface LaserWeldingExportPayload {
  export_meta: {
    schema_version: string
    exported_at: string
    task_type: 'laser_welding_extraction'
    task_description: string
    model: string
    source_filename: string | null
  }
  summary: {
    total_chars: number
    chunk_count: number
    relevant_chunk_count: number
    extracted_record_count: number
    merged_record_count: number
    unmatched_record_count: number
    warning_count: number
  }
  warnings: string[]
  experimental_records: LaserWeldingRecord[]
}

export interface LaserWeldingRecord {
  record_id: string
  association_status: 'paired' | 'partial'
  source_chunk_ids: string[]
  merge_note: string | null
  welding_parameters: {
    welding_power: string | null
    welding_speed: string | null
    defocusing_distance: string | null
    shielding_gas: string | null
    shielding_gas_flow_rate: string | null
  }
  mechanical_performance: {
    tensile_strength: string | null
    yield_strength: string | null
    elongation_rate: string | null
  }
  source: {
    chunk_id: string
    chunk: string
    relevance_reason: string | null
    excerpt: string
  }
}

const FIELD_LABELS = {
  welding_power: '焊接功率 (W)',
  welding_speed: '焊接速度 (m/min)',
  defocusing_distance: '离焦量 (mm)',
  shielding_gas: '保护气体',
  shielding_gas_flow_rate: '保护气流量 (L/min)',
  tensile_strength: '抗拉强度',
  yield_strength: '屈服强度',
  elongation_rate: '延伸率 (%)'
} as const

function normalizeValue(value: string | null): string | null {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || null
}

function hasRecordValue(record: MaterialExtractionRecord): boolean {
  return (
    normalizeValue(record.welding_power) !== null ||
    normalizeValue(record.welding_speed) !== null ||
    normalizeValue(record.defocusing_distance) !== null ||
    normalizeValue(record.shielding_gas) !== null ||
    normalizeValue(record.shielding_gas_flow_rate) !== null ||
    normalizeValue(record.tensile_strength) !== null ||
    normalizeValue(record.yield_strength) !== null ||
    normalizeValue(record.elongation_rate) !== null
  )
}

function toExcerpt(text: string): string {
  const plain = text.replace(/\s+/g, ' ').trim()
  if (plain.length <= 240) return plain
  return `${plain.slice(0, 240)}...`
}

function nowAsiaShanghaiIsoString(): string {
  const now = new Date()
  const shanghaiText = now.toLocaleString('sv-SE', {
    timeZone: 'Asia/Shanghai',
    hour12: false
  })
  return `${shanghaiText.replace(' ', 'T')}+08:00`
}

function mapRecord(item: ExtractionItem, record: MaterialExtractionRecord, index: number): LaserWeldingRecord {
  const sourceChunkIds = Array.isArray(record.source_chunk_ids) && record.source_chunk_ids.length
    ? [...record.source_chunk_ids]
    : [item.chunk_id]
  const kind = record.record_kind ?? 'complete'
  const associationStatus: LaserWeldingRecord['association_status'] =
    kind === 'merged' || kind === 'complete' ? 'paired' : 'partial'
  return {
    record_id: `R${String(index).padStart(3, '0')}`,
    association_status: associationStatus,
    source_chunk_ids: sourceChunkIds,
    merge_note: normalizeValue(record.merge_note ?? null),
    welding_parameters: {
      welding_power: normalizeValue(record.welding_power),
      welding_speed: normalizeValue(record.welding_speed),
      defocusing_distance: normalizeValue(record.defocusing_distance),
      shielding_gas: normalizeValue(record.shielding_gas),
      shielding_gas_flow_rate: normalizeValue(record.shielding_gas_flow_rate)
    },
    mechanical_performance: {
      tensile_strength: normalizeValue(record.tensile_strength),
      yield_strength: normalizeValue(record.yield_strength),
      elongation_rate: normalizeValue(record.elongation_rate)
    },
    source: {
      chunk_id: item.chunk_id,
      chunk: item.source_text,
      relevance_reason: item.relevance.reason ?? null,
      excerpt: toExcerpt(item.source_text)
    }
  }
}

export function buildLaserWeldingExportPayload(
  result: DocumentExtractionResult,
  options: {
    taskDescription: string
    model: string
  }
): LaserWeldingExportPayload {
  const exportedRecords: LaserWeldingRecord[] = []
  let mergedCount = 0
  let unmatchedCount = 0

  for (const item of result.items) {
    if (item.records.length === 0) continue
    for (const record of item.records) {
      if (!hasRecordValue(record)) {
        exportedRecords.push(mapRecord(item, record, exportedRecords.length + 1))
        continue
      }
      const mapped = mapRecord(item, record, exportedRecords.length + 1)
      if ((record.record_kind ?? 'complete') === 'merged') mergedCount += 1
      if (
        (record.record_kind ?? 'complete') === 'process_only' ||
        (record.record_kind ?? 'complete') === 'mechanics_only'
      ) {
        unmatchedCount += 1
      }
      exportedRecords.push(mapped)
    }
  }

  return {
    export_meta: {
      schema_version: 'laser-welding-v1',
      exported_at: nowAsiaShanghaiIsoString(),
      task_type: 'laser_welding_extraction',
      task_description: options.taskDescription.trim(),
      model: options.model,
      source_filename: result.document_meta.filename ?? null
    },
    summary: {
      total_chars: result.document_meta.total_chars,
      chunk_count: result.document_meta.chunk_count,
      relevant_chunk_count: result.document_meta.relevant_count,
      extracted_record_count: exportedRecords.length,
      merged_record_count: mergedCount,
      unmatched_record_count: unmatchedCount,
      warning_count: result.document_meta.warnings.length
    },
    warnings: [...result.document_meta.warnings],
    experimental_records: exportedRecords
  }
}

export function getMissingFields(record: LaserWeldingRecord): string[] {
  const missing: string[] = []
  if (record.welding_parameters.welding_power === null) missing.push(FIELD_LABELS.welding_power)
  if (record.welding_parameters.welding_speed === null) missing.push(FIELD_LABELS.welding_speed)
  if (record.welding_parameters.defocusing_distance === null) missing.push(FIELD_LABELS.defocusing_distance)
  if (record.welding_parameters.shielding_gas === null) missing.push(FIELD_LABELS.shielding_gas)
  if (record.welding_parameters.shielding_gas_flow_rate === null) missing.push(FIELD_LABELS.shielding_gas_flow_rate)
  if (record.mechanical_performance.tensile_strength === null) missing.push(FIELD_LABELS.tensile_strength)
  if (record.mechanical_performance.yield_strength === null) missing.push(FIELD_LABELS.yield_strength)
  if (record.mechanical_performance.elongation_rate === null) missing.push(FIELD_LABELS.elongation_rate)
  return missing
}
