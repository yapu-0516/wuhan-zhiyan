/**
 * 事件图层
 * - 定位针：BillboardCollection（Canvas 图标按 类型×等级×是否办结 缓存，纹理图集去重）
 * - 名称标签：LabelCollection（高等级远距离可见，低等级近距离可见，避免拥挤）
 * - 地面涟漪：所有活动事件合批为一个 Primitive（EllipseGeometry + 涟漪着色器），半径/速度随等级
 * - 光柱：所有活动事件合批为一个 Primitive（竖直 PolylineGeometry + 光柱着色器），高度随等级
 * - 新事件强提示：独立的大半径涟漪 + 高光柱，20 秒后自动移除
 * 事件集合变化时仅在几何签名改变时重建涟漪/光柱 Primitive（百级实例，同步构建 <5ms）。
 */
import * as Cesium from 'cesium'
import type { CityEvent, Severity } from '@/types/event'
import { EVENT_TYPE_META } from '@/types/event'
import type { EventTypeFilter } from './types'
import { aggregateEventsByDistrict } from './eventClusters'
import { prominentEventIds, rankEventsByPriority } from './eventPriority'
import { eventIcon } from './icons'
import {
  LINE_VERTEX_FORMAT,
  SURFACE_VERTEX_FORMAT,
  beamAppearance,
  byte,
  fxAttribute,
  rippleAppearance,
  type SceneClock
} from './shaders'
import { hashByte } from './geo'

const SEV: Record<Severity, { radius: number; speed: number; beam: number; width: number; labelFar: number }> = {
  low: { radius: 55, speed: 0.35, beam: 70, width: 8, labelFar: 1400 },
  medium: { radius: 85, speed: 0.45, beam: 110, width: 10, labelFar: 2000 },
  high: { radius: 125, speed: 0.6, beam: 170, width: 12, labelFar: 3200 },
  critical: { radius: 170, speed: 0.8, beam: 260, width: 14, labelFar: 9000 }
}

const ICON_SCALE = 0.5
const ICON_SCALE_SELECTED = 0.64
const OPERATIONS_SCALE: Record<Severity, number> = {
  low: 0.27,
  medium: 0.33,
  high: 0.43,
  critical: 0.54
}
const QUIET_SCALE = 0.2
const MAX_PROMINENT_EVENTS = 6
const MAX_MAP_LABELS = 3
const MAX_CLUSTER_ZONES = 4
const SCALE_BY_DISTANCE = new Cesium.NearFarScalar(800, 1.0, 14000, 0.55)
const LABEL_BG = Cesium.Color.fromCssColorString('rgba(6, 14, 32, 0.84)')
const LABEL_FG = Cesium.Color.fromCssColorString('#eaf4ff')
const LABEL_FG_DIM = Cesium.Color.fromCssColorString('#8aa3c4')
const LABEL_FONT = '600 13px "PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif'
const LABEL_OFFSET = new Cesium.Cartesian2(0, -54)
const LABEL_PADDING = new Cesium.Cartesian2(8, 5)
const ALWAYS = new Cesium.DistanceDisplayCondition(0, Number.MAX_VALUE)
const LABEL_DDC = Object.fromEntries(
  Object.entries(SEV).map(([k, v]) => [k, new Cesium.DistanceDisplayCondition(0, v.labelFar)])
) as Record<Severity, Cesium.DistanceDisplayCondition>

export interface EventSyncOptions {
  showResolved: boolean
  types: EventTypeFilter
  selectedId: string | null
}

interface Item {
  bb: Cesium.Billboard
  label: Cesium.Label
  iconKey: string
  posKey: string
}

interface Alert {
  event: CityEvent
  until: number
}

function shortName(s: string, n = 16): string {
  return s.length > n ? `${s.slice(0, n)}…` : s
}

