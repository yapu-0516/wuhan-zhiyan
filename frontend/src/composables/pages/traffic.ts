// 路况聚合：按道路名称合并路段，TPI / 车速按路段长度加权
import type { Road, TrafficLevel } from '@/types/building'

export const TRAFFIC_LEVELS: TrafficLevel[] = ['smooth', 'basic', 'light', 'moderate', 'heavy']

/** TPI(0-10) → 拥堵等级：0-2 / 2-4 / 4-6 / 6-8 / 8-10 */
export function levelOfTpi(tpi: number): TrafficLevel {
  if (tpi < 2) return 'smooth'
  if (tpi < 4) return 'basic'
  if (tpi < 6) return 'light'
  if (tpi < 8) return 'moderate'
  return 'heavy'
}

export const HIGHWAY_LABEL: Record<string, string> = {
  motorway: '高速路',
  trunk: '快速路',
  primary: '主干道',
  secondary: '次干道',
  tertiary: '支路'
}

export interface RoadGroup {
  key: string
  name: string
  highway: string
  segments: number
  length_m: number
  speed: number
  speed_limit: number
  tpi: number
  level: TrafficLevel
}

export function groupRoads(roads: Road[]): RoadGroup[] {
  const map = new Map<string, { roads: Road[] }>()
  for (const r of roads) {
    const key = r.name?.trim() || r.id
    const g = map.get(key)
    if (g) g.roads.push(r)
    else map.set(key, { roads: [r] })
  }
  const out: RoadGroup[] = []
  for (const [key, { roads: rs }] of map) {
    const total = rs.reduce((s, r) => s + (r.length_m || 1), 0)
    const w = (f: (r: Road) => number) => rs.reduce((s, r) => s + f(r) * (r.length_m || 1), 0) / total
    const tpi = w((r) => r.tpi)
    out.push({
      key,
      name: key,
      highway: rs[0].highway,
      segments: rs.length,
      length_m: rs.reduce((s, r) => s + r.length_m, 0),
      speed: w((r) => r.speed),
      speed_limit: Math.max(...rs.map((r) => r.speed_limit)),
      tpi,
      level: levelOfTpi(tpi)
    })
  }
  return out
}

/** 全路网长度加权 TPI */
export function cityTpiOf(roads: Road[]): number {
  if (!roads.length) return 0
  const total = roads.reduce((s, r) => s + (r.length_m || 1), 0)
  return roads.reduce((s, r) => s + r.tpi * (r.length_m || 1), 0) / total
}
