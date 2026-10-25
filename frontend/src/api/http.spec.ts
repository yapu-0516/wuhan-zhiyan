import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiState, jsonBody, qs, request, retryConnection } from '@/api/http'

beforeEach(() => {
  // http.ts 使用 window.setTimeout；Node 测试环境把 window 指向 globalThis
  vi.stubGlobal('window', globalThis)
  apiState.mode = 'live'
  apiState.lastError = ''
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('查询串与请求体', () => {
  it('qs 忽略空值并编码', () => {
    expect(qs({ a: 1, b: '', c: null, d: undefined, e: 'x y' })).toBe('?a=1&e=x%20y')
    expect(qs()).toBe('')
  })

  it('jsonBody 默认 POST 并序列化', () => {
    const init = jsonBody({ status: 'processing' })
    expect(init.method).toBe('POST')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(String(init.body))).toEqual({ status: 'processing' })
  })
})

describe('request 超时与重试', () => {
  it('GET 网络失败时重试 2 次后降级为 fallback', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network down'))
    vi.stubGlobal('fetch', fetchMock)
    const fallback = vi.fn(() => ({ events: [] }))

    const result = request('/events', undefined, fallback)
    await vi.advanceTimersByTimeAsync(1500)

    await expect(result).resolves.toEqual({ events: [] })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fallback).toHaveBeenCalledTimes(1)
    expect(apiState.mode).toBe('offline')
  })

  it('写请求（POST）不重试，直接抛 ApiError', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network down'))
    vi.stubGlobal('fetch', fetchMock)

    const task = request('/events', { method: 'POST', body: '{}' })
    const assertion = expect(task).rejects.toBeInstanceOf(ApiError)
    await vi.advanceTimersByTimeAsync(0)
    await assertion
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('请求成功时从 offline 恢复为 live', async () => {
    apiState.mode = 'offline'
    apiState.lastError = 'HTTP 502'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [1] }) }))

    await expect(request('/system/info')).resolves.toEqual({ items: [1] })
    expect(apiState.mode).toBe('live')
    expect(apiState.lastError).toBe('')
  })
})

describe('retryConnection', () => {
  it('健康检查成功则恢复 live', async () => {
    apiState.mode = 'offline'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))
    await expect(retryConnection()).resolves.toEqual({ ok: true })
    expect(apiState.mode).toBe('live')
  })

  it('健康检查失败保持 offline 并返回原因', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }))
    const r = await retryConnection()
    expect(r.ok).toBe(false)
    expect(r.error).toBe('HTTP 502')
    expect(apiState.mode).toBe('offline')
  })
})
