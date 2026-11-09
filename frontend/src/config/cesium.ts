/**
 * Cesium 三维场景配置
 *
 * - CESIUM_ION_TOKEN：可选。留空即可完全脱离 Cesium Ion 运行；如需 Cesium World Terrain / 高清影像，
 *   到 https://ion.cesium.com/signup 免费注册后通过环境变量 VITE_CESIUM_ION_TOKEN 注入。
 * - BASEMAP：底图方案，可在界面图层面板中实时切换：
 *     satellite Esri World Imagery 在线瓦片（默认；失败时回退本地全城概览 + 重点区精图）
 *     dark      Esri World Dark Gray Canvas 暗色底图（低照度备选，含中文路名，无需 Token）
 *     offline   Cesium 自带 NaturalEarthII（完全离线可用）
 *   在线卫星图加载失败时自动尝试本地缓存，本地缓存仍失败时回退 offline。
 */
export const CESIUM_ION_TOKEN: string = import.meta.env.VITE_CESIUM_ION_TOKEN || ''

export type BasemapKey = 'dark' | 'satellite' | 'offline'

export const DEFAULT_BASEMAP: BasemapKey = (import.meta.env.VITE_BASEMAP as BasemapKey) || 'satellite'

/** 中心城区默认视角（后端 /api/system/info 的 region.center 会覆盖） */
export const DEFAULT_REGION = {
  name: '武汉中心城区',
  center: [114.35, 30.585] as [number, number],
  bbox: [114.15, 30.45, 114.55, 30.72] as [number, number, number, number]
}

export interface LocalBasemapLayer {
  url: string
  rectangle: [number, number, number, number]
  width: number
  height: number
}

export interface BasemapConfig {
  label: string
  url?: string
  subdomains?: string[]
  credit?: string
  maxLevel?: number
  /** 离线时叠加的本地影像：全城概览在下，重点区高清在上。 */
  localLayers?: LocalBasemapLayer[]
}

export const BASEMAPS: Record<BasemapKey, BasemapConfig> = {
  dark: {
    label: '暗色底图',
    // 注：CARTO dark_all 自 2025 年起需 API Key，未授权时返回水印瓦片，故改用 Esri 免 Token 暗色画布
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    credit: 'Esri, HERE, Garmin, © OpenStreetMap contributors',
    maxLevel: 16
  },
  satellite: {
    label: '卫星影像',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    localLayers: [
      {
        url: `${import.meta.env.BASE_URL}basemap/wuhan-city-z13.jpg`,
        rectangle: DEFAULT_REGION.bbox,
        width: 2330,
        height: 1827
      },
      {
        url: `${import.meta.env.BASE_URL}basemap/wuhan-satellite-z17.jpg`,
        rectangle: [114.27, 30.57, 114.312, 30.612],
        width: 3915,
        height: 4547
      }
    ],
    credit: 'Esri, Maxar, Earthstar Geographics',
    maxLevel: 19
  },
  offline: { label: '离线底图' }
}
