/**
 * 与后端 API 契约一致的类型定义
 */

export interface SelectOption {
  label: string
  value: string
}

export interface DashboardStats {
  total_extractions: number
  evaluations_done: number
  avg_accuracy_percent: string
  model_count: number
}

export interface StatCardMeta {
  key: keyof DashboardStats
  title: string
}

export interface DashboardCharts {
  exact_match: { models: string[]; values: number[] }
  rmse: { models: string[]; values: number[] }
}

export interface ExtractionWorkspaceOptions {
  models: SelectOption[]
  default_model: string
  default_task_description: string
  sample_text: string
  sample_texts?: string[]
  benchmark_source?: string
  pipeline_defaults?: import('./index').PipelineDefaults
}

export interface EvaluationOptions {
  models: SelectOption[]
  step_descriptions: string[]
  example_cot_log: string
}

export interface DistillationCotSample {
  id: number
  context: string
  gold_standard: string
  ai_prediction: string
  verified_score: string
  cot_trace: string
}

export interface DistillationOptions {
  teacher_models: SelectOption[]
  training_datasets: SelectOption[]
  default_training_dataset?: string
  default_instruction: string
}

export interface DistillationGenerateResponse {
  success: boolean
  sample_count: number
  preview_count?: number
  message: string
  samples?: DistillationCotSample[]
  teacher_generated_count?: number
  output_path?: string
  run_timestamp?: string
  dataset_csv?: string
  errors?: string[]
}

export interface FinetuneTrainingDataset {
  path: string
  filename: string
  source: 'distillation_saved' | 'bundled' | 'dse' | 'missing'
  sample_count: number
  modified_at?: string
  candidate_count?: number
}

export interface FinetuneOptions {
  base_models: SelectOption[]
  learning_rates: string[]
  defaults: {
    loraRank: number
    loraAlpha: number
    loraDropout: number
    epoch: number
    batchSize: number
    learningRate: string
    modelName: string
  }
  training_dataset?: FinetuneTrainingDataset
}

export type ModelDeployType = 'api' | 'local'

export interface ApiModelConfig {
  baseUrl: string
  apiKey: string
  modelId: string
  temperature: number
  maxTokens: number
  api_key_masked?: string
}

export interface LocalModelConfig {
  modelId: string
  baseDir: string
  localPath: string
}

export interface ModelRecord {
  id: string
  name: string
  type: ModelDeployType
  enabled: boolean
  description: string
  api_config: ApiModelConfig | null
  local_config: LocalModelConfig | null
  resolved_path?: string
  created_at: string
  updated_at: string
}

export interface ModelConfigFormOptions {
  default_base_dir: string
  model_types: SelectOption[]
  example_model_ids: string[]
  example_api_models: string[]
}

export interface ModelTestResult {
  success: boolean
  message: string
  path?: string
  model_id?: string
  base_url?: string
  sample_response?: string
  elapsed_seconds?: number
  tried_paths?: string[]
  error?: string
}

export interface ModelDownloadResult {
  success: boolean
  message: string
  path: string
  expected_path: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface EvaluationRunResponse {
  evaluation: import('./index').EvaluationResult
  logs: Array<{ timestamp: string; type: string; content: string }>
}
