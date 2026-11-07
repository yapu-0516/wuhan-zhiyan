/**
 * 路网图层：主干道 LineString → 等距重采样 → PolylineGeometry 合批为一个 Primitive
 *
 * - 颜色按实时路况等级（TRAFFIC_LEVEL_META）；
 * - 流光：着色器中光点沿道路流动，流速与实时车速成正比（拥堵路段缓慢蠕动，畅通路段快速流动）；
 * - WebSocket traffic.updated 仅更新批表中的 color / fx，零重建；
 * - 演示模式可高亮中度/严重拥堵路段。
 */
import * as Cesium from 'cesium'
import type { Road, RoadCollection, TrafficLevel } from '@/types/building'
import { TRAFFIC_LEVEL_META } from '@/types/building'
import type { TrafficUpdate } from '@/types/api'
import { LINE_VERTEX_FORMAT, byte, fxAttribute, roadAppearance, safeLineAppearance, type SceneClock } from './shaders'
import { hashByte, lineMidpoint, resampleLine, type LonLat } from './geo'

const LEVEL_COLORS: Record<TrafficLevel, Cesium.Color> = {
  smooth: Cesium.Color.fromCssColorString('#5f6b72'),
  basic: Cesium.Color.fromCssColorString('#727f6e'),
  light: Cesium.Color.fromCssColorString('#9c8754'),
  moderate: Cesium.Color.fromCssColorString('#bd7046'),
  heavy: Cesium.Color.fromCssColorString('#c94d4f')
}

/** 光点间距（米） */
const DASH_SPACING = 220

function widthOf(highway: string | undefined): number {
  switch (highway) {
    case 'motorway':
    case 'trunk':
      return 7
    case 'primary':
      return 6.5
    case 'secondary':
      return 5.4
    case 'tertiary':
      return 4.6
    default:
      return 3.8
  }
}

/** 流速：车速 km/h → 周期/秒 ×100（字节） */
function flowSpeedByte(speedKmh: number): number {
  const mps = Math.max(1.5, Number.isFinite(speedKmh) ? speedKmh : 30) / 3.6
  return byte(((mps * 3.2) / DASH_SPACING) * 100)
}

interface RoadPart {
  instanceId: string
  repeat: number
  seed: number
}

interface RoadRecord {
  props: Road
  parts: RoadPart[]
  mid: LonLat | null
  /** 几何长度（米），用于加权 TPI */
  len: number
}

export class RoadLayer {
  private prim: Cesium.Primitive | null = null
  private records = new Map<string, RoadRecord>()
  private byInstance = new Map<string, RoadRecord>()
  private dirty = new Set<RoadRecord>()
  private removeTick: () => void
  private safe = false
  private visible = true
  private highlight = false
  private selected: string | null = null

  constructor(
    private scene: Cesium.Scene,
    private clock: SceneClock
  ) {
    this.removeTick = scene.preRender.addEventListener(() => this.flush())
  }

  get count() {
    return this.records.size
  }

  load(fc: RoadCollection | null | undefined): number {
    const features = Array.isArray(fc?.features) ? fc!.features : []
    const instances: Cesium.GeometryInstance[] = []
    features.forEach((feat, i) => {
      const p = feat.properties
      if (!p) return
      const id = String(p.id ?? feat.id ?? `R${i}`)
      const props: Road = {
        ...p,
        id,
        name: p.name || '未命名道路',
        speed: Number(p.speed) || 0,
        tpi: Number(p.tpi) || 0,
        level: (p.level in TRAFFIC_LEVEL_META ? p.level : 'smooth') as TrafficLevel
      }
      let rec = this.records.get(id)
      if (!rec) {
        rec = { props, parts: [], mid: null, len: 0 }
        this.records.set(id, rec)
      }
      for (const line of linesOf(feat.geometry)) {
        const { points, length } = resampleLine(line, 25)
        if (points.length < 2) continue
        if (!rec.mid) rec.mid = lineMidpoint(points)
        rec.len += length
        const positions = Cesium.Cartesian3.fromDegreesArrayHeights(points.flatMap((pt) => [pt[0], pt[1], 2.5]))
        let geometry: Cesium.Geometry | undefined
        try {
          geometry = Cesium.PolylineGeometry.createGeometry(
            new Cesium.PolylineGeometry({
              positions,
              width: widthOf(props.highway),
              vertexFormat: LINE_VERTEX_FORMAT,
              arcType: Cesium.ArcType.NONE
            })
          )
        } catch {
          geometry = undefined
        }
        if (!geometry) continue
        const part: RoadPart = {
          instanceId: `r:${id}:${rec.parts.length}`,
          repeat: byte(Math.max(1, length / DASH_SPACING)),
          seed: hashByte(`${id}${rec.parts.length}`)
        }
        rec.parts.push(part)
        this.byInstance.set(part.instanceId, rec)
        instances.push(
          new Cesium.GeometryInstance({
            geometry,
            id: part.instanceId,
            attributes: {
              color: Cesium.ColorGeometryInstanceAttribute.fromColor(this.colorOf(rec)),
              fx: fxAttribute(flowSpeedByte(props.speed), part.repeat, 0, part.seed)
            }
          })
        )
      }
    })
    if (!instances.length) return 0
    this.prim = new Cesium.Primitive({
      geometryInstances: instances,
      appearance: this.makeAppearance(),
      asynchronous: false,
      releaseGeometryInstances: true,
      allowPicking: true
    })
    this.prim.show = this.visible
    this.scene.primitives.add(this.prim)
    return this.records.size
  }

