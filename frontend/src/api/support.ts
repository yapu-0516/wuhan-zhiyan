import { jsonBody, loadSnapshot, qs, request } from './http'
import type {
  AuditLogRecord,
  EmergencyResource,
  NotificationRecord,
  OperatorAccount,
  ResponsibilityGrid,
  ReviewStats,
  ServiceStatus,
  SlaSummary,
  TraceabilityGraph
} from '@/types/support'

export function getSupportAccounts(): Promise<OperatorAccount[]> {
  return request('/support/accounts', undefined, () => loadSnapshot<OperatorAccount[]>('accounts.json'))
}

export function getResponsibilityGrids(district?: string): Promise<ResponsibilityGrid[]> {
  return request(
    `/support/grids${qs(district ? { district } : undefined)}`,
    undefined,
    async () => {
      const rows = await loadSnapshot<ResponsibilityGrid[]>('grids.json')
      return district ? rows.filter((item) => item.district === district) : rows
    }
  )
}

export function patchResponsibilityGrid(
  id: string,
  body: Partial<Pick<ResponsibilityGrid, 'organization' | 'owner' | 'contact' | 'risk_types' | 'bbox'>>
): Promise<ResponsibilityGrid> {
  return request(`/support/grids/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function getEmergencyResources(kind?: string, status?: string): Promise<EmergencyResource[]> {
  return request(
    `/support/emergency-resources${qs({ ...(kind ? { kind } : {}), ...(status ? { status } : {}) })}`,
    undefined,
    () => loadSnapshot<EmergencyResource[]>('emergency_resources.json')
  )
}

export function patchEmergencyResource(
  id: string,
  body: Partial<Pick<EmergencyResource, 'capability' | 'capacity' | 'available' | 'status' | 'contact' | 'notes'>>
): Promise<EmergencyResource> {
  return request(`/support/emergency-resources/${encodeURIComponent(id)}`, jsonBody(body, 'PATCH'))
}

export function getNotifications(unreadOnly = false): Promise<NotificationRecord[]> {
  return request(
    `/support/notifications${qs(unreadOnly ? { unread_only: 'true' } : undefined)}`,
    undefined,
    () => loadSnapshot<NotificationRecord[]>('notifications.json')
  )
}

export function markNotificationRead(id: number): Promise<NotificationRecord> {
  return request(`/support/notifications/${id}/read`, jsonBody({}, 'PATCH'))
}

export function markAllNotificationsRead(): Promise<{ updated: number }> {
  return request('/support/notifications/read-all', jsonBody({}, 'PATCH'))
}

export function getAuditLogs(limit = 200): Promise<AuditLogRecord[]> {
  return request(
    `/support/audit${qs({ limit })}`,
    undefined,
    () => loadSnapshot<AuditLogRecord[]>('audit.json')
  )
}

export function getSlaSummary(): Promise<SlaSummary> {
  return request('/support/sla-summary', undefined, () => loadSnapshot<SlaSummary>('sla_summary.json'))
}

export function getServiceStatus(): Promise<ServiceStatus> {
  return request('/support/service-status')
}

export function getReviewStats(): Promise<ReviewStats> {
  return request('/support/review-stats')
}

export function getTraceabilityGraph(entityType = '', entityId = '', limit = 240): Promise<TraceabilityGraph> {
  return request(
    `/traceability/graph${qs({
      ...(entityType ? { entity_type: entityType } : {}),
      ...(entityId ? { entity_id: entityId } : {}),
      limit
    })}`,
    undefined,
    () => loadSnapshot<TraceabilityGraph>('traceability_graph.json')
  )
}

export function patchRuntimeConfig(body: {
  task_pacing_sec: number
  workflow_interval_sec: number
  max_upload_mb: number
}): Promise<ServiceStatus> {
  return request('/support/config', jsonBody(body, 'PATCH'))
}
