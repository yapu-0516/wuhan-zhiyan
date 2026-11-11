import { jsonBody, loadSnapshot, qs, request } from './http'
import { API_BASE } from '@/config/api'
import type {
  Assessment,
  AssessmentContext,
  CandidateMergeResult,
  AssessmentCreate,
  MonitoringRun,
  MonitoringExecuteResult,
  MonitoringTask,
  MonitoringTaskCreate,
  MonitoringTaskTemplate,
  MonitoringTaskTemplateCreate,
  ReviewCreate,
  ReviewUpdate,
  ReviewRecord,
  ReviewDraft,
  ScenarioDispatchCreate,
  TaskTemplateRevision,
  WorkOrder,
  WorkOrderCreate,
  WorkOrderFeedbackCreate
} from '@/types/workflow'
import type { MonitoringTaskStatus, WorkOrderStatus } from '@/types/workflow'

export function getMonitoringTasks(status?: MonitoringTaskStatus): Promise<MonitoringTask[]> {
  return request(`/monitoring-tasks${qs(status ? { status } : undefined)}`, undefined, async () => {
    const list = await loadSnapshot<MonitoringTask[]>('monitoring_tasks.json')
    return status ? list.filter((item) => item.status === status) : list
  })
}

export function createMonitoringTask(body: MonitoringTaskCreate): Promise<MonitoringTask> {
  return request('/monitoring-tasks', jsonBody(body, 'POST'))
}

export function getTaskTemplates(): Promise<MonitoringTaskTemplate[]> {
  return request('/task-templates', undefined, () => loadSnapshot<MonitoringTaskTemplate[]>('task_templates.json'))
}

export function createTaskTemplate(body: MonitoringTaskTemplateCreate): Promise<MonitoringTaskTemplate> {
  return request('/task-templates', jsonBody(body, 'POST'))
}

