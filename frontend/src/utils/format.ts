// 通用格式化工具：时间 / 数字 / 算法指标
// 后端时间字段统一为东八区本地时间字符串 yyyy-MM-dd HH:mm:ss（见 docs/api.md）。
import { METRIC_DEFS, METRIC_VALUE_LABEL } from '@/config/metrics'

/** 解析 yyyy-MM-dd HH:mm:ss 为 Date（失败返回 null） */
export function parseTime(s?: string | null): Date | null {
  if (!s) return null
  const d = new Date(s.includes('T') ? s : s.replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

const pad = (n: number) => String(n).padStart(2, '0')

/** HH:mm（非当天时带上 MM-dd，避免把历史数据误读为今天的时刻） */
export function hhmm(s?: string | null): string {
  const d = parseTime(s)
  if (!d) return '--:--'
  const now = new Date()
  const sameDay =
    d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
  return sameDay ? `${pad(d.getHours())}:${pad(d.getMinutes())}` : shortTime(s)
}

/** MM-dd HH:mm */
export function shortTime(s?: string | null): string {
  const d = parseTime(s)
  return d ? `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}` : '--'
}

/** 相对时间：刚刚 / x 分钟前 / x 小时前 / MM-dd HH:mm */
export function relativeTime(s?: string | null, now = Date.now()): string {
  const d = parseTime(s)
  if (!d) return '--'
  const diff = (now - d.getTime()) / 1000
  if (diff < 0) return shortTime(s)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return shortTime(s)
}

/** 是否为今天 */
export function isToday(s?: string | null, now = new Date()): boolean {
  const d = parseTime(s)
  return (
    !!d && d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
  )
}

export function fixed(n: number | null | undefined, digits = 1): string {
  return typeof n === 'number' && Number.isFinite(n) ? n.toFixed(digits) : '--'
}

export function percent(r: number | null | undefined, digits = 0): string {
  return typeof r === 'number' && Number.isFinite(r) ? `${(r * 100).toFixed(digits)}%` : '--'
}

export function thousands(n: number | null | undefined): string {
  return typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('zh-CN') : '--'
}

/** 算法指标中文名与单位（权威字典见 @/config/metrics，未知指标原样展示） */
const METRIC_META = METRIC_DEFS

export function metricLabel(key: string): string {
  return METRIC_META[key]?.label ?? key
}

export function metricValue(key: string, v: number | string): string {
  if (typeof v !== 'number') return METRIC_VALUE_LABEL[v] ?? String(v)
  const m = METRIC_META[key]
  if (!m) return Number.isInteger(v) ? String(v) : v.toFixed(Math.abs(v) < 1 ? 3 : 2)
  if (m.ratio) return `${(v * 100).toFixed(m.digits ?? 1)}%`
  const s = v.toFixed(m.digits ?? 2)
  return m.unit ? `${s} ${m.unit}` : s
}
