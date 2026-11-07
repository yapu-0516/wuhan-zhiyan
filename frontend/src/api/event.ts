// 事件接口层 —— docs/api.md §2
// 页面与组件统一经此层取事件数据；后端不可达时降级为快照数据（离线模式下处置操作仅在本地生效）。
import { request, jsonBody, qs, loadSnapshot, apiState, nowString } from './http'
import type { CityEvent, EventCreate, EventLog, EventPatch, EventStatus, EventType, Severity } from '@/types/event'

export interface EventQuery {
  type?: EventType
  status?: EventStatus
  severity?: Severity
  q?: string
  limit?: number
}

const snapshotEvents = () => loadSnapshot<CityEvent[]>('events.json')

/** 获取事件列表 GET /api/events */
export async function getEvents(query?: EventQuery): Promise<CityEvent[]> {
  return request<CityEvent[]>(`/events${qs(query as Record<string, string>)}`, undefined, async () => {
    let list = await snapshotEvents()
    if (query?.type) list = list.filter((e) => e.event_type === query.type)
    if (query?.status) list = list.filter((e) => e.status === query.status)
    if (query?.severity) list = list.filter((e) => e.severity === query.severity)
    if (query?.q) {
      const q = query.q.toLowerCase()
      list = list.filter((e) => `${e.id}${e.name}${e.address}`.toLowerCase().includes(q))
    }
    return list
  })
}

/** 获取单个事件详情 GET /api/events/{id} */
export async function getEvent(id: string): Promise<CityEvent | undefined> {
  return request<CityEvent | undefined>(`/events/${encodeURIComponent(id)}`, undefined, async () =>
    (await snapshotEvents()).find((e) => e.id === id)
  )
}

/** 事件处置日志 GET /api/events/{id}/logs */
export async function getEventLogs(id: string): Promise<EventLog[]> {
  return request<EventLog[]>(`/events/${encodeURIComponent(id)}/logs`, undefined, async () => {
    const all = await loadSnapshot<Record<string, EventLog[]>>('event_logs.json').catch(
      () => ({}) as Record<string, EventLog[]>
    )
    return all[id] ?? []
  })
}

/** 更新事件（状态流转 / 指派 / 备注）PATCH /api/events/{id} */
export async function patchEvent(id: string, patch: EventPatch): Promise<CityEvent> {
  return request<CityEvent>(`/events/${encodeURIComponent(id)}`, jsonBody(patch, 'PATCH'), async () => {
    // 离线模式：仅本地生效，便于静态演示
    const e = (await snapshotEvents()).find((x) => x.id === id)
    if (!e) throw new Error('事件不存在')
    if (patch.status) e.status = patch.status
    if (patch.assignee) e.assignee = patch.assignee
    e.updated_at = nowString()
    return { ...e }
  })
}

/** 人工上报事件 POST /api/events */
export async function createEvent(body: EventCreate): Promise<CityEvent> {
  if (apiState.mode !== 'live') throw new Error('离线演示模式下不支持上报，请启动后端服务')
  return request<CityEvent>('/events', jsonBody(body))
}
