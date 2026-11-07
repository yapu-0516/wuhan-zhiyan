// 系统 / 数据源 / 演示控制接口层 —— docs/api.md §1 §7 §8
import { request, jsonBody, loadSnapshot, apiState } from './http'
import type { DataSource, SystemInfo } from '@/types/api'
import type { EventType } from '@/types/event'

export function getSystemInfo(): Promise<SystemInfo> {
  return request('/system/info', undefined, () => loadSnapshot<SystemInfo>('system_info.json'))
}

/** 监测数据源 GET /api/sources */
export function getSources(): Promise<DataSource[]> {
  return request('/sources', undefined, () => loadSnapshot<DataSource[]>('sources.json'))
}

/** 触发演示场景 POST /api/demo/scenario */
export function triggerScenario(scenario: EventType | 'random'): Promise<{ task_id: string; event_id: string | null }> {
  if (apiState.mode !== 'live') return Promise.reject(new Error('离线演示模式下无法触发实时场景，请启动后端服务'))
  return request('/demo/scenario', jsonBody({ scenario }))
}

/** 恢复固定演示数据，清除人工上报、历史任务和上次演示产生的事件。 */
export function resetDemo(): Promise<{ ok: boolean }> {
  return request('/demo/reset', { method: 'POST' })
}
