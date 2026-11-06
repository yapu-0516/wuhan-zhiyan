// Canvas 生成的场景图标（事件定位针 / 应急资源点），按 key 缓存复用。
// 图标以 2 倍分辨率绘制，Billboard 以 scale 0.5 显示，保证高分屏清晰。
import type { EventType, Severity } from '@/types/event'
import { EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import type { Poi } from '@/types/building'

const cache = new Map<string, HTMLCanvasElement>()

let emojiOk: boolean | null = null

/** 检测系统是否能渲染彩色 Emoji（部分 Linux 无 Emoji 字体时回退为中文单字） */
function emojiSupported(): boolean {
  if (emojiOk !== null) return emojiOk
  try {
    const c = document.createElement('canvas')
    c.width = c.height = 24
    const ctx = c.getContext('2d', { willReadFrequently: true })
    if (!ctx) return (emojiOk = false)
    ctx.textBaseline = 'top'
    ctx.font = '18px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Segoe UI Symbol",sans-serif'
    ctx.fillText('🔥', 1, 1)
    const d = ctx.getImageData(0, 0, 24, 24).data
    emojiOk = false
    for (let i = 0; i < d.length; i += 4) {
      if (d[i + 3] > 40 && (Math.abs(d[i] - d[i + 1]) > 30 || Math.abs(d[i + 1] - d[i + 2]) > 30)) {
        emojiOk = true
        break
      }
    }
  } catch {
    emojiOk = false
  }
  return emojiOk
}

const EVENT_GLYPH: Record<EventType, string> = { fire: '火', traffic: '堵', building: '建', flood: '涝' }
const POI_GLYPH: Record<Poi['kind'], string> = { hospital: '医', fire_station: '消', police: '警', school: '学' }
const POI_EMOJI: Record<Poi['kind'], string> = { hospital: '🏥', fire_station: '🚒', police: '🚓', school: '🏫' }

const POI_COLOR: Record<Poi['kind'], string> = {
  hospital: '#ff6b81',
  fire_station: '#ff8a3d',
  police: '#3fa9ff',
  school: '#7ddc6f'
}

const EMOJI_FONT = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif'
const CJK_FONT = '"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif'

function shade(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.max(0, Math.min(255, ((n >> 16) & 255) + amt))
  const g = Math.max(0, Math.min(255, ((n >> 8) & 255) + amt))
  const b = Math.max(0, Math.min(255, (n & 255) + amt))
  return `rgb(${r},${g},${b})`
}

/** 事件定位针：外圈等级色环 + 类型色填充 + 类型图标 + 底部落点 */
export function eventIcon(
  type: EventType,
  severity: Severity,
  dim = false,
  quiet = false
): { key: string; canvas: HTMLCanvasElement } {
  const key = `ev|${type}|${severity}|${dim ? 1 : 0}|${quiet ? 1 : 0}`
  const hit = cache.get(key)
  if (hit) return { key, canvas: hit }

  const W = 76
  const H = 96
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const ctx = c.getContext('2d')
  if (!ctx) return { key, canvas: c }

  const typeColor = dim ? '#6b7c96' : quiet ? '#7c878f' : EVENT_TYPE_META[type].color
  const sevColor = dim ? '#56657c' : quiet ? '#879198' : SEVERITY_META[severity].color
  const cx = W / 2
  const cy = 36
  const R = 27

  ctx.globalAlpha = dim ? 0.65 : quiet ? 0.78 : 1

  // 落点光斑
  const g0 = ctx.createRadialGradient(cx, H - 8, 0, cx, H - 8, 14)
  g0.addColorStop(0, typeColor)
  g0.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g0
  ctx.beginPath()
  ctx.ellipse(cx, H - 8, 14, 6, 0, 0, Math.PI * 2)
  ctx.fill()

  // 针尖
  ctx.beginPath()
  ctx.moveTo(cx - 12, cy + R - 6)
  ctx.lineTo(cx, H - 9)
  ctx.lineTo(cx + 12, cy + R - 6)
  ctx.closePath()
  ctx.fillStyle = sevColor
  ctx.fill()

  // 外发光 + 等级色环
  ctx.save()
  ctx.shadowColor = typeColor
  ctx.shadowBlur = dim || quiet ? 0 : 14
  ctx.beginPath()
  ctx.arc(cx, cy, R, 0, Math.PI * 2)
  ctx.fillStyle = '#081226'
  ctx.fill()
  ctx.restore()
  ctx.lineWidth = quiet ? 2 : 4
  ctx.strokeStyle = sevColor
  ctx.beginPath()
  ctx.arc(cx, cy, R - 2, 0, Math.PI * 2)
  ctx.stroke()
  if (severity === 'critical' && !dim && !quiet) {
    ctx.lineWidth = 1.5
    ctx.strokeStyle = 'rgba(255,255,255,0.85)'
    ctx.beginPath()
    ctx.arc(cx, cy, R + 2.5, 0, Math.PI * 2)
    ctx.stroke()
  }

  // 类型色填充
  const g1 = ctx.createRadialGradient(cx - 6, cy - 8, 2, cx, cy, R - 5)
  g1.addColorStop(0, shade(typeColor.startsWith('#') ? typeColor : '#6b7c96', 60))
  g1.addColorStop(1, shade(typeColor.startsWith('#') ? typeColor : '#6b7c96', -70))
  ctx.fillStyle = g1
  ctx.beginPath()
  ctx.arc(cx, cy, R - 6, 0, Math.PI * 2)
  ctx.fill()

  // 图标
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  if (emojiSupported()) {
    ctx.font = `26px ${EMOJI_FONT}`
    ctx.fillText(EVENT_TYPE_META[type].icon, cx, cy + 2)
  } else {
    ctx.font = `bold 24px ${CJK_FONT}`
    ctx.fillStyle = '#ffffff'
    ctx.fillText(EVENT_GLYPH[type], cx, cy + 1)
  }

  cache.set(key, c)
  return { key, canvas: c }
}

/** 应急资源图标：圆角方块 + 类别色描边 */
export function poiIcon(kind: Poi['kind']): { key: string; canvas: HTMLCanvasElement } {
  const key = `poi|${kind}`
  const hit = cache.get(key)
  if (hit) return { key, canvas: hit }
  const S = 52
  const c = document.createElement('canvas')
  c.width = S
  c.height = S + 10
  const ctx = c.getContext('2d')
  if (!ctx) return { key, canvas: c }
  const color = POI_COLOR[kind] ?? '#4fc3f7'

  // 底部小三角
  ctx.beginPath()
  ctx.moveTo(S / 2 - 6, S - 4)
  ctx.lineTo(S / 2, S + 8)
  ctx.lineTo(S / 2 + 6, S - 4)
  ctx.fillStyle = color
  ctx.fill()

  ctx.save()
  ctx.shadowColor = color
  ctx.shadowBlur = 10
  roundRect(ctx, 5, 5, S - 10, S - 10, 9)
  ctx.fillStyle = 'rgba(8,18,38,0.95)'
  ctx.fill()
  ctx.restore()
  ctx.lineWidth = 3
  ctx.strokeStyle = color
  roundRect(ctx, 5, 5, S - 10, S - 10, 9)
  ctx.stroke()

  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  if (emojiSupported()) {
    ctx.font = `22px ${EMOJI_FONT}`
    ctx.fillText(POI_EMOJI[kind] ?? '📍', S / 2, S / 2 + 1)
  } else {
    ctx.font = `bold 20px ${CJK_FONT}`
    ctx.fillStyle = color
    ctx.fillText(POI_GLYPH[kind] ?? '点', S / 2, S / 2 + 1)
  }
  cache.set(key, c)
  return { key, canvas: c }
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
