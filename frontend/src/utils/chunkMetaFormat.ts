/** 分块元信息展示格式化（paragraph_index 为文档内 0-based 段落序号） */

const LANGUAGE_LABELS: Record<string, string> = {
  zh: '中文',
  en: '英文',
  mixed: '中英混合'
}

export interface ChunkMetaInput {
  chunk_id: string
  token_count?: number
  paragraph_index?: number
  language?: string
  chapter?: string | null
}

export function formatChunkLanguage(code?: string | null): string | null {
  if (!code?.trim()) return null
  const key = code.trim().toLowerCase()
  return LANGUAGE_LABELS[key] ?? code
}

/** 从 chunk_id（如 c-001）解析分块序号 */
export function parseChunkSequence(chunkId: string): number | null {
  const match = chunkId.trim().match(/^c-(\d+)$/i)
  if (!match) return null
  const n = Number.parseInt(match[1], 10)
  return Number.isFinite(n) ? n : null
}

export interface ChunkMetaTag {
  key: string
  label: string
}

/**
 * 生成分块元信息标签列表，供 UI 逐项展示。
 * - 分块序号：来自 chunk_id，用户可读
 * - 词元数：token 估算
 * - 语言：中文标签
 * - 来源段落：仅在有章节或多段落上下文时展示（避免单段文本出现「段 0」）
 */
export function buildChunkMetaTags(
  chunk: ChunkMetaInput,
  options?: { totalChunks?: number }
): ChunkMetaTag[] {
  const tags: ChunkMetaTag[] = []
  const seq = parseChunkSequence(chunk.chunk_id)
  const total = options?.totalChunks

  if (seq != null) {
    tags.push({
      key: 'seq',
      label: total && total > 1 ? `分块 ${seq}/${total}` : `分块 ${seq}`
    })
  }

  if (chunk.token_count != null && chunk.token_count > 0) {
    tags.push({
      key: 'tokens',
      label: `约 ${chunk.token_count} 词元`
    })
  }

  const lang = formatChunkLanguage(chunk.language)
  if (lang) {
    tags.push({ key: 'lang', label: lang })
  }

  if (chunk.chapter?.trim()) {
    tags.push({
      key: 'chapter',
      label: `章节：${chunk.chapter.trim()}`
    })
  }

  const paraIdx = chunk.paragraph_index
  const showSourceParagraph =
    paraIdx != null &&
    paraIdx >= 0 &&
    (Boolean(chunk.chapter?.trim()) || paraIdx > 0)

  if (showSourceParagraph) {
    tags.push({
      key: 'paragraph',
      label: `来源段落 ${paraIdx + 1}`
    })
  }

  return tags
}
