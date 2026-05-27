<template>
  <div class="evaluation-tracker">
    <el-row :gutter="16" class="main-layout">
      <!-- 左侧：任务控制和状态机 -->
      <el-col :span="8" class="left-panel">
        <!-- 任务控制区 -->
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <span>评估任务控制</span>
              <el-icon><Setting /></el-icon>
            </div>
          </template>
          
          <el-form :model="evaluationConfig" label-width="100px" class="control-form">
            <el-form-item label="选择模型">
              <el-select v-model="evaluationConfig.model" placeholder="请选择评估模型" style="width: 100%">
                <el-option
                  v-for="model in evaluationModels"
                  :key="model.value"
                  :label="model.label"
                  :value="model.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="评估文件">
              <el-upload
                ref="uploadRef"
                class="eval-upload"
                :auto-upload="false"
                :limit="1"
                :show-file-list="true"
                accept=".json,application/json"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :on-exceed="handleFileExceed"
              >
                <el-button style="width: 100%">上传结构化抽取 JSON</el-button>
              </el-upload>
              <div class="upload-tip">
                文件需包含 `experimental_records[].source.chunk`
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="handleStartEvaluation" :loading="evaluating" style="width: 100%">
                <el-icon><VideoPlay /></el-icon>
                开始评估
              </el-button>
            </el-form-item>
            <el-form-item>
              <el-button
                type="danger"
                plain
                @click="handleAbortEvaluation"
                :disabled="!evaluating"
                style="width: 100%"
              >
                <el-icon><Close /></el-icon>
                中止评估
              </el-button>
            </el-form-item>
            <el-form-item>
              <el-button @click="handleReset" style="width: 100%">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 状态机流转图 -->
        <el-card class="state-machine-card">
          <template #header>
            <div class="card-header">
              <span>思维链状态机流转</span>
              <el-icon><Connection /></el-icon>
            </div>
          </template>
          
          <div class="steps-container">
            <el-steps :active="currentStep" finish-status="success" direction="vertical">
              <el-step :title="evalSteps[0]?.title || 'Step 1 解析字段'" :description="stepDescriptions[0]">
                <template #icon>
                  <el-icon><Search /></el-icon>
                </template>
              </el-step>
              <el-step :title="evalSteps[1]?.title || 'Step 2 证据核验'" :description="stepDescriptions[1]">
                <template #icon>
                  <el-icon><CircleCheck /></el-icon>
                </template>
              </el-step>
              <el-step :title="evalSteps[2]?.title || 'Step 3 关系诊断'" :description="stepDescriptions[2]">
                <template #icon>
                  <el-icon><Document /></el-icon>
                </template>
              </el-step>
              <el-step :title="evalSteps[3]?.title || 'Step 4 评分统合'" :description="stepDescriptions[3]">
                <template #icon>
                  <el-icon><Finished /></el-icon>
                </template>
              </el-step>
            </el-steps>
          </div>
        </el-card>
      </el-col>

      <!-- 中间：CoT Logs -->
      <el-col :span="10" class="center-panel">
        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <span>思维链推理轨迹 (CoT Logs)</span>
              <div>
                <el-button text type="primary" @click="handleClearLogs">
                  <el-icon><Delete /></el-icon>
                  清空
                </el-button>
                <el-button text type="primary" @click="handleExportLogs">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="eval-console">
            <div class="console-header">
              <span>运行日志 (Runtime Log)</span>
              <el-icon v-if="evaluating" class="spinning"><Loading /></el-icon>
            </div>
            <div ref="logContainerRef" class="console-content eval-log-content">
              <div
                v-for="(line, index) in runtimeLogs"
                :key="`log-${index}`"
                :class="['log-line', `log-level-${line.level.toLowerCase()}`]"
              >
                <span v-if="line.time" class="log-time">[{{ line.time }}]</span>
                {{ line.message }}
              </div>
              <div v-if="evaluating && cotStreamText" class="cot-stream-block">
                <div class="cot-stream-label">CoT 推理输出（实时）</div>
                <pre class="cot-stream-text">{{ cotStreamText }}</pre>
              </div>
              <div v-if="evaluating" class="log-line log-cursor">_</div>
              <div
                v-if="!evaluating && !runtimeLogs.length && !cotStreamText"
                class="log-empty"
              >
                <div class="example-title">思维链推理过程示例</div>
                <pre class="example-text">{{ exampleCotLog }}</pre>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：结果判定 -->
      <el-col :span="6" class="right-panel">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>评估结果判定</span>
              <el-icon><Trophy /></el-icon>
            </div>
          </template>
          
          <div class="result-content" v-if="evaluationResult">
            <div class="result-summary">
              <div class="summary-title">整体评估结果</div>
              <div class="summary-desc" v-if="evaluationResult.summary.totalRecords">
                总记录 {{ evaluationResult.summary.totalRecords }} 条 ·
                成功 {{ evaluationResult.summary.successfulRecords }} 条 ·
                失败 {{ evaluationResult.summary.failedRecords }} 条
              </div>
            </div>

            <div class="metrics-list">
              <div v-for="record in evaluationResult.records" :key="`${record.recordId}-${record.index}`" class="metric-item">
                <div class="metric-label">
                  {{ record.recordId }} · {{ record.chunkId }} · {{ record.status === 'success' ? '成功' : '失败' }}
                </div>
                <div class="metric-value record-preview">{{ record.preview || '-' }}</div>
                <div v-if="record.score" class="metric-score">
                  评估计数：{{ record.score.correctly_predicted_relations }}/{{ record.score.total_predicted_relations }}
                </div>
                <el-collapse class="record-collapse">
                  <el-collapse-item :name="`${record.recordId}-${record.index}`">
                    <template #title>
                      CoT 推理输出
                    </template>
                    <pre class="record-analysis">{{ record.analysis || '无推理输出' }}</pre>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="empty-state">
            <div class="empty-text">请先配置并启动评估任务</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadRawFile } from 'element-plus'