  private makeAppearance(): Cesium.Appearance {
    if (this.safe) return safeLineAppearance()
    try {
      return roadAppearance(this.clock)
    } catch (e) {
      console.warn('[roads] 自定义外观创建失败，使用内置外观', e)
      return safeLineAppearance()
    }
  }

  private colorOf(rec: RoadRecord): Cesium.Color {
    const c = (LEVEL_COLORS[rec.props.level] ?? LEVEL_COLORS.smooth).clone()
    c.alpha = alphaOf(rec.props.level)
    return c
  }

  private isHighlighted(rec: RoadRecord): boolean {
    if (this.selected === rec.props.id) return true
    return this.highlight && (rec.props.level === 'heavy' || rec.props.level === 'moderate')
  }

  /** 实时路况更新（WS traffic.updated） */
  applyTraffic(update: TrafficUpdate | null | undefined): number {
    const list = Array.isArray(update?.roads) ? update!.roads : []
    let n = 0
    for (const r of list) {
      const rec = this.records.get(String(r.id))
      if (!rec) continue
      rec.props = {
        ...rec.props,
        speed: Number(r.speed) || rec.props.speed,
        tpi: Number(r.tpi) || 0,
        level: r.level in TRAFFIC_LEVEL_META ? r.level : rec.props.level
      }
      this.dirty.add(rec)
      n++
    }
    return n
  }

  private flush() {
    const prim = this.prim
    if (!this.dirty.size || !prim || prim.isDestroyed() || !prim.ready) return
    const colorScratch = new Cesium.Color()
    for (const rec of this.dirty) {
      const base = LEVEL_COLORS[rec.props.level] ?? LEVEL_COLORS.smooth
      Cesium.Color.clone(base, colorScratch)
      colorScratch.alpha = alphaOf(rec.props.level)
      const colorValue = Cesium.ColorGeometryInstanceAttribute.toValue(colorScratch)
      const hi = this.isHighlighted(rec) ? 1 : 0
      for (const part of rec.parts) {
        try {
          const attrs = prim.getGeometryInstanceAttributes(part.instanceId)
          if (!attrs) continue
          attrs.color = colorValue
          attrs.fx = [flowSpeedByte(rec.props.speed), part.repeat, hi, part.seed]
        } catch {
          /* ignore */
        }
      }
    }
    this.dirty.clear()
  }

  get(id: string): Road | undefined {
    return this.records.get(id)?.props
  }

  fromPick(id: unknown): Road | undefined {
    return typeof id === 'string' ? this.byInstance.get(id)?.props : undefined
  }

  setVisible(v: boolean) {
    this.visible = v
    if (this.prim && !this.prim.isDestroyed()) this.prim.show = v
  }

  setHighlight(on: boolean) {
    this.highlight = on
    this.records.forEach((r) => this.dirty.add(r))
  }

  setSelected(id: string | null) {
    const prev = this.selected
    this.selected = id
    for (const k of [prev, id]) {
      const r = k ? this.records.get(k) : undefined
      if (r) this.dirty.add(r)
    }
  }

  /** 最拥堵路段（TPI 最高）的中点 */
  mostCongested(): { lon: number; lat: number; name: string; tpi: number } | null {
    let best: RoadRecord | null = null
    this.records.forEach((r) => {
      if (r.mid && (!best || r.props.tpi > best.props.tpi)) best = r
    })
    const b = best as RoadRecord | null
    if (!b || !b.mid) return null
    return { lon: b.mid[0], lat: b.mid[1], name: b.props.name, tpi: b.props.tpi }
  }

  /** 全路网长度加权 TPI 与等级 */
  cityTraffic(): { tpi: number; level: TrafficLevel } | null {
    let sw = 0
    let s = 0
    this.records.forEach((r) => {
      const w = Math.max(r.len, 1)
      sw += w
      s += r.props.tpi * w
    })
    if (!sw) return null
    const tpi = s / sw
    const level: TrafficLevel =
      tpi < 2 ? 'smooth' : tpi < 4 ? 'basic' : tpi < 6 ? 'light' : tpi < 8 ? 'moderate' : 'heavy'
    return { tpi, level }
  }

  setSafeMode() {
    if (this.safe) return
    this.safe = true
    if (this.prim && !this.prim.isDestroyed()) this.prim.appearance = safeLineAppearance()
  }

  destroy() {
    this.removeTick()
    if (this.prim && !this.prim.isDestroyed() && !this.scene.isDestroyed()) this.scene.primitives.remove(this.prim)
    this.prim = null
    this.records.clear()
    this.byInstance.clear()
    this.dirty.clear()
  }
}

/** 畅通道路退到卫星影像之下，只有拥堵与重点关注路段保持明确覆盖。 */
function alphaOf(level: TrafficLevel): number {
  switch (level) {
    case 'heavy':
      return 0.78
    case 'moderate':
      return 0.66
    case 'light':
      return 0.5
    case 'basic':
      return 0.34
    default:
      return 0.27
  }
}

function linesOf(geometry: unknown): unknown[] {
  const g = geometry as { type?: string; coordinates?: unknown } | null
  if (!g || !Array.isArray(g.coordinates)) return []
  if (g.type === 'LineString') return [g.coordinates]
  if (g.type === 'MultiLineString') return g.coordinates as unknown[]
  return []
}
