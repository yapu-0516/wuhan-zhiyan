// 城市事件类型定义
// 统一事件结构，后续阶段扩展 flood / accident / road_anomaly 等类型时在此追加

export type EventType = 'fire' | 'traffic' | 'building'

export type EventStatus = 'pending' | 'monitoring' | 'processing' | 'resolved'

export interface CityEvent {
  /** 事件编号，如 E001 */
  id: string
  /** 事件类型 */
  event_type: EventType
  /** 事件名称 */
  name: string
  /** 经度 */
  longitude: number
  /** 纬度 */
  latitude: number
  /** AI 置信度 0~1 */
  confidence: number
  /** 处理状态 */
  status: EventStatus
  /** 发现时间，格式 yyyy-MM-dd HH:mm:ss */
  timestamp: string
}

/** 事件类型展示元信息（中文标签、Emoji 图标、主题色），供 UI 与 Cesium 共用 */
export const EVENT_TYPE_META: Record<
  EventType,
  { label: string; icon: string; color: string }
> = {
  fire: { label: '火灾', icon: '🔥', color: '#ff6b6b' },
  traffic: { label: '交通拥堵', icon: '🚗', color: '#f0c050' },
  building: { label: '建筑异常', icon: '🏢', color: '#9b8fff' }
}

/** 状态中文映射 */
export const EVENT_STATUS_LABEL: Record<EventStatus, string> = {
  pending: '待核查',
  monitoring: '监测中',
  processing: '处理中',
  resolved: '已处置'
}