import {
  Setting,
  VideoPlay,
  Connection,
  Search,
  CircleCheck,
  Document,
  Finished,
  Delete,
  Download,
  Close,
  Trophy,
  Loading
} from '@element-plus/icons-vue'
import type { EvaluationResult } from '@/types'
import {
  evaluationService,
  type EvaluationLogLine,
  type EvaluationStepState
} from '@/services/evaluationService'
import type { SelectOption } from '@/types/api'

const evaluationModels = ref<SelectOption[]>([])

// 评估配置
const evaluationConfig = ref({
  model: '',
  file: null as File | null
})

// 评估状态
const evaluating = ref(false)
const currentStep = ref(-1)
const evalSteps = ref<EvaluationStepState[]>([])
const runtimeLogs = ref<EvaluationLogLine[]>([])
const cotStreamText = ref('')
const cotCollapseActive = ref<string[]>(['realtime-cot'])
const evaluationResult = ref<EvaluationResult | null>(null)
const logContainerRef = ref<HTMLDivElement>()
const uploadRef = ref<UploadInstance>()
const evalAbortController = ref<AbortController | null>(null)

const stepDescriptions = ref<string[]>([])
const exampleCotLog = ref('')

const mapStepStatus = (status: string): EvaluationStepState['status'] => {
  if (status === 'process') return 'process'
  if (status === 'finish') return 'finish'
  if (status === 'error') return 'error'
  return 'wait'
}

const formatNowTime = () => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour12: false, timeZone: 'Asia/Shanghai' })
}

onMounted(async () => {
  try {
    const options = await evaluationService.getOptions()
    evaluationModels.value = options.models
    stepDescriptions.value = options.step_descriptions
    exampleCotLog.value = options.example_cot_log
  } catch {
    ElMessage.warning('评估配置加载失败，请确认已登录且后端服务已启动')
  }
})

