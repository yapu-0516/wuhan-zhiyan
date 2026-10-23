// 页面通用格式化工具：时间 / 百分比 / 数字 / 体积
// 后端时间字符串均为东八区本地时间 `yyyy-MM-dd HH:mm:ss`（或 `yyyy-MM-dd HH:mm`），按"墙上时间"解析。

/** 解析后端时间字符串；失败返回 null */
export function parseTs(ts?: string | null): Date | null {
  if (!ts) return null
  const d = new Date(ts.replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

const p2 = (n: number) => String(n).padStart(2, '0')

/** 当前本地时间 yyyy-MM-dd HH:mm:ss */
export function nowText(d: Date = new Date()): string {
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`
}

/** 今天的日期前缀 yyyy-MM-dd */
export function todayPrefix(d: Date = new Date()): string {
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`
}

/** MM-DD HH:mm（同年省略年份） */
export function shortTime(ts?: string | null): string {
  if (!ts) return '—'
  const d = parseTs(ts)
  if (!d) return ts
  const sameYear = d.getFullYear() === new Date().getFullYear()
  const base = `${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`
  return sameYear ? base : `${d.getFullYear()}-${base}`
}

/** 相对时间：刚刚 / n 秒前 / n 分钟前 / n 小时前 / n 天前 */
export function relativeTime(ts?: string | null, now: number = Date.now()): string {
  const d = parseTs(ts)
  if (!d) return ts || '—'
  const sec = Math.round((now - d.getTime()) / 1000)
  if (sec < -60) return ts ?? '—'
  if (sec < 5) return '刚刚'
  if (sec < 60) return `${sec} 秒前`
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`
  if (sec < 86400 * 30) return `${Math.floor(sec / 86400)} 天前`
  return ts ?? '—'
}

/** 0~1 → "93%"；非数值返回 — */
export function pct(v: unknown, digits = 0): string {
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${(n * 100).toFixed(digits)}%`
}

/** 0~1 → 0~100 的整数（供进度条使用，自动截断） */
export function pct100(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, Math.round(n * 100)))
}

/** 数字格式化：自适应小数位，去除多余的 0 */
export function fmtNum(v: number, maxDigits = 2): string {
  if (!Number.isFinite(v)) return '—'
  const abs = Math.abs(v)
  const digits = abs >= 1000 ? 0 : abs >= 100 ? Math.min(1, maxDigits) : maxDigits
  return Number(v.toFixed(digits)).toLocaleString('zh-CN', { maximumFractionDigits: digits })
}

/** 毫秒 → 1.2 秒 / 85 毫秒 / 1 分 05 秒 */
export function fmtDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '—'
  if (ms < 1000) return `${Math.round(ms)} 毫秒`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)} 秒`
  return `${Math.floor(s / 60)} 分 ${p2(Math.floor(s % 60))} 秒`
}

/** 字节 → 带单位字符串 */
export function fmtBytes(n?: number | null): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v >= 100 || i === 0 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`
}

/** 经纬度格式化 */
export function fmtCoord(lon: number, lat: number, digits = 5): string {
  return `${lon.toFixed(digits)}, ${lat.toFixed(digits)}`
}

/** 判断 URL 是否指向图片 */
export function isImageUrl(url?: string | null): boolean {
  return !!url && /\.(jpe?g|png|gif|webp|bmp|tiff?)(\?.*)?$/i.test(url)
}

/** 判断 URL 是否指向 CSV */
export function isCsvUrl(url?: string | null): boolean {
  return !!url && /\.csv(\?.*)?$/i.test(url)
}

/** 将未知异常转为可展示的中文提示 */
export function errMsg(e: unknown, fallback = '操作失败，请稍后重试'): string {
  if (e instanceof Error && e.message) return e.message
  if (typeof e === 'string' && e) return e
  return fallback
}

/** 十六进制颜色 + 透明度 → rgba() */
export function hexA(hex: string, alpha: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return hex
  const n = parseInt(m[1], 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}
