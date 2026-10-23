// AI 分析任务接口层 —— docs/api.md §6
// 后端在线：任务异步执行真实算法，进度经 WebSocket task.updated 推送；
// 离线/快照模式：createTask 返回 prototype 状态，调用方据此提示，不伪造分析结果。
import { request, jsonBody, loadSnapshot, apiState, qs, nowString } from './http'
import type { AnalysisTask, Sample, TaskCreate } from '@/types/api'

export type { AnalysisTask, Sample }

function prototypeTask(type: string, fileCount: number): AnalysisTask {
  return { id: `T${Date.now()}`, type, status: 'prototype', createdAt: nowString(), file_count: fileCount }
}

/** 获取任务列表 GET /api/tasks */
export function getTasks(): Promise<AnalysisTask[]> {
  return request('/tasks', undefined, () => loadSnapshot<AnalysisTask[]>('tasks.json').catch(() => []))
}

/** 获取任务详情 GET /api/tasks/{id} */
export function getTask(id: string): Promise<AnalysisTask> {
  return request(`/tasks/${encodeURIComponent(id)}`, undefined, async () => {
    const t = (await loadSnapshot<AnalysisTask[]>('tasks.json')).find((x) => x.id === id)
    if (!t) throw new Error('任务不存在')
    return t
  })
}

/** 创建分析任务 POST /api/tasks（使用示例数据，或兼容原型调用） */
export async function createTask(
  type: string,
  fileCount: number,
  extra?: Omit<TaskCreate, 'type' | 'fileCount'>
): Promise<AnalysisTask> {
  if (apiState.mode !== 'live') return prototypeTask(type, fileCount)
  return request<AnalysisTask>('/tasks', jsonBody({ type, fileCount, ...extra }), () => prototypeTask(type, fileCount))
}

/** 上传文件并创建分析任务 POST /api/tasks/upload */
export async function uploadTask(
  type: string,
  files: File[],
  opts?: { longitude?: number; latitude?: number; create_event?: boolean }
): Promise<AnalysisTask> {
  if (apiState.mode !== 'live') return prototypeTask(type, files.length)
  const fd = new FormData()
  fd.append('type', type)
  files.forEach((f) => fd.append('files', f))
  if (opts?.longitude !== undefined) fd.append('longitude', String(opts.longitude))
  if (opts?.latitude !== undefined) fd.append('latitude', String(opts.latitude))
  if (opts?.create_event !== undefined) fd.append('create_event', String(opts.create_event))
  return request<AnalysisTask>('/tasks/upload', { method: 'POST', body: fd }, () => prototypeTask(type, files.length))
}

/** 示例数据 GET /api/samples */
export function getSamples(type?: string): Promise<Sample[]> {
  return request(`/samples${qs({ type })}`, undefined, async () => {
    const all = await loadSnapshot<Sample[]>('samples.json').catch(() => [] as Sample[])
    return type ? all.filter((s) => s.type === type) : all
  })
}
