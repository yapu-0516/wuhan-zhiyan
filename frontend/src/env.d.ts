/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** 后端 API 前缀，默认 /api */
  readonly VITE_API_BASE?: string
  /** 'true' 时强制使用 public/snapshot 静态快照 */
  readonly VITE_USE_MOCK?: string
  /** 自定义 WebSocket 地址 */
  readonly VITE_WS_URL?: string
  /** Cesium Ion Token（可选） */
  readonly VITE_CESIUM_ION_TOKEN?: string
  /** 底图：dark（默认，Esri 暗色画布）| satellite（Esri 影像）| offline（Cesium 自带 NaturalEarthII） */
  readonly VITE_BASEMAP?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Cesium 在运行时读取该全局变量以定位 Workers/Assets 等静态资源
interface Window {
  CESIUM_BASE_URL?: string
}
