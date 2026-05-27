<template>
  <div class="extraction-workspace">
    <!-- 顶部控制栏 -->
    <div class="top-toolbar">
      <div class="toolbar-left">
        <span class="task-name">结构化数据智能抽取</span>
      </div>
      <div class="toolbar-right">
        <el-select 
          v-model="selectedModel" 
          placeholder="选择抽取基座模型"
          class="model-selector"
          size="default"
        >
          <el-option
            v-for="model in extractionModels"
            :key="model.value"
            :label="model.label"
            :value="model.value"
          />
        </el-select>
        <el-button 
          type="primary" 
          size="default"
          class="run-button"
          @click="handleRunExtraction"
          :loading="isExtracting"
        >
          <el-icon><MagicStick /></el-icon>
          一键执行抽取
        </el-button>
      </div>
    </div>

    <!-- 主体内容区：左右双栏布局 -->
    <div class="workspace-content">
      <!-- 左侧：文献输入与解析区 -->
      <div class="left-panel">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="card-title">非结构化文献解析</div>
          </template>

          <!-- 任务描述 -->
          <div class="task-description-section">
            <div class="task-description-label">任务描述：</div>
            <el-input
              v-model="taskDescription"
              type="textarea"
              :autosize="taskDescriptionAutosize"
              placeholder="Identify each laser welding experimental record in the following passage…"
              class="task-description-input-inner"
              resize="none"
              clearable
            />
          </div>

          <!-- 输入方式选择 -->
          <div class="input-mode-selector">
            <el-radio-group v-model="inputMode" size="default" class="mode-switch">
              <el-radio-button label="file">
                <el-icon class="mode-icon"><Document /></el-icon>
                文件上传
              </el-radio-button>
              <el-radio-button label="text">
                <el-icon class="mode-icon"><EditPen /></el-icon>
                文本输入
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- 文件上传 -->
          <div class="upload-section" v-if="inputMode === 'file'">
            <el-upload
              v-show="!uploadedFileName"
              class="upload-dragger"
              drag
              :auto-upload="false"
              :on-change="handleFileChange"
              :file-list="fileList"
              accept=".pdf,.txt"
              :show-file-list="false"
            >
              <div class="upload-inner">
                <div class="upload-icon-wrap">
                  <el-icon class="upload-icon"><UploadFilled /></el-icon>
                </div>
                <p class="upload-title">拖拽文件到此处，或点击选择</p>
                <p class="upload-hint">支持工艺报告、试验记录等 PDF / TXT 文档</p>
                <div class="upload-tags">
                  <span class="format-tag">PDF</span>
                  <span class="format-tag">TXT</span>
                </div>
              </div>
            </el-upload>

            <div class="file-ready-card" v-if="uploadedFileName">
              <div class="file-ready-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="file-ready-meta">
                <span class="file-ready-name">{{ uploadedFileName }}</span>
                <span class="file-ready-size" v-if="uploadedFileSize">{{ uploadedFileSize }}</span>
              </div>
              <el-button type="danger" link @click="clearUploadedFile">移除</el-button>
            </div>
          </div>

          <!-- 文本输入 -->
          <div class="text-input-section" v-if="inputMode === 'text'">
            <div class="text-input-surface">
              <div class="text-input-header">
                <span class="text-input-label">待抽取文本</span>
                <span class="text-input-meta" v-if="textCharCount > 0">{{ textCharCount }} 字</span>
              </div>
              <el-input
                v-model="inputText"
                type="textarea"
                :autosize="textAutosize"
                placeholder="Paste materials science literature paragraph for extraction…"
                class="text-input-area"
                resize="none"
                @input="handleTextInput"
              />
            </div>
          </div>

          <!-- 分块与流水线进度（抽取结束后保留，可折叠） -->
          <el-collapse
            v-if="progressPanelVisible"
            :key="progressPanelKey"
            v-model="progressExpanded"
            class="progress-collapse"
          >
            <el-collapse-item name="progress">
              <template #title>
                <div class="progress-collapse-title">
                  <span class="progress-collapse-label">{{ progressPanelTitle }}</span>
                  <el-tag v-if="isExtracting" size="small" type="warning" effect="plain">进行中</el-tag>
                  <el-tag v-else size="small" type="success" effect="plain">已完成</el-tag>
                </div>
              </template>
              <ExtractionProgressPanel
                :steps="pipelineSteps"
                :chunks="chunkPreviews"
                :stage-message="stageMessage"
                chunk-scroll-height="280px"
              />
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </div>

      <!-- 右侧：结构化数据生成区 -->
      <div class="right-panel">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="card-header-right">
              <div class="card-title">结构化抽取结果</div>
              <div class="header-actions">
                <el-button 
                  size="small" 
                  @click="handleExportJSON"
                  :disabled="!extractionResult"
                >
                  <el-icon><Download /></el-icon>
                  一键导出 JSON
                </el-button>
              </div>
            </div>
          </template>

          <div class="result-panel">
            <div v-if="isExtracting && pipelineSteps.length" class="result-progress-hint">
              <el-text type="info">抽取进行中，相关块的结构化结果将实时追加显示</el-text>
            </div>
            <div class="result-list-container" v-if="displayResult">
              <el-scrollbar height="600px">
                <ExtractionResultList
                  :result="displayResult"
                  :editable="Boolean(extractionResult) && !isExtracting"
                  @update-record="handleUpdateRecord"
                  @delete-record="handleDeleteRecord"
                />
              </el-scrollbar>
            </div>
            <el-empty
              v-else-if="!isExtracting"
              description="暂无抽取结果，请先执行抽取操作"
              :image-size="100"
            />
            <div v-else class="result-waiting">
              <el-icon class="is-loading" :size="28"><Loading /></el-icon>
              <p>等待首个相关块完成抽取…</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadFiles } from 'element-plus'
