// 模拟城市事件数据（阶段6）
// ⚠️ 明确标记为 mock 数据：当前没有真实 AI 模型，
//    这些事件仅用于前端三维可视化与交互联调，不代表真实检测结果。
// 阶段11 之后将切换为调用真实 FastAPI 接口获取 AI 结果。
import type { CityEvent } from '@/types/event'

// 3 类事件：火灾 / 交通拥堵 / 建筑异常
// 经纬度布置在武汉市中心（114.30, 30.52）北方 600~1300m，
// 与测试建筑同处相机俯视视野中心，便于阶段7在三维场景中一并观察。
// 1° 纬度 ≈ 111km。
export const mockEvents: CityEvent[] = [
  {
    id: 'E001',
    event_type: 'fire',
    name: '火灾事件',
    longitude: 114.3005,
    latitude: 30.5260,
    confidence: 0.93,
    status: 'processing',
    timestamp: '2026-09-28 10:30:00'
  },
  {
    id: 'E002',
    event_type: 'traffic',
    name: '交通拥堵',
    longitude: 114.3015,
    latitude: 30.5290,
    confidence: 0.88,
    status: 'monitoring',
    timestamp: '2026-09-28 10:15:00'
  },
  {
    id: 'E003',
    event_type: 'building',
    name: '建筑异常',
    longitude: 114.2995,
    latitude: 30.5315,
    confidence: 0.91,
    status: 'pending',
    timestamp: '2026-09-28 09:50:00'
  }
]
