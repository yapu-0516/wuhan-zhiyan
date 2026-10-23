// 实时通道：WebSocket 单例（自动重连 + 心跳 + 按类型订阅）
// 后端推送格式见 docs/api.md §9。离线/快照模式下不连接。
import { ref } from 'vue'
import { API_BASE, WS_URL } from '@/config/api'
import { apiState } from '@/api/http'
import type { WsMessage, WsMessageType } from '@/types/api'

type Handler<T extends WsMessageType> = (data: Extract<WsMessage, { type: T }>['data']) => void

const connected = ref(false)
const lastMessageAt = ref<number>(0)
const handlers = new Map<WsMessageType, Set<(data: unknown) => void>>()
let ws: WebSocket | null = null
let retry = 0
let started = false
let pingTimer: number | undefined

function wsUrl(): string {
  if (WS_URL) return WS_URL
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}${API_BASE}/ws`
}

function connect() {
  if (apiState.mode === 'mock') return
  try {
    ws = new WebSocket(wsUrl())
  } catch {
    scheduleReconnect()
    return
  }
  ws.onopen = () => {
    connected.value = true
    retry = 0
    window.clearInterval(pingTimer)
    pingTimer = window.setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send('{"type":"ping"}'), 25000)
  }
  ws.onmessage = (ev) => {
    lastMessageAt.value = Date.now()
    let msg: WsMessage
    try {
      msg = JSON.parse(ev.data)
    } catch {
      return
    }
    handlers.get(msg.type)?.forEach((h) => {
      try {
        h(msg.data)
      } catch (e) {
        console.error('[ws handler]', e)
      }
    })
  }
  ws.onclose = () => {
    connected.value = false
    window.clearInterval(pingTimer)
    scheduleReconnect()
  }
  ws.onerror = () => ws?.close()
}

function scheduleReconnect() {
  const delay = Math.min(30000, 1000 * 2 ** retry++)
  window.setTimeout(connect, delay)
}

export function useRealtime() {
  /** 启动连接（幂等） */
  function start() {
    if (started) return
    started = true
    connect()
  }

  /** 订阅某类消息，返回取消订阅函数 */
  function on<T extends WsMessageType>(type: T, handler: Handler<T>): () => void {
    if (!handlers.has(type)) handlers.set(type, new Set())
    handlers.get(type)!.add(handler as (d: unknown) => void)
    return () => handlers.get(type)?.delete(handler as (d: unknown) => void)
  }

  return { connected, lastMessageAt, start, on }
}
