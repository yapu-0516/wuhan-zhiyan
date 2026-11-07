import { describe, expect, it } from 'vitest'
import { RoadGraph, hazardPenalizedCost } from './roadGraph'

describe('provisional road graph', () => {
  it('routes from a road-side origin to a node outside the danger area', () => {
    const graph = new RoadGraph()
    graph.build([
      {
        id: 'R1',
        points: [
          { x: -120, z: 0 },
          { x: 0, z: 0 },
          { x: 120, z: 0 }
        ]
      }
    ])
    const route = graph.prepareEvacuation({ x: 0, z: 0 }, 10)({ x: 0, z: 3 })
    expect(route).not.toBeNull()
    expect(Math.abs(route!.points.at(-1)!.x)).toBeGreaterThan(10)
    expect(route!.distanceM).toBeGreaterThan(0)
  })

  it('penalizes an edge inside the hazard without making routing impossible', () => {
    const outside = hazardPenalizedCost(10, { x: 20, z: 0 }, { x: 0, z: 0 }, 10)
    const inside = hazardPenalizedCost(10, { x: 2, z: 0 }, { x: 0, z: 0 }, 10)
    expect(outside).toBe(10)
    expect(inside).toBeGreaterThan(outside)
  })

  it('connects nearby road endpoints so segmented roads remain traversable', () => {
    const graph = new RoadGraph()
    graph.build([
      {
        id: 'A',
        points: [
          { x: -120, z: 0 },
          { x: 0, z: 0 }
        ]
      },
      {
        id: 'B',
        points: [
          { x: 4, z: 0 },
          { x: 120, z: 0 }
        ]
      }
    ])
    const route = graph.prepareEvacuation({ x: -60, z: 1 }, 4)({ x: -60, z: 3 })
    expect(route).not.toBeNull()
    expect(route!.points.at(-1)!.x).toBeGreaterThanOrEqual(120)
  })

  it('limits demo exits by direction and exposes roads inside the hazard', () => {
    const graph = new RoadGraph()
    graph.build([
      {
        id: 'cross',
        points: [
          { x: -120, z: 0 },
          { x: 0, z: 0 },
          { x: 120, z: 0 }
        ]
      },
      {
        id: 'vertical',
        points: [
          { x: 0, z: -120 },
          { x: 0, z: 0 },
          { x: 0, z: 120 }
        ]
      }
    ])
    const navigate = graph.prepareEvacuation({ x: 0, z: 0 }, 10, 2)
    const exits = new Set(
      [navigate({ x: 1, z: 0 }), navigate({ x: -1, z: 0 }), navigate({ x: 0, z: 1 }), navigate({ x: 0, z: -1 })]
        .filter((route) => route !== null)
        .map((route) => route!.exitNodeId)
    )
    expect(exits.size).toBeGreaterThan(0)
    expect(exits.size).toBeLessThanOrEqual(2)
    expect(graph.segmentsWithin({ x: 0, z: 0 }, 70).length).toBeGreaterThan(0)
  })
})
