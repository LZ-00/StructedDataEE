<template>
  <div class="dashboard-page">
    <header class="page-header">
      <div class="page-header-text">
        <h1 class="page-title">系统仪表盘</h1>
        <p class="page-subtitle">任务运行概览与多模型抽取性能对比</p>
      </div>
    </header>

    <section class="stats-section" aria-label="统计概览">
      <el-row :gutter="20">
        <el-col
          v-for="stat in stats"
          :key="stat.title"
          :xs="24"
          :sm="12"
          :lg="6"
          class="stat-col"
        >
          <div class="stat-card">
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon :size="28"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <section class="charts-section" aria-label="模型性能图表">
      <h2 class="section-title">模型性能对比</h2>
      <el-row :gutter="20" class="charts-grid">
        <el-col :xs="24" :lg="12" class="chart-col">
          <el-card class="chart-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-header-title">精确匹配率 (Exact Match)</span>
                <el-icon class="card-header-icon card-header-icon--primary"><TrendCharts /></el-icon>
              </div>
            </template>
            <div ref="lineChartRef" class="chart-container"></div>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12" class="chart-col">
          <el-card class="chart-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-header-title">均方根误差 (RMSE)</span>
                <el-icon class="card-header-icon card-header-icon--secondary"><DataAnalysis /></el-icon>
              </div>
            </template>
            <div ref="barChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { TrendCharts, DataAnalysis } from '@element-plus/icons-vue'
import { dashboardService } from '@/services/dashboardService'
import { buildStatCards, type StatCardView } from '@/constants/dashboardPresentation'
import { buildExactMatchLineOption, buildRmseBarOption } from '@/charts/dashboardChartOptions'
import type { DashboardCharts } from '@/types/api'

const stats = ref<StatCardView[]>([])
const lineChartRef = ref<HTMLDivElement>()
const barChartRef = ref<HTMLDivElement>()

let lineChart: ECharts | null = null
let barChart: ECharts | null = null

function renderLineChart(charts: DashboardCharts) {
  if (!lineChartRef.value) return
  lineChart?.dispose()
  lineChart = echarts.init(lineChartRef.value)
  lineChart.setOption(
    buildExactMatchLineOption(charts.exact_match.models, charts.exact_match.values)
  )
}

function renderBarChart(charts: DashboardCharts) {
  if (!barChartRef.value) return
  barChart?.dispose()
  barChart = echarts.init(barChartRef.value)
  barChart.setOption(buildRmseBarOption(charts.rmse.models, charts.rmse.values))
}

function resizeCharts() {
  lineChart?.resize()
  barChart?.resize()
}

function handleResize() {
  resizeCharts()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  try {
    const [statMeta, dashboardStats, charts] = await Promise.all([
      dashboardService.getStatCards(),
      dashboardService.getStats(),
      dashboardService.getCharts()
    ])
    stats.value = buildStatCards(statMeta, dashboardStats)
    renderLineChart(charts)
    renderBarChart(charts)
    await nextTick()
    resizeCharts()
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 401) {
      ElMessage.warning('未登录或登录已过期，请重新登录')
    } else if (status === 404) {
      ElMessage.warning('后端接口未就绪，请使用 npm run dev:backend 重启后端（需带 --reload）')
    } else {
      ElMessage.warning('仪表盘数据加载失败，请确认已登录且后端服务已启动')
    }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  lineChart?.dispose()
  barChart?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1440px;
  margin: 0 auto;
  min-height: calc(100vh - 110px);
  padding: 8px 8px 32px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.page-header {
  padding: 4px 4px 0;
}

.page-title {
  margin: 0;
  font-size: var(--ui-font-section);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.3px;
}

.page-subtitle {
  margin: 8px 0 0;
  font-size: var(--ui-font-caption);
  color: var(--text-secondary);
  line-height: 1.5;
}

.stats-section {
  flex-shrink: 0;
}

.stat-col {
  margin-bottom: 20px;
}

@media (min-width: 1200px) {
  .stat-col {
    margin-bottom: 0;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 100%;
  min-height: 108px;
  padding: 20px 22px;
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-light);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  border-color: rgba(107, 174, 214, 0.35);
  box-shadow: var(--shadow-card);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: var(--ui-font-stat-value);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.15;
  letter-spacing: -0.5px;
}

.stat-title {
  margin-top: 6px;
  font-size: var(--ui-font-caption);
  color: var(--text-secondary);
  line-height: 1.4;
}

.charts-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-title {
  margin: 0 0 16px;
  padding-left: 12px;
  font-size: var(--ui-font-card-title);
  font-weight: 600;
  color: var(--text-primary);
  border-left: 4px solid var(--primary-color);
  line-height: 1.3;
}

.charts-grid {
  flex: 1;
  align-items: stretch;
}

.chart-col {
  display: flex;
  margin-bottom: 20px;
}

@media (min-width: 1200px) {
  .chart-col {
    margin-bottom: 0;
  }
}

.chart-card {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  overflow: hidden;
}

.chart-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-extra-light);
  background: #fafbfc;
}

.chart-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px 16px 20px;
  min-height: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-title {
  font-size: var(--ui-font-body);
  font-weight: 600;
  color: var(--text-primary);
}

.card-header-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.card-header-icon--primary {
  color: var(--primary-color);
}

.card-header-icon--secondary {
  color: var(--secondary-color);
}

.chart-container {
  flex: 1;
  width: 100%;
  min-height: clamp(320px, 40vh, 460px);
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 4px 0 24px;
    gap: 20px;
  }

  .stat-value {
    font-size: 30px;
  }

  .chart-container {
    min-height: 300px;
  }
}
</style>
