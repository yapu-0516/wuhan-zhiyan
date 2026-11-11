import type { EventType, Severity } from './event'

export type MonitoringTaskStatus = 'draft' | 'scheduled' | 'running' | 'completed' | 'failed'
export type ScheduleType = 'instant' | 'periodic' | 'special' | 'drill'
export type MonitoringRunStatus = 'pending' | 'running' | 'completed' | 'failed'
export type AssessmentDecision = 'candidate' | 'needs_review' | 'confirmed' | 'false_alarm'
export type WorkOrderStatus =
  | 'pending'
  | 'accepted'
  | 'in_progress'
  | 'completed'
  | 'verified'
  | 'rejected'
  | 'cancelled'
export type ReviewEntityType = 'event' | 'monitoring_task' | 'drill'
export type ReviewStatus = 'draft' | 'confirmed'

export interface MonitoringTask {
  id: string
  name: string
  event_type: EventType
  schedule_type: ScheduleType
  status: MonitoringTaskStatus
  area_name: string
  bbox: number[]
  data_source_ids: string[]
  rule_config: Record<string, unknown>
  owner: string
  notify_targets: string[]
  template_key: string | null
  start_at: string | null
  end_at: string | null
  next_run_at: string | null
  last_run_at: string | null
  created_at: string
  updated_at: string
}

export interface MonitoringTaskCreate {
  name: string
  event_type: EventType
  schedule_type: ScheduleType
  area_name?: string
  data_source_ids?: string[]
  rule_config?: Record<string, unknown>
  owner?: string
  notify_targets?: string[]
  template_key?: string | null
  start_at?: string | null
  end_at?: string | null
  next_run_at?: string | null
}

export interface MonitoringTaskTemplate {
  id: string
  name: string
  description: string
  event_type: EventType
  schedule_type: ScheduleType
  area_name: string
  bbox: number[]
  data_source_ids: string[]
  rule_config: Record<string, unknown>
  owner: string
  notify_targets: string[]
  created_at: string
  updated_at: string
}

export type MonitoringTaskTemplateCreate = Omit<MonitoringTaskTemplate, 'id' | 'created_at' | 'updated_at'>

