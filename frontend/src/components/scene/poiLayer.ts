// 应急资源图层：医院 / 消防站 / 派出所 / 学校（Billboard + Label，可整体开关）
import * as Cesium from 'cesium'
import type { Poi } from '@/types/building'
import { POI_META } from '@/types/building'
import { poiIcon } from './icons'

const SCALE_BY_DISTANCE = new Cesium.NearFarScalar(600, 1.0, 9000, 0.5)

export class PoiLayer {
  private billboards = new Cesium.BillboardCollection()
  private labels = new Cesium.LabelCollection()
  private pois = new Map<string, Poi>()

  constructor(private scene: Cesium.Scene) {
    scene.primitives.add(this.billboards)
    scene.primitives.add(this.labels)
  }

  get count() {
    return this.pois.size
  }

  load(list: Poi[] | null | undefined): number {
    this.billboards.removeAll()
    this.labels.removeAll()
    this.pois.clear()
    if (!Array.isArray(list)) return 0
    for (const p of list) {
      if (!p || !Number.isFinite(p.longitude) || !Number.isFinite(p.latitude) || !(p.kind in POI_META)) continue
      const id = `p:${p.id}`
      const position = Cesium.Cartesian3.fromDegrees(p.longitude, p.latitude, 2)
      const icon = poiIcon(p.kind)
      const bb = this.billboards.add({
        position,
        scale: 0.5,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        scaleByDistance: SCALE_BY_DISTANCE,
        disableDepthTestDistance: 2500,
        id
      })
      bb.setImage(icon.key, icon.canvas)
      this.labels.add({
        position,
        text: p.name,
        font: '12px "PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif',
        fillColor: Cesium.Color.fromCssColorString('#cfe3ff'),
        outlineColor: Cesium.Color.fromCssColorString('#050a17'),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -36),
        pixelOffsetScaleByDistance: SCALE_BY_DISTANCE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 2600),
        disableDepthTestDistance: 2500,
        id
      })
      this.pois.set(id, p)
    }
    return this.pois.size
  }

  fromPick(id: unknown): Poi | undefined {
    return typeof id === 'string' ? this.pois.get(id) : undefined
  }

  setVisible(v: boolean) {
    this.billboards.show = v
    this.labels.show = v
  }

  destroy() {
    if (!this.scene.isDestroyed()) {
      this.scene.primitives.remove(this.billboards)
      this.scene.primitives.remove(this.labels)
    }
    this.pois.clear()
  }
}
