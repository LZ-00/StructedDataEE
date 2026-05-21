import axios from 'axios'

/** 将 Axios / FastAPI 错误转为可读中文提示 */
export function formatApiError(error: unknown, fallback = '操作失败'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback
  }

  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请稍后重试（本地模型检测可能较慢）'
    }
    return '无法连接后端，请确认已执行 npm run dev:backend 且端口 8000 可用'
  }

  const data = error.response.data as { detail?: unknown; message?: string }
  const detail = data?.detail

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') {
        const rec = item as { loc?: unknown[]; msg?: string }
        const loc = Array.isArray(rec.loc) ? rec.loc.slice(1).join('.') : ''
        const msg = rec.msg || '参数错误'
        return loc ? `${loc}: ${msg}` : msg
      }
      return ''
    })
    const joined = parts.filter(Boolean).join('；')
    if (joined) return joined
  }

  if (error.response.status === 401) {
    return '登录已过期，请重新登录'
  }

  if (typeof data?.message === 'string' && data.message) {
    return data.message
  }

  return `${fallback} (HTTP ${error.response.status})`
}
