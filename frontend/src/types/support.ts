export type OperatorRole = 'duty' | 'analyst' | 'dispatcher' | 'field' | 'data_admin' | 'admin'

export interface OperatorAccount {
  id: string
  name: string
  role: OperatorRole
  organization: string
  grid_ids: string[]
  status: 'active' | 'inactive'
  contact: string
  created_at: string
  updated_at: string
}

export interface ResponsibilityGrid {
  id: string
  district: string
  name: string
  organization: string
  owner: string
  contact: string
  bbox: number[]
  risk_types: string[]
  created_at: string
}

export interface EmergencyResource {
  id: string
  name: string
  kind: string
  longitude: number
  latitude: number
  capability: string
  capacity: number
  available: number
  status: 'available' | 'limited' | 'unavailable'
  contact: string
  notes: string
  updated_at: string
}

export type NotificationLevel = 'info' | 'success' | 'warning' | 'critical'

export interface NotificationRecord {
  id: number
  target: string
  title: string
  body: string
  level: NotificationLevel
  entity_type: string
  entity_id: string
  is_read: boolean
  created_at: string
}

export interface AuditLogRecord {
  id: number
  method: string
  path: string
  action: string
  entity_type: string
  entity_id: string
  operator_id: string
  operator_name: string
  role: string
  status_code: number
  summary: string
  before_data: Record<string, unknown>
  after_data: Record<string, unknown>
  created_at: string
}

export interface SlaSummary {
  total_orders: number
  active_orders: number
  overdue_orders: number
  verified_orders: number
  avg_response_min: number | null
  avg_execution_min: number | null
  avg_review_min: number | null
  by_unit: Array<{ name: string; count: number; overdue: number }>
  by_priority: Array<{ name: string; count: number; overdue: number }>
  by_scenario: Array<{ name: string; count: number; overdue: number }>
  trend: Array<{
    date: string
    total: number
    verified: number
    overdue: number
    avg_response_min: number | null
    avg_execution_min: number | null
  }>
  orders: import('./workflow').WorkOrder[]
}

export interface TraceabilityNode {
  id: string
  entity_type: string
  entity_id: string
  label: string
  display_name: string
  stage: string
  color: string
  status: string
  timestamp: string
  summary: string
  details: Record<string, unknown>
}

export interface TraceabilityEdge {
  id: string
  source: string
  target: string
  relation: string
}

export interface TraceabilityGraph {
  generated_at: string
  root: { entity_type: string; entity_id: string }
  nodes: TraceabilityNode[]
  edges: TraceabilityEdge[]
  stats: {
    nodes: number
    edges: number
    available_nodes: number
    available_edges: number
    truncated: boolean
  }
}

export interface ServiceStatus {
  database: string
  simulator_enabled: boolean
  workflow_interval_sec: number
  task_pacing_sec: number
  max_upload_mb: number
  work_order_max_attachment_mb: number
  task_counts: Record<string, number>
  run_counts: Record<string, number>
  overdue_orders: number
  unread_notifications: number
  data_counts: Record<string, number>
  algorithms: Array<{ type: string; name: string; method: string; version: string }>
}

export interface ReviewStats {
  confirmed: number
  draft: number
  by_entity_type: Array<{ name: string; count: number; confirmed: number; draft: number }>
}

export const OPERATOR_ROLE_META: Record<OperatorRole, { label: string; color: string }> = {
  duty: { label: '值班监测', color: '#67c6df' },
  analyst: { label: '研判分析', color: '#9b8fff' },
  dispatcher: { label: '指挥调度', color: '#f0c050' },
  field: { label: '现场处置', color: '#72c39a' },
  data_admin: { label: '数据维护', color: '#5eead4' },
  admin: { label: '系统管理', color: '#92969a' }
}

export const NOTIFICATION_META: Record<NotificationLevel, { label: string; color: string }> = {
  info: { label: '信息', color: '#67c6df' },
  success: { label: '完成', color: '#72c39a' },
  warning: { label: '提醒', color: '#f0c050' },
  critical: { label: '紧急', color: '#e4777b' }
}
