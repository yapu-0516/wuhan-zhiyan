// 氛围特效：示范区雷达扫描（自定义着色器）+ 示范区边界发光线（内置 PolylineGlow 材质）
import * as Cesium from 'cesium'
import { SURFACE_VERTEX_FORMAT, fxAttribute, radarAppearance, type SceneClock } from './shaders'
import type { Region } from './cameraControl'

export class AmbientEffects {
  private radar: Cesium.Primitive | null = null
  private boundary = new Cesium.PolylineCollection()
  private visible = true
  private safe = false

  constructor(
    private scene: Cesium.Scene,
    private clock: SceneClock
  ) {
    scene.primitives.add(this.boundary)
  }

  setRegion(region: Region) {
    const [w, s, e, n] = region.bbox
    const [lon, lat] = region.center
    // 边界：示范区外框
    this.boundary.removeAll()
    this.boundary.add({
      positions: Cesium.Cartesian3.fromDegreesArrayHeights([w, s, 4, e, s, 4, e, n, 4, w, n, 4, w, s, 4]),
      width: 7,
      material: Cesium.Material.fromType('PolylineGlow', {
        color: Cesium.Color.fromCssColorString('#4fc3f7').withAlpha(0.75),
        glowPower: 0.22,
        taperPower: 1.0
      })
    })
    // 雷达：半径取示范区短边的一半
    if (this.radar && !this.radar.isDestroyed()) this.scene.primitives.remove(this.radar)
    this.radar = null
    if (this.safe) return
    const radius =
      Math.min(
        Cesium.Cartesian3.distance(Cesium.Cartesian3.fromDegrees(w, lat), Cesium.Cartesian3.fromDegrees(e, lat)),
        Cesium.Cartesian3.distance(Cesium.Cartesian3.fromDegrees(lon, s), Cesium.Cartesian3.fromDegrees(lon, n))
      ) * 0.5
    try {
      const geometry = Cesium.EllipseGeometry.createGeometry(
        new Cesium.EllipseGeometry({
          center: Cesium.Cartesian3.fromDegrees(lon, lat),
          semiMajorAxis: radius,
          semiMinorAxis: radius,
          height: 1,
          granularity: Cesium.Math.toRadians(0.5),
          vertexFormat: SURFACE_VERTEX_FORMAT
        })
      )
      if (!geometry) return
      this.radar = new Cesium.Primitive({
        geometryInstances: new Cesium.GeometryInstance({
          geometry,
          id: 'radar',
          attributes: {
            color: Cesium.ColorGeometryInstanceAttribute.fromColor(
              Cesium.Color.fromCssColorString('#36e4ff').withAlpha(0.85)
            ),
            fx: fxAttribute(0, 0, 0, 0)
          }
        }),
        appearance: radarAppearance(this.clock),
        asynchronous: false,
        allowPicking: false
      })
      this.radar.show = this.visible
      this.scene.primitives.add(this.radar)
    } catch (e) {
      console.warn('[effects] 雷达扫描创建失败', e)
      this.radar = null
    }
  }

  setVisible(v: boolean) {
    this.visible = v
    this.boundary.show = v
    if (this.radar && !this.radar.isDestroyed()) this.radar.show = v
  }

  setSafeMode() {
    this.safe = true
    if (this.radar && !this.radar.isDestroyed()) this.scene.primitives.remove(this.radar)
    this.radar = null
  }

  destroy() {
    if (this.scene.isDestroyed()) return
    if (this.radar && !this.radar.isDestroyed()) this.scene.primitives.remove(this.radar)
    this.scene.primitives.remove(this.boundary)
    this.radar = null
  }
}
