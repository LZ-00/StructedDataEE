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
              placeholder="Extract base materials, process parameters, and associated weld defects or quality outcomes from laser welding reports"
              class="task-description-input-inner"
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
                placeholder="Paste laser welding process report text (English sample aligned with LP-ParamBank)…"
                class="text-input-area"
                resize="none"
                @input="handleTextInput"
              />
            </div>
          </div>
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
            <div class="json-view-container" v-if="extractionResult">
              <el-scrollbar height="600px">
                <pre class="json-content">{{ formattedJSON }}</pre>
              </el-scrollbar>
            </div>
            <el-empty v-else description="暂无抽取结果，请先执行抽取操作" :image-size="100" />
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
  EditPen
} from '@element-plus/icons-vue'
import { extractionService } from '@/services/extractionService'
import type { SelectOption } from '@/types/api'
import type { ExtractionResult } from '@/types'

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
const hasContent = ref(false)

const textAutosize = { minRows: 12, maxRows: 40 }

const textCharCount = computed(() => inputText.value.length)

// 抽取结果
const extractionResult = ref<ExtractionResult | null>(null)

const ENTITY_KEYS = ['text', 'type', 'start', 'end'] as const
const RELATION_KEYS = ['type', 'source', 'sourceType', 'target', 'targetType', 'evidence'] as const

function pickFields<T extends string>(
  item: Record<string, unknown>,
  keys: readonly T[]
): Record<T, unknown> {
  const out = {} as Record<T, unknown>
  for (const k of keys) {
    if (k in item) out[k] = item[k]
  }
  return out
}

function normalizeExtractionResult(raw: unknown): ExtractionResult {
  const data = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>
  const entities = Array.isArray(data.entities)
    ? data.entities
        .filter((e): e is Record<string, unknown> => !!e && typeof e === 'object')
        .map((e) => pickFields(e, ENTITY_KEYS) as ExtractionResult['entities'][number])
    : []
  const relations = Array.isArray(data.relations)
    ? data.relations
        .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object')
        .map((r) => pickFields(r, RELATION_KEYS) as ExtractionResult['relations'][number])
    : []
  return {
    document_id: String(data.document_id ?? ''),
    entities,
    relations
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function clearUploadedFile(): void {
  fileList.value = []
  uploadedFileName.value = ''
  uploadedFileSize.value = ''
  inputText.value = ''
  hasContent.value = false
  extractionResult.value = null
}

// 格式化 JSON（仅 document_id / entities / relations）
const formattedJSON = computed(() => {
  if (!extractionResult.value) return ''
  return JSON.stringify(extractionResult.value, null, 2)
})

// 文件变化处理
const handleFileChange = (file: UploadFile, files: UploadFiles) => {
  fileList.value = files.slice(-1)
  if (!file.raw) return
  uploadedFileName.value = file.name
  uploadedFileSize.value = formatFileSize(file.size ?? file.raw.size)
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = (e.target?.result as string) || ''
    inputText.value = content
    extractionResult.value = null
    hasContent.value = !!content.trim()
  }
  reader.readAsText(file.raw)
}

// 文本输入处理
const handleTextInput = () => {
  if (inputText.value.trim()) {
    extractionResult.value = null
    hasContent.value = true
  } else {
    hasContent.value = false
    extractionResult.value = null
  }
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
  if (!hasContent.value) {
    ElMessage.warning('请先提供待抽取的内容')
    return
  }
  
  isExtracting.value = true
  try {
    let result
    if (inputMode.value === 'file') {
      const raw = fileList.value[0]?.raw
      if (!raw) {
        ElMessage.warning('请先上传文件')
        return
      }
      result = await extractionService.extractFromFile(raw, selectedModel.value, taskDescription.value)
    } else {
      result = await extractionService.extractFromText({
        text: inputText.value,
        model: selectedModel.value,
        task_description: taskDescription.value
      })
    }
    extractionResult.value = normalizeExtractionResult(result)
    ElMessage.success('抽取完成！')
  } catch {
    ElMessage.error('抽取失败，请确认已登录且后端服务已启动')
  } finally {
    isExtracting.value = false
  }
}

// 导出 JSON
const handleExportJSON = () => {
  if (!extractionResult.value) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  const dataStr = JSON.stringify(extractionResult.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `extraction_result_${Date.now()}.json`
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
    if (options.sample_text?.trim()) {
      inputText.value = options.sample_text
      hasContent.value = true
    }
  } catch {
    ElMessage.warning('工作台配置加载失败，请确认已登录且后端服务已启动')
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

.task-description-input-inner :deep(.el-input__inner) {
  font-size: var(--ui-font-caption);
  padding: 10px 12px;
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
.json-view-container {
  border: 1px solid #E4E7ED;
  border-radius: 4px;
  background: #FFFFFF;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.json-content {
  margin: 0;
  padding: 20px;
  color: #303133;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-code);
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #FFFFFF;
}

.json-view-container :deep(.el-scrollbar) {
  flex: 1;
}

.json-view-container :deep(.el-scrollbar__wrap) {
  overflow-x: hidden;
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
