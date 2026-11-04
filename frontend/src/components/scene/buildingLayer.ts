/**
 * 建筑图层：OSM 真实建筑轮廓 → 拉伸 PolygonGeometry → 合批 Primitive（每批 ~400 栋）
 *
 * - 几何在主线程分帧预计算（每帧 ≤12ms），单个退化多边形 try/catch 跳过，不会拖垮整个场景；
 * - 每实例颜色：中性实体建筑，沉降关注/预警着琥珀/红色；
 * - 每实例 fx：x=效果模式（0 常规 / 1 告警脉冲 / 2 选中 / 3 预警呼吸）、y=高度/2、z=随机种子；
 *   模式切换只改批表中的 4 个字节，零重建；
 * - 着色器：竖向渐变 + 楼层线 + 檐口描边 + 上行扫描光带 + 城市生长动画（见 shaders.ts）。
 */
import * as Cesium from 'cesium'
import type { Building, BuildingCollection } from '@/types/building'
import { buildingAppearance, byte, fxAttribute, regionFrameGlsl, safeBuildingAppearance, type SceneClock } from './shaders'
import { clamp, cleanRing, hashByte, type LonLat } from './geo'

const CHUNK = 400

/** 城市数据块使用冷灰石材层级；高度不再编码为发光亮度。 */
const HEIGHT_STOPS: [number, Cesium.Color][] = [
  [0, Cesium.Color.fromCssColorString('#48565f')],
  [0.3, Cesium.Color.fromCssColorString('#53626b')],
  [0.62, Cesium.Color.fromCssColorString('#607079')],
  [1, Cesium.Color.fromCssColorString('#70818a')]
]
const WATCH_COLOR = Cesium.Color.fromCssColorString('#c59455')
const WARNING_COLOR = Cesium.Color.fromCssColorString('#bd5f5d')
const BASE_ALPHA = 1

export function buildingColor(b: Pick<Building, 'height' | 'risk_level' | 'monitored'>, result = new Cesium.Color()): Cesium.Color {
  const t = clamp((b.height - 6) / 140, 0, 1)
  let i = 0
  while (i < HEIGHT_STOPS.length - 2 && t > HEIGHT_STOPS[i + 1][0]) i++
  const [t0, c0] = HEIGHT_STOPS[i]
  const [t1, c1] = HEIGHT_STOPS[i + 1]
  Cesium.Color.lerp(c0, c1, clamp((t - t0) / (t1 - t0), 0, 1), result)
  if (b.risk_level === 'warning') {
    Cesium.Color.lerp(result, WARNING_COLOR, 0.8, result)
    result.alpha = 1
  } else if (b.risk_level === 'watch') {
    Cesium.Color.lerp(result, WATCH_COLOR, 0.66, result)
    result.alpha = 1
  } else {
    result.alpha = BASE_ALPHA
  }
  return result
}

interface BuildingRecord {
  props: Building
  instanceId: string
  prim: number
  fx: [number, number, number, number]
}

function nextFrame(): Promise<void> {
  // 后台标签页可能暂停 requestAnimationFrame，用短定时器兜底避免构建永久挂起。
  return new Promise((resolve) => {
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      resolve()
    }
    requestAnimationFrame(finish)
    window.setTimeout(finish, 50)
  })
}

function frameNumberOf(scene: Cesium.Scene): number {
  const fs = (scene as unknown as { frameState?: { frameNumber?: number } }).frameState
  return typeof fs?.frameNumber === 'number' ? fs.frameNumber : 0
}

export class BuildingLayer {
  private prims: Cesium.Primitive[] = []
  private records = new Map<string, BuildingRecord>()
  private byInstance = new Map<string, BuildingRecord>()
  private dirty = new Set<BuildingRecord>()
  private alarms = new Set<string>()
  private selected: string | null = null
  private removeTick: () => void
  private destroyed = false
  private safe = false
  private visible = true
  private riskOnly = false
  private frame = ''
  private startFrame = 0
  /** 建筑覆盖范围中心（用于着色器局部坐标系） */
  center: LonLat = [0, 0]

  constructor(
    private scene: Cesium.Scene,
    private clock: SceneClock
  ) {
    // 批表写入需等待 Primitive 就绪，统一在 preRender 中刷新
    this.removeTick = scene.preRender.addEventListener(() => this.flush())
  }

  get count() {
    return this.records.size
  }

  get monitoredCount() {
    let n = 0
    this.records.forEach((r) => r.props.monitored && n++)
    return n
  }

