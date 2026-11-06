// 轻量地理计算工具（局部平面近似，适用于数公里范围的示范区）

const EARTH_R = 6371008.8
const RAD = Math.PI / 180

export type LonLat = [number, number]

/** 两点球面距离（米） */
function distance(a: LonLat, b: LonLat): number {
  const dLat = (b[1] - a[1]) * RAD
  const dLon = (b[0] - a[0]) * RAD
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * RAD) * Math.cos(b[1] * RAD) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_R * Math.asin(Math.min(1, Math.sqrt(s)))
}

function isFiniteCoord(c: unknown): c is number[] {
  return Array.isArray(c) && c.length >= 2 && Number.isFinite(c[0]) && Number.isFinite(c[1])
}

/**
 * 清洗多边形环：去除非法点、连续重复点、首尾闭合点；点数不足 3 或面积过小时返回 null。
 * 防止退化多边形导致三角剖分失败。
 */
export function cleanRing(ring: unknown, minAreaM2 = 1): LonLat[] | null {
  if (!Array.isArray(ring)) return null
  const out: LonLat[] = []
  for (const c of ring) {
    if (!isFiniteCoord(c)) continue
    const p: LonLat = [c[0], c[1]]
    const last = out[out.length - 1]
    if (last && Math.abs(last[0] - p[0]) < 1e-9 && Math.abs(last[1] - p[1]) < 1e-9) continue
    out.push(p)
  }
  if (out.length > 1) {
    const f = out[0]
    const l = out[out.length - 1]
    if (Math.abs(f[0] - l[0]) < 1e-9 && Math.abs(f[1] - l[1]) < 1e-9) out.pop()
  }
  if (out.length < 3) return null
  if (ringAreaM2(out) < minAreaM2) return null
  return out
}

/** 环面积（平方米，局部平面近似） */
function ringAreaM2(ring: LonLat[]): number {
  if (ring.length < 3) return 0
  const lat0 = ring[0][1] * RAD
  const kx = EARTH_R * Math.cos(lat0) * RAD
  const ky = EARTH_R * RAD
  let s = 0
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i]
    const b = ring[(i + 1) % ring.length]
    s += a[0] * kx * (b[1] * ky) - b[0] * kx * (a[1] * ky)
  }
  return Math.abs(s) / 2
}

/** 折线总长（米） */
function lineLength(points: LonLat[]): number {
  let len = 0
  for (let i = 1; i < points.length; i++) len += distance(points[i - 1], points[i])
  return len
}

/**
 * 按固定步长重采样折线（保留首尾点），使纹理坐标 s 与弧长近似成正比，
 * 流光材质的光点间距才能在不同道路上保持一致。
 */
export function resampleLine(raw: unknown, step = 25): { points: LonLat[]; length: number } {
  const pts: LonLat[] = []
  if (Array.isArray(raw)) {
    for (const c of raw) {
      if (!isFiniteCoord(c)) continue
      const last = pts[pts.length - 1]
      if (last && distance(last, [c[0], c[1]]) < 0.5) continue
      pts.push([c[0], c[1]])
    }
  }
  const length = lineLength(pts)
  if (pts.length < 2 || length < step * 1.5) return { points: pts, length }
  const n = Math.max(2, Math.round(length / step))
  const target = length / n
  const out: LonLat[] = [pts[0]]
  let seg = 0
  let segStart = pts[0]
  let segLen = distance(pts[0], pts[1])
  let along = 0 // 当前段内已走距离
  for (let k = 1; k < n; k++) {
    let need = target
    while (need > segLen - along && seg < pts.length - 2) {
      need -= segLen - along
      seg++
      segStart = pts[seg]
      segLen = distance(pts[seg], pts[seg + 1])
      along = 0
    }
    along += need
    const t = segLen > 0 ? Math.min(1, along / segLen) : 0
    const b = pts[seg + 1]
    out.push([segStart[0] + (b[0] - segStart[0]) * t, segStart[1] + (b[1] - segStart[1]) * t])
  }
  out.push(pts[pts.length - 1])
  return { points: out, length }
}

/** 折线按弧长的中点 */
export function lineMidpoint(points: LonLat[]): LonLat | null {
  if (!points.length) return null
  if (points.length === 1) return points[0]
  const half = lineLength(points) / 2
  let acc = 0
  for (let i = 1; i < points.length; i++) {
    const d = distance(points[i - 1], points[i])
    if (acc + d >= half) {
      const t = d > 0 ? (half - acc) / d : 0
      const a = points[i - 1]
      const b = points[i]
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
    }
    acc += d
  }
  return points[points.length - 1]
}

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v
}

/** 简单确定性哈希（0~255），用于实例动画相位错开 */
export function hashByte(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (h >>> 0) % 256
}