export function deleteTaskTemplate(id: string): Promise<{ ok: boolean }> {
  return request(`/task-templates/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function patchTaskTemplate(
  id: string,
  body: Partial<Omit<MonitoringTaskTemplate, 'id' | 'event_type' | 'created_at' | 'updated_at'>>
): Promise<MonitoringTaskTemplate> {
  return request(`/task-templates/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function getTaskTemplateRevisions(id: string): Promise<TaskTemplateRevision[]> {
  return request(`/task-templates/${encodeURIComponent(id)}/revisions`)
}

export function patchMonitoringTask(
  id: string,
  body: Partial<Pick<MonitoringTask, 'status' | 'owner' | 'rule_config' | 'next_run_at'>>
): Promise<MonitoringTask> {
  return request(`/monitoring-tasks/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function getMonitoringRuns(taskId?: string): Promise<MonitoringRun[]> {
  return request(`/monitoring-runs${qs(taskId ? { task_id: taskId } : undefined)}`, undefined, async () => {
    const list = await loadSnapshot<MonitoringRun[]>('monitoring_runs.json')
    return taskId ? list.filter((item) => item.monitoring_task_id === taskId) : list
  })
}

export function executeMonitoringTask(taskId: string, sampleId?: string): Promise<MonitoringExecuteResult> {
  return request(`/monitoring-tasks/${encodeURIComponent(taskId)}/execute`, jsonBody({ sample_id: sampleId ?? null }, 'POST'))
}

export function getAssessments(eventId?: string): Promise<Assessment[]> {
  return request(`/assessments${qs(eventId ? { event_id: eventId } : undefined)}`, undefined, async () => {
    const list = await loadSnapshot<Assessment[]>('assessments.json')
    return eventId ? list.filter((item) => item.event_id === eventId) : list
  })
}

export function getAssessmentContext(eventId: string, radiusM = 300): Promise<AssessmentContext> {
  return request(`/assessments/context${qs({ event_id: eventId, radius_m: radiusM })}`)
}

export function mergeCandidateEvents(
  primaryEventId: string,
  relatedEventId: string,
  operator: string,
  note = ''
): Promise<CandidateMergeResult> {
  return request(
    '/assessments/candidates/merge',
    jsonBody(
      {
        primary_event_id: primaryEventId,
        related_event_id: relatedEventId,
        operator,
        note
      },
      'POST'
    )
  )
}

export function createAssessment(body: AssessmentCreate): Promise<Assessment> {
  return request('/assessments', jsonBody(body, 'POST'))
}

export function getWorkOrders(status?: WorkOrderStatus, eventId?: string): Promise<WorkOrder[]> {
  return request(`/work-orders${qs({ ...(status ? { status } : {}), ...(eventId ? { event_id: eventId } : {}) })}`, undefined, async () => {
    let list = await loadSnapshot<WorkOrder[]>('work_orders.json')
    if (status) list = list.filter((item) => item.status === status)
    if (eventId) list = list.filter((item) => item.event_id === eventId)
    return list
  })
}

export function createWorkOrder(body: WorkOrderCreate): Promise<WorkOrder> {
  return request('/work-orders', jsonBody(body, 'POST'))
}

export function dispatchScenarioRun(runId: string, body: ScenarioDispatchCreate): Promise<WorkOrder[]> {
  return request(
    `/scenario-runs/${encodeURIComponent(runId)}/dispatch`,
    jsonBody(body, 'POST')
  )
}

export function patchWorkOrder(
  id: string,
  body: { status?: WorkOrderStatus; assignee?: string; operator?: string; note?: string; feedback?: Record<string, unknown> }
): Promise<WorkOrder> {
  return request(`/work-orders/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function uploadWorkOrderFeedback(
  id: string,
  body: WorkOrderFeedbackCreate
): Promise<WorkOrder> {
  const fd = new FormData()
  fd.append('note', body.note)
  if (body.operator) fd.append('operator', body.operator)
  if (body.longitude !== null && body.longitude !== undefined) fd.append('longitude', String(body.longitude))
  if (body.latitude !== null && body.latitude !== undefined) fd.append('latitude', String(body.latitude))
  body.files?.forEach((file) => fd.append('files', file))
  return request(`/work-orders/${encodeURIComponent(id)}/feedback`, { method: 'POST', body: fd })
}

export function assessWorkOrderFeedback(
  orderId: string,
  index: number,
  operator: string,
  summary = ''
): Promise<Assessment> {
  return request(
    `/work-orders/${encodeURIComponent(orderId)}/feedback/${index}/assess`,
    jsonBody({ operator, summary }, 'POST')
  )
}

export function useWorkOrderResource(
  orderId: string,
  body: { resource_id: string; quantity: number; note: string; operator: string }
): Promise<WorkOrder> {
  return request(
    `/work-orders/${encodeURIComponent(orderId)}/resources/use`,
    jsonBody(body, 'POST')
  )
}

export function getReviews(entityType?: string, entityId?: string): Promise<ReviewRecord[]> {
  return request(
    `/reviews${qs({ ...(entityType ? { entity_type: entityType } : {}), ...(entityId ? { entity_id: entityId } : {}) })}`,
    undefined,
    async () => {
      let list = await loadSnapshot<ReviewRecord[]>('reviews.json')
      if (entityType) list = list.filter((item) => item.entity_type === entityType)
      if (entityId) list = list.filter((item) => item.entity_id === entityId)
      return list
    }
  )
}

export function createReview(body: ReviewCreate): Promise<ReviewRecord> {
  return request('/reviews', jsonBody(body, 'POST'))
}

export function getReviewDraft(entityType: string, entityId: string): Promise<ReviewDraft> {
  return request(`/reviews/draft${qs({ entity_type: entityType, entity_id: entityId })}`)
}

export function getReviewCases(q?: string): Promise<ReviewRecord[]> {
  return request(`/reviews/cases${qs(q ? { q } : undefined)}`, undefined, async () => {
    const list = await loadSnapshot<ReviewRecord[]>('reviews.json')
    const cases = list.filter((item) => item.status === 'confirmed')
    if (!q?.trim()) return cases
    const needle = q.trim().toLowerCase()
    return cases.filter((item) => `${item.id}${item.entity_id}${item.summary}`.toLowerCase().includes(needle))
  })
}

export function updateReview(id: string, body: ReviewUpdate): Promise<ReviewRecord> {
  return request(`/reviews/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function applyReviewToTemplate(
  reviewId: string,
  body: { template_id: string; rule_config: Record<string, unknown>; operator: string }
): Promise<TaskTemplateRevision> {
  return request(`/reviews/${encodeURIComponent(reviewId)}/apply-template`, jsonBody(body, 'POST'))
}

export function reviewExportUrl(id: string): string {
  return `${API_BASE}/reviews/${encodeURIComponent(id)}/export`
}
