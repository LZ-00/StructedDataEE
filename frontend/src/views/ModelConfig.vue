<template>
  <div class="model-config-page">
    <div class="page-header">
      <h1 class="page-title">模型配置管理</h1>
      <p class="page-subtitle">Model Registry — API 远程调用与本地 ModelScope 部署</p>
    </div>

    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="card-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">已注册模型</span>
            <el-tag type="info" size="small">{{ models.length }} 个</el-tag>
          </div>
          <div class="toolbar-right">
            <el-switch
              v-model="showDisabled"
              active-text="显示已禁用"
              inactive-text=""
              @change="loadModels"
            />
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon>
              添加模型
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="loadError"
        type="error"
        :closable="false"
        show-icon
        class="load-error-alert"
      >
        <template #title>{{ loadError }}</template>
        <p class="load-error-hint">请先在项目根目录启动后端：<code>npm run dev:backend</code></p>
        <el-button type="primary" size="small" :loading="loading" @click="retryLoad">重新加载</el-button>
      </el-alert>

      <el-table v-loading="loading" :data="models" stripe class="model-table">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.type === 'api' ? 'warning' : 'success'" size="small">
              {{ row.type === 'api' ? 'API' : '本地' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模型标识 / 路径" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.type === 'api'">{{ row.api_config?.modelId || row.api_config?.model_id }}</span>
            <span v-else>{{ row.resolved_path || row.local_config?.modelId }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :loading="testingId === row.id" @click="handleTest(row)">
              推理检测
            </el-button>
            <el-button
              v-if="row.type === 'local'"
              link
              type="primary"
              :loading="downloadingId === row.id"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模型' : '添加模型'"
      width="640px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="显示名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：Qwen2.5-7B 本地推理" />
        </el-form-item>
        <el-form-item label="备注说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <el-form-item v-if="!isEdit" label="接入方式" prop="type">
          <el-radio-group v-model="form.type" class="type-radio">
            <el-radio-button value="api">API 远程调用</el-radio-button>
            <el-radio-button value="local">本地模型部署</el-radio-button>
          </el-radio-group>
          <p class="type-hint">
            <template v-if="form.type === 'api'">
              通过 OpenAI 兼容接口调用（参考 DSE ClosedModelLoader：base_url、api_key、model_id）
            </template>
            <template v-else>
              从 ModelScope 本地路径加载（参考 DSE ModelLoader / model_install.py）
            </template>
          </p>
        </el-form-item>

        <template v-if="form.type === 'api'">
          <el-divider content-position="left">API 配置</el-divider>
          <el-form-item label="API Base URL" prop="apiConfig.baseUrl">
            <el-input
              v-model="form.apiConfig.baseUrl"
              placeholder="留空则使用 OPENAI_BASE_URL 或官方默认端点"
            />
          </el-form-item>
          <el-form-item label="API Key" prop="apiConfig.apiKey">
            <el-input
              v-model="form.apiConfig.apiKey"
              type="password"
              show-password
              :placeholder="isEdit ? '留空表示不修改已有密钥' : '或依赖环境变量 OPENAI_API_KEY'"
            />
          </el-form-item>
          <el-form-item label="模型 ID (model)" prop="apiConfig.modelId">
            <el-select
              v-model="form.apiConfig.modelId"
              filterable
              allow-create
              default-first-option
              placeholder="deepseek-v4-flash"
              style="width: 100%"
            >
              <el-option
                v-for="m in formOptions?.example_api_models || []"
                :key="m"
                :label="m"
                :value="m"
              />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="Temperature">
                <el-input-number
                  v-model="form.apiConfig.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Max Tokens">
                <el-input-number
                  v-model="form.apiConfig.maxTokens"
                  :min="256"
                  :max="128000"
                  :step="256"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </template>

        <template v-else>
          <el-divider content-position="left">本地部署配置</el-divider>
          <el-form-item label="ModelScope 模型 ID" prop="localConfig.modelId">
            <el-select
              v-model="form.localConfig.modelId"
              filterable
              allow-create
              default-first-option
              placeholder="Qwen/Qwen2.5-7B-Instruct"
              style="width: 100%"
            >
              <el-option
                v-for="m in formOptions?.example_model_ids || []"
                :key="m"
                :label="m"
                :value="m"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="权重根目录 (base_dir)">
            <el-input
              v-model="form.localConfig.baseDir"
              :placeholder="formOptions?.default_base_dir || '/data/lz/modelscope'"
            />
          </el-form-item>
          <el-alert
            v-if="resolvedPreview"
            type="info"
            :closable="false"
            show-icon
            class="path-preview"
            :title="`解析路径：${resolvedPreview}`"
          />
          <p v-if="!isEdit" class="local-hint">
            添加后可在列表中对本地模型使用「下载」拉取 ModelScope 权重，再通过「推理检测」验证。
          </p>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { modelConfigService } from '@/services/modelConfigService'
import { formatApiError } from '@/utils/httpError'
import type {
  ModelConfigFormOptions,
  ModelRecord,
  ModelDeployType,
  ModelTestResult
} from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const downloadingId = ref('')
const testingId = ref('')
const loadError = ref('')
const showDisabled = ref(false)
const models = ref<ModelRecord[]>([])
const formOptions = ref<ModelConfigFormOptions | null>(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()

const emptyApi = () => ({
  baseUrl: '',
  apiKey: '',
  modelId: 'deepseek-v4-flash',
  temperature: 0.7,
  maxTokens: 4096
})

const emptyLocal = () => ({
  modelId: 'Qwen/Qwen2.5-7B-Instruct',
  baseDir: '/data/lz/modelscope'
})

const form = reactive({
  name: '',
  description: '',
  enabled: true,
  type: 'api' as ModelDeployType,
  apiConfig: emptyApi(),
  localConfig: emptyLocal()
})

const rules = computed<FormRules>(() => {
  const r: FormRules = {
    name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }]
  }
  if (!isEdit.value) {
    r.type = [{ required: true, message: '请选择接入方式', trigger: 'change' }]
  }
  if (form.type === 'api') {
    r['apiConfig.modelId'] = [{ required: true, message: '请输入 API 模型 ID', trigger: 'blur' }]
  } else {
    r['localConfig.modelId'] = [
      { required: true, message: '请输入 ModelScope 模型 ID', trigger: 'blur' }
    ]
  }
  return r
})

watch(
  () => form.type,
  () => {
    formRef.value?.clearValidate()
  }
)

const resolvedPreview = computed(() => {
  if (form.type !== 'local') return ''
  const base = form.localConfig.baseDir || formOptions.value?.default_base_dir || ''
  if (!form.localConfig.modelId) return ''
  const dsePath = form.localConfig.modelId.replace(/\./g, '___')
  return `${base.replace(/\/$/, '')}/${dsePath}`
})

function normalizeRecord(row: ModelRecord): ModelRecord {
  const api = row.api_config as Record<string, unknown> | null
  const local = row.local_config as Record<string, unknown> | null
  return {
    ...row,
    api_config: api
      ? {
          baseUrl: String(api.baseUrl ?? api.base_url ?? ''),
          apiKey: '',
          modelId: String(api.modelId ?? api.model_id ?? ''),
          temperature: Number(api.temperature ?? 0.7),
          maxTokens: Number(api.maxTokens ?? api.max_tokens ?? 4096),
          api_key_masked: String(api.api_key_masked ?? '')
        }
      : null,
    local_config: local
      ? {
          modelId: String(local.modelId ?? local.model_id ?? ''),
          baseDir: String(local.baseDir ?? local.base_dir ?? '/data/lz/modelscope')
        }
      : null
  }
}

async function loadModels() {
  loading.value = true
  try {
    const res = await modelConfigService.listModels(showDisabled.value)
    models.value = (res.models || []).map(normalizeRecord)
    loadError.value = ''
  } catch (e: unknown) {
    const msg = formatApiError(e, '加载模型列表失败')
    loadError.value = msg
    models.value = []
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  try {
    formOptions.value = await modelConfigService.getOptions()
    if (formOptions.value?.default_base_dir) {
      form.localConfig.baseDir = formOptions.value.default_base_dir
    }
  } catch {
    /* 选项加载失败不阻断列表 */
  }
}

async function retryLoad() {
  try {
    await modelConfigService.checkHealth()
  } catch (e: unknown) {
    const msg = formatApiError(e, '后端未就绪')
    loadError.value = msg
    ElMessage.error(msg)
    return
  }
  await Promise.all([loadOptions(), loadModels()])
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = ''
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: ModelRecord) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.description = row.description || ''
  form.enabled = row.enabled
  form.type = row.type
  if (row.type === 'api' && row.api_config) {
    form.apiConfig = { ...emptyApi(), ...row.api_config, apiKey: '' }
  }
  if (row.type === 'local' && row.local_config) {
    form.localConfig = { ...emptyLocal(), ...row.local_config }
  }
  dialogVisible.value = true
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.enabled = true
  form.type = 'api'
  form.apiConfig = emptyApi()
  form.localConfig = {
    ...emptyLocal(),
    baseDir: formOptions.value?.default_base_dir || '/data/lz/modelscope'
  }
  formRef.value?.clearValidate()
}

function buildPayload() {
  const base: Record<string, unknown> = {
    name: form.name,
    description: form.description,
    enabled: form.enabled
  }
  if (!isEdit.value) base.type = form.type
  if (form.type === 'api') {
    base.apiConfig = { ...form.apiConfig }
  } else {
    base.localConfig = { ...form.localConfig }
  }
  return base
}

async function handleSubmit() {
  if (saving.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value) {
      await modelConfigService.updateModel(editingId.value, buildPayload())
      ElMessage.success('模型已更新')
    } else {
      await modelConfigService.createModel(buildPayload())
      ElMessage.success('模型已添加')
    }
    dialogVisible.value = false
    await loadModels()
  } catch (e: unknown) {
    ElMessage.error(formatApiError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

function testLoadingMessage(type: ModelRecord['type']) {
  if (type === 'api') {
    return '正在检测 API 模型（调用远程接口，通常数秒至数十秒）…'
  }
  return '正在检测本地模型（需加载权重并短文本推理，可能耗时数分钟）…'
}

function buildTestResultDetail(row: ModelRecord, res: ModelTestResult) {
  const lines: string[] = [res.message]
  if (row.type === 'local') {
    if (res.path) lines.push(`权重路径: ${res.path}`)
  } else {
    const modelId = row.api_config?.modelId || res.model_id
    if (modelId) lines.push(`模型 ID: ${modelId}`)
    if (res.base_url) lines.push(`API 端点: ${res.base_url}`)
  }
  if (res.elapsed_seconds != null) lines.push(`耗时: ${res.elapsed_seconds}s`)
  if (res.sample_response) lines.push(`回复预览: ${res.sample_response}`)
  return lines.filter(Boolean).join('\n\n')
}

async function handleTest(row: ModelRecord) {
  const isApi = row.type === 'api'
  testingId.value = row.id
  const loadingMsg = ElMessage({
    type: 'info',
    message: testLoadingMessage(row.type),
    duration: 0
  })
  try {
    const res = await modelConfigService.testModel(row.id)
    loadingMsg.close()
    const detail = buildTestResultDetail(row, res)
    const alertTitle = isApi ? 'API 推理检测' : '本地推理检测'
    if (res.success && res.sample_response) {
      await ElMessageBox.alert(detail, `${alertTitle} — 通过`, {
        type: 'success',
        confirmButtonText: '确定'
      })
    } else {
      ElMessage({
        type: res.success ? 'success' : 'warning',
        message: res.message,
        duration: 8000
      })
    }
  } catch (e: unknown) {
    loadingMsg.close()
    ElMessage.error(
      formatApiError(e, isApi ? 'API 推理检测失败' : '本地推理检测失败')
    )
  } finally {
    testingId.value = ''
  }
}

async function handleDownload(row: ModelRecord) {
  const lc = row.local_config
  if (!lc?.modelId) return
  downloadingId.value = row.id
  try {
    const res = await modelConfigService.downloadModel(lc.modelId, lc.baseDir)
    ElMessage.success(res.message)
  } catch (e: unknown) {
    const msg =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      '下载失败'
    ElMessage.error(String(msg))
  } finally {
    downloadingId.value = ''
  }
}

async function handleDelete(row: ModelRecord) {
  try {
    await ElMessageBox.confirm(`确定删除模型「${row.name}」？`, '确认删除', {
      type: 'warning'
    })
    await modelConfigService.deleteModel(row.id)
    ElMessage.success('已删除')
    await loadModels()
  } catch {
    /* cancelled */
  }
}

onMounted(() => {
  retryLoad()
})
</script>

<style scoped>
.model-config-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 26px;
  font-weight: 600;
  color: var(--text-primary, #2c3e50);
  margin: 0 0 8px;
}

.page-subtitle {
  margin: 0;
  color: var(--text-secondary, #7f8c8d);
  font-size: var(--el-font-size-base);
}

.main-card {
  border-radius: 12px;
  border: 1px solid var(--border-color, #e8ecf0);
}

.card-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-title {
  font-weight: 600;
  font-size: var(--el-font-size-large);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.model-table {
  width: 100%;
}

.type-radio {
  width: 100%;
}

.type-hint {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--text-secondary, #7f8c8d);
  line-height: 1.5;
}

.path-preview {
  margin-bottom: 12px;
}

.local-hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary, #7f8c8d);
  line-height: 1.5;
}

.load-error-alert {
  margin-bottom: 16px;
}

.load-error-hint {
  margin: 8px 0 12px;
  font-size: 13px;
  color: var(--text-secondary, #7f8c8d);
}

.load-error-hint code {
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
}
</style>
