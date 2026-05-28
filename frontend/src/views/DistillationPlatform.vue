<template>
  <div class="distillation-platform">
    <div class="platform-header">
      <h1 class="page-title">思维链数据蒸馏与模型微调平台</h1>
      <p class="page-subtitle">CoT Distillation & Fine-tuning Platform</p>
    </div>

    <div class="platform-container">
      <!-- 左侧栏：教师模型推理数据构建区 -->
      <div class="left-panel">
        <el-card class="workflow-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="step-index-ring" aria-label="步骤 1">1</span>
              <div class="step-heading">
                <span class="step-kicker">STEP 01</span>
                <h2 class="step-title">教师模型推理数据构建</h2>
              </div>
            </div>
          </template>

          <el-form :model="teacherForm" label-position="top" class="distillation-form">
            <!-- 教师模型选择 -->
            <el-form-item label="教师模型选择 (Teacher Model)" required>
              <el-select
                v-model="teacherForm.teacherModel"
                placeholder="请选择教师模型"
                style="width: 100%"
                size="large"
              >
                <el-option
                  v-for="model in teacherModels"
                  :key="model.value"
                  :label="model.label"
                  :value="model.value"
                />
              </el-select>
            </el-form-item>

            <!-- 训练数据集选择 -->
            <el-form-item label="训练数据集选择 (Training Dataset)" required>
              <el-select
                v-model="teacherForm.trainingDataset"
                placeholder="请选择训练数据集"
                style="width: 100%"
                size="large"
              >
                <el-option
                  v-for="dataset in trainingDatasets"
                  :key="dataset.value"
                  :label="dataset.label"
                  :value="dataset.value"
                />
              </el-select>
              <div class="dataset-actions">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  accept=".csv"
                  :on-change="handleTrainingDatasetFileChange"
                >
                  <el-button size="small">上传训练 CSV</el-button>
                </el-upload>
                <el-button type="primary" link size="small" @click="handleDownloadTrainingTemplate">
                  下载 CSV 模板
                </el-button>
              </div>
            </el-form-item>

            <!-- 指导指令输入 -->
            <el-form-item label="指导指令输入 (System Instruction)" required>
              <el-input
                v-model="teacherForm.instruction"
                type="textarea"
                :rows="14"
                placeholder="请输入系统级指导指令..."
                class="instruction-textarea"
              />
            </el-form-item>

            <!-- 操作按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="generating"
                @click="handleGenerateDistillationData"
                class="action-button"
              >
                <el-icon><Promotion /></el-icon>
                <span>一键生成蒸馏数据集 (Generate Distillation Data)</span>
              </el-button>
            </el-form-item>

            <!-- 状态反馈区 -->
            <el-form-item v-if="generationComplete">
              <el-progress :percentage="100" :status="'success'" />
              <div class="status-info status-info--clickable" @click="openReviewDialog">
                <el-icon class="success-icon"><CircleCheck /></el-icon>
                <span>成功合成 {{ generatedDataCount }} 条高质量 CoT 轨迹数据</span>
                <el-button type="primary" link class="review-link">查看并校对</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 中间连接线 -->
      <div class="middle-connector">
        <div class="connector-line"></div>
        <el-icon class="connector-arrow"><ArrowRight /></el-icon>
        <div class="connector-line"></div>
      </div>

      <!-- 右侧栏：学生模型蒸馏区 -->
      <div class="right-panel">
        <el-card class="workflow-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="step-index-ring" aria-label="步骤 2">2</span>
              <div class="step-heading">
                <span class="step-kicker">STEP 02</span>
                <h2 class="step-title">轻量级模型 LoRA 参数高效微调</h2>
              </div>
            </div>
          </template>

          <el-form :model="studentForm" label-position="top" class="distillation-form">
            <!-- 基座模型选择 -->
            <el-form-item label="基座模型选择 (Base Model)" required>
              <el-select
                v-model="studentForm.baseModel"
                placeholder="请选择基座模型"
                style="width: 100%"
                size="large"
              >
                <el-option
                  v-for="model in baseModels"
                  :key="model.value"
                  :label="model.label"
                  :value="model.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="微调训练数据集 (Fine-tuning Dataset)" required>
              <el-select
                v-model="selectedFinetuneDatasetPath"
                placeholder="请选择微调训练数据集"
                style="width: 100%"
                size="large"
              >
                <el-option
                  v-for="item in finetuneDatasetOptions"
                  :key="item.path"
                  :label="formatFinetuneDatasetLabel(item)"
                  :value="item.path"
                />
              </el-select>
              <div class="dataset-actions">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  accept=".jsonl"
                  :on-change="handleFinetuneDatasetFileChange"
                >
                  <el-button size="small">上传微调 JSONL</el-button>
                </el-upload>
              </div>
            </el-form-item>

            <!-- 超参数配置面板 -->
            <div class="hyperparams-panel">
              <!-- LoRA 参数组 -->
              <div class="param-group">
                <div class="param-group-title">LoRA 参数组</div>
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="Rank (r)">
                      <el-input-number
                        v-model="studentForm.loraRank"
                        :min="1"
                        :max="512"
                        :step="8"
                        style="width: 100%"
                        size="large"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="Alpha">
                      <el-input-number
                        v-model="studentForm.loraAlpha"
                        :min="1"
                        :max="1024"
                        :step="8"
                        style="width: 100%"
                        size="large"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="Dropout">
                      <el-input-number
                        v-model="studentForm.loraDropout"
                        :min="0"
                        :max="1"
                        :step="0.01"
                        :precision="2"
                        style="width: 100%"
                        size="large"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>

              <!-- 训练参数组 -->
              <div class="param-group">
                <div class="param-group-title">训练参数组</div>
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="Epoch">
                      <el-input-number
                        v-model="studentForm.epoch"
                        :min="1"
                        :max="100"
                        style="width: 100%"
                        size="large"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="Batch Size">
                      <el-input-number
                        v-model="studentForm.batchSize"
                        :min="1"
                        :max="32"
                        style="width: 100%"
                        size="large"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="Learning Rate">
                      <el-select
                        v-model="studentForm.learningRate"
                        style="width: 100%"
                        size="large"
                      >
                        <el-option
                          v-for="rate in learningRates"
                          :key="rate"
                          :label="rate"
                          :value="rate"
                        />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
              </div>
            </div>

            <!-- 操作按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="training"
                :disabled="!canStartFinetune"
                @click="handleStartFineTuning"
                class="action-button"
              >
                <el-icon><VideoPlay /></el-icon>
                <span>启动 LoRA 微调训练 (Start Fine-tuning)</span>
              </el-button>
              <p v-if="trainingDatasetInfo?.filename" class="finetune-dataset-hint">
                训练数据：{{ formatFinetuneDatasetLabel(trainingDatasetInfo) }}
              </p>
              <p v-else class="finetune-dataset-hint finetune-dataset-hint--warn">
                请先选择或上传可用的微调 JSONL 数据集
              </p>
            </el-form-item>

            <!-- 微调完成提示 -->
            <el-form-item v-if="trainingComplete">
              <div class="status-info status-info--clickable" @click="openSaveModelDialog">
                <el-icon class="success-icon"><CircleCheck /></el-icon>
                <span>LoRA 微调已完成，点击配置模型名称并保存</span>
                <el-button type="primary" link class="review-link">保存模型</el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>

  <!-- LoRA 微调流程与日志 -->
  <el-dialog
    v-model="finetuneProgressVisible"
    class="cot-generation-dialog finetune-progress-dialog"
    width="780px"
    align-center
    :close-on-click-modal="false"
    :close-on-press-escape="!training"
    :show-close="!training"
    @closed="resetFinetuneProgress"
  >
    <template #header>
      <div class="generation-dialog-header">
        <span class="generation-dialog-title">LoRA 微调训练中</span>
        <span class="generation-dialog-subtitle">Parameter-Efficient Fine-Tuning Pipeline</span>
      </div>
    </template>

    <div class="generation-dialog-body">
      <el-steps
        :active="finetuneActiveStep"
        direction="vertical"
        finish-status="success"
        process-status="process"
        class="generation-steps"
      >
        <el-step
          v-for="(step, index) in finetuneSteps"
          :key="index"
          :title="step.title"
          :description="step.description"
          :status="step.status"
        />
      </el-steps>

      <div class="generation-console">
        <div class="console-header">
          <span>训练日志 (Training Log)</span>
          <el-icon v-if="training" class="spinning"><Loading /></el-icon>
        </div>
        <div ref="finetuneLogRef" class="console-content generation-log-content">
          <div
            v-for="(line, index) in finetuneLogs"
            :key="index"
            :class="['log-line', `log-level-${line.level.toLowerCase()}`]"
          >
            <span v-if="line.time" class="log-time">[{{ line.time }}]</span>
            {{ line.message }}
          </div>
          <div v-if="training" class="log-line log-cursor">_</div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="generation-dialog-footer">
        <el-button v-if="training" size="large" @click="handleCancelFinetune">中止</el-button>
        <el-button v-else type="primary" size="large" @click="finetuneProgressVisible = false">
          {{ finetuneFailed ? '关闭' : '完成' }}
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- 微调完成：命名与保存 -->
  <el-dialog
    v-model="saveModelDialogVisible"
    class="cot-review-dialog save-model-dialog"
    width="520px"
    align-center
    :close-on-click-modal="false"
    @closed="resetSaveModelDialog"
  >
    <template #header>
      <div class="review-dialog-header">
        <span class="review-dialog-title">保存微调模型</span>
        <span class="review-dialog-subtitle">登记至评估库并可选用</span>
      </div>
    </template>

    <el-form label-position="top" class="save-model-form">
      <el-form-item label="模型显示名称" required>
        <el-input
          v-model="publishModelName"
          placeholder="例如：Qwen2.5-7B-Instruct-CoT-LoRA"
          size="large"
        />
      </el-form-item>
      <el-alert
        v-if="finetuneResult?.checkpoint"
        type="info"
        :closable="false"
        show-icon
        class="checkpoint-alert"
        :title="`权重路径：${finetuneResult.checkpoint}`"
      />
      <div class="export-note save-model-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>保存后将同步至「思维链评估可视化追踪室」模型列表</span>
      </div>
    </el-form>

    <template #footer>
      <div class="review-dialog-footer">
        <el-button size="large" @click="handleSaveModelCancel">取消</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="publishingModel"
          @click="handleSaveModelConfirm"
        >
          <el-icon><DocumentAdd /></el-icon>
          保存
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- CoT 生成流程与日志 -->
  <el-dialog
    v-model="generationProgressVisible"
    class="cot-generation-dialog"
    width="780px"
    align-center
    :close-on-click-modal="false"
    :close-on-press-escape="!generating"
    :show-close="!generating"
    @closed="resetGenerationProgress"
  >
    <template #header>
      <div class="generation-dialog-header">
        <span class="generation-dialog-title">CoT 数据集生成中</span>
        <span class="generation-dialog-subtitle">Chain-of-Thought Distillation Pipeline</span>
      </div>
    </template>

    <div class="generation-dialog-body">
      <el-steps
        :active="generationActiveStep"
        direction="vertical"
        finish-status="success"
        process-status="process"
        class="generation-steps"
      >
        <el-step
          v-for="(step, index) in generationSteps"
          :key="index"
          :title="step.title"
          :description="step.description"
          :status="step.status"
        />
      </el-steps>

      <div class="generation-console">
        <div class="console-header">
          <span>运行日志 (Runtime Log)</span>
          <el-icon v-if="generating" class="spinning"><Loading /></el-icon>
        </div>
        <div ref="generationLogRef" class="console-content generation-log-content">
          <div
            v-for="(line, index) in generationLogs"
            :key="index"
            :class="['log-line', `log-level-${line.level.toLowerCase()}`]"
          >
            <span v-if="line.time" class="log-time">[{{ line.time }}]</span>
            {{ line.message }}
          </div>
          <div v-if="generating" class="log-line log-cursor">_</div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="generation-dialog-footer">
        <el-button
          v-if="generating"
          size="large"
          @click="handleCancelGeneration"
        >
          中止
        </el-button>
        <el-button
          v-else
          type="primary"
          size="large"
          @click="generationProgressVisible = false"
        >
          {{ generationFailed ? '关闭' : '完成' }}
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- CoT 数据预览与校对弹窗 -->
  <el-dialog
    v-model="reviewDialogVisible"
    class="cot-review-dialog"
    width="920px"
    align-center
    destroy-on-close
    :close-on-click-modal="false"
    @closed="handleReviewDialogClosed"
  >
    <template #header>
      <div class="review-dialog-header">
        <span class="review-dialog-title">CoT 蒸馏数据预览与校对</span>
        <span class="review-dialog-subtitle">
          数据集共 {{ generatedDataCount }} 条 · 预览 {{ cotSamples.length }} 条 · 校对后请保存
          <template v-if="sampleTotalPages > 1">
            · 第 {{ samplePage }} / {{ sampleTotalPages }} 页
          </template>
        </span>
      </div>
    </template>

    <div class="review-dialog-body">
      <div class="sample-nav">
        <div class="sample-nav-title">样本列表</div>
        <el-scrollbar class="sample-nav-scroll">
          <button
            v-for="sample in pagedCotSamples"
            :key="sample.id"
            type="button"
            :class="['sample-nav-item', { active: sample.id === activeSampleId }]"
            @click="selectSample(sample.id)"
          >
            <span class="sample-nav-index">#{{ sample.id }}</span>
            <span class="sample-nav-score">{{ sample.verified_score }}</span>
          </button>
        </el-scrollbar>
        <div v-if="sampleTotalPages > 1" class="sample-nav-pagination">
          <el-button
            size="small"
            :disabled="samplePage <= 1"
            @click="goSamplePrevPage"
          >
            上一页
          </el-button>
          <span class="sample-nav-page-info">{{ samplePage }} / {{ sampleTotalPages }}</span>
          <el-button
            size="small"
            type="primary"
            :disabled="samplePage >= sampleTotalPages"
            @click="goSampleNextPage"
          >
            下一页
          </el-button>
        </div>
      </div>

      <div v-if="activeSample" class="sample-editor">
        <el-form label-position="top" class="sample-editor-form">
          <el-row :gutter="16">
            <el-col :span="12">
            <el-form-item label="工艺上下文 (Context)">
                <el-input
                  v-model="activeSample.context"
                  type="textarea"
                  :rows="3"
                  resize="vertical"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Verified Score">
                <el-input v-model="activeSample.verified_score" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="AI 预测 (Prediction)">
            <el-input
              v-model="activeSample.ai_prediction"
              type="textarea"
              :rows="2"
              resize="vertical"
            />
          </el-form-item>
          <el-form-item label="思维链轨迹 (CoT Trace)" required>
            <el-input
              v-model="activeSample.cot_trace"
              type="textarea"
              :rows="10"
              class="cot-trace-input"
              resize="vertical"
              placeholder="可在此修改 Step 1–4 推理轨迹..."
            />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template #footer>
      <div class="review-dialog-footer">
        <el-button size="large" @click="handleDownloadCotDataset">下载 CoT 数据集</el-button>
        <el-button size="large" @click="handleReviewCancel">取消</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="saving"
          @click="handleSaveDataset"
        >
          <el-icon><DocumentAdd /></el-icon>
          保存
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Promotion,
  ArrowRight,
  VideoPlay,
  Loading,
  DocumentAdd,
  CircleCheck,
  InfoFilled,
} from '@element-plus/icons-vue'
import {
  distillationService,
  finetuneService,
  type FinetuneRunResponse,
  type GenerationLogLine,
  type GenerationStepState
} from '@/services/distillationService'
import type {
  DistillationCotSample,
  DistillationGenerateResponse,
  FinetuneTrainingDataset,
  SelectOption
} from '@/types/api'