export class EventLayer {
  private billboards = new Cesium.BillboardCollection()
  private labels = new Cesium.LabelCollection()
  private clusterBadges: Cesium.Billboard[] = []
  private items = new Map<string, Item>()
  private ringPrim: Cesium.Primitive | null = null
  private beamPrim: Cesium.Primitive | null = null
  private alertRingPrim: Cesium.Primitive | null = null
  private alertBeamPrim: Cesium.Primitive | null = null
  private clusterFillPrim: Cesium.Primitive | null = null
  private clusterOutlinePrim: Cesium.Primitive | null = null
  private geoSig = ''
  private clusterSig = ''
  private alerts: Alert[] = []
  private alertTimer: number | undefined
  private visible = true
  private effects = true
  private safe = false
  private lastActive: CityEvent[] = []
  private effectIds = new Set<string>()

  constructor(
    private scene: Cesium.Scene,
    private clock: SceneClock
  ) {
    scene.primitives.add(this.billboards)
    scene.primitives.add(this.labels)
  }

  /** 与事件 store 同步（增量更新图标/标签，几何签名变化时重建涟漪与光柱） */
  sync(events: CityEvent[], opts: EventSyncOptions) {
    const seen = new Set<string>()
    const active: CityEvent[] = []
    const now = Date.now()
    const unresolved = events.filter(
      (event) =>
        event &&
        Number.isFinite(event.longitude) &&
        Number.isFinite(event.latitude) &&
        event.status !== 'resolved' &&
        opts.types[event.event_type] !== false
    )
    const labelIds = prominentEventIds(unresolved, MAX_MAP_LABELS, opts.selectedId, now)
    const effectPool = rankEventsByPriority(
      unresolved.filter((event) => event.severity === 'high' || event.severity === 'critical'),
      now
    )
    this.effectIds = new Set(effectPool.slice(0, MAX_PROMINENT_EVENTS).map((event) => event.id))
    if (opts.selectedId) this.effectIds.add(opts.selectedId)

    for (const e of events) {
      if (!e || !Number.isFinite(e.longitude) || !Number.isFinite(e.latitude)) continue
      const typeOn = opts.types[e.event_type] !== false
      const resolved = e.status === 'resolved'
      const selected = opts.selectedId === e.id
      const show = this.visible && (selected || (typeOn && (!resolved || opts.showResolved)))
      seen.add(e.id)
      let item = this.items.get(e.id)
      const posKey = `${e.longitude.toFixed(6)},${e.latitude.toFixed(6)}`
      const position = Cesium.Cartesian3.fromDegrees(e.longitude, e.latitude, 3)
      if (!item) {
        const bb = this.billboards.add({
          position,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          scale: ICON_SCALE,
          scaleByDistance: SCALE_BY_DISTANCE,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          id: `e:${e.id}`
        })
        const label = this.labels.add({
          position,
          text: shortName(e.name),
          font: LABEL_FONT,
          fillColor: LABEL_FG,
          style: Cesium.LabelStyle.FILL,
          showBackground: true,
          backgroundColor: LABEL_BG,
          backgroundPadding: LABEL_PADDING,
          pixelOffset: LABEL_OFFSET,
          pixelOffsetScaleByDistance: SCALE_BY_DISTANCE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          id: `e:${e.id}`
        })
        item = { bb, label, iconKey: '', posKey }
        this.items.set(e.id, item)
      } else if (item.posKey !== posKey) {
        item.bb.position = position
        item.label.position = position
        item.posKey = posKey
      }
      const rankedEmphasis = labelIds.has(e.id)
      const quiet = !selected && !rankedEmphasis && !this.effectIds.has(e.id)
      const icon = eventIcon(e.event_type, e.severity, resolved, quiet)
      if (item.iconKey !== icon.key) {
        item.bb.setImage(icon.key, icon.canvas)
        item.iconKey = icon.key
      }
      item.bb.show = show
      item.bb.scale = selected
        ? ICON_SCALE_SELECTED
        : quiet
          ? QUIET_SCALE
          : (OPERATIONS_SCALE[e.severity] ?? ICON_SCALE)
      item.bb.color = quiet ? Cesium.Color.WHITE.withAlpha(0.62) : Cesium.Color.WHITE
      const text = shortName(e.name)
      if (item.label.text !== text) item.label.text = text
      item.label.show = selected || (show && rankedEmphasis && !resolved)
      item.label.fillColor = resolved ? LABEL_FG_DIM : LABEL_FG
      item.label.distanceDisplayCondition = selected ? ALWAYS : (LABEL_DDC[e.severity] ?? LABEL_DDC.medium)
      if (show && !resolved) active.push(e)
    }
    // 删除已不存在的事件
    for (const [id, item] of this.items) {
      if (!seen.has(id)) {
        this.billboards.remove(item.bb)
        this.labels.remove(item.label)
        this.items.delete(id)
      }
    }
    this.lastActive = active
    const sig =
      active
        .map((e) => `${e.id}:${e.severity}:${e.event_type}:${e.longitude.toFixed(5)},${e.latitude.toFixed(5)}`)
        .join('|') + `|selected:${opts.selectedId ?? ''}|effects:${[...this.effectIds].sort().join(',')}`
    if (sig !== this.geoSig) {
      this.geoSig = sig
      this.rebuildEffects()
    }
    this.syncClusters(active, opts.selectedId, now)
  }

