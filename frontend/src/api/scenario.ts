import { ApiError, jsonBody, loadSnapshot, request } from './http'
import { API_BASE } from '@/config/api'
import type {
  ScenarioComparison,
  ScenarioReport,
  ScenarioSessionView,
  ScenarioTemplate,
  ScenarioTemplateCreate,
  ScenarioTemplatePatch,
  ScenarioTemplateRevision,
  ScenarioVariantsResult
} from '@/types/scenario'

const LLM_TIMEOUT_MS = 90_000

async function scenarioRequest<T>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const ctrl = new AbortController()
  const timer = window.setTimeout(() => ctrl.abort(), LLM_TIMEOUT_MS)
  try {
    return await request<T>(
      path,
      body === undefined ? { signal: ctrl.signal } : { ...jsonBody(body, method), signal: ctrl.signal }
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 0) {
      throw new ApiError(0, '情景 Agent 响应超时或后端不可达')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

export function createScenarioSession(eventId?: string, templateId?: string): Promise<ScenarioSessionView> {
  return scenarioRequest('/scenario/sessions', {
    ...(eventId ? { event_id: eventId } : {}),
    ...(templateId ? { template_id: templateId } : {})
  })
}

export function getScenarioTemplates(): Promise<ScenarioTemplate[]> {
  return request(
    '/scenario/templates',
    undefined,
    () => loadSnapshot<ScenarioTemplate[]>('scenario_templates.json')
  )
}

export function createScenarioTemplate(body: ScenarioTemplateCreate): Promise<ScenarioTemplate> {
  return scenarioRequest('/scenario/templates', body)
}

export function patchScenarioTemplate(
  id: string,
  body: ScenarioTemplatePatch
): Promise<ScenarioTemplate> {
  return scenarioRequest(`/scenario/templates/${encodeURIComponent(id)}`, body, 'PATCH')
}

export function getScenarioTemplateRevisions(id: string): Promise<ScenarioTemplateRevision[]> {
  return request(`/scenario/templates/${encodeURIComponent(id)}/revisions`)
}

export function deleteScenarioTemplate(id: string): Promise<{ ok: boolean }> {
  return request(`/scenario/templates/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function sendScenarioMessage(sessionId: string, message: string): Promise<ScenarioSessionView> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/messages`, {
    message,
    auto_run: true
  })
}

export function setScenarioResources(
  sessionId: string,
  resourceIds: string[]
): Promise<ScenarioSessionView> {
  return request(
    `/scenario/sessions/${encodeURIComponent(sessionId)}/resources`,
    jsonBody({ resource_ids: resourceIds }, 'PUT')
  )
}

export function runCurrentScenarioVariants(sessionId: string): Promise<ScenarioVariantsResult> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/runs/variants`, {})
}

export function compareScenarioRuns(
  sessionId: string,
  leftRunId: string,
  rightRunId: string
): Promise<ScenarioComparison> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/compare`, {
    left_run_id: leftRunId,
    right_run_id: rightRunId
  })
}

export function generateScenarioReport(runId: string): Promise<ScenarioReport> {
  return scenarioRequest(`/scenario/runs/${encodeURIComponent(runId)}/report`, {})
}

export function scenarioExportUrl(runId: string): string {
  return `${API_BASE}/scenario/runs/${encodeURIComponent(runId)}/export`
}
