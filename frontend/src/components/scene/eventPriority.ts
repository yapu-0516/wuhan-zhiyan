import type { CityEvent, EventStatus, Severity } from '@/types/event'

const SEVERITY_SCORE: Record<Severity, number> = {
  low: 12,
  medium: 40,
  high: 70,
  critical: 100
}

const STATUS_SCORE: Record<EventStatus, number> = {
  pending: 42,
  monitoring: 20,
  processing: 14,
  resolved: -40
}

function eventTime(value: string): number {
  const explicit = value.includes('T') ? value : value.replace(' ', 'T')
  const parsed = new Date(explicit).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

/** 综合严重度、处置状态和新鲜度；只用于地图显示优先级，不改变事件业务排序。 */
export function eventPriorityScore(event: CityEvent, now = Date.now()): number {
  const ageMin = Math.max(0, (now - eventTime(event.timestamp)) / 60_000)
  const freshness = ageMin <= 15 ? 30 : ageMin <= 60 ? 20 : ageMin <= 360 ? 10 : ageMin <= 1440 ? 4 : 0
  return SEVERITY_SCORE[event.severity] + STATUS_SCORE[event.status] + freshness
}

export function rankEventsByPriority(events: CityEvent[], now = Date.now()): CityEvent[] {
  return [...events].sort(
    (a, b) =>
      eventPriorityScore(b, now) - eventPriorityScore(a, now) ||
      b.timestamp.localeCompare(a.timestamp) ||
      a.id.localeCompare(b.id)
  )
}

export function prominentEventIds(events: CityEvent[], limit: number, selectedId: string | null, now = Date.now()): Set<string> {
  const ranked = rankEventsByPriority(events.filter((event) => event.status !== 'resolved'), now)
  const ids = new Set(ranked.slice(0, limit).map((event) => event.id))
  if (selectedId) ids.add(selectedId)
  return ids
}
