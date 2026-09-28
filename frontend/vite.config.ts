import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { fileURLToPath, URL } from 'node:url'

const srcDir = fileURLToPath(new URL('./src', import.meta.url))

// 阶段2：Cesium + Vite 配置
// 1. viteStaticCopy：把 Cesium 运行时所需的四类静态资源拷贝到 /cesium/
//    （Workers / Assets / ThirdParty / Widgets），不能被打进 JS。
// 2. alias：
//    - @zip.js/zip.js/lib/zip-no-worker.js → @zip.js/zip.js
//      Cesium 1.125 的 KmlDataSource 仍按旧子路径导入 zip.js，
//      而 @zip.js/zip.js@2.18 的 exports 不再暴露该子路径，会致 esbuild 预打包失败。
//      这里映射到包主入口（单线程版本，语义等价；第3周不使用 KML，仅保证预打包通过）。
//    - ^@/(.+) → src/$1，且用正则避免误伤 @zip.js 等 @scope 包。
export default defineConfig({
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
    open: false
  }
})
