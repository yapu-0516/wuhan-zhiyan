import type { EventType } from '@/types/event'

interface HazardProfile {
  durationSec: number
  maxScale: number
  label: string
}

const HAZARD_PROFILES: Record<EventType, HazardProfile> = {
  fire: { durationSec: 45, maxScale: 1.38, label: '烟气影响区' },
  flood: { durationSec: 75, maxScale: 1.48, label: '积水影响区' },
  building: { durationSec: 30, maxScale: 1.12, label: '结构警戒区' },
  traffic: { durationSec: 40, maxScale: 1.18, label: '拥堵影响区' }
}

function smoothstep(value: number): number {
  const x = Math.max(0, Math.min(1, value))
  return x * x * (3 - 2 * x)
}

/** Demo 级风险场：风险区从基础半径平滑扩展，不代表专业物理求解。 */
export function hazardRadiusAt(type: EventType, baseRadiusM: number, elapsedSec: number): number {
  const profile = HAZARD_PROFILES[type]
  const progress = smoothstep(elapsedSec / profile.durationSec)
  return baseRadiusM * (1 + (profile.maxScale - 1) * progress)
}

export function hazardProfile(type: EventType): HazardProfile {
  return HAZARD_PROFILES[type]
}

export function requiresPedestrianEvacuation(type: EventType): boolean {
  return type !== 'traffic'
}
