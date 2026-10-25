// 城市运行总览数据：GET /api/stats/overview
// - 事件实时变化（revision）后防抖 1.5s 刷新，另每 30s 定时刷新；
// - WS traffic.updated 实时更新全路网 TPI；
// - 离线模式：快照总览为底，今日/已办结按真实当天由本地事件推导，趋势沿用快照并标注截止时间；
// - 总览接口与快照均不可用时，完全由本地事件推导。
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { getOverview } from '@/api/stats'
import { apiState, nowString } from '@/api/http'
import { useCityEvents } from './useCityEvents'
import { useRealtime } from './useRealtime'
import type { Overview, TrendPoint } from '@/types/api'
import type { CityEvent, EventStatus, EventType, Severity } from '@/types/event'
import { EVENT_TYPES } from '@/types/event'
import { isToday, parseTime } from '@/utils/format'

function defaultIndex(active: number, critical: number): Overview['city_index'] {
  return {
    traffic_tpi: 0,
    traffic_level: 'smooth',
    safety_score: Math.max(0, Math.round(100 - active * 1.5 - critical * 4)),
    sensors_online: 0,
    sensors_total: 0
  }
}

export function deriveOverview(events: CityEvent[], base?: Overview | null): Overview {
  const byType = Object.fromEntries(EVENT_TYPES.map((t) => [t, 0])) as Record<EventType, number>
  const byStatus: Record<EventStatus, number> = { pending: 0, monitoring: 0, processing: 0, resolved: 0 }
  const bySeverity: Record<Severity, number> = { low: 0, medium: 0, high: 0, critical: 0 }
  const districts = new Map<string, number>()
  let today = 0
  let resolvedToday = 0
  const now = new Date()
  // 近 24 小时趋势（整点分桶，最早在前）
  const hourMs = 3600_000
  const endHour = Math.floor(now.getTime() / hourMs) * hourMs
  const trend: TrendPoint[] = Array.from({ length: 24 }, (_, i) => {
    const d = new Date(endHour - (23 - i) * hourMs)
    return { time: `${String(d.getHours()).padStart(2, '0')}:00`, fire: 0, traffic: 0, building: 0, flood: 0 }
  })
  for (const e of events) {
    byType[e.event_type] = (byType[e.event_type] ?? 0) + 1
    byStatus[e.status] = (byStatus[e.status] ?? 0) + 1
    bySeverity[e.severity] = (bySeverity[e.severity] ?? 0) + 1
    if (e.district) districts.set(e.district, (districts.get(e.district) ?? 0) + 1)
    if (isToday(e.timestamp, now)) {
      today++
      if (e.status === 'resolved') resolvedToday++
    }
    const t = parseTime(e.timestamp)?.getTime() ?? null
    if (t !== null) {
      const idx = 23 - Math.floor((endHour - Math.floor(t / hourMs) * hourMs) / hourMs)
      if (idx >= 0 && idx < 24 && e.event_type in trend[idx]) trend[idx][e.event_type] += 1
    }
  }
  const total = events.length
  return {
    total,
    active: total - byStatus.resolved,
    today,
    resolved_today: resolvedToday,
    resolve_rate: total ? byStatus.resolved / total : 0,
    avg_response_min: base?.avg_response_min ?? 0,
    by_type: byType,
    by_status: byStatus,
    by_severity: bySeverity,
    by_district: base?.by_district?.length
      ? base.by_district
      : Array.from(districts, ([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count),
    // 离线时保留快照趋势（由 Dashboard 在面板上标注截至时间），避免 24h 图变空
    trend: base?.trend?.length ? base.trend : trend,
    city_index: { ...defaultIndex(total - byStatus.resolved, bySeverity.critical), ...(base?.city_index ?? {}) },
    updated_at: base?.updated_at ?? nowString()
  }
}

/** 补齐后端/快照可能缺失的字段，避免模板访问 undefined */
function normalize(r: Overview, events: CityEvent[]): Overview {
  if (r.city_index && r.by_type && r.by_status && r.by_severity && Array.isArray(r.trend) && Array.isArray(r.by_district)) return r
  const d = deriveOverview(events, null)
  return {
    ...d,
    ...r,
    by_type: { ...d.by_type, ...(r.by_type ?? {}) },
    by_status: { ...d.by_status, ...(r.by_status ?? {}) },
    by_severity: { ...d.by_severity, ...(r.by_severity ?? {}) },
    by_district: Array.isArray(r.by_district) ? r.by_district : d.by_district,
    trend: Array.isArray(r.trend) ? r.trend : d.trend,
    city_index: { ...d.city_index, ...(r.city_index ?? {}) }
  }
}

export function useOverview() {
  const { events, revision } = useCityEvents()
  const remote = shallowRef<Overview | null>(null)
  const loading = ref(false)
  const failed = ref(false)
  const lastRefresh = ref(0)
  let timer: number | undefined
  let debounce: number | undefined
  let active = false

  async function refresh() {
    loading.value = true
    try {
      remote.value = await getOverview()
      failed.value = false
    } catch (e) {
      failed.value = true
      console.warn('[overview] 获取失败，改用本地事件推导', e)
    } finally {
      loading.value = false
      lastRefresh.value = Date.now()
    }
  }

  const data = computed<Overview>(() => {
    const r = remote.value
    // 离线 / 快照：快照为底，事件计数类由本地推导
    if (!r || apiState.mode !== 'live') return deriveOverview(events.value, r)
    return normalize(r, events.value)
  })

  watch(revision, () => {
    if (!active) return
    window.clearTimeout(debounce)
    debounce = window.setTimeout(refresh, 1500)
  })

  const offTraffic = useRealtime().on('traffic.updated', (d) => {
    const r = remote.value
    if (!r || !d || typeof d.city_tpi !== 'number') return
    remote.value = { ...r, city_index: { ...r.city_index, traffic_tpi: d.city_tpi, traffic_level: d.level ?? r.city_index.traffic_level } }
  })

  function resume() {
    if (active) return
    active = true
    void refresh()
    window.clearInterval(timer)
    timer = window.setInterval(refresh, 30000)
  }

  function pause() {
    active = false
    window.clearInterval(timer)
    window.clearTimeout(debounce)
  }

  onBeforeUnmount(() => {
    pause()
    offTraffic()
  })

  return { data, remote, loading, failed, lastRefresh, refresh, resume, pause }
}
