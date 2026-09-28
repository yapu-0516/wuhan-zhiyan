// 任务接口层 —— 阶段11
// 对应后端：GET /api/tasks、POST /api/tasks
// 第3周前端原型：AI 分析任务尚未接入真实后端，createTask 返回原型标记，
//   调用方（AIAnalysis）据此提示"第3周原型，接口后续接入"，不伪造分析结果。
// 第4周接 FastAPI 后改 fetch 真实创建任务。
import { API_BASE, USE_MOCK } from '@/config/api'

export interface AnalysisTask {
  id: string
  /** 分析类型：fire / traffic / building */
  type: string
  status: 'prototype' | 'pending' | 'running' | 'done'
  createdAt: string
}

/** 获取任务列表 GET /api/tasks */
export async function getTasks(): Promise<AnalysisTask[]> {
  if (USE_MOCK) {
    return []
  }
  const res = await fetch(`${API_BASE}/tasks`)
  if (!res.ok) throw new Error(`获取任务列表失败: ${res.status}`)
  return (await res.json()) as AnalysisTask[]
}

/** 创建分析任务 POST /api/tasks
 *  第3周返回 prototype 状态任务，调用方据此提示原型，不伪造 AI 结果。 */
export async function createTask(type: string, fileCount: number): Promise<AnalysisTask> {
  if (USE_MOCK) {
    return {
      id: `T${Date.now()}`,
      type,
      status: 'prototype',
      createdAt: new Date().toISOString()
    }
  }
  const res = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, fileCount })
  })
  if (!res.ok) throw new Error(`创建任务失败: ${res.status}`)
  return (await res.json()) as AnalysisTask
}
