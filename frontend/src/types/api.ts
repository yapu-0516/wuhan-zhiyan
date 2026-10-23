// 通用接口类型 —— 与 docs/api.md §1 §4~§9 保持一致
import type { CityEvent, EventType, EventStatus, Severity } from './event'
import type { TrafficLevel } from './building'

// ---------- 系统 ----------
export interface AlgorithmInfo {
  type: EventType
  name: string
  method: string
  version: string
}

export interface SystemInfo {
  name: string
  version: string
  demo_mode: boolean
  simulator: { enabled: boolean; interval_sec: number }
  database: string
  uptime_sec: number
  region: { name: string; city: string; center: [number, number]; bbox: [number, number, number, number] }
  algorithms: AlgorithmInfo[]
}

// ---------- 统计 ----------
export type TrendPoint = { time: string } & Record<EventType, number>

export interface Overview {
  total: number
  active: number
  today: number
  resolved_today: number
  resolve_rate: number
  avg_response_min: number
  by_type: Record<EventType, number>
  by_status: Record<EventStatus, number>
  by_severity: Record<Severity, number>
  by_district: { name: string; count: number }[]
  trend: TrendPoint[]
  city_index: {
    traffic_tpi: number
    traffic_level: TrafficLevel
    safety_score: number
    sensors_online: number
    sensors_total: number
  }
  updated_at: string
}

// ---------- 数据资产 ----------
export interface DataItem {
  id?: string
  /** 数据名称 */
  name: string
  /** 数据类型：遥感影像 | 无人机影像 | 视频流 | 三维模型 | 传感器数据 | 矢量数据 */
  type: string
  /** 获取时间 yyyy-MM-dd HH:mm */
  time: string
  /** 数据状态：已入库 | 处理中 | 采集中 | 待接入 */
  status: string
  source?: string
  format?: string
  size?: string
  size_bytes?: number
  records?: number
  description?: string
  url?: string | null
}

export interface DataStats {
  total: number
  total_size: string
  by_type: { type: string; count: number }[]
}

// ---------- AI 分析任务 ----------
export type TaskStatus = 'prototype' | 'pending' | 'running' | 'done' | 'failed'

export interface Detection {
  label: string
  confidence: number
  /** [x, y, w, h] 像素坐标 */
  bbox: [number, number, number, number]
  area_ratio?: number
}

export interface TaskArtifact {
  name: string
  url: string
  kind: 'image' | 'chart' | 'json'
}

export interface TaskResult {
  detected: boolean
  confidence: number
  summary: string
  detections: Detection[]
  metrics: Record<string, number | string>
  artifacts: TaskArtifact[]
  series?: ({ t: string; v: number } & Record<string, number | string>)[] | null
  event_ids: string[]
}

export interface AnalysisTask {
  id: string
  /** 分析类型：fire / traffic / building / flood */
  type: string
  status: TaskStatus
  /** 兼容第3周原型字段名 */
  createdAt: string
  finished_at?: string | null
  progress?: number
  file_count?: number
  inputs?: { name: string; url: string }[]
  algorithm?: { name: string; version: string; method: string }
  location?: { longitude: number; latitude: number } | null
  result?: TaskResult | null
  error?: string | null
}

export interface TaskCreate {
  type: string
  fileCount: number
  sample_id?: string
  longitude?: number
  latitude?: number
  create_event?: boolean
}

export interface Sample {
  id: string
  type: EventType
  name: string
  description: string
  kind: 'image' | 'csv' | 'image_pair'
  thumbnail_url: string
  files: string[]
  longitude?: number
  latitude?: number
}

// ---------- 监测数据源 ----------
export interface DataSource {
  id: string
  name: string
  type: 'drone' | 'satellite' | 'video' | 'sensor' | 'other'
  icon: string
  desc: string
  status: '在线' | '采集中' | '离线' | '待接入'
  devices_online: number
  devices_total: number
  throughput: number
  unit: string
  last_active: string
  coverage: string
}

// ---------- WebSocket ----------
export interface TrafficUpdate {
  city_tpi: number
  level: TrafficLevel
  roads: { id: string; speed: number; tpi: number; level: TrafficLevel }[]
}

export interface SensorTick {
  sources: { id: string; throughput: number; devices_online: number }[]
}

export type WsMessage =
  | { type: 'hello'; data: { server_time: string; demo_mode: boolean; clients: number }; ts: string }
  | { type: 'event.created'; data: CityEvent; ts: string }
  | { type: 'event.updated'; data: CityEvent; ts: string }
  | { type: 'task.updated'; data: AnalysisTask; ts: string }
  | { type: 'traffic.updated'; data: TrafficUpdate; ts: string }
  | { type: 'sensor.tick'; data: SensorTick; ts: string }
  | { type: 'heartbeat'; data: Record<string, never>; ts: string }
  | { type: 'pong'; data?: unknown; ts?: string }

export type WsMessageType = WsMessage['type']
