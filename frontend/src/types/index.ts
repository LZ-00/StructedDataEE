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

// 抽取结果（仅 document_id / entities / relations）
export interface ExtractionResult {
  document_id: string
  entities: Entity[]
  relations: Relation[]
}
