import type { CityEvent, EventType, Severity } from '@/types/event'
import { eventPriorityScore } from './eventPriority'

const SEVERITY_RANK: Record<Severity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4
}

export interface EventCluster {
  district: string
  longitude: number
  latitude: number
  count: number
  urgentCount: number
  score: number
  maxSeverity: Severity
  dominantType: EventType
  eventIds: string[]
}

/**
 * 将活动事件按行政区聚合为地图片区。
 * 中心按事件优先级加权，让高风险事件对片区位置的影响更大，但计数仍使用真实事件数。
 */
export function aggregateEventsByDistrict(events: CityEvent[], now = Date.now()): EventCluster[] {
  const groups = new Map<string, CityEvent[]>()
  for (const event of events) {
    if (
      !event ||
      event.status === 'resolved' ||
      !Number.isFinite(event.longitude) ||
      !Number.isFinite(event.latitude)
    ) {
      continue
    }
    const district = event.district?.trim() || '未分区'
    const list = groups.get(district)
    if (list) list.push(event)
    else groups.set(district, [event])
  }

  const clusters: EventCluster[] = []
  for (const [district, list] of groups) {
    let weight = 0
    let longitude = 0
    let latitude = 0
    let score = 0
    let urgentCount = 0
    let maxSeverity: Severity = 'low'
    const typeCount = new Map<EventType, number>()

    for (const event of list) {
      const priority = Math.max(1, eventPriorityScore(event, now))
      weight += priority
      longitude += event.longitude * priority
      latitude += event.latitude * priority
      score += priority
      if (event.severity === 'high' || event.severity === 'critical') urgentCount++
      if (SEVERITY_RANK[event.severity] > SEVERITY_RANK[maxSeverity]) maxSeverity = event.severity
      typeCount.set(event.event_type, (typeCount.get(event.event_type) ?? 0) + 1)
    }

    let dominantType: EventType = list[0]?.event_type ?? 'traffic'
    let dominantCount = -1
    for (const [type, count] of typeCount) {
      if (count > dominantCount) {
        dominantType = type
        dominantCount = count
      }
    }

    clusters.push({
      district,
      longitude: longitude / weight,
      latitude: latitude / weight,
      count: list.length,
      urgentCount,
      score,
      maxSeverity,
      dominantType,
      eventIds: list.map((event) => event.id)
    })
  }

  return clusters.sort(
    (a, b) =>
      b.score - a.score || b.urgentCount - a.urgentCount || b.count - a.count || a.district.localeCompare(b.district)
  )
}
