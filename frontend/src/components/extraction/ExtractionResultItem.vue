<template>
  <el-card class="result-item" shadow="never">
    <template #header>
      <div class="result-item-header">
        <span class="chunk-id">{{ item.chunk_id }}</span>
        <el-tag size="small" :type="item.records.length > 0 ? 'success' : 'info'">
          {{ item.records.length > 0 ? '已抽取字段' : '无结构化结果' }}
        </el-tag>
      </div>
    </template>

    <div class="result-source">
      <div class="section-title">待抽取文本段</div>
      <div class="source-text">{{ item.source_text }}</div>
    </div>

    <div class="result-structured">
      <div class="section-title">结构化数据</div>
      <el-empty v-if="item.records.length === 0" description="该文本段未抽取到有效字段" :image-size="64" />
      <el-table v-else :data="item.records" border size="small">
        <el-table-column
          v-for="col in recordColumns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
          min-width="140"
        >
          <template #default="{ row, $index }">
            <el-input
              v-if="isEditingRow($index)"
              v-model="editDraft[col.key]"
              size="small"
              clearable
              placeholder="-"
            />
            <span v-else>{{ formatFieldDisplay(row[col.key]) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="editable" label="操作" fixed="right" width="160">
          <template #default="{ row, $index }">
            <div class="row-actions">
              <template v-if="isEditingRow($index)">
                <el-button type="primary" link @click="saveEdit($index)">保存</el-button>
                <el-button link @click="cancelEdit">取消</el-button>
              </template>
              <template v-else>
                <el-button type="primary" link @click="startEdit($index, row)">编辑</el-button>
                <el-button type="danger" link @click="deleteRecord($index)">删除</el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-alert
        v-if="item.error"
        type="warning"
        :closable="false"
        show-icon
        :title="`该块抽取异常：${item.error}`"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import type { ExtractionItem, MaterialExtractionRecord } from '@/types'

type BusinessFieldKey =
  | 'welding_power'
  | 'welding_speed'
  | 'defocusing_distance'
  | 'shielding_gas'
  | 'shielding_gas_flow_rate'
  | 'tensile_strength'
  | 'yield_strength'
  | 'elongation_rate'

const props = withDefaults(
  defineProps<{
  item: ExtractionItem
  editable?: boolean
}>(),
  {
    editable: true
  }
)

const emit = defineEmits<{
  (e: 'update-record', payload: { chunkId: string; recordIndex: number; record: MaterialExtractionRecord }): void
  (e: 'delete-record', payload: { chunkId: string; recordIndex: number }): void
}>()

const recordColumns: Array<{ key: BusinessFieldKey; label: string }> = [
  { key: 'welding_power', label: '焊接功率 (W)' },
  { key: 'welding_speed', label: '焊接速度 (m/min)' },
  { key: 'defocusing_distance', label: '离焦量 (mm)' },
  { key: 'shielding_gas', label: '保护气体' },
  { key: 'shielding_gas_flow_rate', label: '保护气流量 (L/min)' },
  { key: 'tensile_strength', label: '抗拉强度 (MPa)' },
  { key: 'yield_strength', label: '屈服强度 (MPa)' },
  { key: 'elongation_rate', label: '延伸率 (%)' }
]

const editRowIndex = ref<number | null>(null)
const editDraft = reactive<Record<BusinessFieldKey, string>>({
  welding_power: '',
  welding_speed: '',
  defocusing_distance: '',
  shielding_gas: '',
  shielding_gas_flow_rate: '',
  tensile_strength: '',
  yield_strength: '',
  elongation_rate: ''
})

function isEditingRow(index: number): boolean {
  return props.editable && editRowIndex.value === index
}

function normalizeInput(value: unknown): string {
  if (value === null || value === undefined) return ''
  return String(value)
}

function normalizeOptionalText(value: string): string | null {
  const text = value.trim()
  return text.length ? text : null
}

function startEdit(index: number, row: MaterialExtractionRecord): void {
  editRowIndex.value = index
  for (const col of recordColumns) {
    editDraft[col.key] = normalizeInput(row[col.key])
  }
}

function cancelEdit(): void {
  editRowIndex.value = null
}

function saveEdit(index: number): void {
  const current = props.item.records[index]
  if (!current) return
  const nextRecord: MaterialExtractionRecord = {
    ...current
  }
  for (const col of recordColumns) {
    nextRecord[col.key] = normalizeOptionalText(editDraft[col.key])
  }
  emit('update-record', {
    chunkId: props.item.chunk_id,
    recordIndex: index,
    record: nextRecord
  })
  editRowIndex.value = null
}

async function deleteRecord(index: number): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '删除后不可恢复，是否确认删除该条抽取记录？',
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    emit('delete-record', {
      chunkId: props.item.chunk_id,
      recordIndex: index
    })
    if (editRowIndex.value === index) {
      editRowIndex.value = null
    }
  } catch {
    // 用户取消删除，不做处理
  }
}

function formatFieldDisplay(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'string' && value.trim() === '') return '-'
  return String(value)
}
</script>

<style scoped>
.result-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chunk-id {
  font-weight: 600;
  color: #303133;
}

.result-source {
  margin-bottom: 16px;
}

.section-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.source-text {
  white-space: pre-wrap;
  line-height: 1.65;
  color: #303133;
  border: 1px solid #ebeef5;
  background: #f8fafc;
  border-radius: 6px;
  padding: 10px 12px;
}

.result-structured :deep(.el-alert) {
  margin-top: 10px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
