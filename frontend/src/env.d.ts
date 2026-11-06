/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
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
  /** 底图：dark（Esri 暗色画布）| satellite（本地卫星单图，缺失时在线）| offline（NaturalEarthII） */
  readonly VITE_BASEMAP?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Cesium 在运行时读取该全局变量以定位 Workers/Assets 等静态资源
interface Window {
  CESIUM_BASE_URL?: string
}
