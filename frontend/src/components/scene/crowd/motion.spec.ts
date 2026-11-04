import { describe, expect, it } from 'vitest'
import {
  dampHeading,
  densitySpeedFactor,
  sampleReactionDelay,
  sampleWalkSpeed,
  serviceExitQueue,
  trafficSpeedFactor
} from './motion'

describe('crowd motion parameters', () => {
  it('keeps individual walking speeds in type-specific plausible ranges', () => {
    expect(sampleWalkSpeed('resident', () => 0)).toBeCloseTo(1.0)
    expect(sampleWalkSpeed('resident', () => 1)).toBeCloseTo(1.42)
    expect(sampleWalkSpeed('firefighter', () => 0)).toBeGreaterThan(sampleWalkSpeed('tourist', () => 1))
  })

  it('gives civilians a slower reaction than responders', () => {
    expect(sampleReactionDelay('resident', () => 1)).toBeGreaterThan(sampleReactionDelay('firefighter', () => 1))
    expect(sampleReactionDelay('tourist', () => 0)).toBeGreaterThan(0)
  })

  it('slows dense groups without creating zero-speed gridlock', () => {
    expect(densitySpeedFactor(2)).toBe(1)
    expect(densitySpeedFactor(8)).toBeLessThan(1)
    expect(densitySpeedFactor(100)).toBeGreaterThanOrEqual(0.28)
  })

  it('smoothly turns through the shortest angle without snapping', () => {
    const turned = dampHeading(Math.PI - 0.1, -Math.PI + 0.1, 8, 1 / 30)
    expect(turned).toBeGreaterThan(Math.PI - 0.1)
    expect(Math.abs(turned - Math.PI)).toBeLessThan(0.1)
  })

  it('uses exit service capacity without releasing fractional people', () => {
    expect(serviceExitQueue(3, 0, 1.6, 0.5)).toEqual({ released: 0, credit: 0.8 })
    const partial = serviceExitQueue(3, 0.8, 1.6, 0.5)
    expect(partial.released).toBe(1)
    expect(partial.credit).toBeCloseTo(0.6)
    expect(serviceExitQueue(3, 0.8, 1.6, 3)).toEqual({ released: 3, credit: 0 })
  })

  it('slows vehicles around an incident before stopping them in the core', () => {
    expect(trafficSpeedFactor(20, 40)).toBe(0)
    expect(trafficSpeedFactor(60, 40)).toBe(0.25)
    expect(trafficSpeedFactor(80, 40)).toBe(1)
  })
})