const teacherForm = reactive({
  teacherModel: '',
  trainingDataset: '',
  instruction: ''
})

const studentForm = reactive({
  baseModel: '',
  loraRank: 64,
  loraAlpha: 128,
  loraDropout: 0.05,
  epoch: 3,
  batchSize: 1,
  learningRate: '2e-5',
  modelName: ''
})

const teacherModels = ref<SelectOption[]>([])
const trainingDatasets = ref<SelectOption[]>([])
const baseModels = ref<SelectOption[]>([])
const learningRates = ref<string[]>([])
const trainingDatasetInfo = ref<FinetuneTrainingDataset | null>(null)
const finetuneDatasetOptions = ref<FinetuneTrainingDataset[]>([])
const selectedFinetuneDatasetPath = ref('')

const canStartFinetune = computed(
  () => Boolean(selectedFinetuneDatasetPath.value) && Boolean(trainingDatasetInfo.value?.sample_count)
)

onMounted(async () => {
  try {
    const [distillOpts, finetuneOpts] = await Promise.all([
      distillationService.getOptions(),
      finetuneService.getOptions()
    ])
    teacherModels.value = distillOpts.teacher_models
    trainingDatasets.value = distillOpts.training_datasets
    teacherForm.trainingDataset =
      distillOpts.default_training_dataset || distillOpts.training_datasets[0]?.value || 'lp-param'
    teacherForm.instruction = distillOpts.default_instruction
    baseModels.value = finetuneOpts.base_models
    learningRates.value = finetuneOpts.learning_rates
    finetuneDatasetOptions.value = finetuneOpts.training_datasets ?? []
    selectedFinetuneDatasetPath.value =
      finetuneOpts.default_training_dataset || finetuneOpts.training_dataset?.path || ''
    trainingDatasetInfo.value =
      finetuneDatasetOptions.value.find((item) => item.path === selectedFinetuneDatasetPath.value) ??
      finetuneOpts.training_dataset ??
      null
    Object.assign(studentForm, finetuneOpts.defaults)
  } catch {
    ElMessage.warning('蒸馏平台配置加载失败，请确认已登录且后端服务已启动')
  }
})

