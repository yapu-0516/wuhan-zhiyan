// 底图控制：暗色（Esri Dark Gray）/ 卫星（在线 Esri→本地单幅缓存→离线
// NaturalEarthII），运行时切换；各级失败都会自动降级，并通过回调通知界面。
import * as Cesium from 'cesium'
import { BASEMAPS, type BasemapConfig, type BasemapKey } from '@/config/cesium'

/** 各底图的色彩调校：让底图退居背景，突出三维对象与 HUD */
const STYLE: Record<
  BasemapKey,
  Partial<Pick<Cesium.ImageryLayer, 'alpha' | 'brightness' | 'contrast' | 'saturation' | 'gamma' | 'hue'>>
> = {
  dark: { alpha: 1, brightness: 0.94, contrast: 1.18, saturation: 0.45 },
  // 卫星影像是“真实武汉”的底稿。只做轻微校正，不再压暗成背景纹理。
  satellite: { alpha: 1, brightness: 0.86, contrast: 1.08, saturation: 0.55, gamma: 0.99 },
  offline: { alpha: 1, brightness: 0.42, contrast: 1.1, saturation: 0.45 }
}

/** 底色：中性深灰，瓦片加载前也不会出现蓝色数据底板。 */
export const GLOBE_BASE_COLOR = '#101519'

export class BasemapController {
  private layer: Cesium.ImageryLayer | null = null
  private removeError: (() => void) | null = null
  private probeTimer: number | undefined
  private token = 0
  current: BasemapKey = 'offline'

  private readonly onOffline = () => {
    if (this.current === 'satellite' || this.current === 'dark') this.fallback(this.current)
  }

  constructor(
    private viewer: Cesium.Viewer,
    private probePoint: () => [number, number],
    private onFallback: (from: BasemapKey, to: BasemapKey) => void
  ) {
    window.addEventListener('offline', this.onOffline)
  }

  set(key: BasemapKey) {
    if (this.viewer.isDestroyed()) return
    const token = ++this.token
    this.clear()
    this.current = key
    const cfg = BASEMAPS[key]
    const style = STYLE[key]
    if (key === 'offline' || !cfg?.url) {
      const layer = Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII')),
        {}
      )
      Object.assign(layer, style)
      this.viewer.imageryLayers.add(layer, 0)
      this.layer = layer
      return
    }
    this.addRemote(key, cfg, style, token)
  }

  private addLocalSatellite(
    cfg: BasemapConfig,
    style: Partial<Pick<Cesium.ImageryLayer, 'alpha' | 'brightness' | 'contrast' | 'saturation' | 'gamma' | 'hue'>>,
    token: number,
    key: BasemapKey
  ) {
    if (!cfg.localUrl || !cfg.localRectangle || !cfg.localWidth || !cfg.localHeight) return
    const [west, south, east, north] = cfg.localRectangle
    const provider = new Cesium.SingleTileImageryProvider({
      url: cfg.localUrl,
      rectangle: Cesium.Rectangle.fromDegrees(west, south, east, north),
      tileWidth: cfg.localWidth,
      tileHeight: cfg.localHeight,
      credit: cfg.credit ? new Cesium.Credit(cfg.credit) : undefined
    })
    const layer = new Cesium.ImageryLayer(provider, {})
    Object.assign(layer, style)
    this.viewer.imageryLayers.add(layer, 0)
    this.layer = layer
    let failed = false
    this.removeError = provider.errorEvent.addEventListener(() => {
      if (failed || token !== this.token) return
      failed = true
      console.warn('[basemap] 本地卫星底图加载失败，切换内置离线底图', cfg.localUrl)
      this.removeError?.()
      this.removeError = null
      if (!this.viewer.isDestroyed()) this.viewer.imageryLayers.remove(layer, true)
      if (this.layer === layer) this.layer = null
      this.fallback(key, false)
    })
  }

  private addRemote(
    key: BasemapKey,
    cfg: BasemapConfig,
    style: Partial<Pick<Cesium.ImageryLayer, 'alpha' | 'brightness' | 'contrast' | 'saturation' | 'gamma' | 'hue'>>,
    token: number
  ) {
    if (!cfg.url) {
      this.fallback(key)
      return
    }
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      this.fallback(key)
      return
    }
    const provider = new Cesium.UrlTemplateImageryProvider({
      url: cfg.url,
      subdomains: cfg.subdomains,
      credit: cfg.credit ? new Cesium.Credit(cfg.credit) : undefined,
      maximumLevel: cfg.maxLevel ?? 18
    })
    const layer = new Cesium.ImageryLayer(provider, {})
    Object.assign(layer, style)
    this.viewer.imageryLayers.add(layer, 0)
    this.layer = layer
    this.probe(cfg.url, cfg.subdomains, token, key)
  }

  /** 探测一张示范区瓦片，6 秒内加载失败则回退离线底图 */
  private probe(template: string, subdomains: string[] | undefined, token: number, key: BasemapKey) {
    const [lon, lat] = this.probePoint()
    const z = 12
    const n = 2 ** z
    const x = Math.floor(((lon + 180) / 360) * n)
    const latRad = (lat * Math.PI) / 180
    const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n)
    const url = template
      .replace('{s}', subdomains?.[0] ?? 'a')
      .replace('{z}', String(z))
      .replace('{x}', String(x))
      .replace('{y}', String(y))
    const img = new Image()
    img.crossOrigin = 'anonymous'
    let settled = false
    const fail = () => {
      if (settled) return
      settled = true
      if (token === this.token) this.fallback(key)
    }
    img.onload = () => {
      settled = true
      window.clearTimeout(this.probeTimer)
    }
    img.onerror = fail
    this.probeTimer = window.setTimeout(fail, 6000)
    img.src = url
  }

  private fallback(from: BasemapKey, allowLocal = true) {
    if (this.current === 'offline' || this.viewer.isDestroyed()) return
    const cfg = BASEMAPS.satellite
    if (from === 'satellite' && allowLocal && cfg.localUrl && cfg.localRectangle && cfg.localWidth && cfg.localHeight) {
      const token = ++this.token
      this.clear()
      this.current = 'satellite'
      console.warn('[basemap] 在线卫星影像不可用，切换本地缓存')
      this.addLocalSatellite(cfg, STYLE.satellite, token, 'satellite')
      return
    }
    this.set('offline')
    this.onFallback(from, 'offline')
  }

  private clear() {
    window.clearTimeout(this.probeTimer)
    this.removeError?.()
    this.removeError = null
    if (this.layer && !this.viewer.isDestroyed()) {
      this.viewer.imageryLayers.remove(this.layer, true)
    }
    this.layer = null
  }

  destroy() {
    this.token++
    window.removeEventListener('offline', this.onOffline)
    window.clearTimeout(this.probeTimer)
    this.removeError?.()
    this.removeError = null
    this.layer = null
  }
}