// 开始评估（SSE 流式）
const handleStartEvaluation = async () => {
  if (!evaluationConfig.value.model || !evaluationConfig.value.file) {
    ElMessage.warning('请先选择模型并上传结构化抽取 JSON')
    return
  }

  evaluating.value = true
  currentStep.value = 0
  runtimeLogs.value = []
  cotStreamText.value = ''
  cotCollapseActive.value = ['realtime-cot']
  evaluationResult.value = null
  evalSteps.value = []
  runtimeLogs.value.push({
    time: formatNowTime(),
    level: 'INFO',
    message: `当前评估文件：${evaluationConfig.value.file.name}`
  })

  evalAbortController.value?.abort()
  const controller = new AbortController()
  evalAbortController.value = controller

  try {
    const result = await evaluationService.evaluateStream(
      evaluationConfig.value,
      {
        onStepInit: (steps) => {
          evalSteps.value = steps.map((s) => ({
            title: s.title,
            description: s.description,
            status: 'wait'
          }))
          stepDescriptions.value = steps.map((s) => s.description)
        },
        onStep: (index, status) => {
          if (evalSteps.value[index]) {
            evalSteps.value[index].status = mapStepStatus(status)
          }
          if (index === 3 && status === 'finish') {
            currentStep.value = 4
          } else {
            currentStep.value = Math.min(3, index)
          }
        },
        onLog: (line) => {
          runtimeLogs.value.push(line)
          scrollToBottom()
        },
        onCotStart: () => {
          cotStreamText.value = ''
          scrollToBottom()
        },
        onCotDelta: (text) => {
          cotStreamText.value += text
          scrollToBottom()
        },
        onCotEnd: () => {
          scrollToBottom()
        },
        onSampleResult: () => {
          scrollToBottom()
        },
        onDone: (evaluation) => {
          evaluationResult.value = evaluation
          currentStep.value = 4
          evalSteps.value.forEach((s) => {
            if (s.status === 'process') s.status = 'finish'
          })
        },
        onCancelled: (msg) => {
          ElMessage.warning(msg)
          runtimeLogs.value.push({
            time: formatNowTime(),
            level: 'WARN',
            message: msg
          })
          scrollToBottom()
        },
        onError: (msg) => {
          ElMessage.error(msg)
        }
      },
      controller.signal
    )

    if (result) {
      ElMessage.success('评估完成！')
    }
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      const msg = (e as Error).message?.trim() || '评估失败，请确认后端服务已启动并已登录'
      ElMessage.error(msg)
      runtimeLogs.value.push({
        time: formatNowTime(),
        level: 'ERROR',
        message: msg
      })
      await scrollToBottom()
    }
  } finally {
    evaluating.value = false
    evalAbortController.value = null
    await scrollToBottom()
  }
}

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

const handleFileChange = (uploadFile: { raw?: File | null }) => {
  evaluationConfig.value.file = uploadFile.raw || null
}

const handleFileRemove = () => {
  evaluationConfig.value.file = null
}

const handleFileExceed = (files: UploadRawFile[]) => {
  const latest = files[files.length - 1]
  if (!latest) return
  uploadRef.value?.clearFiles()
  latest.uid = Date.now()
  uploadRef.value?.handleStart(latest)
  evaluationConfig.value.file = latest
  ElMessage.info('已替换为最新选择的评估文件')
}

const handleAbortEvaluation = () => {
  if (!evaluating.value) return
  evalAbortController.value?.abort()
  runtimeLogs.value.push({
    time: formatNowTime(),
    level: 'WARN',
    message: '用户已请求中止评估，正在停止模型推理...'
  })
  ElMessage.warning('已发送中止请求')
}