  async load(fc: BuildingCollection | null | undefined): Promise<number> {
    const features = Array.isArray(fc?.features) ? fc!.features : []
    if (!features.length) return 0

    // 1) 以数据包围盒中心建立局部坐标系
    let w = 180
    let s = 90
    let e = -180
    let n = -90
    for (const f of features) {
      const lon = Number(f.properties?.longitude)
      const lat = Number(f.properties?.latitude)
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue
      w = Math.min(w, lon)
      e = Math.max(e, lon)
      s = Math.min(s, lat)
      n = Math.max(n, lat)
    }
    this.center = w <= e ? [(w + e) / 2, (s + n) / 2] : [114.2955, 30.5895]
    this.frame = regionFrameGlsl(this.center[0], this.center[1])

    // 2) 分帧预计算几何
    const vertexFormat = Cesium.VertexFormat.POSITION_AND_NORMAL
    const chunks: Cesium.GeometryInstance[][] = []
    let chunk: Cesium.GeometryInstance[] = []
    let t0 = performance.now()
    for (let i = 0; i < features.length; i++) {
      if (this.destroyed) return 0
      const feat = features[i]
      const props = this.normalize(feat.properties, feat.id, i)
      if (!props || this.records.has(props.id)) continue
      const polys = polygonsOf(feat.geometry)
      let geometry: Cesium.Geometry | undefined
      for (const poly of polys) {
        // 多部件建筑仅取首个有效部件（其余部件极少且面积很小）
        geometry = extrude(poly, props.height, vertexFormat)
        if (geometry) break
      }
      if (!geometry) continue
      const seed = hashByte(props.id)
      const rec: BuildingRecord = {
        props,
        instanceId: `b:${props.id}`,
        prim: chunks.length,
        fx: [props.risk_level === 'warning' ? 3 : 0, byte(props.height / 2), seed, 0]
      }
      this.records.set(props.id, rec)
      this.byInstance.set(rec.instanceId, rec)
      chunk.push(
        new Cesium.GeometryInstance({
          geometry,
          id: rec.instanceId,
          attributes: {
            color: Cesium.ColorGeometryInstanceAttribute.fromColor(buildingColor(props)),
            fx: fxAttribute(...rec.fx),
            show: new Cesium.ShowGeometryInstanceAttribute(this.isShown(props))
          }
        })
      )
      if (chunk.length >= CHUNK) {
        chunks.push(chunk)
        chunk = []
      }
      if (performance.now() - t0 > 12) {
        await nextFrame()
        t0 = performance.now()
      }
    }
    if (chunk.length) chunks.push(chunk)
    if (this.destroyed) return 0

    // 3) 逐帧加入场景（分摊合批开销），统一起始帧使"城市生长"动画同步开始
    this.startFrame = frameNumberOf(this.scene) + chunks.length + 4
    for (const instances of chunks) {
      if (this.destroyed) return 0
      const prim = new Cesium.Primitive({
        geometryInstances: instances,
        appearance: this.makeAppearance(),
        asynchronous: false,
        releaseGeometryInstances: true,
        compressVertices: true,
        allowPicking: true
      })
      prim.show = this.visible
      this.scene.primitives.add(prim)
      this.prims.push(prim)
      await nextFrame()
    }
    // 初始模式（告警 / 选中）可能在加载期间已设置
    this.records.forEach((r) => this.refreshMode(r))
    return this.records.size
  }

  private makeAppearance(): Cesium.Appearance {
    if (this.safe) return safeBuildingAppearance()
    try {
      return buildingAppearance(this.clock, this.frame, this.startFrame)
    } catch (e) {
      console.warn('[buildings] 自定义外观创建失败，使用内置外观', e)
      return safeBuildingAppearance()
    }
  }

  private normalize(p: Building | undefined, fid: string | undefined, i: number): Building | null {
    if (!p) return null
    const id = String(p.id ?? fid ?? `B${i}`)
    const height = Number(p.height)
    return {
      ...p,
      id,
      name: p.name || `建筑 ${id}`,
      height: Number.isFinite(height) && height > 0 ? clamp(height, 3, 650) : 12,
      longitude: Number(p.longitude),
      latitude: Number(p.latitude)
    }
  }

  get(id: string): Building | undefined {
    return this.records.get(id)?.props
  }

  /** 由拾取到的实例 id（b:xxx）取建筑 */
  fromPick(id: unknown): Building | undefined {
    return typeof id === 'string' ? this.byInstance.get(id)?.props : undefined
  }

  all(): Building[] {
    return Array.from(this.records.values(), (r) => r.props)
  }

  setVisible(v: boolean) {
    this.visible = v
    this.prims.forEach((p) => (p.show = v))
  }

  /** 精细建筑启用时，基础图层只保留监测/风险建筑作为业务叠层。 */
  setRiskOnly(v: boolean) {
    this.riskOnly = v
    this.records.forEach((r) => this.dirty.add(r))
  }

