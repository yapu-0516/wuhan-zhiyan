// 城市事件状态管理（阶段3：单例 reactive store）
// 阶段11：改为通过 API 接口层取数（USE_MOCK=true 时走 mock）。
// 页面与组件统一从此 composable 取数据，避免到处写死。
import { reactive, computed } from 'vue'
import type { CityEvent, EventType } from '@/types/event'
import { getEvents } from '@/api/event'

// 模块级单例：整个应用共享同一份事件状态
const state = reactive<{ events: CityEvent[] }>({
  events: [] // 阶段3 暂为空，由 loadFromApi 填充
})

export function useCityEvents() {
  const events = computed(() => state.events)

  const stats = computed(() => {
    const total = state.events.length
    const byType = state.events.reduce<Record<EventType, number>>(
      (acc, e) => {
        acc[e.event_type] = (acc[e.event_type] ?? 0) + 1
        return acc
      },
      { fire: 0, traffic: 0, building: 0 }
    )
    return { total, byType }
  })

  /** 按 id 查事件 */
  function getEventById(id: string): CityEvent | undefined {
    return state.events.find((e) => e.id === id)
  }

  /** 内部注入（保留供测试或同步注入场景使用） */
  function setEvents(list: CityEvent[]) {
    state.events.splice(0, state.events.length, ...list)
  }

  /** 通过 API 接口层加载事件（USE_MOCK 时走 mock，接后端后走 fetch） */
  async function loadFromApi() {
    const list = await getEvents()
    setEvents(list)
  }

  return { events, stats, getEventById, setEvents, loadFromApi }
}
