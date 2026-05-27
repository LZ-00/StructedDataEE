<template>
  <div class="result-list">
    <div class="meta-line">
      <span>总块数：{{ result.document_meta.chunk_count }}</span>
      <span>相关块：{{ result.document_meta.relevant_count }}</span>
      <span>记录数：{{ result.records.length }}</span>
    </div>

    <el-empty
      v-if="result.items.length === 0"
      description="未找到与任务描述相关的文本段"
      :image-size="90"
    />

    <div v-else class="items">
      <ExtractionResultItem
        v-for="item in result.items"
        :key="item.chunk_id"
        :item="item"
        :editable="editable"
        @update-record="(payload) => emit('update-record', payload)"
        @delete-record="(payload) => emit('delete-record', payload)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentExtractionResult } from '@/types'
import ExtractionResultItem from './ExtractionResultItem.vue'

defineProps<{
  result: DocumentExtractionResult
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'update-record', payload: { chunkId: string; recordIndex: number; record: import('@/types').MaterialExtractionRecord }): void
  (e: 'delete-record', payload: { chunkId: string; recordIndex: number }): void
}>()
</script>

<style scoped>
.meta-line {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
}


.items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
