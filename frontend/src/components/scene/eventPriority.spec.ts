import { describe, expect, it } from 'vitest'
import type { CityEvent } from '@/types/event'
import { eventPriorityScore, prominentEventIds, rankEventsByPriority } from './eventPriority'

const now = new Date('2026-10-31T12:00:00+08:00').getTime()

function event(
  id: string,
  severity: CityEvent['severity'],
  status: CityEvent['status'],
  minutesAgo: number
): CityEvent {
  return {
    id,
    event_type: 'flood',
    name: id,
    longitude: 114.29,
    latitude: 30.58,
    confidence: 0.9,
    status,
    timestamp: new Date(now - minutesAgo * 60_000).toLocaleString('sv-SE').replace('T', ' '),
    severity,
    source: 'sensor',
    district: '江汉区',
    address: '测试地址',
    grid: 'JH-01-01',
    description: '',
    metrics: {},
    updated_at: ''
  }
}

describe('event map priority', () => {
  it('puts a fresh pending event above an older high event', () => {
    const pending = event('E-PENDING', 'medium', 'pending', 5)
    const oldHigh = event('E-OLD', 'high', 'monitoring', 240)
    expect(eventPriorityScore(pending, now)).toBeGreaterThan(eventPriorityScore(oldHigh, now))
  })

  it('keeps critical severity ahead of ordinary pending work', () => {
    const critical = event('E-CRITICAL', 'critical', 'monitoring', 90)
    const pending = event('E-PENDING', 'medium', 'pending', 1)
    expect(eventPriorityScore(critical, now)).toBeGreaterThan(eventPriorityScore(pending, now))
  })

  it('limits the prominent set and always includes the selected event', () => {
    const events = [
      event('E1', 'critical', 'pending', 2),
      event('E2', 'high', 'pending', 3),
      event('E3', 'medium', 'pending', 4),
      event('E4', 'low', 'monitoring', 2000),
      event('E5', 'low', 'monitoring', 3000)
    ]
    const ids = prominentEventIds(events, 2, 'E5', now)
    expect(ids.size).toBe(3)
    expect(ids.has('E5')).toBe(true)
    expect([...ids].some((id) => id === 'E1' || id === 'E2')).toBe(true)
  })

  it('orders by score then newer timestamp', () => {
    const ranked = rankEventsByPriority(
      [
        event('E-OLD', 'high', 'processing', 120),
        event('E-NEW', 'high', 'processing', 5),
        event('E-CRITICAL', 'critical', 'monitoring', 180)
      ],
      now
    )
    expect(ranked.map((item) => item.id)).toEqual(['E-CRITICAL', 'E-NEW', 'E-OLD'])
  })
})
