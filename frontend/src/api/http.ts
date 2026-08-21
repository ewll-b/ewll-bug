import axios, { AxiosError } from 'axios'
import { Message } from '@arco-design/web-vue'
import { withAppBase, withoutAppBase } from './paths'

export interface ApiResponse<T> {
  ok: boolean
  message?: string
  data: T
}

export const http = axios.create({
  baseURL: withAppBase('/api/v1'),
  timeout: 30000,
  withCredentials: true,
  paramsSerializer: { indexes: null },
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string }>) => {
    const message = error.response?.data?.message || error.message || '请求失败，请稍后重试。'
    if (error.response?.status === 401 && !window.location.pathname.endsWith('/login')) {
      const next = `${withoutAppBase(window.location.pathname)}${window.location.search}`
      window.location.assign(`${withAppBase('/login')}?next=${encodeURIComponent(next)}`)
    } else {
      Message.error(message)
    }
    return Promise.reject(error)
  },
)

export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await http.get<ApiResponse<T>>(url, { params })
  return response.data.data
}

export async function apiPost<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const response = await http.post<ApiResponse<T>>(url, data)
  return response.data
}
