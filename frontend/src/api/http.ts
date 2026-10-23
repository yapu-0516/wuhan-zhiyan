// HTTP 基础层：统一 fetch、错误处理、离线降级
// 后端可达 → live；后端不可达（网络错误 / 网关 5xx）→ 自动降级为快照数据 offline；VITE_USE_MOCK=true → mock。
import { reactive } from 'vue'
import { API_BASE, SNAPSHOT_BASE, USE_MOCK } from '@/config/api'

export type ApiMode = 'live' | 'offline' | 'mock'

export const apiState = reactive<{ mode: ApiMode; lastError: string }>({
  mode: USE_MOCK ? 'mock' : 'live',
  lastError: ''
})

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

const snapshotCache = new Map<string, Promise<unknown>>()

/** 读取 public/snapshot/<name> 静态快照（带缓存） */
export function loadSnapshot<T>(name: string): Promise<T> {
  if (!snapshotCache.has(name)) {
    snapshotCache.set(
      name,
      fetch(`${SNAPSHOT_BASE}/${name}`).then((r) => {
        if (!r.ok) throw new Error(`快照 ${name} 不存在`)
        return r.json()
      })
    )
  }
  return snapshotCache.get(name) as Promise<T>
}

function isGatewayFailure(status: number) {
  // Vite 代理在后端未启动时返回 500/502/503/504
  return status === 500 || status === 502 || status === 503 || status === 504
}

/**
 * 发起 API 请求。
 * @param path      以 / 开头的路径（不含 /api 前缀）
 * @param init      fetch 选项
 * @param fallback  后端不可达时的降级数据提供者；不提供则直接抛错
 */
export async function request<T>(
  path: string,
  init?: RequestInit,
  fallback?: () => Promise<T> | T
): Promise<T> {
  if (apiState.mode === 'mock' && fallback) return fallback()
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch (e) {
    if (fallback) {
      apiState.mode = 'offline'
      apiState.lastError = (e as Error).message
      return fallback()
    }
    throw new ApiError(0, '无法连接后端服务')
  }
  if (!res.ok) {
    if (isGatewayFailure(res.status) && fallback) {
      apiState.mode = 'offline'
      apiState.lastError = `HTTP ${res.status}`
      return fallback()
    }
    let detail = `请求失败 (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  if (apiState.mode === 'offline') apiState.mode = 'live'
  return (await res.json()) as T
}

export function jsonBody(body: unknown, method = 'POST'): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

/** 拼接查询串（忽略空值） */
export function qs(params?: Record<string, string | number | undefined | null>): string {
  if (!params) return ''
  const s = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&')
  return s ? `?${s}` : ''
}

export function nowString(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}
