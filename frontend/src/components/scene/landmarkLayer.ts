import * as Cesium from 'cesium'

interface Landmark {
  key: string
  name: string
  longitude: number
  latitude: number
  heading?: number
}

const LANDMARKS: Landmark[] = [
  { key: 'yellow-building', name: '黄鹤楼', longitude: 114.305378, latitude: 30.545682 },
  { key: 'yangtze-bridge', name: '武汉长江大桥', longitude: 114.283457, latitude: 30.551792, heading: -61 }
]

export class LandmarkLayer {
  private tilesets: Cesium.Cesium3DTileset[] = []
  private loaded = new Set<string>()
  private loading = new Map<string, Promise<void>>()
  private visible = true
  private destroyed = false

  constructor(private scene: Cesium.Scene) {}

  get count() {
    return this.tilesets.length
  }

  async load(): Promise<number> {
    // 黄鹤楼原始包约 269 MB，进入武昌精细图层时再加载；大桥仅 2 MB，可直接加载。
    const eager = LANDMARKS.filter((item) => item.key !== 'yellow-building')
    const results = await Promise.allSettled(eager.map((item) => this.loadOne(item.key)))
    if (this.destroyed) return 0
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        console.warn(`[landmarks] ${eager[index].name} 3D Tiles 加载失败`, result.reason)
      }
    })
    return this.tilesets.length
  }

  loadOne(key: string): Promise<void> {
    const existing = this.loading.get(key)
    if (existing) return existing
    const item = LANDMARKS.find((entry) => entry.key === key)
    if (!item || this.loaded.has(key) || this.destroyed) return Promise.resolve()
    const task = this.add(item)
      .then(() => {
        this.loaded.add(key)
      })
      .finally(() => this.loading.delete(key))
    this.loading.set(key, task)
    return task
  }

  private async add(item: Landmark): Promise<void> {
    const base = import.meta.env.BASE_URL.replace(/\/?$/, '/')
    const tileset = await Cesium.Cesium3DTileset.fromUrl(`${base}models/3d-tiles/${item.key}/tileset.json`, {
      maximumScreenSpaceError: 12,
      dynamicScreenSpaceError: true,
      cullWithChildrenBounds: true
    })
    if (this.destroyed) {
      tileset.destroy()
      return
    }

    // 桥梁包内的根变换指向错误城市，按根节点原点重定位到武汉本地 ENU 坐标系。
    const root = tileset.root
    const transform = root?.transform
    if (transform) {
      const origin = Cesium.Matrix4.getTranslation(transform, new Cesium.Cartesian3())
      const from = Cesium.Transforms.eastNorthUpToFixedFrame(origin)
      const to = Cesium.Transforms.eastNorthUpToFixedFrame(
        Cesium.Cartesian3.fromDegrees(item.longitude, item.latitude)
      )
      const oriented = Cesium.Matrix4.multiply(
        to,
        Cesium.Matrix4.fromRotationTranslation(
          Cesium.Matrix3.fromRotationZ(Cesium.Math.toRadians(item.heading ?? 0)),
          Cesium.Cartesian3.ZERO,
          new Cesium.Matrix4()
        ),
        new Cesium.Matrix4()
      )
      const correction = Cesium.Matrix4.multiply(
        oriented,
        Cesium.Matrix4.inverse(from, new Cesium.Matrix4()),
        new Cesium.Matrix4()
      )
      tileset.modelMatrix = correction
    }
    tileset.show = this.visible
    this.scene.primitives.add(tileset)
    this.tilesets.push(tileset)
  }

  setVisible(visible: boolean) {
    this.visible = visible
    this.tilesets.forEach((tileset) => (tileset.show = visible))
  }

  destroy() {
    this.destroyed = true
    this.tilesets.forEach((tileset) => {
      if (!tileset.isDestroyed() && !this.scene.isDestroyed()) this.scene.primitives.remove(tileset)
    })
    this.tilesets = []
  }
}
