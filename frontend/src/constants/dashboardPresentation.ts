/**
 * 仪表盘 UI 展示配置（与业务数据解耦，仅负责视觉呈现）
 */

import type { DashboardStats } from '@/types/api'

export interface StatCardView {
  title: string
  value: string
  icon: string
  color: string
}

const STAT_PRESENTATION: Array<{
  key: keyof DashboardStats
  icon: string
  color: string
}> = [
  {
    key: 'total_extractions',
    icon: 'Document',
    color: 'linear-gradient(135deg, #6BAED6 0%, #8FC4E0 100%)'
  },
  {
    key: 'evaluations_done',
    icon: 'DataAnalysis',
    color: 'linear-gradient(135deg, #6BAED6 0%, #4A90A4 100%)'
  },
  {
    key: 'avg_accuracy_percent',
    icon: 'TrendCharts',
    color: 'linear-gradient(135deg, #FC8D62 0%, #FEB896 100%)'
  },
  {
    key: 'model_count',
    icon: 'Connection',
    color: 'linear-gradient(135deg, #FC8D62 0%, #E67E5A 100%)'
  }
]

export function buildStatCards(
  meta: Array<{ key: string; title: string }>,
  stats: DashboardStats
): StatCardView[] {
  const titleByKey = new Map(meta.map((m) => [m.key, m.title]))
  return STAT_PRESENTATION.map((preset) => {
    const value = String(stats[preset.key])
    return {
      title: titleByKey.get(preset.key) ?? preset.key,
      value,
      icon: preset.icon,
      color: preset.color
    }
  })
}
