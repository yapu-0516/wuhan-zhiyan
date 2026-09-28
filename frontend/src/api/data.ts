// 数据接口层 —— 阶段11
// 对应后端：GET /api/data
// 第3周 USE_MOCK=true 返回 mock；第4周接 FastAPI 后改 fetch。
import { mockDataList, type DataItem } from '@/mock/data'
import { API_BASE, USE_MOCK } from '@/config/api'

/** 获取数据资产清单 GET /api/data */
export async function getDataList(): Promise<DataItem[]> {
  if (USE_MOCK) {
    return mockDataList
  }
  const res = await fetch(`${API_BASE}/data`)
  if (!res.ok) throw new Error(`获取数据清单失败: ${res.status}`)
  return (await res.json()) as DataItem[]
}

export type { DataItem }
