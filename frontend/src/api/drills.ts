import { jsonBody, loadSnapshot, request } from './http'
import type { DrillRun, DrillRunCreate, DrillRunUpdate, ReviewRecord } from '@/types/workflow'

export function getDrillRuns(limit = 50): Promise<DrillRun[]> {
  return request(
    `/drills/runs?limit=${limit}`,
    undefined,
    async () => (await loadSnapshot<DrillRun[]>('drills.json')).slice(0, limit)
  )
}

export function getDrillRun(id: string): Promise<DrillRun> {
  return request(`/drills/runs/${encodeURIComponent(id)}`, undefined, async () => {
    const rows = await loadSnapshot<DrillRun[]>('drills.json')
    const row = rows.find((item) => item.id === id)
    if (!row) throw new Error(`演练运行 ${id} 不存在`)
    return row
  })
}

export function createDrillRun(body: DrillRunCreate): Promise<DrillRun> {
  return request('/drills/runs', jsonBody(body, 'POST'))
}

export function updateDrillRun(id: string, body: DrillRunUpdate): Promise<DrillRun> {
  return request(`/drills/runs/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function createDrillReview(id: string): Promise<ReviewRecord> {
  return request(`/drills/runs/${encodeURIComponent(id)}/review`, jsonBody({}, 'POST'))
}
