<template>
  <div class="progress-panel">
    <el-collapse v-model="innerExpanded" class="inner-collapse">
      <el-collapse-item v-if="steps.length > 0" name="steps" title="流水线步骤">
        <el-steps :active="activeStep" finish-status="success" align-center class="pipeline-steps">
          <el-step
            v-for="(step, idx) in steps"
            :key="idx"
            :title="step.title"
            :description="step.description"
            :status="step.status"
          />
        </el-steps>
        <p v-if="stageMessage" class="stage-message">{{ stageMessage }}</p>
      </el-collapse-item>

      <el-collapse-item
        v-if="chunks.length > 0"
        name="chunks"
        :title="`语义分块（${chunks.length}，相关 ${relevantCount}，已抽取 ${doneCount}）`"
      >
        <el-scrollbar :max-height="chunkScrollHeight">
          <div class="chunk-list">
            <div
              v-for="chunk in chunks"
              :key="chunk.chunk_id"
              class="chunk-card"
              :class="`status-${chunk.status}`"
            >
              <div class="chunk-card-head">
                <div class="chunk-head-left">
                  <span v-if="chunkSequence(chunk.chunk_id)" class="chunk-seq">
                    分块 {{ chunkSequence(chunk.chunk_id) }}<template v-if="chunks.length > 1">/{{ chunks.length }}</template>
                  </span>
                  <span class="chunk-id">{{ chunk.chunk_id }}</span>
                </div>
                <el-tag size="small" :type="statusTagType(chunk.status)">
                  {{ statusLabel(chunk.status) }}
                </el-tag>
              </div>
              <div v-if="chunkMetaTags(chunk).length" class="chunk-meta">
                <span
                  v-for="tag in chunkMetaTags(chunk)"
                  :key="`${chunk.chunk_id}-${tag.key}`"
                  class="chunk-meta-item"
                >
                  {{ tag.label }}
                </span>
              </div>
              <p class="chunk-text">{{ chunk.text }}</p>
              <p v-if="chunk.relevance_reason" class="chunk-reason">{{ chunk.relevance_reason }}</p>
            </div>
          </div>
        </el-scrollbar>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ExtractionChunkPreview, ExtractionStepState } from '@/services/extractionService'
import {
  buildChunkMetaTags,
  parseChunkSequence,
  type ChunkMetaTag
} from '@/utils/chunkMetaFormat'

const props = withDefaults(
  defineProps<{
    steps: ExtractionStepState[]
    chunks: ExtractionChunkPreview[]
    stageMessage?: string
    chunkScrollHeight?: string
  }>(),
  {
    stageMessage: '',
    chunkScrollHeight: '320px'
  }
)

const innerExpanded = ref<string[]>(['steps', 'chunks'])

watch(
  () => [props.steps.length, props.chunks.length] as const,
  ([stepCount, chunkCount]) => {
    const names: string[] = []
    if (stepCount > 0) names.push('steps')
    if (chunkCount > 0) names.push('chunks')
    if (names.length && innerExpanded.value.length === 0) {
      innerExpanded.value = names
    }
  },
  { immediate: true }
)

const activeStep = computed(() => {
  const processing = props.steps.findIndex((s) => s.status === 'process')
  if (processing >= 0) return processing
  const lastFinish = [...props.steps].reverse().findIndex((s) => s.status === 'finish')
  if (lastFinish >= 0) return props.steps.length - 1 - lastFinish
  return 0
})

const relevantCount = computed(
  () => props.chunks.filter((c) => c.status === 'relevant' || c.status === 'extracting' || c.status === 'done').length
)

const doneCount = computed(() => props.chunks.filter((c) => c.status === 'done' || c.status === 'skipped').length)

function chunkSequence(chunkId: string): number | null {
  return parseChunkSequence(chunkId)
}

function chunkMetaTags(chunk: ExtractionChunkPreview): ChunkMetaTag[] {
  return buildChunkMetaTags(chunk, { totalChunks: props.chunks.length }).filter(
    (tag) => tag.key !== 'seq'
  )
}

function statusLabel(status: ExtractionChunkPreview['status']): string {
  const map: Record<ExtractionChunkPreview['status'], string> = {
    pending: '待判断',
    irrelevant: '不相关',
    relevant: '相关',
    extracting: '抽取中',
    done: '已抽取',
    skipped: '已跳过',
    error: '失败'
  }
  return map[status] || status
}

function statusTagType(status: ExtractionChunkPreview['status']): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<ExtractionChunkPreview['status'], '' | 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info',
    irrelevant: 'info',
    relevant: 'warning',
    extracting: 'warning',
    done: 'success',
    skipped: 'info',
    error: 'danger'
  }
  return map[status] ?? 'info'
}
</script>

<style scoped>
.progress-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pipeline-steps {
  margin-bottom: 4px;
}

.stage-message {
  margin: 0;
  font-size: 13px;
  color: #606266;
}

.inner-collapse {
  border: none;
}

.inner-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  height: 40px;
  padding-left: 4px;
}

.inner-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}

.chunk-list {
  padding: 4px 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chunk-card {
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  background: #fff;
}

.chunk-card.status-relevant,
.chunk-card.status-extracting {
  border-color: #e6a23c;
}

.chunk-card.status-done {
  border-color: #67c23a;
}

.chunk-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.chunk-head-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.chunk-seq {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.chunk-id {
  font-size: 12px;
  font-weight: 500;
  color: #909399;
}

.chunk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.chunk-meta-item {
  font-size: 12px;
  color: #606266;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f4f4f5;
}

.chunk-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  max-height: 120px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
}

.chunk-reason {
  margin: 8px 0 0;
  font-size: 12px;
  color: #909399;
  font-style: italic;
}
</style>
