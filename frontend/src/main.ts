import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import '@/assets/styles/main.css'
import { useCityEvents } from '@/composables/useCityEvents'

// Cesium 运行时静态资源基础路径
// 由 vite-plugin-static-copy 在 dev/build 时拷贝到 /cesium/
window.CESIUM_BASE_URL = '/cesium'

const app = createApp(App)

// 注册 Element Plus 图标为全局组件
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp as never)
}

app.use(router)
app.use(ElementPlus)

// 阶段11：通过 API 接口层加载事件后再挂载（USE_MOCK 走 mock，接后端后走 fetch）
// 确保组件 onMounted 时事件数据已就绪（CesiumViewer 据此加载事件 entity）。
// 第3周 mock 几乎无延迟；第4周接真实 API 时可在此处加 loading 占位。
;(async () => {
  await useCityEvents().loadFromApi()
  app.mount('#app')
})()