  /** 行政区聚合层：面积表示待办密度，色调表示片区最高风险。 */
  private syncClusters(events: CityEvent[], selectedId: string | null, now: number) {
    const clusters = aggregateEventsByDistrict(events, now)
      .filter((cluster) => cluster.count >= 2)
      .slice(0, MAX_CLUSTER_ZONES)
    const sig =
      clusters
        .map(
          (cluster) =>
            `${cluster.district}:${cluster.count}:${cluster.urgentCount}:${cluster.maxSeverity}:${cluster.longitude.toFixed(5)},${cluster.latitude.toFixed(5)}`
        )
        .join('|') + `|selected:${selectedId ?? ''}`
    if (sig === this.clusterSig) return
    this.clusterSig = sig
    this.removePrim(this.clusterFillPrim)
    this.removePrim(this.clusterOutlinePrim)
    this.clusterFillPrim = null
    this.clusterOutlinePrim = null
    for (const badge of this.clusterBadges) this.billboards.remove(badge)
    this.clusterBadges = []
    if (this.safe || !clusters.length) return

    const fills: Cesium.GeometryInstance[] = []
    const outlines: Cesium.GeometryInstance[] = []
    const maxCount = Math.max(1, ...clusters.map((cluster) => cluster.count))
    for (const cluster of clusters) {
      const selected = !!selectedId && cluster.eventIds.includes(selectedId)
      // 片区圆是定位提示，不是覆盖街区的底图。用较小的同心范围保留密度差异，
      // 让建筑、道路、事件点仍能从片区内部被看清。
      const radius = 90 + Math.sqrt(cluster.count / maxCount) * 110 + (selected ? 36 : 0)
      const color = clusterColor(cluster.maxSeverity)
      const fill = ellipseFillInstance(
        `cluster:${cluster.district}`,
        cluster.longitude,
        cluster.latitude,
        radius,
        color.withAlpha(selected ? 0.2 : cluster.urgentCount ? 0.07 : 0.045)
      )
      if (fill) fills.push(fill)
      const outline = clusterOutlineInstance(
        `cluster-outline:${cluster.district}`,
        cluster.longitude,
        cluster.latitude,
        radius,
        color.withAlpha(selected ? 0.86 : 0.48)
      )
      if (outline) outlines.push(outline)
      this.clusterBadges.push(
        this.billboards.add({
          position: Cesium.Cartesian3.fromDegrees(cluster.longitude, cluster.latitude, 24),
          image: clusterBadge(clusterColor(cluster.maxSeverity), `${cluster.district} · ${cluster.count}`),
          scale: selected ? 0.92 : 0.8,
          scaleByDistance: new Cesium.NearFarScalar(800, 1.08, 14000, 0.64),
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        })
      )
    }
    this.clusterFillPrim = this.addFlatPrimitive(fills)
    this.clusterOutlinePrim = this.addOutlinePrimitive(outlines)
    this.applyClusterVisibility()
  }

