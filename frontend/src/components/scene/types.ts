// 三维场景对外类型：图层开关、拾取对象、场景 API（供 Dashboard / 演示导览调用）
import type { BasemapKey } from '@/config/cesium'
import type { Building, TrafficLevel } from '@/types/building'
import type { CityEvent, EventType } from '@/types/event'

export type LayerKey = 'buildings' | 'buildingsFine' | 'roads' | 'events' | 'pois' | 'effects'

export type LayerVisibility = Record<LayerKey, boolean>

export const DEFAULT_LAYERS: LayerVisibility = {
  // 默认只显示少量超高层、风险建筑与事件关联建筑，街区仍以卫星屋顶为主。
  buildings: true,
  buildingsFine: false,
  roads: true,
  events: true,
  pois: true,
  effects: true
}

export type EventTypeFilter = Record<EventType, boolean>

/** 演示导览聚焦的大屏面板（Dashboard 据此高亮对应面板） */
export type TourFocus = 'safety' | 'traffic' | 'kpi' | 'feed' | 'types' | 'trend' | 'district' | 'sensor'

export interface FlyOptions {
  /** 相机到目标的距离（米） */
  range?: number
  /** 俯仰角（度，负值向下看） */
  pitch?: number
  /** 航向角（度，0=北）；缺省保持当前航向 */
  heading?: number
  /** 飞行时长（秒） */
  duration?: number
}

export interface OrbitOptions {
  range?: number
  pitch?: number
  /** 环绕角速度（度/秒） */
  speed?: number
  heading?: number
}

export interface TourState {
  running: boolean
  index: number
  total: number
  title: string
  caption: string
  focus: TourFocus | null
}

/** CesiumViewer 通过 defineExpose 暴露的场景 API */
export interface SceneApi {
  /** 场景与数据是否就绪 */
  isReady(): boolean
  flyHome(duration?: number): Promise<boolean>
  flySkyline(duration?: number): Promise<boolean>
  flyFromSpace(): Promise<boolean>
  flyTo(lon: number, lat: number, opts?: FlyOptions): Promise<boolean>
  flyToEvent(id: string, opts?: { open?: boolean } & FlyOptions): Promise<boolean>
  flyToBuilding(id: string, opts?: { open?: boolean } & FlyOptions): Promise<boolean>
  orbit(lon: number, lat: number, opts?: OrbitOptions): Promise<boolean>
  stopOrbit(): void
  cancelFlight(): void
  setLayerVisible(layer: LayerKey, visible: boolean): void
  setBuildingRiskOnly(on: boolean): void
  loadFineBuildingLayer(): Promise<boolean>
  setBasemap(key: BasemapKey): void
  /** 高亮拥堵路段（演示用） */
  highlightCongestion(on: boolean): void
  openEvent(id: string): void
  openBuilding(id: string): void
  closePanels(): void
  /** 演示：在事件详情中打开派单表单并提交 */
  demoDispatch(assignee?: string): Promise<CityEvent | null>
  /** 示范区中心 [lon, lat] */
  regionCenter(): [number, number]
  /** 高层建筑最密集处（CBD）[lon, lat] */
  denseCenter(): [number, number]
  /** 最拥堵路段中点 [lon, lat]（无路网时为 null） */
  congestedSpot(): { lon: number; lat: number; name: string; tpi: number } | null
  /** 全路网长度加权 TPI（无路网时为 null） */
  cityTraffic(): { tpi: number; level: TrafficLevel } | null
  /** 演示用沉降预警建筑（warning 优先，其次 watch） */
  findRiskBuilding(): Building | null
  /** 统计信息：建筑 / 道路 / 应急资源数量 */
  sceneStats(): { buildings: number; roads: number; pois: number; monitored: number }
}
