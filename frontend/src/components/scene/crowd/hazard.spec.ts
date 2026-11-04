import { describe, expect, it } from 'vitest'
import { hazardRadiusAt, hazardProfile, requiresPedestrianEvacuation } from './hazard'

describe('demo hazard field', () => {
  it('starts at the configured radius and expands over time', () => {
    expect(hazardRadiusAt('fire', 200, 0)).toBe(200)
    expect(hazardRadiusAt('fire', 200, 20)).toBeGreaterThan(200)
    expect(hazardRadiusAt('fire', 200, 90)).toBeCloseTo(276)
  })

  it('keeps the structural warning area tighter than a flood field', () => {
    expect(hazardProfile('building').maxScale).toBeLessThan(hazardProfile('flood').maxScale)
  })

  it('does not trigger a mass pedestrian evacuation for traffic congestion', () => {
    expect(requiresPedestrianEvacuation('traffic')).toBe(false)
    expect(requiresPedestrianEvacuation('fire')).toBe(true)
  })
})