  private isShown(b: Building): boolean {
    if (this.riskOnly) return b.monitored || b.risk_level === 'watch' || b.risk_level === 'warning' || this.alarms.has(b.id)
    // 数据块视图使用完整 OSM 轮廓，街区密度本身就是城市信息。
    return !!b
  }

  setSelected(id: string | null) {
    const prev = this.selected
    this.selected = id
    if (prev && prev !== id) {
      const r = this.records.get(prev)
      if (r) this.refreshMode(r)
    }
    if (id) {
      const r = this.records.get(id)
      if (r) this.refreshMode(r)
    }
  }

  /** 设置关联活动事件的建筑（红色脉冲） */
  setAlarms(ids: Set<string>) {
    const changed = new Set<string>()
    this.alarms.forEach((id) => !ids.has(id) && changed.add(id))
    ids.forEach((id) => !this.alarms.has(id) && changed.add(id))
    this.alarms = new Set(ids)
    changed.forEach((id) => {
      const r = this.records.get(id)
      if (r) {
        this.refreshMode(r)
        this.dirty.add(r)
      }
    })
  }

  private refreshMode(r: BuildingRecord) {
    const mode = this.selected === r.props.id ? 2 : this.alarms.has(r.props.id) ? 1 : r.props.risk_level === 'warning' ? 3 : 0
    if (r.fx[0] !== mode) {
      r.fx[0] = mode
      this.dirty.add(r)
    }
  }

  private flush() {
    if (!this.dirty.size) return
    for (const r of Array.from(this.dirty)) {
      const prim = this.prims[r.prim]
      if (!prim || prim.isDestroyed()) {
        // 尚未创建（加载中），保留待下次刷新
        if (prim?.isDestroyed()) this.dirty.delete(r)
        continue
      }
      if (!prim.ready) continue
      try {
        const attrs = prim.getGeometryInstanceAttributes(r.instanceId)
        if (attrs) {
          attrs.fx = r.fx.slice()
          attrs.show = Cesium.ShowGeometryInstanceAttribute.toValue(this.isShown(r.props))
        }
      } catch {
        /* 批表尚未创建 */
        continue
      }
      this.dirty.delete(r)
    }
  }

  /** 着色器失败时切换为内置外观 */
  setSafeMode() {
    if (this.safe) return
    this.safe = true
    this.prims.forEach((p) => {
      if (!p.isDestroyed()) p.appearance = safeBuildingAppearance()
    })
  }

  /** 高层建筑最密集处（按高度加权的前 40 栋质心） */
  denseCenter(): LonLat | null {
    const list = this.all()
      .filter((b) => Number.isFinite(b.longitude) && Number.isFinite(b.latitude))
      .sort((a, b) => b.height - a.height)
      .slice(0, 40)
    if (!list.length) return null
    let sw = 0
    let x = 0
    let y = 0
    for (const b of list) {
      sw += b.height
      x += b.longitude * b.height
      y += b.latitude * b.height
    }
    return [x / sw, y / sw]
  }

  destroy() {
    this.destroyed = true
    this.removeTick()
    this.prims.forEach((p) => {
      if (!p.isDestroyed() && !this.scene.isDestroyed()) this.scene.primitives.remove(p)
    })
    this.prims = []
    this.records.clear()
    this.byInstance.clear()
    this.dirty.clear()
  }
}

/** 兼容 Polygon / MultiPolygon，返回多边形环数组列表 */
function polygonsOf(geometry: unknown): unknown[][] {
  const g = geometry as { type?: string; coordinates?: unknown } | null
  if (!g || !Array.isArray(g.coordinates)) return []
  if (g.type === 'Polygon') return [g.coordinates as unknown[]]
  if (g.type === 'MultiPolygon') return (g.coordinates as unknown[]).filter(Array.isArray) as unknown[][]
  return []
}

function extrude(rings: unknown[], height: number, vertexFormat: Cesium.VertexFormat): Cesium.Geometry | undefined {
  const outer = cleanRing(rings[0], 4)
  if (!outer) return undefined
  const holes: Cesium.PolygonHierarchy[] = []
  for (let i = 1; i < rings.length; i++) {
    const h = cleanRing(rings[i], 1)
    if (h) holes.push(new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(h.flat())))
  }
  try {
    return Cesium.PolygonGeometry.createGeometry(
      new Cesium.PolygonGeometry({
        polygonHierarchy: new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(outer.flat()), holes),
        height: 0,
        extrudedHeight: height,
        vertexFormat
      })
    )
  } catch {
    return undefined
  }
}
