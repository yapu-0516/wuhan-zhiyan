export interface GraphPoint {
  x: number
  z: number
}

export interface GraphLine {
  id: string
  points: GraphPoint[]
}

export interface PlannedRoute {
  points: GraphPoint[]
  exitNodeId: number
  cost: number
  distanceM: number
}

interface GraphEdge {
  from: number
  to: number
  length: number
}

interface QueueEntry {
  node: number
  cost: number
}

const NODE_MERGE_KEY_SCALE = 100_000
const ENDPOINT_LINK_M = 8
const SAFE_MARGIN_M = 70
const HAZARD_WEIGHT = 8

function pointDistance(a: GraphPoint, b: GraphPoint): number {
  return Math.hypot(a.x - b.x, a.z - b.z)
}

function projectOnSegment(point: GraphPoint, a: GraphPoint, b: GraphPoint): GraphPoint {
  const dx = b.x - a.x
  const dz = b.z - a.z
  const lengthSquared = dx * dx + dz * dz
  if (lengthSquared < 1e-9) return { x: a.x, z: a.z }
  const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.z - a.z) * dz) / lengthSquared))
  return { x: a.x + dx * t, z: a.z + dz * t }
}

export function hazardPenalizedCost(
  length: number,
  midpoint: GraphPoint,
  danger: GraphPoint,
  radius: number
): number {
  const distance = pointDistance(midpoint, danger)
  if (distance >= radius) return length
  const exposure = 1 - distance / Math.max(1, radius)
  return length * (1 + HAZARD_WEIGHT * exposure * exposure)
}

export class RoadGraph {
  private readonly nodes: GraphPoint[] = []
  private readonly edges: GraphEdge[] = []
  private readonly adjacency: Array<Array<{ to: number; length: number }>> = []
  private nodeByKey = new Map<string, number>()
  private endpoints = new Set<number>()

  get nodeCount(): number {
    return this.nodes.length
  }

  get edgeCount(): number {
    return this.edges.length
  }

  pointForNode(nodeId: number): GraphPoint | null {
    const node = this.nodes[nodeId]
    return node ? { x: node.x, z: node.z } : null
  }

  build(lines: GraphLine[]): void {
    this.nodes.length = 0
    this.edges.length = 0
    this.adjacency.length = 0
    this.nodeByKey = new Map()
    this.endpoints = new Set()

    for (const line of lines) {
      if (line.points.length < 2) continue
      const ids = line.points.map((point) => this.nodeFor(point))
      this.endpoints.add(ids[0])
      this.endpoints.add(ids[ids.length - 1])
      for (let i = 1; i < ids.length; i++) {
        this.connect(ids[i - 1], ids[i])
      }
    }

    const endpointIds = Array.from(this.endpoints)
    for (let i = 0; i < endpointIds.length; i++) {
      for (let j = i + 1; j < endpointIds.length; j++) {
        const a = endpointIds[i]
        const b = endpointIds[j]
        if (pointDistance(this.nodes[a], this.nodes[b]) <= ENDPOINT_LINK_M) this.connect(a, b)
      }
    }
  }