  private rebuildEffects() {
    this.removePrim(this.ringPrim)
    this.removePrim(this.beamPrim)
    this.ringPrim = null
    this.beamPrim = null
    if (this.safe || !this.lastActive.length) return
    const rings: Cesium.GeometryInstance[] = []
    const beams: Cesium.GeometryInstance[] = []
    const effectEvents = this.lastActive.filter((event) => this.effectIds.has(event.id))
    for (const e of effectEvents) {
      const s = SEV[e.severity] ?? SEV.medium
      const color = Cesium.Color.fromCssColorString(EVENT_TYPE_META[e.event_type]?.color ?? '#4fc3f7')
      const seed = hashByte(e.id)
      const ring = ellipseInstance(`ring:${e.id}`, e.longitude, e.latitude, s.radius, color.withAlpha(0.9), [
        0,
        s.speed * 100,
        seed,
        0
      ])
      if (ring) rings.push(ring)
      const beam = beamInstance(`beam:${e.id}`, e.longitude, e.latitude, s.beam, s.width, color.withAlpha(0.95), seed)
      if (beam) beams.push(beam)
    }
    this.ringPrim = this.addPrim(rings, 'ripple')
    this.beamPrim = this.addPrim(beams, 'beam')
  }

  private addPrim(instances: Cesium.GeometryInstance[], kind: 'ripple' | 'beam'): Cesium.Primitive | null {
    if (!instances.length) return null
    try {
      const prim = new Cesium.Primitive({
        geometryInstances: instances,
        appearance: kind === 'ripple' ? rippleAppearance(this.clock) : beamAppearance(this.clock),
        asynchronous: false,
        allowPicking: false,
        releaseGeometryInstances: true
      })
      prim.show = this.visible && this.effects
      this.scene.primitives.add(prim)
      return prim
    } catch (e) {
      console.warn('[events] 特效创建失败', e)
      return null
    }
  }

  private addFlatPrimitive(instances: Cesium.GeometryInstance[]): Cesium.Primitive | null {
    if (!instances.length) return null
    const prim = new Cesium.Primitive({
      geometryInstances: instances,
      appearance: new Cesium.PerInstanceColorAppearance({
        translucent: true,
        closed: false,
        flat: true
      }),
      asynchronous: false,
      allowPicking: false,
      releaseGeometryInstances: true
    })
    this.scene.primitives.add(prim)
    return prim
  }

  private addOutlinePrimitive(instances: Cesium.GeometryInstance[]): Cesium.Primitive | null {
    if (!instances.length) return null
    const prim = new Cesium.Primitive({
      geometryInstances: instances,
      appearance: new Cesium.PolylineColorAppearance({ translucent: true }),
      asynchronous: false,
      allowPicking: false,
      releaseGeometryInstances: true
    })
    this.scene.primitives.add(prim)
    return prim
  }

  private removePrim(p: Cesium.Primitive | null) {
    if (p && !p.isDestroyed() && !this.scene.isDestroyed()) this.scene.primitives.remove(p)
  }

  /** 新事件强提示：大半径快速涟漪 + 高光柱（20 秒） */
  flash(e: CityEvent) {
    if (!Number.isFinite(e.longitude) || !Number.isFinite(e.latitude)) return
    const now = Date.now()
    this.alerts = this.alerts.filter((a) => a.until > now && a.event.id !== e.id)
    this.alerts.push({ event: e, until: now + 20000 })
    this.alerts = this.alerts.slice(-5)
    this.rebuildAlerts()
    window.clearTimeout(this.alertTimer)
    this.alertTimer = window.setTimeout(() => this.expireAlerts(), 20500)
  }

  private expireAlerts() {
    const now = Date.now()
    this.alerts = this.alerts.filter((a) => a.until > now)
    this.rebuildAlerts()
    if (this.alerts.length) {
      const next = Math.min(...this.alerts.map((a) => a.until)) - now + 200
      this.alertTimer = window.setTimeout(() => this.expireAlerts(), Math.max(200, next))
    }
  }

