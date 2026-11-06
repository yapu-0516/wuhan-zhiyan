// 大模型桥接接口层（backend/app/routers/llm.py）
// 注意：模型调用为付费 API 且耗时较长（数秒~几十秒），超时放宽到 90s；不传 fallback，离线时直接抛错。
import { ApiError, jsonBody, request } from './http'
import type { AssistantReply, AssistantTurn, EventReport, ParsedTask } from '@/types/llm'

const LLM_TIMEOUT_MS = 90_000

async function llmRequest<T>(path: string, body: unknown): Promise<T> {
  const ctrl = new AbortController()
  const timer = window.setTimeout(() => ctrl.abort(), LLM_TIMEOUT_MS)
  try {
    return await request<T>(path, { ...jsonBody(body), signal: ctrl.signal })
  } catch (e) {
    // AbortError 会被 http 层包装成 status=0 的“无法连接后端服务”，改写为更准确的文案
    if (e instanceof ApiError && e.status === 0) {
      throw new ApiError(0, '大模型响应超时或后端不可达，请稍后重试')
    }
    throw e
  } finally {
    window.clearTimeout(timer)
  }
}

/** POST /api/llm/parse-task —— 自然语言 → 结构化任务 */
export function parseTaskText(text: string): Promise<ParsedTask> {
  return llmRequest<ParsedTask>('/llm/parse-task', { text })
}

/** POST /api/llm/report —— 基于事件目录数据生成结构化研判报告 */
export function generateEventReport(eventId: string): Promise<EventReport> {
  return llmRequest<EventReport>('/llm/report', { event_id: eventId })
}

/** POST /api/llm/chat —— 城市治理助手多轮问答，可选关联当前事件 */
export function chatWithAssistant(messages: AssistantTurn[], eventId?: string | null): Promise<AssistantReply> {
  return llmRequest<AssistantReply>('/llm/chat', {
    messages,
    event_id: eventId || null
  })
}
