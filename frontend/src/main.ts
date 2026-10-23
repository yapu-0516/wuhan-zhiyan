import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import '@/assets/styles/main.css'
import { useCityEvents } from '@/composables/useCityEvents'
import { useSystemInfo } from '@/composables/useSystemInfo'

// Cesium 运行时静态资源基础路径：vite-plugin-static-copy 在 dev/build 时拷贝到 <BASE_URL>cesium/
window.CESIUM_BASE_URL = `${import.meta.env.BASE_URL}cesium`

// Element Plus 暗色主题（index.html 已带 class="dark"，此处兜底）
document.documentElement.classList.add('dark')

const app = createApp(App)

// 注册 Element Plus 图标为全局组件
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp as never)
}

app.use(router)
app.use(ElementPlus, { locale: zhCn })

function setSplash(text: string) {
  const el = document.getElementById('splash-status')
  if (el) el.textContent = text
}

function hideSplash() {
  const splash = document.getElementById('splash')
  if (!splash) return
  splash.classList.add('is-hidden')
  window.setTimeout(() => splash.remove(), 700)
}

function timeout(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms))
}

// 先加载事件（及系统信息）再挂载，确保三维场景与大屏首帧即有数据；
// 后端无响应时最多等待 8 秒，随后降级挂载（API 层会自动切换离线快照）。
;(async () => {
  setSplash('正在连接城市数据中台…')
  await Promise.race([
    Promise.allSettled([useCityEvents().loadFromApi(), useSystemInfo().load()]),
    timeout(8000)
  ])
  setSplash('正在构建三维城市…')
  await router.isReady().catch(() => undefined)
  app.mount('#app')
  window.requestAnimationFrame(() => hideSplash())
})()