import {
  UploadFilled,
  MagicStick,
  Download,
  Document,
  EditPen,
  Loading
} from '@element-plus/icons-vue'
import {
  extractionService,
  type ExtractionChunkPreview,
  type ExtractionStepState
} from '@/services/extractionService'
import type { SelectOption } from '@/types/api'
import type { DocumentExtractionResult, ExtractionItem, MaterialExtractionRecord } from '@/types'
import { normalizeExtractionResult } from '@/utils/extractionNormalize'
import { buildLaserWeldingExportPayload } from '@/utils/extractionExport'
import ExtractionResultList from '@/components/extraction/ExtractionResultList.vue'
import ExtractionProgressPanel from '@/components/extraction/ExtractionProgressPanel.vue'

// 顶部控制栏
const extractionModels = ref<SelectOption[]>([])
const selectedModel = ref('')
const isExtracting = ref(false)
const taskDescription = ref('')

// 输入方式
const inputMode = ref<'file' | 'text'>('text') // 默认使用文本输入

// 文件上传
const fileList = ref<UploadFiles>([])
const uploadedFileName = ref('')
const uploadedFileSize = ref('')
const inputText = ref('')

const textAutosize = { minRows: 12, maxRows: 40 }
const taskDescriptionAutosize = { minRows: 6, maxRows: 12 }
const DEFAULT_EXTRACTION_INPUT_TEXT = `Laser wire-filled welding of thin aluminum alloy sheet was performed using a welding power of 2800 W, a welding speed of 1.2 m/min, and a defocusing distance of 0 mm. Argon was used as the shielding gas at a shielding gas flow rate of 20 L/min. Under these welding conditions, the welded joint exhibited a tensile strength of 286 MPa, a yield strength of 175 MPa, and an elongation rate of 7.8%. Porosity defects were observed in the weld bead, suggesting that the selected welding parameters and shielding condition affected the joint quality.`

const textCharCount = computed(() => inputText.value.length)

