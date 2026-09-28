// 事件接口层 —— 阶段11
// 对应后端：GET /api/events、GET /api/events/{id}
// 第3周 USE_MOCK=true，直接返回 mock 数据；第4周接 FastAPI 后改 fetch 真实接口。
// 页面与组件统一经此层取事件数据，避免到处写死。
import { mockEvents } from '@/mock/events'
import { API_BASE, USE_MOCK } from '@/config/api'
import type { CityEvent } from '@/types/event'

/** 获取事件列表 GET /api/events */
export async function getEvents(): Promise<CityEvent[]> {
  if (USE_MOCK) {
    return mockEvents
  }
  const res = await fetch(`${API_BASE}/events`)
  if (!res.ok) throw new Error(`获取事件列表失败: ${res.status}`)
  return (await res.json()) as CityEvent[]
}

/** 获取单个事件详情 GET /api/events/{id} */
export async function getEvent(id: string): Promise<CityEvent | undefined> {
  if (USE_MOCK) {
    return mockEvents.find((e) => e.id === id)
  }
  const res = await fetch(`${API_BASE}/events/${id}`)
  if (!res.ok) throw new Error(`获取事件详情失败: ${res.status}`)
  return (await res.json()) as CityEvent
}
