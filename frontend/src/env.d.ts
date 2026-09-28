/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Cesium 在运行时读取该全局变量以定位 Workers/Assets 等静态资源
interface Window {
  CESIUM_BASE_URL?: string
}
