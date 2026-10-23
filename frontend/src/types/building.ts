// 城市三维对象类型 —— 与 docs/api.md §3 保持一致
// v1：建筑由 4 个测试盒体升级为 OpenStreetMap 真实建筑轮廓（GeoJSON Polygon），按高度拉伸。

export type BuildingCategory = 'residential' | 'commercial' | 'office' | 'public' | 'industrial' | 'other'
export type RiskLevel = 'normal' | 'watch' | 'warning'
export type TrafficLevel = 'smooth' | 'basic' | 'light' | 'moderate' | 'heavy'

export interface Building {
  /** 建筑编号，如 B0001 */
  id: string
  /** 建筑名称 */
  name: string
  /** 质心经度 */
  longitude: number
  /** 质心纬度 */
  latitude: number
  /** 建筑高度（米） */
  height: number
  levels?: number | null
  /** osm：OSM 实测高度；levels：楼层数 × 3.2m；estimated：按占地面积与类别估算 */
  height_source?: 'osm' | 'levels' | 'estimated'
  category?: BuildingCategory
  district?: string
  grid?: string
  area_m2?: number
  monitored?: boolean
  risk_level?: RiskLevel
}

export interface PolygonGeometry {
  type: 'Polygon'
  coordinates: number[][][]
}

export interface LineStringGeometry {
  type: 'LineString'
  coordinates: number[][]
}

export interface Feature<G, P> {
  type: 'Feature'
  id?: string
  geometry: G
  properties: P
}

export interface FeatureCollection<G, P> {
  type: 'FeatureCollection'
  features: Feature<G, P>[]
}

export type BuildingCollection = FeatureCollection<PolygonGeometry, Building>

export interface SettlementPoint {
  date: string
  displacement_mm: number
}

export interface BuildingMonitoring {
  series: SettlementPoint[]
  rate_mm_per_month: number
  acceleration: number
  cumulative_mm: number
  risk_level: RiskLevel
  analysis: string
}

export interface BuildingDetail {
  properties: Building
  monitoring: BuildingMonitoring | null
  events: import('./event').CityEvent[]
}

export interface Road {
  id: string
  name: string
  highway: string
  length_m: number
  speed_limit: number
  speed: number
  tpi: number
  level: TrafficLevel
}

export type RoadCollection = FeatureCollection<LineStringGeometry, Road>

export interface Poi {
  id: string
  name: string
  kind: 'hospital' | 'fire_station' | 'police' | 'school'
  longitude: number
  latitude: number
}

export const TRAFFIC_LEVEL_META: Record<TrafficLevel, { label: string; color: string }> = {
  smooth: { label: '畅通', color: '#2ed47a' },
  basic: { label: '基本畅通', color: '#9be15d' },
  light: { label: '轻度拥堵', color: '#f0c050' },
  moderate: { label: '中度拥堵', color: '#ff8a3d' },
  heavy: { label: '严重拥堵', color: '#ff3b3b' }
}

export const RISK_LEVEL_META: Record<RiskLevel, { label: string; color: string }> = {
  normal: { label: '正常', color: '#4dd984' },
  watch: { label: '关注', color: '#f0c050' },
  warning: { label: '预警', color: '#ff4d4f' }
}

export const POI_META: Record<Poi['kind'], { label: string; icon: string }> = {
  hospital: { label: '医院', icon: '🏥' },
  fire_station: { label: '消防站', icon: '🚒' },
  police: { label: '派出所', icon: '🚓' },
  school: { label: '学校', icon: '🏫' }
}
