/** 登录态：调用 backend JWT，令牌存 sessionStorage */

import { api } from '@/utils/api'

export const AUTH_TOKEN_KEY = 'sdweb_access_token'

export const DEFAULT_USERNAME = 'root'
export const DEFAULT_PASSWORD = '123456'

export function getAccessToken(): string | null {
  return sessionStorage.getItem(AUTH_TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken())
}

export function clearSession(): void {
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
}

export type LoginResult = { ok: true } | { ok: false; message: string }

export async function loginWithApi(username: string, password: string): Promise<LoginResult> {
  try {
    const res = await api.login(username.trim(), password)
    if (res?.access_token) {
      sessionStorage.setItem(AUTH_TOKEN_KEY, res.access_token)
      return { ok: true }
    }
    return { ok: false, message: '用户名或密码错误' }
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 401) {
      return { ok: false, message: '用户名或密码错误' }
    }
    if (!status) {
      return { ok: false, message: '无法连接后端服务，请确认已执行 npm run dev:backend' }
    }
    return { ok: false, message: '登录失败，请稍后重试' }
  }
}

export function logout(): void {
  clearSession()
}
