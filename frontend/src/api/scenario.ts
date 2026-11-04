import { ApiError, jsonBody, request } from './http'
import type {
  ScenarioComparison,
  ScenarioReport,
  ScenarioRun,
  ScenarioSessionView,
  ScenarioVariantsResult
} from '@/types/scenario'

const LLM_TIMEOUT_MS = 90_000

async function scenarioRequest<T>(path: string, body?: unknown): Promise<T> {
  const ctrl = new AbortController()
  const timer = window.setTimeout(() => ctrl.abort(), LLM_TIMEOUT_MS)
  try {
    return await request<T>(path, body === undefined ? { signal: ctrl.signal } : { ...jsonBody(body), signal: ctrl.signal })
  } catch (error) {
    if (error instanceof ApiError && error.status === 0) {
      throw new ApiError(0, '情景 Agent 响应超时或后端不可达')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

export function createScenarioSession(): Promise<ScenarioSessionView> {
  return scenarioRequest('/scenario/sessions', {})
}

export function sendScenarioMessage(sessionId: string, message: string): Promise<ScenarioSessionView> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/messages`, {
    message,
    auto_run: true
  })
}

export function runCurrentScenario(sessionId: string): Promise<ScenarioRun> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/runs`, {})
}

export function runCurrentScenarioVariants(sessionId: string): Promise<ScenarioVariantsResult> {
  return scenarioRequest(`/scenario/sessions/${encodeURIComponent(sessionId)}/runs/variants`, {})
}

export function getScenarioRun(runId: string): Promise<ScenarioRun> {
  return scenarioRequest(`/scenario/runs/${encodeURIComponent(runId)}`)
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
