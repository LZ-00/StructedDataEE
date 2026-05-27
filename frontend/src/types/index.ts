/**
 * 系统类型定义
 */

// 实体类型
export interface Entity {
  type: string
  text: string
  start: number
  end: number
}

// 关系类型
export interface Relation {
  type: string
  source: string
  sourceType?: string
  target: string
  targetType?: string
  evidence?: string
}

/** 激光焊接实验记录结构化抽取单条结果 */
export interface MaterialExtractionRecord {
  welding_power: string | null
  welding_speed: string | null
  defocusing_distance: string | null
  shielding_gas: string | null
  shielding_gas_flow_rate: string | null
  tensile_strength: string | null
  yield_strength: string | null
  elongation_rate: string | null
  record_kind?: 'complete' | 'process_only' | 'mechanics_only' | 'merged'
  source_chunk_ids?: string[]
  merge_note?: string | null
}

export interface RelevanceResult {
  is_relevant: boolean
  reason?: string | null
}

export interface TextChunkMeta {
  chunk_id: string
  document_name?: string | null
  chapter?: string | null
  paragraph_index?: number
  language?: string
  token_count?: number
  start_offset?: number
  end_offset?: number
}

export interface ExtractionItem {
  chunk_id: string
  source_text: string
  relevance: RelevanceResult
  records: MaterialExtractionRecord[]
  error?: string | null
}

export interface DocumentMeta {
  filename?: string | null
  total_chars: number
  chunk_count: number
  relevant_count: number
  warnings: string[]
}

// 抽取结果（分块+相关性+结构化）
export interface DocumentExtractionResult {
  document_meta: DocumentMeta
  items: ExtractionItem[]
  records: MaterialExtractionRecord[]
}

// 兼容旧命名
export interface ExtractionResult extends DocumentExtractionResult {
}

export interface PipelineDefaults {
  max_chunk_chars: number
  min_chunk_chars: number
  max_chunks: number
  min_chunk_tokens: number
  max_chunk_tokens: number
  similarity_threshold: number
  similarity_drop_delta: number
  llm_concurrency: number
  embedding_model: string
  embedding_cache_dir: string
}