  prepareEvacuation(
    danger: GraphPoint,
    radius: number,
    exitLimit = Number.POSITIVE_INFINITY
  ): (point: GraphPoint) => PlannedRoute | null {
    if (this.nodes.length === 0) return () => null

    const costs = new Float64Array(this.nodes.length)
    const next = new Int32Array(this.nodes.length)
    const exitNode = new Int32Array(this.nodes.length)
    const queue = new MinHeap()
    costs.fill(Number.POSITIVE_INFINITY)
    next.fill(-1)
    exitNode.fill(-1)

    const candidates: Array<{ index: number; distance: number; angle: number }> = []
    for (let index = 0; index < this.nodes.length; index++) {
      const node = this.nodes[index]
      const distance = pointDistance(node, danger)
      if (distance <= radius + SAFE_MARGIN_M) continue
      candidates.push({
        index,
        distance,
        angle: Math.atan2(node.z - danger.z, node.x - danger.x)
      })
    }
    let selected = candidates
    if (Number.isFinite(exitLimit) && candidates.length > exitLimit) {
      const sectors = new Map<number, Array<{ index: number; distance: number; angle: number }>>()
      for (const item of candidates) {
        const sector = Math.floor(((item.angle + Math.PI) / (Math.PI * 2)) * 4) % 4
        const list = sectors.get(sector)
        if (list) list.push(item)
        else sectors.set(sector, [item])
      }
      const picked: typeof candidates = []
      for (const list of sectors.values()) {
        list.sort((a, b) => a.distance - b.distance)
        if (list[0]) picked.push(list[0])
      }
      const pickedIds = new Set(picked.map((item) => item.index))
      candidates.sort((a, b) => a.distance - b.distance)
      selected = picked
        .concat(candidates.filter((item) => !pickedIds.has(item.index)))
        .slice(0, exitLimit)
    }
    for (const item of selected) {
      const index = item.index
      costs[index] = 0
      exitNode[index] = index
      queue.push({ node: index, cost: 0 })
    }
    if (queue.size === 0) return () => null

    while (queue.size) {
      const current = queue.pop()!
      if (current.cost > costs[current.node] + 1e-9) continue
      for (const edge of this.adjacency[current.node]) {
        const midpoint = {
          x: (this.nodes[current.node].x + this.nodes[edge.to].x) / 2,
          z: (this.nodes[current.node].z + this.nodes[edge.to].z) / 2
        }
        const candidate = current.cost + hazardPenalizedCost(edge.length, midpoint, danger, radius)
        if (candidate + 1e-9 >= costs[edge.to]) continue
        costs[edge.to] = candidate
        next[edge.to] = current.node
        exitNode[edge.to] = exitNode[current.node]
        queue.push({ node: edge.to, cost: candidate })
      }
    }

    return (point: GraphPoint): PlannedRoute | null => {
      let best: {
        endpoint: number
        projection: GraphPoint
        connector: number
        cost: number
      } | null = null

      for (const edge of this.edges) {
        if (!Number.isFinite(costs[edge.from]) && !Number.isFinite(costs[edge.to])) continue
        const projection = projectOnSegment(point, this.nodes[edge.from], this.nodes[edge.to])
        const connector = pointDistance(point, projection)
        for (const endpoint of [edge.from, edge.to]) {
          if (!Number.isFinite(costs[endpoint])) continue
          const alongEdge = pointDistance(projection, this.nodes[endpoint])
          const cost = connector + alongEdge + costs[endpoint]
          if (!best || cost < best.cost) best = { endpoint, projection, connector, cost }
        }
      }
      if (!best) return null

      const points: GraphPoint[] = [
        { x: point.x, z: point.z },
        { x: best.projection.x, z: best.projection.z }
      ]
      let current = best.endpoint
      let distanceM = best.connector
      while (current !== -1) {
        const previous = points[points.length - 1]
        const node = this.nodes[current]
        distanceM += pointDistance(previous, node)
        points.push({ x: node.x, z: node.z })
        current = next[current]
      }

      const lastNode = exitNode[best.endpoint]
      if (lastNode < 0) return null
      return {
        points,
        exitNodeId: lastNode,
        cost: best.cost,
        distanceM
      }
    }
  }

  segmentsWithin(center: GraphPoint, radius: number, limit = 120): GraphPoint[][] {
    const matches: Array<{ distance: number; points: GraphPoint[] }> = []
    for (const edge of this.edges) {
      const from = this.nodes[edge.from]
      const to = this.nodes[edge.to]
      const midpoint = { x: (from.x + to.x) / 2, z: (from.z + to.z) / 2 }
      const distance = pointDistance(midpoint, center)
      if (distance > radius) continue
      matches.push({
        distance,
        points: [
          { x: from.x, z: from.z },
          { x: to.x, z: to.z }
        ]
      })
    }
    matches.sort((a, b) => a.distance - b.distance)
    return matches.slice(0, limit).map((item) => item.points)
  }

  private nodeFor(point: GraphPoint): number {
    const key = `${Math.round(point.x * NODE_MERGE_KEY_SCALE)}:${Math.round(point.z * NODE_MERGE_KEY_SCALE)}`
    const existing = this.nodeByKey.get(key)
    if (existing !== undefined) return existing
    const id = this.nodes.length
    this.nodes.push({ x: point.x, z: point.z })
    this.adjacency.push([])
    this.nodeByKey.set(key, id)
    return id
  }

  private connect(a: number, b: number): void {
    if (a === b) return
    if (this.adjacency[a].some((edge) => edge.to === b)) return
    const length = pointDistance(this.nodes[a], this.nodes[b])
    this.edges.push({ from: a, to: b, length })
    this.adjacency[a].push({ to: b, length })
    this.adjacency[b].push({ to: a, length })
  }
}

class MinHeap {
  private readonly items: QueueEntry[] = []

  get size(): number {
    return this.items.length
  }

  push(item: QueueEntry): void {
    this.items.push(item)
    let index = this.items.length - 1
    while (index > 0) {
      const parent = (index - 1) >> 1
      if (this.items[parent].cost <= item.cost) break
      this.items[index] = this.items[parent]
      index = parent
    }
    this.items[index] = item
  }

  pop(): QueueEntry | undefined {
    if (!this.items.length) return undefined
    const root = this.items[0]
    const last = this.items.pop()!
    if (!this.items.length) return root
    let index = 0
    while (true) {
      const left = index * 2 + 1
      const right = left + 1
      if (left >= this.items.length) break
      const child = right < this.items.length && this.items[right].cost < this.items[left].cost ? right : left
      if (this.items[child].cost >= last.cost) break
      this.items[index] = this.items[child]
      index = child
    }
    this.items[index] = last
    return root
  }
}