// 状态管理
const generating = ref(false)
const generationComplete = ref(false)
const generatedDataCount = ref(0)
const generationProgressVisible = ref(false)
const generationSteps = ref<GenerationStepState[]>([])
const generationLogs = ref<GenerationLogLine[]>([])
const generationLogRef = ref<HTMLElement | null>(null)
const generationFailed = ref(false)
const generationAbortController = ref<AbortController | null>(null)

const generationActiveStep = computed(() => {
  const processing = generationSteps.value.findIndex((s) => s.status === 'process')
  if (processing >= 0) return processing
  const finished = generationSteps.value.filter((s) => s.status === 'finish').length
  return Math.min(finished, Math.max(0, generationSteps.value.length - 1))
})

const reviewDialogVisible = ref(false)
const SAMPLE_PAGE_SIZE = 10
const cotSamples = ref<DistillationCotSample[]>([])
const samplePage = ref(1)
const activeSampleId = ref(1)
const saving = ref(false)

const sampleTotalPages = computed(() =>
  Math.max(1, Math.ceil(cotSamples.value.length / SAMPLE_PAGE_SIZE))
)

const pagedCotSamples = computed(() => {
  const start = (samplePage.value - 1) * SAMPLE_PAGE_SIZE
  return cotSamples.value.slice(start, start + SAMPLE_PAGE_SIZE)
})

