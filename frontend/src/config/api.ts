// API 接口配置
// v1：已接入 FastAPI 后端。
//   - 开发期：Vite 代理 /api、/files（含 WebSocket）到 VITE_BACKEND（默认 http://127.0.0.1:8000），见 vite.config.ts；
//   - 生产期：后端直接托管前端 dist，同源访问；
//   - 纯静态部署（如 GitHub Pages）：设置 VITE_USE_MOCK=true，读取 public/snapshot 下由后端导出的数据快照。
// 后端不可达时 API 层自动降级为快照数据（离线演示模式），界面顶部会给出提示。
export const API_BASE: string = import.meta.env.VITE_API_BASE || '/api'

/** 是否强制使用快照数据（不请求后端） */
export const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK === 'true'

/** WebSocket 地址；为空时按当前页面 host 推导 */
export const WS_URL: string = import.meta.env.VITE_WS_URL || ''

/** 静态快照目录（相对 BASE_URL） */
export const SNAPSHOT_BASE = `${import.meta.env.BASE_URL}snapshot`

/** 把后端返回的 /files/... 相对地址转为可访问地址（快照模式下指向 public/snapshot/files） */
export function fileUrl(url?: string | null): string {
  if (!url) return ''
  if (/^(https?:|data:|blob:)/.test(url)) return url
  if (USE_MOCK && url.startsWith('/files/')) return `${SNAPSHOT_BASE}${url}`
  return url
}