  private rebuildAlerts() {
    this.removePrim(this.alertRingPrim)
    this.removePrim(this.alertBeamPrim)
    this.alertRingPrim = null
    this.alertBeamPrim = null
    if (this.safe || !this.alerts.length) return
    const rings: Cesium.GeometryInstance[] = []
    const beams: Cesium.GeometryInstance[] = []
    for (const { event: e } of this.alerts) {
      const color = Cesium.Color.fromCssColorString(EVENT_TYPE_META[e.event_type]?.color ?? '#ff6b6b')
      const r = ellipseInstance(`alert:${e.id}`, e.longitude, e.latitude, 420, color.withAlpha(1), [1, 90, 0, 0])
      if (r) rings.push(r)
      const b = beamInstance(`alertbeam:${e.id}`, e.longitude, e.latitude, 380, 20, color.withAlpha(1), 0)
      if (b) beams.push(b)
    }
    this.alertRingPrim = this.addPrim(rings, 'ripple')
    this.alertBeamPrim = this.addPrim(beams, 'beam')
  }

  /** 由拾取 id（e:xxx）取事件 id */
  fromPick(id: unknown): string | undefined {
    return typeof id === 'string' && id.startsWith('e:') ? id.slice(2) : undefined
  }

  setVisible(v: boolean) {
    this.visible = v
    this.billboards.show = v
    this.labels.show = v
    this.applyEffectsShow()
    this.applyClusterVisibility()
  }

  /** 特效（涟漪/光柱）单独开关 */
  setEffects(v: boolean) {
    this.effects = v
    this.applyEffectsShow()
  }

  private applyEffectsShow() {
    for (const p of [this.ringPrim, this.beamPrim, this.alertRingPrim, this.alertBeamPrim]) {
      if (p && !p.isDestroyed()) p.show = this.visible && this.effects
    }
  }

  private applyClusterVisibility() {
    for (const p of [this.clusterFillPrim, this.clusterOutlinePrim]) {
      if (p && !p.isDestroyed()) p.show = this.visible
    }
  }

  setSafeMode() {
    if (this.safe) return
    this.safe = true
    for (const p of [this.ringPrim, this.beamPrim, this.alertRingPrim, this.alertBeamPrim]) this.removePrim(p)
    this.ringPrim = this.beamPrim = this.alertRingPrim = this.alertBeamPrim = null
  }

  destroy() {
    window.clearTimeout(this.alertTimer)
    for (const p of [
      this.ringPrim,
      this.beamPrim,
      this.alertRingPrim,
      this.alertBeamPrim,
      this.clusterFillPrim,
      this.clusterOutlinePrim
    ]) {
      this.removePrim(p)
    }
    if (!this.scene.isDestroyed()) {
      this.scene.primitives.remove(this.billboards)
      this.scene.primitives.remove(this.labels)
    }
    this.items.clear()
  }
}

function clusterBadge(color: Cesium.Color, text: string): HTMLCanvasElement {
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  ctx.font = '600 14px "Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif'
  const textWidth = Math.ceil(ctx.measureText(text).width)
  const width = textWidth + 24
  const height = 30
  canvas.width = width * dpr
  canvas.height = height * dpr
  ctx.scale(dpr, dpr)
  ctx.fillStyle = 'rgba(6, 11, 14, 0.9)'
  roundedRect(ctx, 0.5, 0.5, width - 1, height - 1, 5)
  ctx.fill()
  ctx.strokeStyle = color.toCssColorString()
  ctx.globalAlpha = 0.76
  ctx.stroke()
  ctx.globalAlpha = 1
  ctx.fillStyle = '#eef4f6'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, width / 2, height / 2 + 0.5)
  return canvas
}

function roundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.arcTo(x + width, y, x + width, y + height, radius)
  ctx.arcTo(x + width, y + height, x, y + height, radius)
  ctx.arcTo(x, y + height, x, y, radius)
  ctx.arcTo(x, y, x + width, y, radius)
  ctx.closePath()
}

function clusterColor(severity: Severity): Cesium.Color {
  if (severity === 'critical') return Cesium.Color.fromCssColorString('#d56f61')
  if (severity === 'high') return Cesium.Color.fromCssColorString('#c99756')
  if (severity === 'medium') return Cesium.Color.fromCssColorString('#7c9aa4')
  return Cesium.Color.fromCssColorString('#6d8a97')
}