// 重置
const handleReset = () => {
  evalAbortController.value?.abort()
  currentStep.value = -1
  runtimeLogs.value = []
  cotStreamText.value = ''
  cotCollapseActive.value = ['realtime-cot']
  evalSteps.value = []
  evaluationResult.value = null
  evaluationConfig.value = {
    model: '',
    file: null
  }
  uploadRef.value?.clearFiles()
}

// 清空日志
const handleClearLogs = () => {
  runtimeLogs.value = []
  cotStreamText.value = ''
  ElMessage.success('日志已清空')
}

// 导出日志
const handleExportLogs = () => {
  if (runtimeLogs.value.length === 0 && !cotStreamText.value) {
    ElMessage.warning('没有可导出的日志')
    return
  }

  const logText = [
    ...runtimeLogs.value.map(
      (log) => `[${log.time}] [${log.level}] ${log.message}`
    ),
    cotStreamText.value ? `\n--- CoT ---\n${cotStreamText.value}` : ''
  ].join('\n')
  
  const blob = new Blob([logText], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `cot_logs_${Date.now()}.txt`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('日志导出成功')
}
</script>

<style scoped>
.evaluation-tracker {
  height: calc(100vh - 120px);
  overflow: hidden;
}

.main-layout {
  height: 100%;
}

.left-panel,
.center-panel,
.right-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.control-card,
.state-machine-card,
.log-card,
.result-card {
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  border: 1px solid #e0e0e0;
  margin-bottom: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.control-card :deep(.el-card__body),
.state-machine-card :deep(.el-card__body),
.log-card :deep(.el-card__body),
.result-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
  color: #2c3e50;
  font-size: var(--ui-font-body);
}

.card-header .el-icon {
  color: #5a7ba7;
  font-size: var(--el-font-size-medium);
}

.control-form {
  flex: 1;
  overflow: hidden;
}

.control-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.control-form :deep(.el-form-item__label) {
  color: #555;
  font-size: var(--ui-font-caption);
  font-weight: 500;
}

.upload-tip {
  margin-top: 6px;
  color: #7f8c8d;
  font-size: var(--el-font-size-extra-small);
}

.steps-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.steps-container :deep(.el-steps) {
  padding: 0;
}

.steps-container :deep(.el-step__title) {
  font-size: var(--ui-font-caption);
  color: #2c3e50;
  font-weight: 500;
}

.steps-container :deep(.el-step__description) {
  font-size: var(--el-font-size-extra-small);
  color: #7f8c8d;
  margin-top: 4px;
}

.steps-container :deep(.el-step__icon) {
  width: 28px;
  height: 28px;
  font-size: var(--ui-font-body);
}

.steps-container :deep(.el-step__head.is-process .el-step__icon) {
  color: #5a7ba7;
  border-color: #5a7ba7;
}

.steps-container :deep(.el-step__head.is-success .el-step__icon) {
  color: #4a90a4;
  border-color: #4a90a4;
}

.eval-console {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7f9;
  color: #2c3e50;
  font-size: var(--ui-font-caption);
  font-weight: 600;
  border-bottom: 1px solid #e0e0e0;
}

.console-header .el-icon {
  color: #5a7ba7;
}

.spinning {
  animation: eval-spin 1s linear infinite;
}

@keyframes eval-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.eval-log-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
  background: #ffffff;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-log);
  line-height: 1.65;
}

.eval-log-content .log-time {
  color: #5a7ba7;
  margin-right: 6px;
  font-weight: 500;
}

.eval-log-content .log-line.log-level-info {
  color: #555;
}

.eval-log-content .log-line.log-level-success {
  color: #3d7a8c;
  background: #f0f7f9;
  padding: 4px 8px;
  border-radius: 2px;
  border-left: 3px solid #4a90a4;
}

.eval-log-content .log-line.log-level-warn {
  color: #8a6d3b;
  background: #fefbf3;
  padding: 4px 8px;
  border-radius: 2px;
  border-left: 3px solid #c9a961;
}

