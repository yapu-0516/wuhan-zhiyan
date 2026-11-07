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
  constructor(
    public status: number,
    message: string
  ) {
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

function isRetryableStatus(status: number) {
  return isGatewayFailure(status) || status === 408 || status === 429
}

const REQUEST_TIMEOUT_MS = 10_000
/** GET 幂等请求的退避重试间隔（共重试 2 次） */
const RETRY_DELAYS = [300, 900]

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

/** 给请求挂上超时中断；已自带 signal 时不覆盖调用方设置 */
function withTimeout(init?: RequestInit, ms = REQUEST_TIMEOUT_MS) {
  if (init?.signal) return { init, done: () => {} }
  const ctrl = new AbortController()
  const timer = window.setTimeout(() => ctrl.abort(), ms)
  return { init: { ...init, signal: ctrl.signal }, done: () => window.clearTimeout(timer) }
}

function markOffline(message: string) {
  apiState.mode = 'offline'
  apiState.lastError = message
}

/**
 * 发起 API 请求。
 * - 超时 10s；GET 幂等请求在网络错误 / 网关 5xx / 408 / 429 时最多重试 2 次；
 * - 后端不可达且提供 fallback 时降级为快照数据。
 * @param path      以 / 开头的路径（不含 /api 前缀）
 * @param init      fetch 选项
 * @param fallback  后端不可达时的降级数据提供者；不提供则直接抛错
 */
export async function request<T>(path: string, init?: RequestInit, fallback?: () => Promise<T> | T): Promise<T> {
  if (apiState.mode === 'mock' && fallback) return fallback()
  const method = (init?.method ?? 'GET').toUpperCase()
  const retries = method === 'GET' ? RETRY_DELAYS.length : 0
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) await sleep(RETRY_DELAYS[attempt - 1])
    const { init: reqInit, done } = withTimeout(init)
    let res: Response
    try {
      res = await fetch(`${API_BASE}${path}`, reqInit)
    } catch (e) {
      done()
      const err = e as Error
      const timedOut = err.name === 'AbortError'
      lastError = timedOut ? new Error('请求超时') : err
      if (attempt < retries) continue
      if (fallback) {
        markOffline(lastError.message)
        return fallback()
      }
      throw new ApiError(0, timedOut ? '请求超时，请检查后端服务' : '无法连接后端服务')
    }
    done()

    if (res.ok) {
      if (apiState.mode === 'offline') {
        apiState.mode = 'live'
        apiState.lastError = ''
      }
      return (await res.json()) as T
    }

    if (isRetryableStatus(res.status)) {
      lastError = new ApiError(res.status, `HTTP ${res.status}`)
      if (attempt < retries) continue
      if (fallback) {
        markOffline(`HTTP ${res.status}`)
        return fallback()
      }
      // 业务后端主动返回的 5xx（如大模型 503）带有可读 detail，透传给用户；网关错误页为非 JSON，忽略
      try {
        const body = await res.json()
        if (typeof body?.detail === 'string' && body.detail) {
          lastError = new ApiError(res.status, body.detail)
        }
      } catch {
        /* 保持 HTTP 状态码文案 */
      }
      throw lastError
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

  throw lastError ?? new ApiError(0, '请求失败')
}

/** 手动探测后端连接（顶栏 / 离线提示条的“重试”入口） */
export async function retryConnection(): Promise<{ ok: boolean; error?: string }> {
  if (apiState.mode === 'mock') return { ok: true }
  const { init, done } = withTimeout(undefined, 5000)
  try {
    const res = await fetch(`${API_BASE}/health`, init)
    done()
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    apiState.mode = 'live'
    apiState.lastError = ''
    return { ok: true }
  } catch (e) {
    done()
    const err = e as Error
    const msg = err.name === 'AbortError' ? '连接超时' : err.message
    markOffline(msg)
    return { ok: false, error: msg }
  }
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
