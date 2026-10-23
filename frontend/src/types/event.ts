// 城市事件类型定义 —— 与 docs/api.md §2 保持一致
// v1：在第3周原型字段基础上扩展 severity / source / district / evidence 等字段，原字段语义不变。

export type EventType = 'fire' | 'traffic' | 'building' | 'flood'

export type EventStatus = 'pending' | 'monitoring' | 'processing' | 'resolved'

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export type EventSource = 'drone' | 'satellite' | 'video' | 'sensor' | 'citizen' | 'ai_task'

export interface CityEvent {
  /** 事件编号，如 E0001 */
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
  /** 事件等级 */
  severity: Severity
  /** 发现来源 */
  source: EventSource
  /** 所属行政区 */
  district: string
  /** 地址描述 */
  address: string
  /** 网格化管理编号 */
  grid: string
  /** 事件描述（算法结论 / 上报内容） */
  description: string
  building_id?: string | null
  road_id?: string | null
  task_id?: string | null
  /** 算法标注证据图 */
  evidence_url?: string | null
  /** 算法指标 */
  metrics: Record<string, number | string>
  /** 当前处置单位 */
  assignee?: string | null
  updated_at: string
}

export type EventLogAction = 'created' | 'status_changed' | 'assigned' | 'comment' | 'ai_detected'

export interface EventLog {
  id: number
  event_id: string
  action: EventLogAction
  from_status: EventStatus | null
  to_status: EventStatus | null
  operator: string
  note: string
  timestamp: string
}

/** PATCH /api/events/{id} 请求体 */
export interface EventPatch {
  status?: EventStatus
  assignee?: string
  operator?: string
  note?: string
}

/** POST /api/events 请求体 */
export interface EventCreate {
  event_type: EventType
  name: string
  longitude: number
  latitude: number
  severity?: Severity
  description?: string
  source?: EventSource
  confidence?: number
}

export const EVENT_TYPES: EventType[] = ['fire', 'traffic', 'building', 'flood']

/** 事件类型展示元信息（中文标签、Emoji 图标、主题色），供 UI 与 Cesium 共用 */
export const EVENT_TYPE_META: Record<EventType, { label: string; icon: string; color: string }> = {
  fire: { label: '火灾', icon: '🔥', color: '#ff6b6b' },
  traffic: { label: '交通拥堵', icon: '🚗', color: '#f0c050' },
  building: { label: '建筑异常', icon: '🏢', color: '#9b8fff' },
  flood: { label: '内涝积水', icon: '🌊', color: '#3fa9ff' }
}

/** 状态中文映射 */
export const EVENT_STATUS_LABEL: Record<EventStatus, string> = {
  pending: '待核查',
  monitoring: '监测中',
  processing: '处置中',
  resolved: '已办结'
}

export const EVENT_STATUS_COLOR: Record<EventStatus, string> = {
  pending: '#ff9f43',
  monitoring: '#4fc3f7',
  processing: '#f0c050',
  resolved: '#4dd984'
}

/** 合法的状态流转（与后端状态机一致） */
export const STATUS_TRANSITIONS: Record<EventStatus, EventStatus[]> = {
  pending: ['monitoring', 'processing', 'resolved'],
  monitoring: ['processing', 'resolved'],
  processing: ['resolved'],
  resolved: ['processing']
}

export const SEVERITY_META: Record<Severity, { label: string; short: string; color: string; rank: number }> = {
  low: { label: 'Ⅳ级 一般', short: 'Ⅳ', color: '#4fc3f7', rank: 1 },
  medium: { label: 'Ⅲ级 较大', short: 'Ⅲ', color: '#f0c050', rank: 2 },
  high: { label: 'Ⅱ级 重大', short: 'Ⅱ', color: '#ff9f43', rank: 3 },
  critical: { label: 'Ⅰ级 特别重大', short: 'Ⅰ', color: '#ff4d4f', rank: 4 }
}

export const SOURCE_META: Record<EventSource, { label: string; icon: string }> = {
  drone: { label: '无人机巡检', icon: '🚁' },
  satellite: { label: '卫星遥感', icon: '🛰️' },
  video: { label: '视频监控', icon: '📹' },
  sensor: { label: '物联感知', icon: '📡' },
  citizen: { label: '市民上报', icon: '🙋' },
  ai_task: { label: 'AI 分析任务', icon: '🧠' }
}