const activeSample = computed(() =>
  cotSamples.value.find((s) => s.id === activeSampleId.value) ?? null
)

watch(selectedFinetuneDatasetPath, (path) => {
  const selected = finetuneDatasetOptions.value.find((item) => item.path === path)
  if (selected) {
    trainingDatasetInfo.value = selected
  }
})

function formatFinetuneDatasetLabel(item: FinetuneTrainingDataset | null | undefined): string {
  if (!item?.filename) return '未命名数据集'
  const filename = item.filename
  const stamp = filename.match(/(\d{8}_\d{6})/)
  const stem = filename.replace(/\.(jsonl|csv)$/i, '')

  const compactName = (raw: string): string => {
    const cleaned = raw.replace(/^[\W_]+|[\W_]+$/g, '')
    if (!cleaned) return '默认'
    return cleaned.length > 18 ? `${cleaned.slice(0, 18)}…` : cleaned
  }

  if (filename.startsWith('finetune_upload_')) {
    const namePart = stem
      .replace(/^finetune_upload_/, '')
      .replace(/_\d{8}_\d{6}$/, '')
    const title = compactName(namePart)
    return stamp ? `上传数据集 ${title} ${stamp[1]}` : `上传数据集 ${title}`
  }
  if (filename.startsWith('finetune_')) {
    const namePart = stem
      .replace(/^finetune_/, '')
      .replace(/_\d{8}_\d{6}$/, '')
    const title = compactName(namePart)
    return stamp ? `蒸馏数据集 ${title} ${stamp[1]}` : `蒸馏数据集 ${title}`
  }
  return compactName(stem)
}

const training = ref(false)
const trainingComplete = ref(false)
const finetuneProgressVisible = ref(false)
const finetuneSteps = ref<GenerationStepState[]>([])
const finetuneLogs = ref<GenerationLogLine[]>([])
const finetuneLogRef = ref<HTMLElement | null>(null)
const finetuneFailed = ref(false)
const finetuneAbortController = ref<AbortController | null>(null)
const finetuneResult = ref<FinetuneRunResponse | null>(null)

const saveModelDialogVisible = ref(false)
const publishModelName = ref('')
const publishingModel = ref(false)

const finetuneActiveStep = computed(() => {
  const processing = finetuneSteps.value.findIndex((s) => s.status === 'process')
  if (processing >= 0) return processing
  const finished = finetuneSteps.value.filter((s) => s.status === 'finish').length
  return Math.min(finished, Math.max(0, finetuneSteps.value.length - 1))
})

function cloneSamples(samples: DistillationCotSample[]): DistillationCotSample[] {
  return samples.map((s) => ({ ...s }))
}

async function refreshTrainingDatasetInfo() {
  try {
    const finetuneOpts = await finetuneService.getOptions()
    finetuneDatasetOptions.value = finetuneOpts.training_datasets ?? []
    if (
      !selectedFinetuneDatasetPath.value &&
      (finetuneOpts.default_training_dataset || finetuneOpts.training_dataset?.path)
    ) {
      selectedFinetuneDatasetPath.value =
        finetuneOpts.default_training_dataset || finetuneOpts.training_dataset?.path || ''
    }
    const selected = finetuneDatasetOptions.value.find(
      (item) => item.path === selectedFinetuneDatasetPath.value
    )
    trainingDatasetInfo.value = selected ?? finetuneOpts.training_dataset ?? null
  } catch {
    /* 忽略刷新失败 */
  }
}

function setCotSamples(samples: DistillationCotSample[]) {
  cotSamples.value = cloneSamples(samples)
  samplePage.value = 1
  activeSampleId.value = samples[0]?.id ?? 1
}

function focusSampleOnCurrentPage() {
  const onPage = pagedCotSamples.value.some((s) => s.id === activeSampleId.value)
  if (!onPage && pagedCotSamples.value.length) {
    activeSampleId.value = pagedCotSamples.value[0].id
  }
}

function goSampleNextPage() {
  if (samplePage.value >= sampleTotalPages.value) return
  samplePage.value += 1
  focusSampleOnCurrentPage()
}

function goSamplePrevPage() {
  if (samplePage.value <= 1) return
  samplePage.value -= 1
  focusSampleOnCurrentPage()
}

function openReviewDialog() {
  if (!cotSamples.value.length) return
  samplePage.value = 1
  focusSampleOnCurrentPage()
  reviewDialogVisible.value = true
}

function selectSample(id: number) {
  activeSampleId.value = id
}

function handleReviewDialogClosed() {
  samplePage.value = 1
}

function handleReviewCancel() {
  reviewDialogVisible.value = false
}

