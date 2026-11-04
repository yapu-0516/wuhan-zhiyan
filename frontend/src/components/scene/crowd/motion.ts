import type { PersonType } from './types'

const WALK_SPEED_MPS: Record<PersonType, [number, number]> = {
  resident: [1.0, 1.42],
  tourist: [0.82, 1.22],
  firefighter: [1.35, 1.68],
  rescuer: [1.2, 1.55]
}

const REACTION_DELAY_SEC: Record<PersonType, [number, number]> = {
  resident: [0.6, 5.5],
  tourist: [0.8, 6.5],
  firefighter: [0.15, 0.8],
  rescuer: [0.2, 1.0]
}

function sampleRange([min, max]: [number, number], random: () => number): number {
  return min + (max - min) * random()
}

/** 个体步行速度仅用于可视化演练，不替代实测人群参数。 */
export function sampleWalkSpeed(type: PersonType, random: () => number = Math.random): number {
  return sampleRange(WALK_SPEED_MPS[type], random)
}

/** 疏散警报后的个体反应时间。 */
export function sampleReactionDelay(type: PersonType, random: () => number = Math.random): number {
  return sampleRange(REACTION_DELAY_SEC[type], random)
}

/** 邻近人数越多，步速越低，形成简单的拥堵减速。 */
export function densitySpeedFactor(neighbors: number): number {
  if (neighbors <= 2) return 1
  return Math.max(0.28, 1 / (1 + (neighbors - 2) * 0.16))
}

/** 以最短角度差平滑转向，避免人物在折线节点瞬间转头。 */
export function dampHeading(current: number, target: number, rate: number, dt: number): number {
  const delta = Math.atan2(Math.sin(target - current), Math.cos(target - current))
  return current + delta * (1 - Math.exp(-Math.max(0, rate) * Math.max(0, dt)))
}

/** 按服务率推进出口队列；credit 保留不足一人的服务额度。 */
export function serviceExitQueue(
  queueLength: number,
  credit: number,
  capacityPerSecond: number,
  dt: number
): { released: number; credit: number } {
  if (queueLength <= 0) return { released: 0, credit: 0 }
  const available = Math.max(0, credit) + Math.max(0, capacityPerSecond) * Math.max(0, dt)
  const released = Math.min(queueLength, Math.floor(available))
  return {
    released,
    credit: released < queueLength ? available - released : 0
  }
}

/** 车辆在事件核心区停车，在外围减速，形成可视化排队缓冲。 */
export function trafficSpeedFactor(distanceM: number, radiusM: number): number {
  if (distanceM <= radiusM) return 0
  if (distanceM <= radiusM * 1.7) return 0.25
  return 1
}