export interface MonitoringRun {
  id: string
  monitoring_task_id: string
  analysis_task_id: string | null
  event_ids: string[]
  status: MonitoringRunStatus
  coverage: Record<string, unknown>
  quality: Record<string, unknown>
  failure_reason: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export interface MonitoringExecuteResult {
  monitoring_run: MonitoringRun
  analysis_task: import('./api').AnalysisTask
}

export interface Assessment {
  id: string
  event_id: string
  monitoring_run_id: string | null
  decision: AssessmentDecision
  summary: string
  evidence: Array<Record<string, unknown>>
  impact: Record<string, unknown>
  missing_information: string[]
  priority: Severity
  operator: string
  created_at: string
}

export interface AssessmentContext {
  event_id: string
  longitude: number
  latitude: number
  district: string
  grid: string
  radius_m: number
  buildings: Array<{ id: string; name: string; category: string; distance_m: number; risk_level: string }>
  roads: Array<{ id: string; name: string; highway: string; distance_m: number }>
  pois: Array<{ id: string; name: string; kind: string; distance_m: number }>
}

export interface CandidateMergeResult {
  primary: import('./event').CityEvent
  merged: import('./event').CityEvent
}

export interface AssessmentCreate {
  event_id: string
  monitoring_run_id?: string | null
  decision: AssessmentDecision
  summary: string
  evidence?: Array<Record<string, unknown>>
  impact?: Record<string, unknown>
  missing_information?: string[]
  priority?: Severity
  operator?: string
}

export interface WorkOrder {
  id: string
  event_id: string
  assessment_id: string | null
  scenario_run_id: string | null
  title: string
  unit: string
  assignee: string
  status: WorkOrderStatus
  priority: Severity
  description: string
  due_at: string | null
  feedback: Array<Record<string, unknown>>
  sla?: WorkOrderSla
  created_at: string
  updated_at: string
}

export interface WorkOrderSla {
  accepted_at: string | null
  started_at: string | null
  completed_at: string | null
  verified_at: string | null
  response_min: number | null
  execution_min: number | null
  review_min: number | null
  elapsed_min: number
  remaining_min: number | null
  overdue: boolean
}

export interface WorkOrderFeedbackCreate {
  note: string
  longitude?: number | null
  latitude?: number | null
  operator?: string
  files?: File[]
}

export interface WorkOrderCreate {
  event_id: string
  assessment_id?: string | null
  scenario_run_id?: string | null
  title: string
  unit?: string
  assignee?: string
  priority?: Severity
  description?: string
  due_at?: string | null
}

export interface ScenarioActionCreate {
  title: string
  unit?: string
  assignee?: string
  priority?: Severity
  description?: string
}

export interface ScenarioDispatchCreate {
  event_id: string
  assessment_id?: string | null
  actions?: ScenarioActionCreate[]
}

export interface ReviewRecord {
  id: string
  entity_type: ReviewEntityType
  entity_id: string
  status: ReviewStatus
  summary: string
  metrics: Record<string, unknown>
  findings: string[]
  recommendations: string[]
  created_at: string
  updated_at: string
}

export interface ReviewCreate {
  entity_type: ReviewEntityType
  entity_id: string
  status?: ReviewStatus
  summary: string
  metrics?: Record<string, unknown>
  findings?: string[]
  recommendations?: string[]
}

export interface ReviewUpdate {
  status?: ReviewStatus
  summary?: string
  metrics?: Record<string, unknown>
  findings?: string[]
  recommendations?: string[]
}

export interface TaskTemplateRevision {
  id: number
  template_id: string
  version_no: number
  rule_config: Record<string, unknown>
  source_review_id: string | null
  operator: string
  created_at: string
}

export interface ReviewDraft {
  entity_type: ReviewEntityType
  entity_id: string
  summary: string
  metrics: Record<string, unknown>
  findings: string[]
  recommendations: string[]
  timeline: Array<{ at: string; kind: string; operator: string; text: string; ref: string }>
}

export const TASK_STATUS_META: Record<MonitoringTaskStatus, { label: string; color: string }> = {
  draft: { label: '草稿', color: '#92969a' },
  scheduled: { label: '已排程', color: '#67c6df' },
  running: { label: '运行中', color: '#d8aa57' },
  completed: { label: '已完成', color: '#72c39a' },
  failed: { label: '失败', color: '#e4777b' }
}

export const SCHEDULE_META: Record<ScheduleType, string> = {
  instant: '即时',
  periodic: '周期监测',
  special: '专项',
  drill: '演练'
}

export const RUN_STATUS_META: Record<MonitoringRunStatus, { label: string; color: string }> = {
  pending: { label: '待执行', color: '#92969a' },
  running: { label: '执行中', color: '#d8aa57' },
  completed: { label: '已完成', color: '#72c39a' },
  failed: { label: '失败', color: '#e4777b' }
}

export const DECISION_META: Record<AssessmentDecision, { label: string; color: string }> = {
  candidate: { label: '线索', color: '#9ab0ba' },
  needs_review: { label: '待补核', color: '#d8aa57' },
  confirmed: { label: '已确认', color: '#72c39a' },
  false_alarm: { label: '误报', color: '#92969a' }
}

export const ORDER_STATUS_META: Record<WorkOrderStatus, { label: string; color: string; hint: string }> = {
  pending: { label: '待接单', color: '#92969a', hint: '等待责任单位受理' },
  accepted: { label: '已接单', color: '#67c6df', hint: '责任单位已接单' },
  in_progress: { label: '执行中', color: '#d8aa57', hint: '现场处置进行中' },
  completed: { label: '待复核', color: '#9ab0ba', hint: '执行完成，等待调度复核' },
  verified: { label: '已复核', color: '#72c39a', hint: '复核通过' },
  rejected: { label: '复核退回', color: '#e4777b', hint: '需要补充处置或反馈' },
  cancelled: { label: '已取消', color: '#707478', hint: '工单已取消' }
}

export const ORDER_TRANSITIONS: Record<WorkOrderStatus, WorkOrderStatus[]> = {
  pending: ['accepted', 'in_progress', 'cancelled'],
  accepted: ['in_progress', 'rejected', 'cancelled'],
  in_progress: ['completed', 'cancelled'],
  completed: ['verified', 'rejected'],
  rejected: ['in_progress', 'cancelled'],
  verified: [],
  cancelled: []
}

export const TASK_TRANSITIONS: Record<MonitoringTaskStatus, MonitoringTaskStatus[]> = {
  draft: ['scheduled', 'running'],
  scheduled: ['running', 'failed'],
  running: ['completed', 'failed'],
  failed: ['scheduled', 'running'],
  completed: ['scheduled', 'running']
}