function handleDownloadCotDataset() {
  if (!cotSamples.value.length) {
    ElMessage.warning('暂无可下载的 CoT 数据')
    return
  }
  const lines = cotSamples.value.map((s) =>
    JSON.stringify(
      {
        id: s.id,
        context: s.context,
        ai_prediction: s.ai_prediction,
        verified_score: s.verified_score,
        cot_trace: s.cot_trace
      },
      null,
      0
    )
  )
  const blob = new Blob([`${lines.join('\n')}\n`], { type: 'application/jsonl;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const ts = new Date()
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\..+/, '')
  const filename = `cot_edited_${teacherForm.trainingDataset || 'dataset'}_${ts}.jsonl`
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  ElMessage.success('CoT 数据集已下载')
}

async function handleSaveDataset() {
  if (!cotSamples.value.length) {
    ElMessage.warning('暂无可保存的样本数据')
    return
  }
  const emptyTrace = cotSamples.value.some((s) => !s.cot_trace?.trim())
  if (emptyTrace) {
    ElMessage.warning('思维链轨迹不能为空')
    return
  }

  saving.value = true
  try {
    const res = await distillationService.saveDataset({
      teacherModel: teacherForm.teacherModel,
      trainingDataset: teacherForm.trainingDataset,
      samples: cotSamples.value.map((s) => ({
        id: s.id,
        context: s.context,
        aiPrediction: s.ai_prediction,
        verifiedScore: s.verified_score,
        cotTrace: s.cot_trace
      }))
    })
    reviewDialogVisible.value = false
    await refreshTrainingDatasetInfo()
    ElMessage.success(res.message || '微调数据集已保存')
  } catch {
    ElMessage.error('保存失败，请确认后端服务已启动')
  } finally {
    saving.value = false
  }
}

async function handleTrainingDatasetFileChange(uploadFile: any) {
  const rawFile = uploadFile?.raw as File | undefined
  if (!rawFile) return
  try {
    const uploaded = await distillationService.uploadTrainingDataset(rawFile)
    const options = await distillationService.getOptions()
    trainingDatasets.value = options.training_datasets
    teacherForm.trainingDataset = uploaded.dataset.value || teacherForm.trainingDataset
    ElMessage.success('训练 CSV 上传成功')
  } catch {
    ElMessage.error('训练 CSV 上传失败，请检查表头格式')
  }
}

async function handleDownloadTrainingTemplate() {
  try {
    const blob = await distillationService.downloadTrainingTemplate()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'distillation_template.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('模板下载失败')
  }
}

async function handleFinetuneDatasetFileChange(uploadFile: any) {
  const rawFile = uploadFile?.raw as File | undefined
  if (!rawFile) return
  try {
    const res = await finetuneService.uploadTrainingDataset(rawFile)
    await refreshTrainingDatasetInfo()
    selectedFinetuneDatasetPath.value = res.dataset.path
    trainingDatasetInfo.value = res.dataset
    ElMessage.success(res.message || '微调数据上传成功')
  } catch {
    ElMessage.error('微调 JSONL 上传失败，请检查字段 Instruction/Input/Output')
  }
}

function scrollGenerationLog() {
  nextTick(() => {
    const el = generationLogRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function appendGenerationLog(line: GenerationLogLine) {
  generationLogs.value.push(line)
  scrollGenerationLog()
}

function mapStepStatus(status: string): GenerationStepState['status'] {
  if (status === 'process') return 'process'
  if (status === 'finish') return 'finish'
  if (status === 'error') return 'error'
  return 'wait'
}

function resetGenerationProgress() {
  generationSteps.value = []
  generationLogs.value = []
  generationFailed.value = false
  generationAbortController.value = null
}

function handleCancelGeneration() {
  if (!generationAbortController.value) return
  generationAbortController.value.abort()
  appendGenerationLog({ time: '', level: 'WARN', message: '>>> 正在中止，请等待当前 API 请求结束…' })
}

function applyGenerationResult(res: DistillationGenerateResponse) {
  generatedDataCount.value = res.sample_count
  if (res.samples?.length) {
    setCotSamples(res.samples)
  }
  generationComplete.value = true
}

// 生成蒸馏数据集（流式日志 + 步骤）
const handleGenerateDistillationData = async () => {
  if (!teacherForm.teacherModel || !teacherForm.trainingDataset) {
    ElMessage.warning('请先选择教师模型')
    return
  }
  if (generating.value) {
    ElMessage.warning('已有生成任务在进行中')
    return
  }

  generating.value = true
  generationComplete.value = false
  generationFailed.value = false
  cotSamples.value = []
  generationLogs.value = []
  generationSteps.value = []
  generationProgressVisible.value = true

  const controller = new AbortController()
  generationAbortController.value = controller

  appendGenerationLog({ time: '', level: 'INFO', message: '>>> 启动 CoT 蒸馏数据集生成流水线…' })

  try {
    const res = await distillationService.generateDatasetStream(
      {
        teacherModel: teacherForm.teacherModel,
        trainingDataset: teacherForm.trainingDataset,
        instruction: teacherForm.instruction
      },
      {
        onStepInit: (steps) => {
          generationSteps.value = steps.map((s) => ({
            title: s.title,
            description: s.description,
            status: 'wait'
          }))
        },
        onStep: (index, status) => {
          if (generationSteps.value[index]) {
            generationSteps.value[index].status = mapStepStatus(status)
          }
        },
        onLog: (line) => appendGenerationLog(line),
        onDone: (result) => {
          applyGenerationResult(result)
          appendGenerationLog({ time: '', level: 'SUCCESS', message: `>>> ${result.message}` })
          if (result.errors?.length) {
            for (const err of result.errors.slice(0, 5)) {
              appendGenerationLog({ time: '', level: 'WARN', message: err })
            }
          }
        },
        onCancelled: (message) => {
          generationFailed.value = true
          generationComplete.value = false
          appendGenerationLog({ time: '', level: 'WARN', message: `>>> ${message}` })
        },
        onError: (message) => {
          generationFailed.value = true
          generationComplete.value = false
          appendGenerationLog({ time: '', level: 'ERROR', message: `>>> ${message}` })
        }
      },
      controller.signal
    )

    if (res && !generationFailed.value) {
      if (res.errors?.length) {
        ElMessage.warning(res.message || '部分样本生成失败，请查看运行日志')
      } else {
        ElMessage.success(res.message || '蒸馏数据集生成成功')
      }
      setTimeout(() => {
        generationProgressVisible.value = false
        reviewDialogVisible.value = Boolean(res.samples?.length)
      }, 600)
    } else if (!res && !controller.signal.aborted) {
      generationFailed.value = true
      ElMessage.error('生成失败，请查看运行日志')
    }
  } catch (err) {
    if (!controller.signal.aborted) {
      generationFailed.value = true
      generationComplete.value = false
      const msg = err instanceof Error ? err.message : '生成失败'
      appendGenerationLog({ time: '', level: 'ERROR', message: `>>> ${msg}` })
      ElMessage.error('生成失败，请确认后端服务已启动并已登录')
    }
  } finally {
    generating.value = false
    generationAbortController.value = null
  }
}

function scrollFinetuneLog() {
  nextTick(() => {
    const el = finetuneLogRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function appendFinetuneLog(line: GenerationLogLine) {
  finetuneLogs.value.push(line)
  scrollFinetuneLog()
}

function resetFinetuneProgress() {
  finetuneSteps.value = []
  finetuneLogs.value = []
  finetuneFailed.value = false
  finetuneAbortController.value = null
}

function handleCancelFinetune() {
  finetuneAbortController.value?.abort()
  training.value = false
  finetuneFailed.value = true
  appendFinetuneLog({ time: '', level: 'WARN', message: '用户已中止微调任务' })
}

function openSaveModelDialog() {
  if (!finetuneResult.value) return
  publishModelName.value =
    finetuneResult.value.suggested_model_name || studentForm.modelName || ''
  saveModelDialogVisible.value = true
}

function resetSaveModelDialog() {
  publishingModel.value = false
}

function handleSaveModelCancel() {
  saveModelDialogVisible.value = false
}

async function handleSaveModelConfirm() {
  const name = publishModelName.value.trim()
  if (!name) {
    ElMessage.warning('请输入模型名称')
    return
  }
  if (!finetuneResult.value?.checkpoint) {
    ElMessage.warning('缺少 checkpoint 路径')
    return
  }

  publishingModel.value = true
  try {
    await finetuneService.publishModel(name, {
      checkpoint: finetuneResult.value.checkpoint,
      baseModel: studentForm.baseModel
    })
    studentForm.modelName = name
    saveModelDialogVisible.value = false
    ElMessage.success(`模型「${name}」已保存并同步至评估库`)
  } catch {
    ElMessage.error('保存失败，请确认后端服务已启动')
  } finally {
    publishingModel.value = false
  }
}

// 启动 LoRA 微调（流式）
const handleStartFineTuning = async () => {
  if (!studentForm.baseModel) {
    ElMessage.warning('请先选择基座模型')
    return
  }
  await refreshTrainingDatasetInfo()
  if (!selectedFinetuneDatasetPath.value) {
    ElMessage.warning('请先选择微调训练数据集')
    return
  }
  const selected = finetuneDatasetOptions.value.find(
    (item) => item.path === selectedFinetuneDatasetPath.value
  )
  if (!selected?.sample_count) {
    ElMessage.warning('微调数据集为空，请重新保存校对结果')
    return
  }
  trainingDatasetInfo.value = selected

  training.value = true
  trainingComplete.value = false
  finetuneFailed.value = false
  finetuneResult.value = null
  finetuneLogs.value = []
  finetuneSteps.value = []
  finetuneProgressVisible.value = true

  const controller = new AbortController()
  finetuneAbortController.value = controller
  appendFinetuneLog({ time: '', level: 'INFO', message: '>>> 启动 LoRA 微调流水线…' })
  appendFinetuneLog({
    time: '',
    level: 'INFO',
    message: `>>> 将使用训练数据: ${formatFinetuneDatasetLabel(trainingDatasetInfo.value)}`
  })

  try {
    const res = await finetuneService.runFineTuningStream(
      { ...studentForm, trainingDatasetPath: selectedFinetuneDatasetPath.value },
      {
        onStepInit: (steps) => {
          finetuneSteps.value = steps.map((s) => ({
            title: s.title,
            description: s.description,
            status: 'wait'
          }))
        },
        onStep: (index, status) => {
          if (finetuneSteps.value[index]) {
            finetuneSteps.value[index].status = mapStepStatus(status)
          }
        },
        onLog: (line) => appendFinetuneLog(line),
        onDone: (result) => {
          finetuneResult.value = result
          trainingComplete.value = true
          appendFinetuneLog({ time: '', level: 'SUCCESS', message: `>>> ${result.message}` })
        },
        onError: (message) => {
          finetuneFailed.value = true
          appendFinetuneLog({ time: '', level: 'ERROR', message: `>>> ${message}` })
        }
      },
      controller.signal
    )

    if (res && !finetuneFailed.value) {
      await refreshTrainingDatasetInfo()
      ElMessage.success(res.message || 'LoRA 微调完成')
      setTimeout(() => {
        finetuneProgressVisible.value = false
        openSaveModelDialog()
      }, 500)
    } else if (!res && !controller.signal.aborted) {
      finetuneFailed.value = true
      ElMessage.error('微调失败，请查看训练日志')
    }
  } catch (err) {
    if (!controller.signal.aborted) {
      finetuneFailed.value = true
      const msg = err instanceof Error ? err.message : '微调失败'
      appendFinetuneLog({ time: '', level: 'ERROR', message: `>>> ${msg}` })
      ElMessage.error('训练调用失败，请确认后端服务已启动并已登录')
    }
  } finally {
    training.value = false
    finetuneAbortController.value = null
  }
}
</script>

<style scoped>
/* 学术论文风格配色方案 - 参考 IEEE/ACM 期刊 */
.distillation-platform {
  max-width: 1800px;
  margin: 0 auto;
  padding: 0;
  background: #FFFFFF;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
}

.platform-header {
  text-align: center;
  margin-bottom: 22px;
  padding: 10px 0 12px 0;
  border-bottom: 1.5px solid #1A1A1A;
}

.page-title {
  font-size: var(--ui-font-page-title);
  font-weight: 700;
  color: #1A1A1A;
  margin: 0;
  line-height: 1.08;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  letter-spacing: 0.2px;
}

.page-subtitle {
  font-size: var(--el-font-size-extra-small);
  color: #4A4A4A;
  margin: -0.12em 0 0 0;
  line-height: 1.15;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  font-weight: 400;
  letter-spacing: 0.5px;
  font-style: italic;
}

.platform-container {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.left-panel,
.right-panel {
  flex: 1;
  min-width: 0;
}

.middle-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  min-width: 56px;
  margin-top: 100px;
}

.connector-line {
  width: 1.5px;
  height: 50px;
  background: #808080;
}

.connector-arrow {
  font-size: var(--el-font-size-extra-large);
  color: var(--primary-color);
  margin: 10px 0;
  font-weight: 500;
}

.workflow-card {
  border: 1px solid #e2e5ea;
  border-radius: 2px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.workflow-card :deep(.el-card__header) {
  padding: 12px 18px 12px 16px;
  border-bottom: 1px solid #e8eaee;
  background: linear-gradient(180deg, #fbfcfd 0%, #f6f7f9 100%);
}

.workflow-card :deep(.el-card__body) {
  padding: 28px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 论文系统结构图常见：线框序号 + 小号阶段标签 + 主标题 */
.step-index-ring {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1.5px solid #9aa3af;
  background: #ffffff;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  line-height: 1;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.step-heading {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  text-align: left;
}

.step-kicker {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #6b7280;
  text-transform: uppercase;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.2;
}

.step-title {
  margin: 0;
  font-size: var(--ui-font-body);
  font-weight: 600;
  color: #1a1d24;
  font-family: 'Times New Roman', 'STSong', 'SimSun', serif;
  letter-spacing: 0.02em;
  line-height: 1.35;
}

.distillation-form {
  width: 100%;
}

.distillation-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.dataset-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.distillation-form :deep(.el-form-item__label) {
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 10px;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  line-height: 1.6;
  letter-spacing: 0.1px;
}

.distillation-form :deep(.el-input__inner),
.distillation-form :deep(.el-textarea__inner),
.distillation-form :deep(.el-select .el-input__inner) {
  border-color: #B0B0B0;
  border-width: 1px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-caption);
  line-height: 1.7;
  color: #1A1A1A;
  background: #FFFFFF;
}

.distillation-form :deep(.el-input__inner):focus,
.distillation-form :deep(.el-textarea__inner):focus,
.distillation-form :deep(.el-select .el-input__inner):focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px rgba(107, 174, 214, 0.35);
}

.distillation-form :deep(.el-input__inner):hover,
.distillation-form :deep(.el-textarea__inner):hover {
  border-color: #808080;
}

.instruction-textarea :deep(.el-textarea__inner) {
  resize: vertical;
  min-height: 400px;
  padding: 14px;
  background: #FAFAFA;
  border: 1px solid #B0B0B0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--el-font-size-extra-small);
  line-height: 1.7;
  color: #1A1A1A;
}

/* 主操作区按钮统一尺寸 */
.distillation-form :deep(.action-button) {
  width: 100%;
  height: 46px;
  font-size: var(--ui-font-caption);
  font-weight: 600;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
  border-radius: 4px;
  letter-spacing: 0.2px;
}

/* 主按钮：与「思维链评估」页「开始评估」一致，使用 Element Plus 默认主色 var(--el-color-primary) */
.distillation-form :deep(.action-button .el-icon) {
  margin-right: 6px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 14px 16px;
  background: rgba(107, 174, 214, 0.12);
  border: 1px solid rgba(107, 174, 214, 0.45);
  border-radius: 4px;
  color: var(--primary-dark);
  font-size: var(--el-font-size-extra-small);
  font-weight: 500;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
}

.success-icon {
  font-size: var(--el-font-size-medium);
  color: #006633;
}

.status-info--clickable {
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.status-info--clickable:hover {
  background: rgba(107, 174, 214, 0.18);
  border-color: rgba(107, 174, 214, 0.65);
}

.review-link {
  margin-left: auto;
  font-weight: 600;
  font-size: var(--el-font-size-extra-small);
}

.hyperparams-panel {
  margin: 28px 0;
}

.param-group {
  margin-bottom: 28px;
  padding: 18px;
  background: #F8F8F8;
  border: 1px solid #D0D0D0;
  border-radius: 0;
}

.param-group-title {
  font-size: var(--el-font-size-extra-small);
  font-weight: 700;
  color: #1A1A1A;
  margin-bottom: 18px;
  padding-bottom: 10px;
  border-bottom: 1.5px solid #D0D0D0;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  letter-spacing: 0.2px;
}

.param-group :deep(.el-form-item) {
  margin-bottom: 18px;
}

.param-group :deep(.el-form-item__label) {
  font-size: var(--ui-font-caption);
  font-weight: 600;
  color: #4A4A4A;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
}

.param-group :deep(.el-input-number) {
  width: 100%;
}

.param-group :deep(.el-input-number .el-input__inner) {
  text-align: left;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.training-console {
  width: 100%;
  background: #1A1A1A;
  border: 1.5px solid #404040;
  border-radius: 0;
  overflow: hidden;
  min-height: 400px;
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: #2A2A2A;
  border-bottom: 1.5px solid #404040;
  color: #E0E0E0;
  font-size: var(--ui-font-caption);
  font-weight: 600;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  letter-spacing: 0.2px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.console-content {
  flex: 1;
  padding: 14px 18px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-caption);
  line-height: 1.7;
  color: #D0D0D0;
}

.log-line {
  margin: 3px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: #00CCCC;
  font-weight: 600;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

.export-panel {
  padding: 22px;
  background: rgba(107, 174, 214, 0.1);
  border: 1px solid rgba(107, 174, 214, 0.4);
  border-radius: 4px;
  margin-top: 20px;
}

.export-title {
  font-size: var(--ui-font-body);
  font-weight: 700;
  color: #1A1A1A;
  margin-bottom: 18px;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
  letter-spacing: 0.2px;
}

.export-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
  padding: 14px;
  background: rgba(143, 196, 224, 0.2);
  border: 1px solid rgba(107, 174, 214, 0.45);
  border-radius: 4px;
  color: var(--primary-dark);
  font-size: var(--ui-font-caption);
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
  line-height: 1.6;
}

.export-note .el-icon {
  font-size: var(--el-font-size-base);
  color: var(--primary-color);
  flex-shrink: 0;
}

/* Element Plus 组件样式覆盖 - 学术风格 */
.distillation-form :deep(.el-select) {
  width: 100%;
}

.distillation-form :deep(.el-select .el-input__inner) {
  cursor: pointer;
}

.distillation-form :deep(.el-progress-bar__outer) {
  background-color: #E0E0E0;
  border-radius: 0;
}

.distillation-form :deep(.el-progress-bar__inner) {
  background-color: #006633;
  border-radius: 0;
}

.distillation-form :deep(.el-button--success) {
  background: #006633;
  border-color: #005222;
  color: #FFFFFF;
}

.distillation-form :deep(.el-button--success:hover) {
  background: #005222;
  border-color: #004011;
}

.distillation-form :deep(.el-button.is-disabled) {
  background: #E0E0E0;
  border-color: #C0C0C0;
  color: #808080;
  cursor: not-allowed;
}

/* CoT 生成流程弹窗 */
.cot-generation-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 18px 22px 12px;
  border-bottom: 1px solid #e8eaee;
}

.cot-generation-dialog :deep(.el-dialog__body) {
  padding: 20px 22px 12px;
}

.cot-generation-dialog :deep(.el-dialog__footer) {
  padding: 12px 22px 18px;
  border-top: 1px solid #e8eaee;
}

.generation-dialog-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.generation-dialog-title {
  font-size: var(--ui-font-body);
  font-weight: 700;
  color: #1a1d24;
  font-family: 'Times New Roman', 'STSong', 'SimSun', serif;
}

.generation-dialog-subtitle {
  font-size: var(--el-font-size-extra-small);
  color: #6b7280;
  font-style: italic;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
}

.generation-dialog-body {
  display: flex;
  gap: 20px;
  min-height: 360px;
}

.generation-steps {
  flex: 0 0 220px;
  padding: 8px 12px 8px 4px;
  border: 1px solid #d0d0d0;
  background: #f8f8f8;
}

.generation-steps :deep(.el-step__title) {
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
}

.generation-steps :deep(.el-step__description) {
  font-size: 11px;
  line-height: 1.4;
}

.generation-console {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  border: 1.5px solid #404040;
  border-radius: 0;
  overflow: hidden;
}

.generation-log-content {
  min-height: 300px;
  max-height: 360px;
}

.generation-log-content .log-time {
  color: #7eb8da;
  margin-right: 6px;
}

.generation-log-content .log-level-info {
  color: #d0d0d0;
}

.generation-log-content .log-level-success {
  color: #6ee7a0;
}

.generation-log-content .log-level-warn {
  color: #fbbf24;
}

.generation-log-content .log-level-error {
  color: #f87171;
}

.generation-dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.save-model-dialog :deep(.el-dialog__body) {
  padding: 16px 22px 8px;
}

.save-model-form :deep(.el-form-item__label) {
  font-weight: 600;
  font-size: var(--el-font-size-extra-small);
}

.checkpoint-alert {
  margin-bottom: 12px;
}

.finetune-dataset-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary, #64748b);
}

.finetune-dataset-hint--warn {
  color: var(--el-color-warning);
}

.save-model-hint {
  margin-top: 8px;
}

/* CoT 校对弹窗 */
.cot-review-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 18px 22px 12px;
  border-bottom: 1px solid #e8eaee;
}

.cot-review-dialog :deep(.el-dialog__body) {
  padding: 18px 22px 8px;
}

.cot-review-dialog :deep(.el-dialog__footer) {
  padding: 12px 22px 18px;
  border-top: 1px solid #e8eaee;
}

.review-dialog-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.review-dialog-title {
  font-size: var(--ui-font-body);
  font-weight: 700;
  color: #1a1d24;
  font-family: 'Times New Roman', 'STSong', 'SimSun', serif;
}

.review-dialog-subtitle {
  font-size: var(--el-font-size-extra-small);
  color: #6b7280;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
}

.review-dialog-body {
  display: flex;
  gap: 16px;
  min-height: 420px;
}

.sample-nav {
  flex: 0 0 168px;
  display: flex;
  flex-direction: column;
  border: 1px solid #d0d0d0;
  background: #f8f8f8;
}

.sample-nav-title {
  padding: 12px 14px;
  font-size: var(--el-font-size-extra-small);
  font-weight: 700;
  color: #1a1a1a;
  border-bottom: 1px solid #d0d0d0;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
}

.sample-nav-scroll {
  flex: 1;
  padding: 8px;
}

.sample-nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
  padding: 10px 12px;
  border: 1px solid #d8dce3;
  border-radius: 4px;
  background: #ffffff;
  cursor: pointer;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-caption);
  color: #374151;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.sample-nav-item:hover {
  border-color: rgba(107, 174, 214, 0.65);
}

.sample-nav-item.active {
  border-color: var(--primary-color);
  background: rgba(107, 174, 214, 0.12);
  color: var(--primary-dark);
}

.sample-nav-index {
  font-weight: 600;
}

.sample-nav-score {
  font-size: 11px;
  color: #6b7280;
}

.sample-nav-pagination {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 10px 8px 12px;
  border-top: 1px solid #d0d0d0;
  background: #ffffff;
}

.sample-nav-pagination .el-button {
  width: 100%;
  margin: 0;
}

.sample-nav-page-info {
  text-align: center;
  font-size: 11px;
  color: #6b7280;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
}

.sample-editor {
  flex: 1;
  min-width: 0;
  padding: 4px 2px 0;
}

.sample-editor-form :deep(.el-form-item__label) {
  font-size: var(--el-font-size-extra-small);
  font-weight: 600;
  color: #1a1a1a;
  font-family: 'Times New Roman', 'Arial', 'Helvetica Neue', sans-serif;
}

.sample-editor-form :deep(.el-textarea__inner),
.sample-editor-form :deep(.el-input__inner) {
  border-color: #b0b0b0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--ui-font-caption);
  line-height: 1.65;
}

.cot-trace-input :deep(.el-textarea__inner) {
  min-height: 220px;
  background: #fafafa;
}

.review-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.review-dialog-footer .el-button {
  min-width: 108px;
  font-weight: 600;
}

.review-dialog-footer .el-button .el-icon {
  margin-right: 4px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .platform-container {
    flex-direction: column;
  }

  .middle-connector {
    flex-direction: row;
    margin-top: 0;
    margin: 20px 0;
    min-width: auto;
  }

  .connector-line {
    width: 50px;
    height: 1.5px;
  }

  .connector-arrow {
    transform: rotate(90deg);
    margin: 0 10px;
  }

  .review-dialog-body {
    flex-direction: column;
  }

  .sample-nav {
    flex: none;
    max-height: 180px;
  }

  .generation-dialog-body {
    flex-direction: column;
  }

  .generation-steps {
    flex: none;
    width: 100%;
  }
}
</style>
