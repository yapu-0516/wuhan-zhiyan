import { describe, expect, it } from 'vitest'
import {
  errMsg,
  fmtBytes,
  fmtCoord,
  fmtDuration,
  fmtNum,
  hexA,
  isCsvUrl,
  isImageUrl,
  parseTs,
  pct,
  pct100,
  relativeTime,
  shortTime,
  todayPrefix
} from '@/composables/pages/format'

const NOW = new Date('2026-03-18T12:00:00').getTime()

describe('时间解析与展示', () => {
  it('parseTs 支持后端墙上时间格式', () => {
    expect(parseTs('2026-03-18 10:30:00')?.getTime()).toBe(new Date('2026-03-18T10:30:00').getTime())
    expect(parseTs('bad')).toBeNull()
    expect(parseTs(null)).toBeNull()
  })

  it('relativeTime 覆盖刚刚 / 分钟 / 小时 / 天', () => {
    expect(relativeTime('2026-03-18 11:59:58', NOW)).toBe('刚刚')
    expect(relativeTime('2026-03-18 11:55:00', NOW)).toBe('5 分钟前')
    expect(relativeTime('2026-03-18 09:00:00', NOW)).toBe('3 小时前')
    expect(relativeTime('2026-03-16 12:00:00', NOW)).toBe('2 天前')
    expect(relativeTime(null, NOW)).toBe('—')
  })

  it('shortTime 同年省略年份', () => {
    const y = new Date().getFullYear()
    expect(shortTime(`${y}-03-18 10:30:00`)).toBe('03-18 10:30')
  })

  it('todayPrefix 输出日期前缀', () => {
    expect(todayPrefix(new Date('2026-01-02T03:04:05'))).toBe('2026-01-02')
  })
})

describe('数值格式化', () => {
  it('pct 处理非法值', () => {
    expect(pct(0.936)).toBe('94%')
    expect(pct(0.936, 1)).toBe('93.6%')
    expect(pct('abc')).toBe('—')
  })

  it('pct100 截断到 0~100', () => {
    expect(pct100(1.2)).toBe(100)
    expect(pct100(-0.2)).toBe(0)
    expect(pct100(0.456)).toBe(46)
  })

  it('fmtNum 自适应小数位', () => {
    expect(fmtNum(1234.56)).toBe('1,235')
    expect(fmtNum(12.345)).toBe('12.35')
    expect(fmtNum(Number.NaN)).toBe('—')
  })

  it('fmtDuration 分级展示', () => {
    expect(fmtDuration(850)).toBe('850 毫秒')
    expect(fmtDuration(1200)).toBe('1.2 秒')
    expect(fmtDuration(65000)).toBe('1 分 05 秒')
    expect(fmtDuration(-1)).toBe('—')
  })

  it('fmtBytes 按 1024 进制', () => {
    expect(fmtBytes(512)).toBe('512 B')
    expect(fmtBytes(1536)).toBe('1.5 KB')
    expect(fmtBytes(null)).toBe('—')
  })

  it('fmtCoord 固定小数位', () => {
    expect(fmtCoord(114.29551, 30.58952)).toBe('114.29551, 30.58952')
  })
})

describe('URL 与颜色工具', () => {
  it('识别图片 / CSV 链接', () => {
    expect(isImageUrl('https://x/a.JPG?t=1')).toBe(true)
    expect(isImageUrl('https://x/a.pdf')).toBe(false)
    expect(isCsvUrl('/files/a.csv?download=1')).toBe(true)
  })

  it('hexA 转 rgba', () => {
    expect(hexA('#4fc3f7', 0.5)).toBe('rgba(79, 195, 247, 0.5)')
    expect(hexA('not-a-color', 0.5)).toBe('not-a-color')
  })

  it('errMsg 兜底', () => {
    expect(errMsg(new Error('后端超时'))).toBe('后端超时')
    expect(errMsg('字符串错误')).toBe('字符串错误')
    expect(errMsg(null, '默认提示')).toBe('默认提示')
  })
})
