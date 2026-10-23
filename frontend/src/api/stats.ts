// 统计接口层 —— docs/api.md §4
import { request, loadSnapshot } from './http'
import type { Overview } from '@/types/api'

/** 城市运行总览 GET /api/stats/overview */
export function getOverview(): Promise<Overview> {
  return request('/stats/overview', undefined, () => loadSnapshot<Overview>('stats_overview.json'))
}
