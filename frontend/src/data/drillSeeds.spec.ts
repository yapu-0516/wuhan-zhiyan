import { describe, expect, it } from 'vitest'
import { DRILL_SEEDS } from './drillSeeds'

describe('emergency drill seeds', () => {
  it('covers all four supported incident types', () => {
    expect(new Set(DRILL_SEEDS.map((seed) => seed.eventType))).toEqual(
      new Set(['fire', 'traffic', 'flood', 'building'])
    )
  })

  it('keeps every seed inside the Hankou demonstration region', () => {
    for (const seed of DRILL_SEEDS) {
      expect(seed.longitude).toBeGreaterThanOrEqual(114.27)
      expect(seed.longitude).toBeLessThanOrEqual(114.312)
      expect(seed.latitude).toBeGreaterThanOrEqual(30.57)
      expect(seed.latitude).toBeLessThanOrEqual(30.612)
    }
  })

  it('provides evidence metrics, a risk radius and a response plan', () => {
    for (const seed of DRILL_SEEDS) {
      expect(seed.sourceEventId).toMatch(/^E\d{4}$/)
      expect(seed.metrics).toHaveLength(3)
      expect(seed.riskRadiusM).toBeGreaterThanOrEqual(100)
      expect(seed.riskRadiusM).toBeLessThanOrEqual(500)
      expect(seed.responseMix.reduce((sum, item) => sum + item.count, 0)).toBeGreaterThan(0)
    }
  })
})
