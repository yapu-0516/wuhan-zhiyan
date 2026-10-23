import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { fileURLToPath, URL } from 'node:url'

const srcDir = fileURLToPath(new URL('./src', import.meta.url))

// Cesium + Vite 配置
// 1. viteStaticCopy：把 Cesium 运行时所需的四类静态资源拷贝到 /cesium/
//    （Workers / Assets / ThirdParty / Widgets），不能被打进 JS。
// 2. alias：
//    - @zip.js/zip.js/lib/zip-no-worker.js → @zip.js/zip.js
//      Cesium 1.125 的 KmlDataSource 仍按旧子路径导入 zip.js，
//      而 @zip.js/zip.js@2.18 的 exports 不再暴露该子路径，会致 esbuild 预打包失败。
//    - ^@/(.+) → src/$1，且用正则避免误伤 @zip.js 等 @scope 包。
// 3. server.proxy：开发期把 /api（含 WebSocket）与 /files 转发到 FastAPI 后端（VITE_BACKEND，默认 127.0.0.1:8000）。
// 4. build.rollupOptions.manualChunks：Cesium / ECharts / Element Plus 拆分独立 chunk，利于缓存。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_BACKEND || 'http://127.0.0.1:8000'
  return {
    base: env.VITE_BASE || '/',
    plugins: [
      vue(),
      viteStaticCopy({
        targets: [
          { src: 'node_modules/cesium/Build/Cesium/Workers', dest: 'cesium' },
          { src: 'node_modules/cesium/Build/Cesium/Assets', dest: 'cesium' },
          { src: 'node_modules/cesium/Build/Cesium/ThirdParty', dest: 'cesium' },
          { src: 'node_modules/cesium/Build/Cesium/Widgets', dest: 'cesium' }
        ]
      })
    ],
    resolve: {
      alias: [
        {
          find: '@zip.js/zip.js/lib/zip-no-worker.js',
          replacement: '@zip.js/zip.js'
        },
        {
          find: /^@\/(.+)$/,
          replacement: `${srcDir}/$1`
        }
      ]
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      open: false,
      proxy: {
        '/api': { target: backend, changeOrigin: true, ws: true },
        '/files': { target: backend, changeOrigin: true }
      }
    },
    build: {
      chunkSizeWarningLimit: 6000,
      rollupOptions: {
        output: {
          manualChunks: {
            cesium: ['cesium'],
            echarts: ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers'],
            'element-plus': ['element-plus']
          }
        }
      }
    }
  }
})