.eval-log-content .log-line.log-level-error {
  color: #a94442;
  background: #fef5f5;
  padding: 4px 8px;
  border-radius: 2px;
  border-left: 3px solid #c85a5a;
}

.log-line {
  margin-bottom: 6px;
  word-wrap: break-word;
}

.log-cursor {
  color: #5a7ba7;
  animation: eval-blink 1s step-end infinite;
}

@keyframes eval-blink {
  50% {
    opacity: 0;
  }
}

.cot-stream-block {
  margin-top: 12px;
  padding: 10px 12px;
  background: #f8f9fa;
  border: 1px solid #e8ecef;
  border-radius: 3px;
  border-left: 3px solid #5a7ba7;
}

.cot-stream-label {
  font-size: var(--el-font-size-extra-small);
  color: #5a7ba7;
  margin-bottom: 8px;
  font-weight: 600;
}

.cot-stream-text {
  margin: 0;
  color: #2c3e50;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  font-size: inherit;
  line-height: 1.7;
}

.log-empty {
  padding: 8px 0;
}

.example-title {
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
  color: #5a7ba7;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e0e0e0;
}

.example-text {
  margin: 0;
  color: #555;
  font-size: var(--ui-font-caption);
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
}

.result-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.result-summary {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 3px;
  margin-bottom: 12px;
  border: 1px solid #e0e0e0;
}

.summary-title {
  font-size: var(--el-font-size-medium);
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 6px;
}

.summary-desc {
  color: #555;
  font-size: var(--el-font-size-extra-small);
  line-height: 1.5;
}

.metrics-list {
  margin-bottom: 12px;
}

.metric-item {
  padding: 10px;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  margin-bottom: 8px;
  text-align: center;
}

.metric-label {
  font-size: var(--el-font-size-extra-small);
  color: #7f8c8d;
  margin-bottom: 6px;
  font-weight: 500;
}

.metric-value {
  font-size: var(--el-font-size-medium);
  font-weight: 600;
  color: #2c3e50;
}

.record-preview {
  font-size: var(--el-font-size-extra-small);
  font-weight: 500;
}

.metric-score {
  margin-top: 6px;
  color: #5a7ba7;
  font-size: var(--el-font-size-extra-small);
}

.record-collapse {
  margin-top: 8px;
  text-align: left;
}

.record-analysis {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--ui-font-log);
  line-height: 1.6;
  color: #2c3e50;
}

.metric-value.excellent {
  color: #4a90a4;
}

.metric-value.good {
  color: #5a7ba7;
}

.metric-value.fair {
  color: #c9a961;
}

.metric-value.poor {
  color: #c85a5a;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.empty-text {
  color: #999;
  font-size: var(--ui-font-caption);
  text-align: center;
}

/* Element Plus 组件样式覆盖 */
:deep(.el-card__header) {
  padding: 10px 12px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

:deep(.el-select),
:deep(.el-button) {
  font-size: var(--el-font-size-base);
}

:deep(.el-form-item__label) {
  font-size: var(--ui-font-caption);
}

:deep(.el-input__inner),
:deep(.el-select__placeholder) {
  font-size: var(--el-font-size-base);
}

/* 滚动条样式 */
.eval-log-content::-webkit-scrollbar,
.result-content::-webkit-scrollbar,
.steps-container::-webkit-scrollbar {
  width: 6px;
}

.eval-log-content::-webkit-scrollbar-track,
.result-content::-webkit-scrollbar-track,
.steps-container::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 3px;
}

.eval-log-content::-webkit-scrollbar-thumb,
.result-content::-webkit-scrollbar-thumb,
.steps-container::-webkit-scrollbar-thumb {
  background: #c0c0c0;
  border-radius: 3px;
}

.eval-log-content::-webkit-scrollbar-thumb:hover,
.result-content::-webkit-scrollbar-thumb:hover,
.steps-container::-webkit-scrollbar-thumb:hover {
  background: #a0a0a0;
}
</style>
