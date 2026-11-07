// 相机控制：默认斜视视角、飞行定位（Promise 化）、环绕巡航、太空切入
import * as Cesium from 'cesium'
import { DEFAULT_REGION } from '@/config/cesium'
import type { FlyOptions, OrbitOptions } from './types'

const toRad = Cesium.Math.toRadians

export interface Region {
  name: string
  center: [number, number]
  bbox: [number, number, number, number]
}

export class CameraController {
  region: Region = { ...DEFAULT_REGION }
  private removeOrbit: (() => void) | null = null
  private orbitHpr = new Cesium.HeadingPitchRange()
  private orbitCenter = new Cesium.Cartesian3()
  private lastOrbitTs = 0

  constructor(private viewer: Cesium.Viewer) {}

  private get camera() {
    return this.viewer.camera
  }

  setRegion(r: Region) {
    this.region = r
  }

  /** 默认视角参数：斜视 -32°，朝东南方向看向长江，覆盖整个示范区 */
  homeParams() {
    const [w, s, e, n] = this.region.bbox
    const diag = Cesium.Cartesian3.distance(Cesium.Cartesian3.fromDegrees(w, s), Cesium.Cartesian3.fromDegrees(e, n))
    const range = Cesium.Math.clamp(diag * 0.72, 2200, 9000)
    // 视点略向西北偏移，使沿江密集街区与江面同时入画
    const lon = this.region.center[0] + (e - w) * 0.04
    const lat = this.region.center[1] - (n - s) * 0.02
    return { lon, lat, heading: 118, pitch: -32, range }
  }

  jumpHome() {
    const p = this.homeParams()
    this.camera.lookAt(
      Cesium.Cartesian3.fromDegrees(p.lon, p.lat, 0),
      new Cesium.HeadingPitchRange(toRad(p.heading), toRad(p.pitch), p.range)
    )
    this.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  }

  flyHome(duration = 2.2): Promise<boolean> {
    const p = this.homeParams()
    return this.flyTo(p.lon, p.lat, { heading: p.heading, pitch: p.pitch, range: p.range, duration })
  }

  /** 天际线视角：低俯仰、以高层密集区为视觉中心，保留前中后景层次。 */
  skylineParams(target?: [number, number]) {
    const lon = target?.[0] ?? this.region.center[0]
    const lat = target?.[1] ?? this.region.center[1]
    return { lon, lat, heading: 106, pitch: -27, range: 2400 }
  }

  jumpSkyline(target?: [number, number]) {
    const p = this.skylineParams(target)
    this.camera.lookAt(
      Cesium.Cartesian3.fromDegrees(p.lon, p.lat, 0),
      new Cesium.HeadingPitchRange(toRad(p.heading), toRad(p.pitch), p.range)
    )
    this.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  }

  flySkyline(target?: [number, number], duration = 2.4): Promise<boolean> {
    const p = this.skylineParams(target)
    return this.flyTo(p.lon, p.lat, {
      heading: p.heading,
      pitch: p.pitch,
      range: p.range,
      duration
    })
  }

  /** 从高空俯冲到示范区 */
  async flyFromSpace(): Promise<boolean> {
    this.stopOrbit()
    const [lon, lat] = this.region.center
    this.camera.cancelFlight()
    this.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(lon - 1.2, lat - 4.5, 2_600_000),
      orientation: { heading: toRad(12), pitch: toRad(-58), roll: 0 }
    })
    await wait(350)
    return this.flyHome(5.2)
  }

  /** 首次加载的入场动画：从 20km 高空斜飞到默认视角 */
  intro(): Promise<boolean> {
    const p = this.homeParams()
    this.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(p.lon - 0.08, p.lat - 0.11, 20000),
      orientation: { heading: toRad(30), pitch: toRad(-62), roll: 0 }
    })
    return this.flyTo(p.lon, p.lat, { heading: p.heading, pitch: p.pitch, range: p.range, duration: 3.2 })
  }

  flyTo(lon: number, lat: number, opts: FlyOptions & { height?: number } = {}): Promise<boolean> {
    this.stopOrbit()
    const heading = opts.heading !== undefined ? toRad(opts.heading) : this.camera.heading
    const pitch = toRad(opts.pitch ?? -38)
    const range = opts.range ?? 900
    const target = new Cesium.BoundingSphere(Cesium.Cartesian3.fromDegrees(lon, lat, opts.height ?? 0), 1)
    return new Promise((resolve) => {
      this.camera.flyToBoundingSphere(target, {
        offset: new Cesium.HeadingPitchRange(heading, pitch, range),
        duration: opts.duration ?? 1.8,
        easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT,
        complete: () => resolve(true),
        cancel: () => resolve(false)
      })
    })
  }

  /** 环绕目标巡航：先飞到起始位，再以固定角速度绕行 */
  async orbit(lon: number, lat: number, opts: OrbitOptions = {}): Promise<boolean> {
    const range = opts.range ?? 1600
    const pitch = opts.pitch ?? -30
    const heading = opts.heading ?? Cesium.Math.toDegrees(this.camera.heading)
    const ok = await this.flyTo(lon, lat, { range, pitch, heading, duration: 2.2 })
    if (!ok) return false
    this.stopOrbit()
    Cesium.Cartesian3.fromDegrees(lon, lat, 0, Cesium.Ellipsoid.WGS84, this.orbitCenter)
    this.orbitHpr.heading = toRad(heading)
    this.orbitHpr.pitch = toRad(pitch)
    this.orbitHpr.range = range
    const rate = toRad(opts.speed ?? 6)
    this.lastOrbitTs = performance.now()
    this.removeOrbit = this.viewer.scene.preRender.addEventListener(() => {
      const now = performance.now()
      const dt = Math.min(0.1, (now - this.lastOrbitTs) / 1000)
      this.lastOrbitTs = now
      this.orbitHpr.heading += rate * dt
      this.camera.lookAt(this.orbitCenter, this.orbitHpr)
    })
    return true
  }

  get orbiting() {
    return !!this.removeOrbit
  }

  stopOrbit() {
    if (!this.removeOrbit) return
    this.removeOrbit()
    this.removeOrbit = null
    if (!this.viewer.isDestroyed()) this.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
  }

  cancel() {
    this.stopOrbit()
    if (!this.viewer.isDestroyed()) this.camera.cancelFlight()
  }

  destroy() {
    this.removeOrbit?.()
    this.removeOrbit = null
  }
}

function wait(ms: number): Promise<void> {
  return new Promise((r) => window.setTimeout(r, ms))
}