// 抽取结果与流式进度
const extractionResult = ref<DocumentExtractionResult | null>(null)
const pipelineSteps = ref<ExtractionStepState[]>([])
const chunkPreviews = ref<ExtractionChunkPreview[]>([])
const partialItems = ref<ExtractionItem[]>([])
const stageMessage = ref('')
const abortController = ref<AbortController | null>(null)
const progressExpanded = ref<string[]>([])
const progressPanelVisible = ref(false)
const progressPanelKey = ref(0)
let extractionSession = 0

const progressRelevantCount = computed(() =>
  chunkPreviews.value.filter(
    (c) => c.status === 'relevant' || c.status === 'extracting' || c.status === 'done'
  ).length
)

const progressDoneCount = computed(() =>
  chunkPreviews.value.filter((c) => c.status === 'done').length
)

const progressPanelTitle = computed(() => {
  const total = chunkPreviews.value.length
  if (isExtracting.value) {
    return total > 0
      ? `分块与抽取进度（${total} 块，已处理 ${progressDoneCount.value}）`
      : '分块与抽取进度'
  }
  if (total > 0) {
    return `分块与抽取进度（共 ${total} 块，相关 ${progressRelevantCount.value}，已抽取 ${progressDoneCount.value}）`
  }
  return '分块与抽取进度'
})

function expandProgressPanels(): void {
  progressExpanded.value = ['progress']
}

const displayResult = computed((): DocumentExtractionResult | null => {
  if (extractionResult.value) return extractionResult.value
  if (partialItems.value.length === 0) return null
  const records = partialItems.value.flatMap((item) => item.records)
  return {
    document_meta: {
      total_chars: 0,
      chunk_count: chunkPreviews.value.length,
      relevant_count: chunkPreviews.value.filter(
        (c) => c.status === 'relevant' || c.status === 'extracting' || c.status === 'done'
      ).length,
      warnings: []
    },
    items: [...partialItems.value],
    records
  }
})

function resetProgressState(): void {
  pipelineSteps.value = []
  chunkPreviews.value = []
  partialItems.value = []
  stageMessage.value = ''
  progressExpanded.value = []
  progressPanelVisible.value = false
  progressPanelKey.value += 1
}

function cancelActiveExtraction(): void {
  extractionSession += 1
  abortController.value?.abort()
  abortController.value = null
  isExtracting.value = false
}

function isCurrentExtractionSession(session: number): boolean {
  return session === extractionSession
}

function updateChunkStatus(chunkId: string, status: ExtractionChunkPreview['status'], reason?: string | null): void {
  const ch = chunkPreviews.value.find((c) => c.chunk_id === chunkId)
  if (ch) {
    ch.status = status
    if (reason !== undefined) ch.relevance_reason = reason
  }
}

