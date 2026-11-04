export type PersonType = 'resident' | 'tourist' | 'firefighter' | 'rescuer'
export type SpawnType = PersonType | 'mixed'
export type PersonState = 'idle' | 'walking' | 'reacting' | 'evacuating' | 'waiting' | 'arrived'

export interface CrowdRegion {
  center: [number, number]
  bbox: [number, number, number, number]
}

export interface PersonView {
  id: string
  type: PersonType
  longitude: number
  latitude: number
  scale: number
  heading: number
  state: PersonState
}

export interface CrowdStats {
  total: number
  moving: number
  byType: Record<PersonType, number>
  byArea: Record<string, number>
}

export interface CrowdBenchmarkRow {
  people: number
  fps: number
  frameMs: number
  drawCalls: number
  triangles: number
}

export interface VehicleStats {
  total: number
  moving: number
  affected: number
  stopped: number
  rerouted: number
  averageSpeedKmh: number
}

export const PERSON_META: Record<PersonType, { label: string; color: string }> = {
  resident: { label: '居民', color: '#4fc3f7' },
  tourist: { label: '游客', color: '#f0c050' },
  firefighter: { label: '消防员', color: '#ff5a5a' },
  rescuer: { label: '救援人员', color: '#4dd984' }
}