function ellipseFillInstance(
  id: string,
  lon: number,
  lat: number,
  radius: number,
  color: Cesium.Color
): Cesium.GeometryInstance | null {
  try {
    const geometry = Cesium.EllipseGeometry.createGeometry(
      new Cesium.EllipseGeometry({
        center: Cesium.Cartesian3.fromDegrees(lon, lat),
        semiMajorAxis: radius,
        semiMinorAxis: radius,
        height: 3,
        granularity: Cesium.Math.toRadians(1),
        vertexFormat: Cesium.PerInstanceColorAppearance.VERTEX_FORMAT
      })
    )
    if (!geometry) return null
    return new Cesium.GeometryInstance({
      geometry,
      id,
      attributes: {
        color: Cesium.ColorGeometryInstanceAttribute.fromColor(color)
      }
    })
  } catch {
    return null
  }
}

function clusterOutlineInstance(
  id: string,
  lon: number,
  lat: number,
  radius: number,
  color: Cesium.Color
): Cesium.GeometryInstance | null {
  try {
    const positions = circlePositions(lon, lat, radius, 6)
    const geometry = Cesium.PolylineGeometry.createGeometry(
      new Cesium.PolylineGeometry({
        positions,
        width: 1.5,
        vertexFormat: Cesium.PolylineColorAppearance.VERTEX_FORMAT,
        arcType: Cesium.ArcType.NONE
      })
    )
    if (!geometry) return null
    return new Cesium.GeometryInstance({
      geometry,
      id,
      attributes: {
        color: Cesium.ColorGeometryInstanceAttribute.fromColor(color)
      }
    })
  } catch {
    return null
  }
}

function circlePositions(lon: number, lat: number, radius: number, height: number): Cesium.Cartesian3[] {
  const latRad = Cesium.Math.toRadians(lat)
  const dLat = radius / 111_320
  const dLon = radius / (111_320 * Math.max(0.2, Math.cos(latRad)))
  const positions: Cesium.Cartesian3[] = []
  for (let i = 0; i <= 64; i++) {
    const angle = (i / 64) * Math.PI * 2
    positions.push(Cesium.Cartesian3.fromDegrees(lon + Math.cos(angle) * dLon, lat + Math.sin(angle) * dLat, height))
  }
  return positions
}

function ellipseInstance(
  id: string,
  lon: number,
  lat: number,
  radius: number,
  color: Cesium.Color,
  fx: [number, number, number, number]
): Cesium.GeometryInstance | null {
  try {
    const geometry = Cesium.EllipseGeometry.createGeometry(
      new Cesium.EllipseGeometry({
        center: Cesium.Cartesian3.fromDegrees(lon, lat),
        semiMajorAxis: radius,
        semiMinorAxis: radius,
        height: 1.5,
        granularity: Cesium.Math.toRadians(0.75),
        vertexFormat: SURFACE_VERTEX_FORMAT
      })
    )
    if (!geometry) return null
    return new Cesium.GeometryInstance({
      geometry,
      id,
      attributes: {
        color: Cesium.ColorGeometryInstanceAttribute.fromColor(color),
        fx: fxAttribute(fx[0], byte(fx[1]), fx[2], fx[3])
      }
    })
  } catch {
    return null
  }
}

function beamInstance(
  id: string,
  lon: number,
  lat: number,
  height: number,
  width: number,
  color: Cesium.Color,
  seed: number
): Cesium.GeometryInstance | null {
  try {
    const geometry = Cesium.PolylineGeometry.createGeometry(
      new Cesium.PolylineGeometry({
        positions: Cesium.Cartesian3.fromDegreesArrayHeights([lon, lat, 2, lon, lat, height]),
        width,
        vertexFormat: LINE_VERTEX_FORMAT,
        arcType: Cesium.ArcType.NONE
      })
    )
    if (!geometry) return null
    return new Cesium.GeometryInstance({
      geometry,
      id,
      attributes: {
        color: Cesium.ColorGeometryInstanceAttribute.fromColor(color),
        fx: fxAttribute(0, 0, seed, 0)
      }
    })
  } catch {
    return null
  }
}