function buildStreamHandlers(session: number): import('@/services/extractionService').ExtractStreamHandlers {
  return {
    onStepInit: (steps) => {
      if (!isCurrentExtractionSession(session)) return
      progressPanelVisible.value = true
      pipelineSteps.value = steps.map((s) => ({
        title: s.title,
        description: s.description,
        status: 'wait'
      }))
    },
    onStep: (index, status) => {
      if (!isCurrentExtractionSession(session)) return
      if (pipelineSteps.value[index]) {
        pipelineSteps.value[index].status = status as ExtractionStepState['status']
      }
    },
    onStage: (_stage, message) => {
      if (!isCurrentExtractionSession(session)) return
      stageMessage.value = message
    },
    onChunked: (chunks) => {
      if (!isCurrentExtractionSession(session)) return
      progressPanelVisible.value = true
      chunkPreviews.value = chunks
    },
    onRelevanceDone: (chunkId, _index, _total, isRelevant, reason) => {
      if (!isCurrentExtractionSession(session)) return
      updateChunkStatus(chunkId, isRelevant ? 'relevant' : 'irrelevant', reason ?? null)
    },
    onExtractStart: (chunkId) => {
      if (!isCurrentExtractionSession(session)) return
      updateChunkStatus(chunkId, 'extracting')
    },
    onItem: (item) => {
      if (!isCurrentExtractionSession(session)) return
      const existing = partialItems.value.findIndex((i) => i.chunk_id === item.chunk_id)
      if (existing >= 0) {
        partialItems.value[existing] = item
      } else {
        partialItems.value.push(item)
      }
      updateChunkStatus(item.chunk_id, item.error ? 'error' : 'done')
    },
    onError: (message) => {
      if (!isCurrentExtractionSession(session)) return
      ElMessage.error(message)
    }
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function clearUploadedFile(): void {
  cancelActiveExtraction()
  fileList.value = []
  uploadedFileName.value = ''
  uploadedFileSize.value = ''
  extractionResult.value = null
  resetProgressState()
}

function syncFlattenRecords(result: DocumentExtractionResult): void {
  result.records = result.items.flatMap((item) => item.records)
}

function handleUpdateRecord(payload: {
  chunkId: string
  recordIndex: number
  record: MaterialExtractionRecord
}): void {
  if (!extractionResult.value) return
  const item = extractionResult.value.items.find((entry) => entry.chunk_id === payload.chunkId)
  if (!item) return
  if (payload.recordIndex < 0 || payload.recordIndex >= item.records.length) return
  item.records[payload.recordIndex] = payload.record
  syncFlattenRecords(extractionResult.value)
}

function handleDeleteRecord(payload: { chunkId: string; recordIndex: number }): void {
  if (!extractionResult.value) return
  const item = extractionResult.value.items.find((entry) => entry.chunk_id === payload.chunkId)
  if (!item) return
  if (payload.recordIndex < 0 || payload.recordIndex >= item.records.length) return
  item.records.splice(payload.recordIndex, 1)
  syncFlattenRecords(extractionResult.value)
}

// 文件变化处理
const handleFileChange = (file: UploadFile, files: UploadFiles) => {
  fileList.value = files.slice(-1)
  if (!file.raw) return
  uploadedFileName.value = file.name
  uploadedFileSize.value = formatFileSize(file.size ?? file.raw.size)
  extractionResult.value = null
  resetProgressState()
}

// 文本输入处理
const handleTextInput = () => {
  extractionResult.value = null
  resetProgressState()
}

// 执行抽取
const handleRunExtraction = async () => {
  if (inputMode.value === 'file' && fileList.value.length === 0) {
    ElMessage.warning('请先上传文件')
    return
  }
  if (inputMode.value === 'text' && !inputText.value.trim()) {
    ElMessage.warning('请先输入待抽取的文本内容')
    return
  }
  abortController.value?.abort()
  abortController.value = new AbortController()
  const session = ++extractionSession
  isExtracting.value = true
  extractionResult.value = null
  resetProgressState()
  expandProgressPanels()
  progressPanelVisible.value = true

  const handlers = buildStreamHandlers(session)
  const signal = abortController.value.signal

  try {
    let result: DocumentExtractionResult | null = null
    if (inputMode.value === 'file') {
      const raw = fileList.value[0]?.raw
      if (!raw) {
        ElMessage.warning('请先上传文件')
        return
      }
      result = await extractionService.extractFromFileStream(
        raw,
        selectedModel.value,
        taskDescription.value,
        handlers,
        signal
      )
    } else {
      result = await extractionService.extractFromTextStream(
        {
          text: inputText.value,
          model: selectedModel.value,
          task_description: taskDescription.value
        },
        handlers,
        signal
      )
    }
    if (result && isCurrentExtractionSession(session)) {
      extractionResult.value = normalizeExtractionResult(result)
      stageMessage.value = '抽取已完成，可展开上方进度面板查看分块与流水线详情。'
      ElMessage.success('抽取完成！')
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (isCurrentExtractionSession(session)) {
        ElMessage.info('已取消抽取')
      }
    } else {
      ElMessage.error('抽取失败，请确认已登录且后端服务已启动')
    }
  } finally {
    isExtracting.value = false
    abortController.value = null
  }
}

// 导出 JSON
const handleExportJSON = () => {
  if (!extractionResult.value) {
    ElMessage.warning('没有可导出的数据')
    return
  }

  const payload = buildLaserWeldingExportPayload(extractionResult.value, {
    taskDescription: taskDescription.value,
    model: selectedModel.value
  })
  const dataStr = JSON.stringify(payload, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `laser_welding_extraction_${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)

  ElMessage.success('JSON 导出成功！')
}

onMounted(async () => {
  try {
    const options = await extractionService.getOptions()
    extractionModels.value = options.models
    selectedModel.value = options.default_model
    taskDescription.value = options.default_task_description
    inputText.value = DEFAULT_EXTRACTION_INPUT_TEXT
  } catch {
    ElMessage.warning('工作台配置加载失败，请确认已登录且后端服务已启动')
    inputText.value = DEFAULT_EXTRACTION_INPUT_TEXT
  }
})
</script>

<style scoped>
/* 学术风格：纯白背景，极简设计 */
.extraction-workspace {
  width: 100%;
  min-height: calc(100vh - 78px);
  background: #F5F7FA;
  padding: 24px;
}

/* 顶部控制栏 */
.top-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  background: #FFFFFF;
  border: 1px solid #E4E7ED;
  border-radius: 4px;
  margin-bottom: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.task-name {
  font-size: var(--ui-font-card-title);
  font-weight: 600;
  color: #303133;
  letter-spacing: 0.5px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}


.model-selector {
  width: 220px;
}

.run-button {
  background: #1890FF;
  border-color: #1890FF;
  font-weight: 500;
}

.run-button:hover {
  background: #40A9FF;
  border-color: #40A9FF;
}

/* 主体内容区：左右双栏布局 */
.workspace-content {
  display: flex;
  gap: 24px;
  align-items: stretch;
  height: calc(100vh - 180px);
  min-height: 700px;
}

.left-panel,
.right-panel {
  flex: 1;
  min-width: 0;
}

/* 卡片样式：极简学术风格 */
.panel-card {
  border: 1px solid #E4E7ED;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  background: #FFFFFF;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-card :deep(.el-card__header) {
  padding: 18px 24px;
  border-bottom: 1px solid #E4E7ED;
  background: #FAFAFA;
  flex-shrink: 0;
}

.panel-card :deep(.el-card__body) {
  padding: 24px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.card-title {
  font-size: var(--ui-font-body);
  font-weight: 600;
  color: #303133;
}

/* 任务描述部分 */
.task-description-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #E4E7ED;
  flex-shrink: 0;
}

.task-description-label {
  font-size: var(--ui-font-caption);
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  letter-spacing: 0.3px;
}

.task-description-input-inner {
  width: 100%;
}

.task-description-input-inner :deep(.el-textarea__inner) {
  font-size: var(--ui-font-caption);
  line-height: 1.65;
  padding: 12px 14px;
  min-height: 140px;
}

.card-header-right {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-actions .el-button {
  border-color: #D9D9D9;
  color: #595959;
  font-size: var(--ui-font-caption);
}

.header-actions .el-button:hover {
  border-color: #1890FF;
  color: #1890FF;
}

/* 输入方式选择器 */
.input-mode-selector {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.mode-switch {
  width: 100%;
}

.mode-switch :deep(.el-radio-group) {
  width: 100%;
  display: flex;
  gap: 8px;
  background: #f0f4f8;
  padding: 4px;
  border-radius: 10px;
}

.mode-switch :deep(.el-radio-button) {
  flex: 1;
}

.mode-switch :deep(.el-radio-button__inner) {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: none !important;
  border-radius: 8px !important;
  background: transparent;
  color: #606266;
  font-size: var(--ui-font-caption);
  font-weight: 500;
  box-shadow: none !important;
  transition: background 0.2s ease, color 0.2s ease;
}

.mode-switch :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #ffffff;
  color: var(--primary-color);
  box-shadow: 0 1px 4px rgba(44, 62, 80, 0.08) !important;
}

.mode-icon {
  font-size: 16px;
}

/* 文件上传 */
.upload-section {
  flex-shrink: 0;
}

.upload-dragger {
  width: 100%;
}

.upload-dragger :deep(.el-upload) {
  width: 100%;
}

.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
  min-height: 220px;
  padding: 36px 28px;
  border: 1.5px dashed #c5d3e0;
  border-radius: 12px;
  background: linear-gradient(160deg, #fafcff 0%, #f3f7fb 100%);
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: linear-gradient(160deg, #f5faff 0%, #ebf4fc 100%);
  box-shadow: 0 4px 16px rgba(107, 174, 214, 0.15);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(44, 62, 80, 0.06);
  margin-bottom: 4px;
}

.upload-icon {
  font-size: 32px;
  color: var(--primary-color);
}

.upload-title {
  margin: 0;
  font-size: var(--ui-font-body);
  font-weight: 600;
  color: #303133;
}

.upload-hint {
  margin: 0;
  font-size: var(--ui-font-caption);
  color: #909399;
  line-height: 1.5;
  text-align: center;
  max-width: 360px;
}

.upload-tags {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

.format-tag {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-dark);
  background: rgba(107, 174, 214, 0.15);
  border: 1px solid rgba(107, 174, 214, 0.25);
}

.file-ready-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 12px;
  border: 1px solid #d4e4f0;
  background: linear-gradient(135deg, #f8fbff 0%, #eef6fc 100%);
}

.file-ready-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--primary-color);
  flex-shrink: 0;
}

.file-ready-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-ready-name {
  font-size: var(--ui-font-body);
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-ready-size {
  font-size: var(--ui-font-caption);
  color: #909399;
}

/* 文本输入 */
.text-input-section {
  flex-shrink: 0;
}

.text-input-surface {
  border: 1px solid #dce4ec;
  border-radius: 12px;
  background: #ffffff;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.text-input-surface:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(107, 174, 214, 0.12);
}

.text-input-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #eef2f6;
}

.text-input-label {
  font-size: var(--ui-font-caption);
  font-weight: 600;
  color: #303133;
}

.text-input-meta {
  font-size: 13px;
  color: #909399;
}

.text-input-area :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  padding: 16px 18px;
  font-size: var(--ui-font-body);
  line-height: 1.75;
  color: #303133;
  background: transparent;
  font-family: inherit;
}

.text-input-area :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.text-input-area :deep(.el-textarea__inner::placeholder) {
  color: #b8c0cc;
}

/* 抽取结果区 */
.result-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* JSON 视图 */
.result-list-container {
  border: 1px solid #E4E7ED;
  border-radius: 4px;
  background: #FFFFFF;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.result-list-container :deep(.el-scrollbar) {
  flex: 1;
}

.result-list-container :deep(.el-scrollbar__wrap) {
  overflow-x: auto;
  padding: 14px;
}

.progress-collapse {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.progress-collapse :deep(.el-collapse-item__header) {
  padding: 0 14px;
  height: 44px;
  background: #fafafa;
  font-weight: 500;
}

.progress-collapse :deep(.el-collapse-item__wrap) {
  border-top: 1px solid #e4e7ed;
}

.progress-collapse :deep(.el-collapse-item__content) {
  padding: 14px;
}

.progress-collapse-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.progress-collapse-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-progress-hint {
  margin-bottom: 12px;
}

.result-waiting {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #909399;
  font-size: 14px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .extraction-workspace {
    padding: 16px;
  }
  
  .top-toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    padding: 16px 20px;
  }
  
  .toolbar-left {
    width: 100%;
  }
  
  .toolbar-right {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .workspace-content {
    flex-direction: column;
    height: auto;
    min-height: auto;
  }
  
  .left-panel,
  .right-panel {
    width: 100%;
  }
  
  .panel-card {
    height: auto;
    min-height: 500px;
  }
  
  .panel-card :deep(.el-card__body) {
    height: auto;
    min-height: 500px;
  }
}
</style>
