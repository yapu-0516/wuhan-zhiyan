// 城市事件状态管理（模块级单例 reactive store）
// v1：经 API 层加载；订阅 WebSocket event.created / event.updated 实时增量更新。
// 页面与组件统一从此 composable 取数据，避免到处写死。
import { reactive, computed, ref } from 'vue'
import type { CityEvent, EventPatch, EventStatus, EventType } from '@/types/event'
import { EVENT_TYPES } from '@/types/event'
import { getEvents, patchEvent } from '@/api/event'
import { useRealtime } from './useRealtime'

const state = reactive<{ events: CityEvent[]; loaded: boolean }>({ events: [], loaded: false })

/** 最近一次实时新增的事件（供三维场景脉冲动画、通知使用） */
const lastCreated = ref<CityEvent | null>(null)
/** 每次实时变更自增，供统计面板等做节流刷新 */
const revision = ref(0)
let wired = false

function upsert(e: CityEvent): boolean {
  const i = state.events.findIndex((x) => x.id === e.id)
  if (i >= 0) {
    state.events.splice(i, 1, e)
    return false
  }
  state.events.unshift(e)
  return true
}

export function useCityEvents() {
  const events = computed(() => state.events)

  const stats = computed(() => {
    const total = state.events.length
    const byType = Object.fromEntries(EVENT_TYPES.map((t) => [t, 0])) as Record<EventType, number>
    const byStatus: Record<EventStatus, number> = { pending: 0, monitoring: 0, processing: 0, resolved: 0 }
    for (const e of state.events) {
      byType[e.event_type] = (byType[e.event_type] ?? 0) + 1
      byStatus[e.status] = (byStatus[e.status] ?? 0) + 1
    }
    const active = total - byStatus.resolved
    return { total, active, byType, byStatus }
  })

  /** 按 id 查事件 */
  function getEventById(id: string): CityEvent | undefined {
    return state.events.find((e) => e.id === id)
  }

  /** 内部注入（保留供测试或同步注入场景使用） */
  function setEvents(list: CityEvent[]) {
    state.events.splice(0, state.events.length, ...list)
  }

  /** 通过 API 接口层加载事件，并接入实时通道 */
  async function loadFromApi() {
    try {
      const list = await getEvents()
      setEvents(list)
    } catch (e) {
      console.warn('[events] 加载失败', e)
    }
    state.loaded = true
    wireRealtime()
  }

  /** 处置操作：调用 PATCH 并就地更新 */
  async function updateEvent(id: string, patch: EventPatch): Promise<CityEvent> {
    const updated = await patchEvent(id, patch)
    upsert(updated)
    revision.value++
    return updated
  }

  function wireRealtime() {
    if (wired) return
    wired = true
    const rt = useRealtime()
    rt.on('event.created', (e) => {
      if (upsert(e)) lastCreated.value = e
      revision.value++
    })
    rt.on('event.updated', (e) => {
      upsert(e)
      revision.value++
    })
    rt.start()
  }

  return { events, stats, lastCreated, revision, getEventById, setEvents, loadFromApi, updateEvent, upsert }
}
