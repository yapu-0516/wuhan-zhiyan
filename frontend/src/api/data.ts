// 数据接口层 —— docs/api.md §5
import { request, loadSnapshot, apiState } from './http'
import type { DataItem, DataStats } from '@/types/api'

/** 获取数据资产清单 GET /api/data */
export function getDataList(): Promise<DataItem[]> {
  return request('/data', undefined, () => loadSnapshot<DataItem[]>('data.json'))
}

/** 数据资产统计 GET /api/data/stats */
export function getDataStats(): Promise<DataStats> {
  return request('/data/stats', undefined, () => loadSnapshot<DataStats>('data_stats.json'))
}

/** 上传数据 POST /api/data/upload */
export function uploadData(files: File[], type?: string): Promise<DataItem[]> {
  if (apiState.mode !== 'live') return Promise.reject(new Error('离线演示模式下不支持上传，请启动后端服务'))
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  if (type) fd.append('type', type)
  return request('/data/upload', { method: 'POST', body: fd })
}

export type { DataItem, DataStats }
