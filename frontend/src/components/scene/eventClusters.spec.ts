import { describe, expect, it } from 'vitest'
import type { CityEvent } from '@/types/event'
import { aggregateEventsByDistrict } from './eventClusters'

const now = new Date('2026-10-31T12:00:00+08:00').getTime()

function event(
  id: string,
  district: string,
  longitude: number,
  latitude: number,
  severity: CityEvent['severity'] = 'medium',
  status: CityEvent['status'] = 'pending'
): CityEvent {
  return {
    id,
    event_type: 'flood',
    name: id,
    longitude,
    latitude,
    confidence: 0.9,
    status,
    timestamp: new Date(now - 5 * 60_000).toLocaleString('sv-SE').replace('T', ' '),
    severity,
    source: 'sensor',
    district,
    address: '测试地址',
    grid: 'TEST-01',
    description: '',
    metrics: {},
    updated_at: ''
  }
}

describe('event district clusters', () => {
  it('excludes resolved and invalid events', () => {
    const clusters = aggregateEventsByDistrict(
      [
        event('E1', '江岸区', 114.3, 30.6),
        event('E2', '江岸区', 114.31, 30.61, 'medium', 'resolved'),
        event('E3', '江汉区', Number.NaN, 30.58)
      ],
      now
    )
    expect(clusters).toHaveLength(1)
    expect(clusters[0]).toMatchObject({ district: '江岸区', count: 1 })
  })

  it('aggregates active counts and urgent events per district', () => {
    const clusters = aggregateEventsByDistrict(
      [
        event('E1', '江岸区', 114.3, 30.6, 'critical'),
        event('E2', '江岸区', 114.31, 30.61, 'high'),
        event('E3', '江海区', 114.28, 30.58, 'low')
      ],
      now
    )
    const jiangAn = clusters.find((cluster) => cluster.district === '江岸区')
    expect(jiangAn).toMatchObject({ count: 2, urgentCount: 2, maxSeverity: 'critical' })
  })

  it('orders districts by accumulated priority rather than raw count', () => {
    const clusters = aggregateEventsByDistrict(
      [
        event('E1', '江岸区', 114.3, 30.6, 'critical'),
        event('E2', '江汉区', 114.28, 30.58, 'low'),
        event('E3', '江汉区', 114.281, 30.581, 'low')
      ],
      now
    )
    expect(clusters.map((cluster) => cluster.district)).toEqual(['江岸区', '江汉区'])
  })

  it('uses a priority-weighted centroid and reports the dominant type', () => {
    const clusters = aggregateEventsByDistrict(
      [
        event('E1', '江岸区', 114.3, 30.6, 'critical'),
        event('E2', '江岸区', 114.4, 30.7, 'low')
      ],
      now
    )
    expect(clusters[0].longitude).toBeLessThan(114.4)
    expect(clusters[0].dominantType).toBe('flood')
  })
})
